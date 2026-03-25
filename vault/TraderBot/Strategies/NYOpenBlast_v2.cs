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
    public class NYOpenBlast_v2 : Strategy
    {
        // ================================================================
        // NY Open Blast v2.0 - Counter-Move Entry
        //
        // INSIGHT CLAVE:
        //   Avg MAE = 97 ticks → el mercado SIEMPRE va ~97 ticks en contra
        //   antes de hacer el movimiento real al open.
        //
        // LOGICA:
        //   1. A las 9:29 determinamos la DIRECCION (pre-market + VWAP)
        //   2. InvertDirection=true → entramos CONTRA el pre-market
        //      (pre-market bajista → LONG, comprar el rebote matinal)
        //   3. AllowLong=true, AllowShort=false → solo el edge real
        //      Longs: PF 1.54 | Shorts: PF 0.72
        //   4. Esperamos counter-move antes de entrar (mejor precio)
        //   5. ForceExit a las 10:00 AM
        // ================================================================

        // === Timezone ===
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        // === VWAP manual ===
        private double cumTPV;
        private double cumVol;
        private double cumTPSqV;
        private double vwapValue;
        private double vwapStdDev;

        // === Indicadores ===
        private MACD macd;

        // ML Filter (ZMQ)
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        // === State machine del dia ===
        private enum DayState { Idle, WatchingCounterMove, InTrade, Done }
        private DayState dayState = DayState.Idle;

        private bool pendingLong;
        private double referencePrice;
        private double extremePrice;
        private bool breakevenSet;
        private string activeSignalName;

        // === Performance tracking ===
        private int lastTradeCount;
        private int consecutiveLosses;
        private int totalWins;
        private int totalLosses;
        private double cumulativePnL;
        private int skippedToday;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"NY Open Blast v2.0 - Compra el rebote matinal del MNQ";
                Name        = "NYOpenBlast_v2";
                Calculate   = Calculate.OnBarClose;
                EntriesPerDirection             = 1;
                EntryHandling                   = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy    = true;
                ExitOnSessionCloseSeconds       = 30;
                IsFillLimitOnTouch              = false;
                MaximumBarsLookBack             = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution             = OrderFillResolution.Standard;
                Slippage                        = 2;
                StartBehavior                   = StartBehavior.WaitUntilFlat;
                TimeInForce                     = TimeInForce.Gtc;
                TraceOrders                     = false;
                RealtimeErrorHandling           = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling              = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade             = 60;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. TIMING (siempre en hora ET — GetEtTime() maneja la conversion) ===
                DirectionTime       = 92900;    // 9:29 ET — NY open
                EntryDeadlineTime   = 94500;    // 9:45 ET
                ForceExitTime       = 100000;   // 10:00 ET

                // === 1b. TENDENCIA PRE-MARKET ===
                TrendLookbackBars = 28;         // 28 barras de 1M — confirmado 24/02/2026

                // === 2. COUNTER-MOVE ===
                MinCounterMoveTicks     = 10;   // Minimo de ticks para esperar
                EnterWithoutCounterMove = true; // Entrar al deadline si no hubo movimiento

                // === 3. VWAP ===
                NearVWAPThreshold = 1.0;
                FarVWAPThreshold  = 2.0;

                // === 4. MACD ===
                // MACD 10/22 mas rapido que el clasico 12/26 → mejor señal al open
                InvertDirection = true;         // CONTRA el pre-market (edge real)
                UseMACDFilter   = true;         // ON: pre-market bajista Y MACD bajista → solo los mejores dias
                MACDFast        = 10;           // Optimizado: 10/22 > 12/26 para el open
                MACDSlow        = 22;
                MACDSignal      = 9;

                // === 4b. FILTRO DE DIRECCION ===
                // LONGS: PF 1.90 | Sortino 1.37 | R²=0.93 (4 años) ← EDGE VALIDADO
                // Shorts: pendiente de optimizacion
                AllowLong  = true;
                AllowShort = false;

                // === 5. TARGET / STOP ===
                // Target=450 es el sweet spot (T400→PF1.87, T450→PF1.90, T500→PF1.87)
                // El time exit a 10:30 es el mecanismo principal; target es techo de ganancia
                TargetTicks = 450;              // Sweet spot validado en 4 años
                StopTicks   = 100;              // 10 contratos × $50/ct = $500/trade riesgo
                // EV = 0.4715 × $996 - 0.5285 × $478 = +$218/trade (4 años)

                // === 6. BREAKEVEN ===
                UseBreakeven         = false;   // OFF: el time exit maneja la salida, breakeven interfiere
                BreakevenTriggerTicks = 60;

                // === 7. SIZING ===
                MaxDrawdownLimit = 7500;        // Apex $300K max drawdown
                SurvivalTrades   = 20;          // $7500/20 = $375/trade (conservador)

                // === 8. DEBUG ===
                DebugMode = true;

                // === 9. ML FILTER ===
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                macd = MACD(MACDFast, MACDSlow, MACDSignal);

                lastTradeCount    = 0;
                consecutiveLosses = 0;
                totalWins         = 0;
                totalLosses       = 0;
                cumulativePnL     = 0;
                dayState          = DayState.Idle;

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("NYBlast ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("NYBlast ML: Error al conectar ZMQ: {0}", ex.Message));
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
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // === VWAP: Reset al inicio de sesion ===
            if (Bars.IsFirstBarOfSession)
            {
                cumTPV       = 0;
                cumVol       = 0;
                cumTPSqV     = 0;
                dayState     = DayState.Idle;
                skippedToday = 0;
            }

            // === VWAP: Acumular datos ===
            if (Volume[0] > 0)
            {
                double tp = (High[0] + Low[0] + Close[0]) / 3.0;
                cumTPV   += tp * Volume[0];
                cumVol   += Volume[0];
                cumTPSqV += tp * tp * Volume[0];
            }

            if (cumVol > 0)
            {
                vwapValue = cumTPV / cumVol;
                double variance = (cumTPSqV / cumVol) - (vwapValue * vwapValue);
                vwapStdDev = Math.Sqrt(Math.Max(variance, 0));
            }

            // Tiempo en ET — funciona en backtest (Time[0] ya es ET en CME) y en live (UTC→ET)
            int timeNow = GetEtTime();

            // ================================================================
            // STATE MACHINE
            // ================================================================
            switch (dayState)
            {
                case DayState.Idle:
                    // >= en lugar de == para evitar perder el bar en live trading
                    if (timeNow >= DirectionTime && timeNow < EntryDeadlineTime)
                        DetermineDirection();
                    break;

                case DayState.WatchingCounterMove:
                    if (Position.MarketPosition != MarketPosition.Flat)
                    {
                        ManagePosition(timeNow);
                        dayState = DayState.InTrade;
                        break;
                    }

                    // Actualizar extremo del counter-move
                    if (pendingLong)
                        extremePrice = Math.Min(extremePrice, Close[0]);
                    else
                        extremePrice = Math.Max(extremePrice, Close[0]);

                    double counterMoveTicks = Math.Abs(extremePrice - referencePrice) / TickSize;

                    if (counterMoveTicks >= MinCounterMoveTicks)
                    {
                        if (DebugMode)
                            Print(string.Format("  Counter-move: {0:F0} ticks | Ref={1:F2} Extreme={2:F2}",
                                counterMoveTicks, referencePrice, extremePrice));
                        ExecuteEntry("COUNTER_MOVE");
                        dayState = DayState.InTrade;
                        break;
                    }

                    if (timeNow >= EntryDeadlineTime)
                    {
                        if (EnterWithoutCounterMove)
                        {
                            if (DebugMode)
                                Print(string.Format("  DEADLINE ({0:F0} ticks) → ENTRANDO",
                                    counterMoveTicks));
                            ExecuteEntry("NO_COUNTER");
                            dayState = DayState.InTrade;
                        }
                        else
                        {
                            if (DebugMode)
                                Print(string.Format("  DEADLINE ({0:F0} ticks) → SKIP", counterMoveTicks));
                            dayState = DayState.Done;
                            skippedToday++;
                        }
                    }
                    break;

                case DayState.InTrade:
                    ManagePosition(timeNow);
                    break;

                case DayState.Done:
                    break;
            }
        }

        // ================================================================
        // TIEMPO EN ET — consistente en backtest y live trading
        // Backtest: Time[0] ya está en ET (CME exchange time)
        // Live (CR): DateTime.UtcNow convertido a ET explícitamente
        // ================================================================
        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        // ================================================================
        // DETERMINAR DIRECCION (a las 9:29)
        // ================================================================
        private void DetermineDirection()
        {
            if (vwapStdDev <= 0 || cumVol <= 0)
            {
                if (DebugMode)
                    Print(string.Format("{0} | SKIP: VWAP no calculado", Time[0]));
                return;
            }

            // === TENDENCIA PRE-MARKET ===
            double preMarketMove   = Close[0] - Close[TrendLookbackBars];
            bool preMarketBullish  = preMarketMove > 0;

            // === POSICION VS VWAP ===
            double distanceFromVWAP  = Close[0] - vwapValue;
            double distanceInStdDev  = vwapStdDev > 0 ? Math.Abs(distanceFromVWAP) / vwapStdDev : 0;
            string mode;

            bool directionLong;
            if (distanceInStdDev >= FarVWAPThreshold)
            {
                mode          = "REV";
                directionLong = distanceFromVWAP < 0;   // Abajo del VWAP → LONG
            }
            else
            {
                mode          = distanceInStdDev <= NearVWAPThreshold ? "AMP" : "MID";
                directionLong = preMarketBullish;
            }

            // === FILTRO MACD ===
            if (UseMACDFilter)
            {
                bool macdBullish = macd.Diff[0] > 0;
                bool macdAligned = (directionLong && macdBullish) || (!directionLong && !macdBullish);

                if (!macdAligned)
                {
                    if (DebugMode)
                        Print(string.Format("{0} | SKIP: MACD no confirma | Dir={1} Hist={2:F4}",
                            Time[0], directionLong ? "LONG" : "SHORT", macd.Diff[0]));
                    dayState = DayState.Done;
                    return;
                }
            }

            // === INVERTIR DIRECCION ===
            if (InvertDirection)
                directionLong = !directionLong;

            // === FILTRO DE DIRECCION ===
            if (directionLong && !AllowLong)
            {
                if (DebugMode)
                    Print(string.Format("{0} | SKIP: LONG filtrado (AllowLong=false)", Time[0]));
                dayState = DayState.Done;
                return;
            }
            if (!directionLong && !AllowShort)
            {
                if (DebugMode)
                    Print(string.Format("{0} | SKIP: SHORT filtrado (AllowShort=false)", Time[0]));
                dayState = DayState.Done;
                return;
            }

            // === GUARDAR ESTADO ===
            pendingLong    = directionLong;
            referencePrice = Close[0];
            extremePrice   = Close[0];
            dayState       = DayState.WatchingCounterMove;

            if (DebugMode)
                Print(string.Format("{0} | DIR: {1} | Mode={2} | Ref={3:F2} | VWAP={4:F2} ({5:F1}σ) | Hist={6:F4} | PreMkt={7:F2}",
                    Time[0], pendingLong ? "LONG" : "SHORT", mode, referencePrice,
                    vwapValue, distanceInStdDev, macd.Diff[0], preMarketMove));
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

                mlTradeId = string.Format("NYBLAST_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"NYOpenBlast_v2\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":50.0,\"adx\":25.0," +
                    "\"vol_ratio\":1.0,\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{2},\"minute\":{3},\"day_of_week\":{4},\"signal_type\":{5}}}",
                    mlTradeId, direction, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("NYBlast ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (!allow) Print(string.Format("NYBlast ML bloqueado [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("NYBlast ML Error: {0} — permitiendo trade", ex.Message));
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
                    "{{\"type\":\"outcome\",\"strategy\":\"NYOpenBlast_v2\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("NYBlast ML outcome error: {0}", ex.Message)); }
        }

        // ================================================================
        // EJECUTAR ENTRADA
        // ================================================================
        private void ExecuteEntry(string reason)
        {
            int contracts   = CalculateContracts();
            double tickValue = TickSize * Instrument.MasterInstrument.PointValue;

            // ML gate
            if (UseMLFilter && !QueryMLFilter(pendingLong ? 1 : -1, 0)) return;

            if (pendingLong)
            {
                activeSignalName  = "BLAST_LONG";
                double stopPrice  = Close[0] - (StopTicks   * TickSize);
                double targetPrice = Close[0] + (TargetTicks * TickSize);

                EnterLong(contracts, activeSignalName);
                SetStopLoss(activeSignalName, CalculationMode.Price, stopPrice, false);
                SetProfitTarget(activeSignalName, CalculationMode.Price, targetPrice);
                breakevenSet = false;

                if (DebugMode)
                    Print(string.Format("*** BLAST LONG [{0}] {1}ct @ {2:F2} | Stop={3:F2} (-{4}tk=${5:F0}) | Tgt={6:F2} (+{7}tk=${8:F0}) | DesdeRef={9:F0}tk ***",
                        reason, contracts, Close[0],
                        stopPrice, StopTicks, StopTicks * tickValue * contracts,
                        targetPrice, TargetTicks, TargetTicks * tickValue * contracts,
                        (referencePrice - Close[0]) / TickSize));
            }
            else
            {
                activeSignalName  = "BLAST_SHORT";
                double stopPrice  = Close[0] + (StopTicks   * TickSize);
                double targetPrice = Close[0] - (TargetTicks * TickSize);

                EnterShort(contracts, activeSignalName);
                SetStopLoss(activeSignalName, CalculationMode.Price, stopPrice, false);
                SetProfitTarget(activeSignalName, CalculationMode.Price, targetPrice);
                breakevenSet = false;

                if (DebugMode)
                    Print(string.Format("*** BLAST SHORT [{0}] {1}ct @ {2:F2} | Stop={3:F2} (-{4}tk=${5:F0}) | Tgt={6:F2} (+{7}tk=${8:F0}) | DesdeRef={9:F0}tk ***",
                        reason, contracts, Close[0],
                        stopPrice, StopTicks, StopTicks * tickValue * contracts,
                        targetPrice, TargetTicks, TargetTicks * tickValue * contracts,
                        (Close[0] - referencePrice) / TickSize));
            }
        }

        // ================================================================
        // GESTION DE POSICION
        // ================================================================
        private void ManagePosition(int timeNow)
        {
            if (Position.MarketPosition == MarketPosition.Flat)
            {
                dayState = DayState.Done;
                return;
            }

            // Salida forzada por tiempo
            if (timeNow >= ForceExitTime)
            {
                if (Position.MarketPosition == MarketPosition.Long)
                    ExitLong("TIME_EXIT", activeSignalName);
                else if (Position.MarketPosition == MarketPosition.Short)
                    ExitShort("TIME_EXIT", activeSignalName);

                if (DebugMode)
                    Print(string.Format("  TIME EXIT @ {0}", Time[0]));
                return;
            }

            // Breakeven
            if (!UseBreakeven || breakevenSet)
                return;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double ticks = (Close[0] - Position.AveragePrice) / TickSize;
                if (ticks >= BreakevenTriggerTicks)
                {
                    SetStopLoss(activeSignalName, CalculationMode.Price, Position.AveragePrice, false);
                    breakevenSet = true;
                    if (DebugMode)
                        Print(string.Format("  BREAKEVEN @ {0:F2} (+{1:F0}tk)", Close[0], ticks));
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double ticks = (Position.AveragePrice - Close[0]) / TickSize;
                if (ticks >= BreakevenTriggerTicks)
                {
                    SetStopLoss(activeSignalName, CalculationMode.Price, Position.AveragePrice, false);
                    breakevenSet = true;
                    if (DebugMode)
                        Print(string.Format("  BREAKEVEN @ {0:F2} (+{1:F0}tk)", Close[0], ticks));
                }
            }
        }

        // ================================================================
        // POSITION SIZING
        // ================================================================
        private int CalculateContracts()
        {
            double tickValue              = TickSize * Instrument.MasterInstrument.PointValue;
            double stopDollarsPerContract = StopTicks * tickValue;

            if (stopDollarsPerContract <= 0) return 1;

            double riskPerTrade = MaxDrawdownLimit / SurvivalTrades;
            int contracts       = (int)Math.Floor(riskPerTrade / stopDollarsPerContract);

            if (DebugMode)
                Print(string.Format("  SIZING: ${0:F0}/{1}=${2:F0}/trade | Stop=${3:F2}/ct | Contracts={4}",
                    MaxDrawdownLimit, SurvivalTrades, riskPerTrade, stopDollarsPerContract, contracts));

            return Math.Max(1, contracts);
        }

        // ================================================================
        // P&L TRACKING
        // ================================================================
        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            if (marketPosition == MarketPosition.Flat)
            {
                int currentTradeCount = SystemPerformance.AllTrades.Count;
                if (currentTradeCount > lastTradeCount)
                {
                    Trade lastTrade   = SystemPerformance.AllTrades[currentTradeCount - 1];
                    double tradePnL   = lastTrade.ProfitCurrency;
                    cumulativePnL    += tradePnL;

                    if (tradePnL >= 0)
                    {
                        totalWins++;
                        consecutiveLosses = 0;
                    }
                    else
                    {
                        totalLosses++;
                        consecutiveLosses++;
                    }

                    lastTradeCount = currentTradeCount;
                    dayState       = DayState.Done;

                    // ML outcome
                    if (UseMLFilter) LogMLOutcome(tradePnL);

                    if (DebugMode)
                    {
                        int total  = totalWins + totalLosses;
                        double wr  = total > 0 ? (double)totalWins / total * 100.0 : 0;
                        Print(string.Format("  RESULTADO: ${0:F2} | Acum: ${1:F2} | WR: {2:F0}% ({3}W/{4}L) | Skip={5}",
                            tradePnL, cumulativePnL, wr, totalWins, totalLosses, skippedToday));
                    }
                }
            }
        }

        #region Properties

        // === 1. TIMING ===
        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Direction Time (HHMMSS)", Order = 1, GroupName = "1. Timing")]
        public int DirectionTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Entry Deadline (HHMMSS)", Order = 2, GroupName = "1. Timing")]
        public int EntryDeadlineTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Force Exit Time (HHMMSS)", Order = 3, GroupName = "1. Timing")]
        public int ForceExitTime { get; set; }

        [NinjaScriptProperty]
        [Range(5, 120)]
        [Display(Name = "Trend Lookback (barras 1M)", Order = 4, GroupName = "1. Timing")]
        public int TrendLookbackBars { get; set; }

        // === 2. COUNTER-MOVE ===
        [NinjaScriptProperty]
        [Range(10, 300)]
        [Display(Name = "Min Counter-Move (ticks)", Order = 1, GroupName = "2. Counter-Move")]
        public int MinCounterMoveTicks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Entrar sin counter-move", Order = 2, GroupName = "2. Counter-Move")]
        public bool EnterWithoutCounterMove { get; set; }

        // === 3. VWAP ===
        [NinjaScriptProperty]
        [Range(0.1, 3.0)]
        [Display(Name = "Near VWAP (σ)", Order = 1, GroupName = "3. VWAP")]
        public double NearVWAPThreshold { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name = "Far VWAP (σ)", Order = 2, GroupName = "3. VWAP")]
        public double FarVWAPThreshold { get; set; }

        // === 4. MACD ===
        [NinjaScriptProperty]
        [Display(Name = "Invertir Direccion", Order = 0, GroupName = "4. MACD")]
        public bool InvertDirection { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro MACD", Order = 1, GroupName = "4. MACD")]
        public bool UseMACDFilter { get; set; }

        [NinjaScriptProperty]
        [Range(3, 30)]
        [Display(Name = "MACD Fast", Order = 2, GroupName = "4. MACD")]
        public int MACDFast { get; set; }

        [NinjaScriptProperty]
        [Range(10, 60)]
        [Display(Name = "MACD Slow", Order = 3, GroupName = "4. MACD")]
        public int MACDSlow { get; set; }

        [NinjaScriptProperty]
        [Range(3, 20)]
        [Display(Name = "MACD Signal", Order = 4, GroupName = "4. MACD")]
        public int MACDSignal { get; set; }

        // === 4b. FILTRO DE DIRECCION ===
        [NinjaScriptProperty]
        [Display(Name = "Allow Long", Order = 1, GroupName = "4b. Direction Filter")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", Order = 2, GroupName = "4b. Direction Filter")]
        public bool AllowShort { get; set; }

        // === 5. TARGET / STOP ===
        [NinjaScriptProperty]
        [Range(30, 500)]
        [Display(Name = "Target (ticks)", Order = 1, GroupName = "5. Target-Stop")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(10, 500)]
        [Display(Name = "Stop Loss (ticks)", Order = 2, GroupName = "5. Target-Stop")]
        public int StopTicks { get; set; }

        // === 6. BREAKEVEN ===
        [NinjaScriptProperty]
        [Display(Name = "Usar Breakeven", Order = 1, GroupName = "6. Breakeven")]
        public bool UseBreakeven { get; set; }

        [NinjaScriptProperty]
        [Range(10, 300)]
        [Display(Name = "Breakeven Trigger (ticks)", Order = 2, GroupName = "6. Breakeven")]
        public int BreakevenTriggerTicks { get; set; }

        // === 7. SIZING ===
        [NinjaScriptProperty]
        [Range(500, 100000)]
        [Display(Name = "Max Drawdown Limit ($)", Order = 1, GroupName = "7. Sizing")]
        public double MaxDrawdownLimit { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "Trades de Supervivencia", Order = 2, GroupName = "7. Sizing")]
        public int SurvivalTrades { get; set; }

        // === 8. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name = "Debug Mode", Order = 1, GroupName = "8. Debug")]
        public bool DebugMode { get; set; }

        // === 9. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML (ZMQ)", Order = 1, GroupName = "9. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name = "Puerto Python (meta_brain.py)", Order = 2, GroupName = "9. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
