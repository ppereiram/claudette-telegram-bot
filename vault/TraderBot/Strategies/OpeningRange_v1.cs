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
// ZMQ (NetMQ) — solo se usa cuando UseMLFilter = true
using NetMQ;
using NetMQ.Sockets;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    // ====================================================================
    // OpeningRange_v1
    //
    // Concepto:
    //   La primera vela(s) del open de NYSE (9:30 AM) forma el
    //   "Opening Range" (OR) — una caja con MAXIMO y MINIMO que
    //   actuan como niveles estrategicos para el resto del dia.
    //
    // Logica:
    //   TENDENCIA BAJISTA -> SELL en MAX del OR (resistencia)
    //     "El mercado no volvera a ese nivel por un buen rato"
    //   TENDENCIA ALCISTA -> BUY en MIN del OR (soporte)
    //     "El mercado usara ese piso para impulsarse al alza"
    //
    // Filtro de tendencia: EMA sobre barras de 15-min (serie secundaria)
    //   Captura el contexto de Londres + pre-open USA automaticamente.
    //
    // Riesgo: Stop 200 ticks, Target DINAMICO = N x ancho del OR (default 2x)
    // Frecuencia: 1 trade/dia maximo
    // Chart: 5-min MNQ
    // ====================================================================
    public class OpeningRange_v1 : Strategy
    {
        // === TIMEZONE ===
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        // === OR LEVELS ===
        private double orHigh;
        private double orLow;
        private bool   orEstablished;
        private int    orEndTimeHHMMSS;

        // === SESSION CONTROL ===
        private bool     tradedToday;
        private int      tradesHoy;
        private bool     beSet;
        private string   activeSignal;
        private DateTime lastSessionDate;
        private double   prevDayClose;
        private double   sessionOpenPrice;
        private bool     sessionOpenSet;

        // === DAILY P&L ===
        private double dailyPnL;
        private bool   maxLossHit;

        // === INDICADORES ===
        private EMA emaTrend;

        // ML Filter (ZMQ)
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Name        = "OpeningRange_v1";
                Description = "Opening Range — BUY en MIN o SELL en MAX del OR segun tendencia de 15-min";
                Calculate   = Calculate.OnBarClose;

                EntriesPerDirection                       = 1;
                EntryHandling                             = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy              = true;
                ExitOnSessionCloseSeconds                 = 30;
                StopTargetHandling                        = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                       = 25;
                Slippage                                  = 1;
                StartBehavior                             = StartBehavior.WaitUntilFlat;
                TimeInForce                               = TimeInForce.Gtc;
                MaximumBarsLookBack                       = MaximumBarsLookBack.TwoHundredFiftySix;
                TraceOrders                               = false;
                RealtimeErrorHandling                     = RealtimeErrorHandling.StopCancelClose;
                IsInstantiatedOnEachOptimizationIteration = true;

                // 1. OPENING RANGE (hora CR = ET - 1h en EST)
                ORMinutos         = 15;
                SessionOpenTime   = 83000;  // 8:30 CR = 9:30 ET en EST

                // 2. TENDENCIA
                TrendEMAPeriod    = 9;
                UseGapFilter      = true;
                GapMinPoints      = 5.0;

                // 3. ENTRADA
                EntryDeadlineTime = 120000;  // 12:00 CR = 13:00 ET en EST
                ORBreakoutBuffer  = 15;

                // 4. RIESGO
                Contratos         = 1;
                StopTicks         = 150;   // confirmado (no 200)
                TargetORMultiple  = 3.0;   // confirmado (no 2.0) — Target = 3 x ancho OR
                MinTargetTicks    = 100;   // confirmado
                MaxTradesPerDay   = 1;
                MaxDailyLoss      = 0;

                // 5. BREAKEVEN
                UseBreakeven      = true;
                BreakevenTicks    = 100;   // confirmado (no 150)

                // 6. SALIDA
                ForceExitTime     = 143000;  // 14:30 CR = 15:30 ET en EST

                // 7. DIRECCION
                AllowLong         = true;
                AllowShort        = true;

                // 8. DEBUG
                DebugMode         = false;

                // 9. ML FILTER
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.Configure)
            {
                AddDataSeries(BarsPeriodType.Minute, 15);
            }
            else if (State == State.DataLoaded)
            {
                emaTrend = EMA(BarsArray[1], TrendEMAPeriod);

                int h = SessionOpenTime / 10000;
                int m = (SessionOpenTime / 100) % 100;
                m += ORMinutos;
                h += m / 60;
                m  = m % 60;
                orEndTimeHHMMSS = h * 10000 + m * 100;

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("OR ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("OR ML: Error al conectar ZMQ: {0}", ex.Message));
                        mlSocket = null;
                    }
                }
            }
            else if (State == State.Terminated)
            {
                if (mlSocket != null)
                {
                    try { mlSocket.Dispose(); NetMQConfig.Cleanup(); } catch { }
                    mlSocket = null;
                }
            }
        }

        protected override void OnBarUpdate()
        {
            if (BarsInProgress != 0) return;
            if (CurrentBar < BarsRequiredToTrade) return;

            // Tiempo ET — consistente en backtest y live (GetEtTime() maneja la conversion)
            int t = GetEtTime();

            // RESET DIARIO
            if (Time[0].Date != lastSessionDate)
            {
                lastSessionDate  = Time[0].Date;
                orHigh           = double.MinValue;
                orLow            = double.MaxValue;
                orEstablished    = false;
                tradedToday      = false;
                tradesHoy        = 0;
                beSet            = false;
                dailyPnL         = 0;
                maxLossHit       = false;
                sessionOpenSet   = false;
                prevDayClose     = CurrentBar > 0 ? Close[1] : Close[0];

                if (DebugMode)
                    Print(string.Format("=== NUEVA SESION: {0} | PrevClose={1:F2} ===",
                        Time[0].Date.ToShortDateString(), prevDayClose));
            }

            // Capturar precio de apertura
            if (!sessionOpenSet && t >= SessionOpenTime)
            {
                sessionOpenPrice = Open[0];
                sessionOpenSet   = true;
                if (DebugMode)
                    Print(string.Format("{0} | APERTURA={1:F2} | Gap={2:+0.00;-0.00} pts",
                        Time[0].ToShortTimeString(), sessionOpenPrice, sessionOpenPrice - prevDayClose));
            }

            // SALIDA FORZADA POR TIEMPO
            if (Position.MarketPosition != MarketPosition.Flat && t >= ForceExitTime)
            {
                if (Position.MarketPosition == MarketPosition.Long)
                    ExitLong("TIME_EXIT", activeSignal);
                else if (Position.MarketPosition == MarketPosition.Short)
                    ExitShort("TIME_EXIT", activeSignal);
                return;
            }

            // GESTIONAR POSICION ABIERTA
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageBreakeven();
                return;
            }

            // GUARDS
            if (maxLossHit)                   return;
            if (tradesHoy >= MaxTradesPerDay) return;
            if (!sessionOpenSet)              return;
            if (t < SessionOpenTime)          return;
            if (t >= EntryDeadlineTime)       return;

            // CONSTRUIR OPENING RANGE
            if (!orEstablished)
            {
                if (t < orEndTimeHHMMSS)
                {
                    orHigh = Math.Max(orHigh, High[0]);
                    orLow  = Math.Min(orLow,  Low[0]);
                    return;
                }
                else
                {
                    orHigh = Math.Max(orHigh, High[0]);
                    orLow  = Math.Min(orLow,  Low[0]);
                    orEstablished = true;

                    Draw.HorizontalLine(this, "OR_HIGH", false, orHigh, Brushes.Cyan,
                        DashStyleHelper.Dot, 1);
                    Draw.HorizontalLine(this, "OR_LOW", false, orLow, Brushes.Cyan,
                        DashStyleHelper.Dot, 1);

                    Print(string.Format("{0} | OR ESTABLECIDO | H={1:F2} L={2:F2} | Rango={3:F0} ticks",
                        Time[0].ToShortTimeString(), orHigh, orLow, (orHigh - orLow) / TickSize));
                }
                return;
            }

            // BUSCAR ENTRADA
            BuscarEntrada(t);
        }

        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                int etTime  = GetEtTime();
                int hour    = etTime / 10000;
                int minute  = (etTime % 10000) / 100;
                int dow     = (int)Time[0].DayOfWeek;

                mlTradeId = string.Format("OR_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"OpeningRange_v1\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":50.0,\"adx\":25.0," +
                    "\"vol_ratio\":1.0,\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{2},\"minute\":{3},\"day_of_week\":{4},\"signal_type\":{5}}}",
                    mlTradeId, direction, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("OR ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (!allow) Print(string.Format("OR ML bloqueado [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("OR ML Error: {0} — permitiendo trade", ex.Message));
                return true;
            }
        }

        private void LogMLOutcome(double pnl)
        {
            if (mlSocket == null || string.IsNullOrEmpty(mlTradeId)) return;
            try
            {
                int result = pnl > 0 ? 1 : -1;
                string json = string.Format(
                    "{{\"type\":\"outcome\",\"strategy\":\"OpeningRange_v1\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("OR ML outcome error: {0}", ex.Message)); }
        }

        private void BuscarEntrada(int t)
        {
            if (emaTrend == null || emaTrend.Count == 0) return;

            double ema15    = emaTrend[0];
            bool bullish    = Close[0] > ema15;
            bool bearish    = Close[0] < ema15;

            double gap      = sessionOpenSet ? (sessionOpenPrice - prevDayClose) : 0;
            bool gapUp      = !UseGapFilter || gap   >=  GapMinPoints;
            bool gapDown    = !UseGapFilter || gap   <= -GapMinPoints;
            if (UseGapFilter && Math.Abs(gap) < GapMinPoints)
            { gapUp = true; gapDown = true; }

            double buf = ORBreakoutBuffer * TickSize;

            // Ancho del OR en ticks — base del target dinamico
            double orWidthTicks   = (orHigh - orLow) / TickSize;
            double dynTargetTicks = Math.Max(MinTargetTicks, TargetORMultiple * orWidthTicks);

            // BUY: precio retestea MINIMO del OR en tendencia ALCISTA
            if (AllowLong && bullish && gapUp)
            {
                bool tocaORLow    = Low[0]   <= orLow + buf;
                bool noRompioBajo = Low[0]   >= orLow - buf;
                bool cerroArriba  = Close[0] >= orLow - buf;

                if (tocaORLow && noRompioBajo && cerroArriba)
                {
                    double stopPrecio   = orLow - StopTicks     * TickSize;
                    double targetPrecio = orLow + dynTargetTicks * TickSize;
                    activeSignal = "OR_LONG";

                    // ML gate
                    if (UseMLFilter && !QueryMLFilter(1, 0)) return;

                    EnterLong(Contratos, activeSignal);
                    SetStopLoss(activeSignal,     CalculationMode.Price, stopPrecio,   false);
                    SetProfitTarget(activeSignal, CalculationMode.Price, targetPrecio);

                    tradesHoy++;
                    tradedToday = (tradesHoy >= MaxTradesPerDay);
                    beSet       = false;

                    Print(string.Format("{0} | *** OR LONG | ORlow={1:F2} | ORwidth={2:F0}tk | Target={3:F0}tk ({4:F1}x) | SL={5:F2} | TP={6:F2} | EMA15={7:F2} | Gap={8:+0.0;-0.0}",
                        Time[0].ToShortTimeString(), orLow, orWidthTicks, dynTargetTicks, TargetORMultiple, stopPrecio, targetPrecio, ema15, gap));
                }
            }
            // SELL: precio retestea MAXIMO del OR en tendencia BAJISTA
            else if (AllowShort && bearish && gapDown)
            {
                bool tocaORHigh      = High[0]  >= orHigh - buf;
                bool noRompioArriba  = High[0]  <= orHigh + buf;
                bool cerroBajo       = Close[0] <= orHigh + buf;

                if (tocaORHigh && noRompioArriba && cerroBajo)
                {
                    double stopPrecio   = orHigh + StopTicks     * TickSize;
                    double targetPrecio = orHigh - dynTargetTicks * TickSize;
                    activeSignal = "OR_SHORT";

                    // ML gate
                    if (UseMLFilter && !QueryMLFilter(-1, 0)) return;

                    EnterShort(Contratos, activeSignal);
                    SetStopLoss(activeSignal,     CalculationMode.Price, stopPrecio,   false);
                    SetProfitTarget(activeSignal, CalculationMode.Price, targetPrecio);

                    tradesHoy++;
                    tradedToday = (tradesHoy >= MaxTradesPerDay);
                    beSet       = false;

                    Print(string.Format("{0} | *** OR SHORT | ORhigh={1:F2} | ORwidth={2:F0}tk | Target={3:F0}tk ({4:F1}x) | SL={5:F2} | TP={6:F2} | EMA15={7:F2} | Gap={8:+0.0;-0.0}",
                        Time[0].ToShortTimeString(), orHigh, orWidthTicks, dynTargetTicks, TargetORMultiple, stopPrecio, targetPrecio, ema15, gap));
                }
            }

            if (DebugMode && CurrentBar % 6 == 0)
                Print(string.Format("{0} | OR H={1:F2} L={2:F2} | EMA15={3:F2} | {4} | Gap={5:+0.0;-0.0}",
                    Time[0].ToShortTimeString(), orHigh, orLow, ema15,
                    bullish ? "BULL" : bearish ? "BEAR" : "FLAT", gap));
        }

        private void ManageBreakeven()
        {
            if (!UseBreakeven || beSet) return;

            double beDist = BreakevenTicks * TickSize;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double profit = Close[0] - Position.AveragePrice;
                if (profit >= beDist)
                {
                    SetStopLoss(activeSignal, CalculationMode.Price,
                        Position.AveragePrice + TickSize, false);
                    beSet = true;
                    if (DebugMode)
                        Print(string.Format("{0} | BE LONG @ {1:F2} | +{2:F0} ticks",
                            Time[0].ToShortTimeString(), Position.AveragePrice, profit / TickSize));
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double profit = Position.AveragePrice - Close[0];
                if (profit >= beDist)
                {
                    SetStopLoss(activeSignal, CalculationMode.Price,
                        Position.AveragePrice - TickSize, false);
                    beSet = true;
                    if (DebugMode)
                        Print(string.Format("{0} | BE SHORT @ {1:F2} | +{2:F0} ticks",
                            Time[0].ToShortTimeString(), Position.AveragePrice, profit / TickSize));
                }
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition,
            string orderId, DateTime time)
        {
            if (MaxDailyLoss <= 0 || execution.Order == null) return;

            if (marketPosition == MarketPosition.Flat && SystemPerformance.AllTrades.Count > 0)
            {
                var last = SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1];
                if (last.Exit.Time.Date == time.Date)
                {
                    dailyPnL += last.ProfitCurrency;
                    if (dailyPnL <= -MaxDailyLoss)
                    {
                        maxLossHit = true;
                        Print(string.Format("*** OR: PERDIDA DIARIA MAXIMA ${0:F2} ***", dailyPnL));
                    }

                    // ML outcome
                    if (UseMLFilter) LogMLOutcome(last.ProfitCurrency);
                }
            }
        }

        #region Properties

        [NinjaScriptProperty]
        [Range(5, 60)]
        [Display(Name="OR Minutos (5 o 15)", Order=1, GroupName="1. Opening Range")]
        public int ORMinutos { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Session Open Time (HHMMSS)", Order=2, GroupName="1. Opening Range")]
        public int SessionOpenTime { get; set; }

        [NinjaScriptProperty]
        [Range(3, 50)]
        [Display(Name="EMA Periodo (barras de 15-min)", Order=1, GroupName="2. Tendencia")]
        public int TrendEMAPeriod { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Filtro Gap Pre-Market", Order=2, GroupName="2. Tendencia")]
        public bool UseGapFilter { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 100.0)]
        [Display(Name="Gap Minimo Significativo (puntos)", Order=3, GroupName="2. Tendencia")]
        public double GapMinPoints { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Deadline Entrada (HHMMSS)", Order=1, GroupName="3. Entrada")]
        public int EntryDeadlineTime { get; set; }

        [NinjaScriptProperty]
        [Range(1, 200)]
        [Display(Name="OR Breakout Buffer (ticks)", Order=2, GroupName="3. Entrada")]
        public int ORBreakoutBuffer { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name="Contratos", Order=1, GroupName="4. Riesgo")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(50, 2000)]
        [Display(Name="Stop Loss (ticks)", Order=2, GroupName="4. Riesgo")]
        public int StopTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name="Target = N x Ancho OR (dinamico)", Order=3, GroupName="4. Riesgo")]
        public double TargetORMultiple { get; set; }

        [NinjaScriptProperty]
        [Range(50, 1000)]
        [Display(Name="Target Minimo (ticks, si OR es pequeno)", Order=4, GroupName="4. Riesgo")]
        public int MinTargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5)]
        [Display(Name="Max Trades por Dia", Order=4, GroupName="4. Riesgo")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0, 10000)]
        [Display(Name="Max Perdida Diaria $ (0=OFF)", Order=5, GroupName="4. Riesgo")]
        public double MaxDailyLoss { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Usar Breakeven", Order=1, GroupName="5. Breakeven")]
        public bool UseBreakeven { get; set; }

        [NinjaScriptProperty]
        [Range(50, 1000)]
        [Display(Name="Breakeven Trigger (ticks)", Order=2, GroupName="5. Breakeven")]
        public int BreakevenTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Force Exit Time (HHMMSS)", Order=1, GroupName="6. Salida")]
        public int ForceExitTime { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Long", Order=1, GroupName="7. Direccion")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Short", Order=2, GroupName="7. Direccion")]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=1, GroupName="8. Debug")]
        public bool DebugMode { get; set; }

        // 9. ML FILTER
        [NinjaScriptProperty]
        [Display(Name="Activar Filtro ML (ZMQ)", Order=1, GroupName="9. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name="Puerto Python (meta_brain.py)", Order=2, GroupName="9. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
