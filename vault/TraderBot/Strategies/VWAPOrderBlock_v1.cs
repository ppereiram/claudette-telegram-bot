#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using System.Text;
using System.Threading.Tasks;
using System.Windows;
using System.Windows.Input;
using System.Windows.Media;
using System.Xml.Serialization;
using NinjaTrader.Cbi;
using NinjaTrader.Gui;
using NinjaTrader.Gui.Chart;
using NinjaTrader.Gui.SuperDom;
using NinjaTrader.Gui.Tools;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.Core.FloatingPoint;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.DrawingTools;
using NetMQ;
using NetMQ.Sockets;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    // ============================================================
    // VWAPOrderBlock_v1 — 5-min MNQ
    //
    // Concepto: Price Action puro (sin indicadores rezagados)
    //
    //   1. VWAP diario = referencia de precio justo institucional
    //      Las instituciones rebalancean inventario vs VWAP.
    //      Precio > VWAP = sesgo alcista | Precio < VWAP = sesgo bajista
    //
    //   2. Order Block = la última vela de consolidación antes de
    //      un impulso fuerte. Las instituciones dejaron órdenes
    //      sin completar ahí. Cuando el precio regresa, las
    //      completan y el precio vuelve a moverse.
    //
    //   3. Entrada: retroceso al OB en dirección del VWAP
    //      - OB bullish + precio > VWAP → LONG cuando precio toca la zona
    //      - OB bearish + precio < VWAP → SHORT cuando precio toca la zona
    //
    //   4. Stop: por debajo/arriba del OB + buffer
    //   5. Target: R:R fijo (default 2:1)
    //
    // Horario: Costa Rica (ET - 1h)
    //   Prime AM: 8:30-11:30 CR = 9:30-12:30 ET
    //   Prime PM: 12:30-14:30 CR = 13:30-15:30 ET
    // ============================================================
    public class VWAPOrderBlock_v1 : Strategy
    {
        // ===== TIMEZONE =====
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        // ===== CLASE INTERNA: ORDER BLOCK =====
        private class OBZone
        {
            public bool   IsBullish;
            public double OBHigh;
            public double OBLow;
            public int    BarCreated;
            public bool   Used;
            public string Tag;
        }

        // ===== VWAP MANUAL =====
        private double   vwapNum  = 0;
        private double   vwapDen  = 0;
        private double   vwapVal  = 0;
        private DateTime vwapDate = DateTime.MinValue;

        // ===== ORDER BLOCKS ACTIVOS =====
        private List<OBZone> activeOBs;

        // ===== INDICADORES =====
        private ATR atr;
        private SMA volSMA;

        // ===== ML FILTER =====
        private RequestSocket mlSocket     = null;
        private string        mlTradeId    = "";
        private string        mlEntryContext = "";

        // ===== CONTROL DE SESION =====
        private DateTime lastDate  = DateTime.MinValue;
        private double   dailyPnL  = 0;
        private int      tradesHoy = 0;
        private bool     stopHoy   = false;

        // ===== TRACKING TRADE ACTIVO =====
        private double entryPx   = 0;
        private double stopPx    = 0;
        private bool   beDone    = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "VWAP + Order Block v1 — 5 min MNQ | Price Action + Volume puro";
                Name        = "VWAPOrderBlock_v1";
                Calculate   = Calculate.OnBarClose;

                EntriesPerDirection                       = 1;
                EntryHandling                             = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy              = true;
                ExitOnSessionCloseSeconds                 = 30;
                StopTargetHandling                        = StopTargetHandling.PerEntryExecution;
                MaximumBarsLookBack                       = MaximumBarsLookBack.TwoHundredFiftySix;
                BarsRequiredToTrade                       = 20;
                Slippage                                  = 1;
                StartBehavior                             = StartBehavior.WaitUntilFlat;
                TimeInForce                               = TimeInForce.Gtc;
                TraceOrders                               = false;
                RealtimeErrorHandling                     = RealtimeErrorHandling.StopCancelClose;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. SIZING ===
                FixedContracts  = 1;
                MaxDailyLoss    = 200;
                MaxTradesPerDay = 3;

                // === 2. ORDER BLOCK ===
                OBMinATRMult = 2.0;   // confirmado (no 1.5)
                OBMaxAge     = 40;    // confirmado
                OBLookback   = 2;     // confirmado (no 5)
                ATRPeriod    = 7;     // confirmado (no 14)

                // === 3. GESTION TRADE ===
                StopBufferTicks = 5;    // confirmado (no 4)
                TargetRR        = 4.0;  // confirmado R:R=4 (no 2.0)
                BreakevenR      = 1.0;  // confirmado

                // === 4. FILTROS ===
                UseVWAPFilter = true;
                MinVolRatio   = 1.0;   // confirmado
                AllowLong     = true;
                AllowShort    = false;  // Longs PF=2.89 — shorts degradan y aumentan DD

                // === 5. HORARIO (siempre ET — GetEtTime() maneja backtest vs live) ===
                SessionOpenHHMMSS = 93000;   // 9:30 ET
                EntryDeadline     = 153000;  // 15:30 ET
                UsePrimeHours     = true;
                MorningStart      = 93000;   // 9:30 ET
                MorningEnd        = 123000;  // 12:30 ET
                AfternoonStart    = 133000;  // 13:30 ET
                AfternoonEnd      = 153000;  // 15:30 ET

                // === 6. DEBUG ===
                DebugMode = false;

                // === 7. ML FILTER ===
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                atr       = ATR(ATRPeriod);
                volSMA    = SMA(Volume, 20);
                activeOBs = new List<OBZone>();

                if (UseMLFilter)
                {
                    AsyncIO.ForceDotNet.Force();
                    mlSocket = new RequestSocket();
                    mlSocket.Connect("tcp://127.0.0.1:" + MLPort);
                    mlSocket.Options.SendTimeout    = TimeSpan.FromMilliseconds(400);
                    mlSocket.Options.ReceiveTimeout = TimeSpan.FromMilliseconds(400);
                }
            }
            else if (State == State.Terminated)
            {
                if (mlSocket != null) { try { mlSocket.Close(); } catch { } mlSocket = null; }
            }
        }

        // ============================================================
        // ML FILTER — consulta meta_brain.py via ZMQ
        // ============================================================
        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                mlTradeId = Guid.NewGuid().ToString("N").Substring(0, 8);
                DateTime et = State == State.Realtime
                    ? TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone)
                    : Time[0];
                double volRatio = (volSMA != null && volSMA[0] > 0) ? Volume[0] / volSMA[0] : 1.0;

                mlEntryContext = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"VWAPOrderBlock_v1\"," +
                    "\"trade_id\":\"{0}\",\"direction\":{1}," +
                    "\"rsi\":50.0,\"adx\":25.0,\"vol_ratio\":{2}," +
                    "\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{3},\"minute\":{4},\"day_of_week\":{5}," +
                    "\"signal_type\":{6}}}",
                    mlTradeId, direction,
                    volRatio.ToString("F3", System.Globalization.CultureInfo.InvariantCulture),
                    et.Hour, et.Minute, (int)et.DayOfWeek, signalType);

                mlSocket.SendFrame(mlEntryContext);
                string resp = mlSocket.ReceiveFrameString();

                int idx = resp.IndexOf("\"allow\":");
                if (idx >= 0)
                {
                    char c = resp[idx + 8];
                    return c == '1';
                }
                return true;
            }
            catch { return true; }
        }

        private void LogMLOutcome(double pnl)
        {
            if (mlSocket == null || mlTradeId == "") return;
            try
            {
                string msg = string.Format(
                    "{{\"type\":\"outcome\",\"strategy\":\"VWAPOrderBlock_v1\"," +
                    "\"trade_id\":\"{0}\",\"pnl\":{1}}}",
                    mlTradeId,
                    pnl.ToString("F2", System.Globalization.CultureInfo.InvariantCulture));
                mlSocket.SendFrame(msg);
                mlSocket.ReceiveFrameString();
                mlTradeId = "";
            }
            catch { mlTradeId = ""; }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < 20) return;

            // Tiempo ET — consistente en backtest y live (GetEtTime maneja la conversion)
            int t = GetEtTime();

            // ===== VWAP: reset en apertura de sesión =====
            if (Time[0].Date != vwapDate && t >= SessionOpenHHMMSS)
            {
                vwapNum  = 0;
                vwapDen  = 0;
                vwapDate = Time[0].Date;

                // Limpiar OBs y líneas del día anterior
                foreach (var ob in activeOBs)
                {
                    try { RemoveDrawObject(ob.Tag + "_H"); } catch { }
                    try { RemoveDrawObject(ob.Tag + "_L"); } catch { }
                }
                activeOBs.Clear();

                if (DebugMode)
                    Print(string.Format("=== VWAP RESET: {0} ===", Time[0].Date.ToShortDateString()));
            }

            // Acumular VWAP (precio típico × volumen)
            double tp = (High[0] + Low[0] + Close[0]) / 3.0;
            vwapNum  += tp * Volume[0];
            vwapDen  += Volume[0];
            vwapVal   = vwapDen > 0 ? vwapNum / vwapDen : tp;

            // ===== RESET DIARIO =====
            if (lastDate != Time[0].Date)
            {
                lastDate  = Time[0].Date;
                dailyPnL  = 0;
                tradesHoy = 0;
                stopHoy   = false;
            }

            // ===== CIRCUIT BREAKER =====
            if (stopHoy)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong("OBLong");
                    ExitShort("OBShort");
                }
                return;
            }

            // ===== DETECTAR NUEVOS ORDER BLOCKS =====
            DetectOBs();

            // ===== LIMPIAR OBs EXPIRADOS/INVÁLIDOS =====
            PurgeOBs();

            // ===== ROUTING PRINCIPAL =====
            if (Position.MarketPosition != MarketPosition.Flat)
                ManageTrade();
            else
                CheckEntries(t);
        }

        // ============================================================
        // TIEMPO EN ET — consistente en backtest y live trading
        // ============================================================
        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        // ============================================================
        // DETECCIÓN DE ORDER BLOCKS
        // ============================================================
        private void DetectOBs()
        {
            if (CurrentBar < OBLookback + 1) return;
            if (atr[0] <= 0) return;

            double minSize = OBMinATRMult * atr[0];

            // --- IMPULSO ALCISTA: body bullish >= minSize ---
            // El OB es la última vela bajista/doji antes del impulso
            double bullBody = Close[0] - Open[0];
            if (bullBody >= minSize && Volume[0] >= volSMA[0] * MinVolRatio)
            {
                for (int i = 1; i <= Math.Min(OBLookback, CurrentBar - 1); i++)
                {
                    if (Close[i] <= Open[i]) // bajista o doji
                    {
                        AddOB(true, High[i], Low[i]);
                        break;
                    }
                }
            }

            // --- IMPULSO BAJISTA: body bearish >= minSize ---
            // El OB es la última vela alcista/doji antes del impulso
            double bearBody = Open[0] - Close[0];
            if (bearBody >= minSize && Volume[0] >= volSMA[0] * MinVolRatio)
            {
                for (int i = 1; i <= Math.Min(OBLookback, CurrentBar - 1); i++)
                {
                    if (Close[i] >= Open[i]) // alcista o doji
                    {
                        AddOB(false, High[i], Low[i]);
                        break;
                    }
                }
            }
        }

        private void AddOB(bool isBull, double high, double low)
        {
            // No duplicar zonas ya conocidas
            foreach (var existing in activeOBs)
            {
                if (Math.Abs(existing.OBHigh - high) < TickSize * 4 &&
                    Math.Abs(existing.OBLow  - low)  < TickSize * 4)
                    return;
            }

            string tag = (isBull ? "OBBull_" : "OBBear_") + CurrentBar;

            activeOBs.Add(new OBZone
            {
                IsBullish  = isBull,
                OBHigh     = high,
                OBLow      = low,
                BarCreated = CurrentBar,
                Used       = false,
                Tag        = tag
            });

            // Visualización: líneas de la zona OB
            Brush color = isBull ? Brushes.LimeGreen : Brushes.Tomato;
            Draw.HorizontalLine(this, tag + "_H", high, color);
            Draw.HorizontalLine(this, tag + "_L", low,  color);

            if (DebugMode)
                Print(string.Format("{0} OB {1}: H={2:F2} L={3:F2}",
                    Time[0].ToShortTimeString(),
                    isBull ? "BULL" : "BEAR",
                    high, low));
        }

        // ============================================================
        // LIMPIAR OBs EXPIRADOS O INVALIDADOS
        // ============================================================
        private void PurgeOBs()
        {
            var toRemove = new List<OBZone>();

            foreach (var ob in activeOBs)
            {
                bool expired     = (CurrentBar - ob.BarCreated) > OBMaxAge;
                bool used        = ob.Used;
                bool invBull     = ob.IsBullish  && Close[0] < ob.OBLow  - atr[0] * 0.5;
                bool invBear     = !ob.IsBullish && Close[0] > ob.OBHigh + atr[0] * 0.5;

                if (expired || used || invBull || invBear)
                {
                    try { RemoveDrawObject(ob.Tag + "_H"); } catch { }
                    try { RemoveDrawObject(ob.Tag + "_L"); } catch { }
                    toRemove.Add(ob);
                }
            }

            foreach (var ob in toRemove)
                activeOBs.Remove(ob);
        }

        // ============================================================
        // BUSCAR ENTRADAS EN ORDER BLOCKS
        // ============================================================
        private void CheckEntries(int t)
        {
            if (tradesHoy >= MaxTradesPerDay) return;
            if (t >= EntryDeadline) return;

            if (UsePrimeHours)
            {
                bool am = (t >= MorningStart   && t <= MorningEnd);
                bool pm = (t >= AfternoonStart  && t <= AfternoonEnd);
                if (!am && !pm) return;
            }

            foreach (var ob in activeOBs)
            {
                if (ob.Used) continue;

                // === LONG: retroceso a OB bullish ===
                if (ob.IsBullish && AllowLong)
                {
                    // Precio "tocó" la zona OB pero cerró dentro o arriba (no rompió abajo)
                    bool inZone    = Low[0] <= ob.OBHigh && Close[0] >= ob.OBLow;
                    bool bullClose = Close[0] > Open[0];          // Confirmación: vela bullish
                    bool vwapOK    = !UseVWAPFilter || Close[0] > vwapVal;

                    if (inZone && bullClose && vwapOK)
                    {
                        double sl     = ob.OBLow - StopBufferTicks * TickSize;
                        double risk   = Close[0] - sl;
                        if (risk <= TickSize) continue;           // Riesgo mínimo razonable

                        double target = Close[0] + risk * TargetRR;

                        if (UseMLFilter && !QueryMLFilter(1, 0)) continue;
                        EnterLong(FixedContracts, "OBLong");
                        SetStopLoss("OBLong",     CalculationMode.Price, sl,     false);
                        SetProfitTarget("OBLong", CalculationMode.Price, target);

                        entryPx = Close[0];
                        stopPx  = sl;
                        beDone  = false;
                        ob.Used = true;

                        if (DebugMode)
                            Print(string.Format("{0} LONG @ {1:F2} | SL={2:F2} | TP={3:F2} | VWAP={4:F2} | OB={5:F2}-{6:F2}",
                                Time[0].ToShortTimeString(), Close[0], sl, target, vwapVal,
                                ob.OBLow, ob.OBHigh));
                        return; // Una sola entrada por barra
                    }
                }

                // === SHORT: retroceso a OB bearish ===
                if (!ob.IsBullish && AllowShort)
                {
                    bool inZone    = High[0] >= ob.OBLow && Close[0] <= ob.OBHigh;
                    bool bearClose = Close[0] < Open[0];          // Confirmación: vela bearish
                    bool vwapOK    = !UseVWAPFilter || Close[0] < vwapVal;

                    if (inZone && bearClose && vwapOK)
                    {
                        double sl     = ob.OBHigh + StopBufferTicks * TickSize;
                        double risk   = sl - Close[0];
                        if (risk <= TickSize) continue;

                        double target = Close[0] - risk * TargetRR;

                        if (UseMLFilter && !QueryMLFilter(-1, 0)) continue;
                        EnterShort(FixedContracts, "OBShort");
                        SetStopLoss("OBShort",     CalculationMode.Price, sl,     false);
                        SetProfitTarget("OBShort", CalculationMode.Price, target);

                        entryPx = Close[0];
                        stopPx  = sl;
                        beDone  = false;
                        ob.Used = true;

                        if (DebugMode)
                            Print(string.Format("{0} SHORT @ {1:F2} | SL={2:F2} | TP={3:F2} | VWAP={4:F2} | OB={5:F2}-{6:F2}",
                                Time[0].ToShortTimeString(), Close[0], sl, target, vwapVal,
                                ob.OBLow, ob.OBHigh));
                        return;
                    }
                }
            }
        }

        // ============================================================
        // GESTIÓN DEL TRADE ABIERTO
        // ============================================================
        private void ManageTrade()
        {
            if (stopPx == 0 || entryPx == 0) return;

            double risk = Math.Abs(entryPx - stopPx);
            if (risk <= 0) return;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double gain = Close[0] - entryPx;
                if (!beDone && gain >= risk * BreakevenR)
                {
                    beDone = true;
                    double newSL = entryPx + TickSize;
                    SetStopLoss("OBLong", CalculationMode.Price, newSL, false);
                    stopPx = newSL;
                    if (DebugMode)
                        Print(string.Format("{0} BE Long activado @ {1:F2}", Time[0].ToShortTimeString(), newSL));
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double gain = entryPx - Close[0];
                if (!beDone && gain >= risk * BreakevenR)
                {
                    beDone = true;
                    double newSL = entryPx - TickSize;
                    SetStopLoss("OBShort", CalculationMode.Price, newSL, false);
                    stopPx = newSL;
                    if (DebugMode)
                        Print(string.Format("{0} BE Short activado @ {1:F2}", Time[0].ToShortTimeString(), newSL));
                }
            }
        }

        // ============================================================
        // EJECUCIONES: TRACKING DE P&L DIARIO
        // ============================================================
        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition,
            string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            if (marketPosition == MarketPosition.Flat)
            {
                var all = SystemPerformance.AllTrades;
                if (all.Count > 0)
                {
                    double pnl = all[all.Count - 1].ProfitCurrency;
                    dailyPnL += pnl;
                    tradesHoy++;
                    if (UseMLFilter) LogMLOutcome(pnl);

                    if (DebugMode)
                        Print(string.Format("EXIT | P&L=${0:F2} | Diario=${1:F2} | Trades={2}/{3}",
                            pnl, dailyPnL, tradesHoy, MaxTradesPerDay));
                }

                entryPx = 0;
                stopPx  = 0;
                beDone  = false;

                if (dailyPnL <= -MaxDailyLoss)
                {
                    stopHoy = true;
                    Print(string.Format("VWAPOrderBlock: Max perdida diaria ${0:F2}. Deteniendo.", dailyPnL));
                }
            }
        }

        #region Properties

        // === 1. SIZING ===
        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Contratos MNQ", Order = 1, GroupName = "1. Sizing")]
        public int FixedContracts { get; set; }

        [NinjaScriptProperty]
        [Range(50, 5000)]
        [Display(Name = "Max Perdida Diaria ($)", Order = 2, GroupName = "1. Sizing")]
        public double MaxDailyLoss { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Max Trades / Dia", Order = 3, GroupName = "1. Sizing")]
        public int MaxTradesPerDay { get; set; }

        // === 2. ORDER BLOCK ===
        [NinjaScriptProperty]
        [Range(0.5, 5.0)]
        [Display(Name = "Impulso Min (x ATR)", Order = 1, GroupName = "2. Order Block")]
        public double OBMinATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name = "Edad Max OB (barras)", Order = 2, GroupName = "2. Order Block")]
        public int OBMaxAge { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Barras Lookback OB", Order = 3, GroupName = "2. Order Block")]
        public int OBLookback { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "ATR Period", Order = 4, GroupName = "2. Order Block")]
        public int ATRPeriod { get; set; }

        // === 3. GESTION TRADE ===
        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Stop Buffer (ticks)", Order = 1, GroupName = "3. Trade Mgmt")]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 6.0)]
        [Display(Name = "Target R:R", Order = 2, GroupName = "3. Trade Mgmt")]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 3.0)]
        [Display(Name = "Breakeven (x R)", Order = 3, GroupName = "3. Trade Mgmt")]
        public double BreakevenR { get; set; }

        // === 4. FILTROS ===
        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro VWAP", Order = 1, GroupName = "4. Filtros")]
        public bool UseVWAPFilter { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 3.0)]
        [Display(Name = "Vol Min Impulso (x SMA)", Order = 2, GroupName = "4. Filtros")]
        public double MinVolRatio { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", Order = 3, GroupName = "4. Filtros")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", Order = 4, GroupName = "4. Filtros")]
        public bool AllowShort { get; set; }

        // === 5. HORARIO CR ===
        [NinjaScriptProperty]
        [Display(Name = "Session Open (HHMMSS)", Order = 1, GroupName = "5. Horario ET")]
        public int SessionOpenHHMMSS { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Entry Deadline (HHMMSS)", Order = 2, GroupName = "5. Horario ET")]
        public int EntryDeadline { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Solo Horas Prime", Order = 3, GroupName = "5. Horario ET")]
        public bool UsePrimeHours { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime AM Start (HHMMSS)", Order = 4, GroupName = "5. Horario ET")]
        public int MorningStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime AM End (HHMMSS)", Order = 5, GroupName = "5. Horario ET")]
        public int MorningEnd { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime PM Start (HHMMSS)", Order = 6, GroupName = "5. Horario ET")]
        public int AfternoonStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime PM End (HHMMSS)", Order = 7, GroupName = "5. Horario ET")]
        public int AfternoonEnd { get; set; }

        // === 6. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name = "Debug Mode", Order = 1, GroupName = "6. Debug")]
        public bool DebugMode { get; set; }

        // === 7. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML", Order = 1, GroupName = "7. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(1024, 65535)]
        [Display(Name = "Puerto ZMQ", Order = 2, GroupName = "7. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
