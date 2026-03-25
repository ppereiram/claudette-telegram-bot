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
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NYOpenBlast_v1 : Strategy
    {
        // ================================================================
        // NY Open Blast v1.0
        //
        // Concepto: El MNQ SIEMPRE mueve al menos 100 ticks en los
        // primeros minutos del open de NYSE. Esta estrategia se
        // posiciona 1 minuto antes (9:29 AM) en la direccion correcta
        // y captura ese movimiento.
        //
        // Dos modos de operacion:
        //   1. AMPLIFICACION: Precio cerca del VWAP (<1 std dev)
        //      → La direccion pre-market se amplifica al open
        //      → Entrar en la direccion del pre-market
        //
        //   2. REVERSION: Precio lejos del VWAP (>2 std dev)
        //      → Extension extrema buscara revertir al VWAP
        //      → Entrar contra la direccion actual (hacia VWAP)
        //
        // Money Management: Diseñado para 50/50 win rate con R:R > 1
        //   Target 100 ticks, Stop 75 ticks → R:R 1.33
        //   EV = 0.5 * 100 - 0.5 * 75 = +12.5 ticks/trade
        //   ~252 dias/año = +3,150 ticks/año
        //
        // IMPORTANTE: Usar chart de 1 MINUTO con sesion ETH (no RTH)
        // para que el VWAP tenga datos overnight.
        // ================================================================

        // === VWAP manual (no depende de indicador externo) ===
        private double cumTPV;
        private double cumVol;
        private double cumTPSqV;
        private double vwapValue;
        private double vwapStdDev;

        // === Indicadores ===
        private Stochastics stoch;

        // === Control de sesion ===
        private bool tradedToday;
        private bool breakevenSet;
        private string activeSignalName;

        // === Performance tracking ===
        private int lastTradeCount;
        private int consecutiveLosses;
        private int totalWins;
        private int totalLosses;
        private double cumulativePnL;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"NY Open Blast v1.0 - Captura los 100+ ticks del opening de NYSE";
                Name = "NYOpenBlast_v1";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 2;  // Mayor slippage por volatilidad de apertura
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 60;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === TIMING ===
                EntryTime = 92900;         // 9:29 AM ET (1 min antes del open)
                ForceExitTime = 100000;    // 10:00 AM (30 min max en trade)

                // === TENDENCIA PRE-MARKET ===
                TrendLookbackBars = 30;    // 30 min en chart 1M

                // === VWAP UMBRALES ===
                NearVWAPThreshold = 1.0;   // <1 std dev = amplificacion
                FarVWAPThreshold = 2.0;    // >2 std dev = reversion

                // === ESTOCASTICO ===
                UseStochFilter = true;
                StochPeriodK = 14;
                StochPeriodD = 3;
                StochSmooth = 3;
                StochOverbought = 80;
                StochOversold = 20;

                // === TARGET / STOP (en ticks) ===
                TargetTicks = 100;         // 25 pts MNQ = $50/ct
                StopTicks = 75;            // 18.75 pts MNQ = $37.50/ct
                // R:R = 100/75 = 1.33

                // === BREAKEVEN ===
                UseBreakeven = true;
                BreakevenTriggerTicks = 50; // A +50 ticks, mover stop a entry

                // === POSITION SIZING (cuenta fondeada) ===
                MaxDrawdownLimit = 7500;    // Apex $300K DD limit
                SurvivalTrades = 15;        // Sobrevivir 15 perdidas consecutivas

                // === DEBUG ===
                DebugMode = true;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                stoch = Stochastics(StochPeriodK, StochPeriodD, StochSmooth);

                lastTradeCount = 0;
                consecutiveLosses = 0;
                totalWins = 0;
                totalLosses = 0;
                cumulativePnL = 0;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // === VWAP: Reset al inicio de sesion ===
            if (Bars.IsFirstBarOfSession)
            {
                cumTPV = 0;
                cumVol = 0;
                cumTPSqV = 0;
                tradedToday = false;
            }

            // === VWAP: Acumular datos (solo si hay volumen) ===
            if (Volume[0] > 0)
            {
                double tp = (High[0] + Low[0] + Close[0]) / 3.0;
                cumTPV += tp * Volume[0];
                cumVol += Volume[0];
                cumTPSqV += tp * tp * Volume[0];
            }

            if (cumVol > 0)
            {
                vwapValue = cumTPV / cumVol;
                double variance = (cumTPSqV / cumVol) - (vwapValue * vwapValue);
                vwapStdDev = Math.Sqrt(Math.Max(variance, 0));
            }

            // === GESTION DE POSICION ABIERTA ===
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManagePosition();
                return;
            }

            // === ENTRADA: solo a la hora exacta, 1 vez por dia ===
            if (tradedToday)
                return;

            int timeNow = ToTime(Time[0]);
            if (timeNow != EntryTime)
                return;

            EvaluateAndEnter();
        }

        // ================================================================
        // LOGICA DE ENTRADA
        // ================================================================
        private void EvaluateAndEnter()
        {
            if (vwapStdDev <= 0 || cumVol <= 0)
            {
                if (DebugMode)
                    Print(string.Format("{0} | SKIP: VWAP no calculado (StdDev={1:F2}, Vol={2:F0})",
                        Time[0], vwapStdDev, cumVol));
                return;
            }

            // === TENDENCIA PRE-MARKET (ultimos 30 minutos) ===
            double preMarketMove = Close[0] - Close[TrendLookbackBars];
            bool preMarketBullish = preMarketMove > 0;

            // === DISTANCIA AL VWAP EN DESVIACIONES ESTANDAR ===
            double distanceFromVWAP = Close[0] - vwapValue;
            double distanceInStdDev = Math.Abs(distanceFromVWAP) / vwapStdDev;

            // === DETERMINAR MODO Y DIRECCION ===
            bool goLong = false;
            bool goShort = false;
            string mode;

            if (distanceInStdDev <= NearVWAPThreshold)
            {
                // MODO AMPLIFICACION: cerca del VWAP, la direccion se amplifica
                mode = "AMP";
                if (preMarketBullish)
                    goLong = true;
                else
                    goShort = true;
            }
            else if (distanceInStdDev >= FarVWAPThreshold)
            {
                // MODO REVERSION: lejos del VWAP, buscara revertir
                mode = "REV";
                if (distanceFromVWAP > 0)  // Precio MUY arriba del VWAP → short
                    goShort = true;
                else                        // Precio MUY abajo del VWAP → long
                    goLong = true;
            }
            else
            {
                // ZONA INTERMEDIA: usar direccion pre-market (sesgo amplificacion)
                mode = "MID";
                if (preMarketBullish)
                    goLong = true;
                else
                    goShort = true;
            }

            // === FILTRO ESTOCASTICO ===
            if (UseStochFilter)
            {
                double k = stoch.K[0];
                bool stochAllows = true;

                if (goLong)
                {
                    if (mode == "REV")
                        stochAllows = k < StochOversold;       // Reversion: debe estar sobrevendido
                    else
                        stochAllows = k < StochOverbought;     // Amp: no debe estar sobrecomprado
                }
                else if (goShort)
                {
                    if (mode == "REV")
                        stochAllows = k > StochOverbought;     // Reversion: debe estar sobrecomprado
                    else
                        stochAllows = k > StochOversold;       // Amp: no debe estar sobrevendido
                }

                if (!stochAllows)
                {
                    if (DebugMode)
                        Print(string.Format("{0} | SKIP: Stoch K={1:F0} no confirma {2} {3} | VWAP={4:F2} ({5:F1}σ)",
                            Time[0], k, mode, goLong ? "LONG" : "SHORT", vwapValue, distanceInStdDev));
                    tradedToday = true;  // No reintentar hoy
                    return;
                }
            }

            // === CALCULAR CONTRATOS ===
            int contracts = CalculateContracts();

            // === EJECUTAR ENTRADA ===
            double tickValue = TickSize * Instrument.MasterInstrument.PointValue;

            if (goLong)
            {
                activeSignalName = "BLAST_LONG";
                double stopPrice = Close[0] - (StopTicks * TickSize);
                double targetPrice = Close[0] + (TargetTicks * TickSize);

                EnterLong(contracts, activeSignalName);
                SetStopLoss(activeSignalName, CalculationMode.Price, stopPrice, false);
                SetProfitTarget(activeSignalName, CalculationMode.Price, targetPrice);

                tradedToday = true;
                breakevenSet = false;

                if (DebugMode)
                    Print(string.Format("*** BLAST LONG {0}ct @ {1:F2} | Stop: {2:F2} (-{3}tk=${4:F0}) | Target: {5:F2} (+{6}tk=${7:F0}) | Mode: {8} | VWAP: {9:F2} ({10:F1}σ) | Stoch: {11:F0} | PreMkt: +{12:F2} ***",
                        contracts, Close[0], stopPrice, StopTicks, StopTicks * tickValue * contracts,
                        targetPrice, TargetTicks, TargetTicks * tickValue * contracts,
                        mode, vwapValue, distanceInStdDev, stoch.K[0], preMarketMove));
            }
            else if (goShort)
            {
                activeSignalName = "BLAST_SHORT";
                double stopPrice = Close[0] + (StopTicks * TickSize);
                double targetPrice = Close[0] - (TargetTicks * TickSize);

                EnterShort(contracts, activeSignalName);
                SetStopLoss(activeSignalName, CalculationMode.Price, stopPrice, false);
                SetProfitTarget(activeSignalName, CalculationMode.Price, targetPrice);

                tradedToday = true;
                breakevenSet = false;

                if (DebugMode)
                    Print(string.Format("*** BLAST SHORT {0}ct @ {1:F2} | Stop: {2:F2} (-{3}tk=${4:F0}) | Target: {5:F2} (+{6}tk=${7:F0}) | Mode: {8} | VWAP: {9:F2} ({10:F1}σ) | Stoch: {11:F0} | PreMkt: {12:F2} ***",
                        contracts, Close[0], stopPrice, StopTicks, StopTicks * tickValue * contracts,
                        targetPrice, TargetTicks, TargetTicks * tickValue * contracts,
                        mode, vwapValue, distanceInStdDev, stoch.K[0], preMarketMove));
            }
        }

        // ================================================================
        // POSITION SIZING - Cuenta Fondeada
        // ================================================================
        private int CalculateContracts()
        {
            double tickValue = TickSize * Instrument.MasterInstrument.PointValue;
            double stopDollarsPerContract = StopTicks * tickValue;

            if (stopDollarsPerContract <= 0)
                return 1;

            // Riesgo por trade = DD limite / trades de supervivencia
            double riskPerTrade = MaxDrawdownLimit / SurvivalTrades;

            int contracts = (int)Math.Floor(riskPerTrade / stopDollarsPerContract);
            contracts = Math.Max(1, contracts);

            if (DebugMode)
                Print(string.Format("  SIZING: DD_Limit=${0:F0} / {1} trades = ${2:F0}/trade | Stop=${3:F2}/ct | Contracts={4}",
                    MaxDrawdownLimit, SurvivalTrades, riskPerTrade, stopDollarsPerContract, contracts));

            return contracts;
        }

        // ================================================================
        // GESTION DE POSICION (breakeven + exit por tiempo)
        // ================================================================
        private void ManagePosition()
        {
            int timeNow = ToTime(Time[0]);

            // === SALIDA FORZADA POR TIEMPO ===
            if (timeNow >= ForceExitTime)
            {
                if (Position.MarketPosition == MarketPosition.Long)
                    ExitLong("TIME_EXIT", activeSignalName);
                else if (Position.MarketPosition == MarketPosition.Short)
                    ExitShort("TIME_EXIT", activeSignalName);

                if (DebugMode)
                    Print(string.Format("{0} | TIME EXIT: Cerrando posicion a las {1}", Time[0], ForceExitTime));
                return;
            }

            // === BREAKEVEN ===
            if (!UseBreakeven || breakevenSet)
                return;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double unrealizedTicks = (Close[0] - Position.AveragePrice) / TickSize;
                if (unrealizedTicks >= BreakevenTriggerTicks)
                {
                    SetStopLoss(activeSignalName, CalculationMode.Price, Position.AveragePrice, false);
                    breakevenSet = true;

                    if (DebugMode)
                        Print(string.Format("  BREAKEVEN activado @ {0:F2} (+{1:F0} ticks)", Close[0], unrealizedTicks));
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double unrealizedTicks = (Position.AveragePrice - Close[0]) / TickSize;
                if (unrealizedTicks >= BreakevenTriggerTicks)
                {
                    SetStopLoss(activeSignalName, CalculationMode.Price, Position.AveragePrice, false);
                    breakevenSet = true;

                    if (DebugMode)
                        Print(string.Format("  BREAKEVEN activado @ {0:F2} (+{1:F0} ticks)", Close[0], unrealizedTicks));
                }
            }
        }

        // ================================================================
        // P&L TRACKING
        // ================================================================
        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            // Cuando la posicion se cierra
            if (marketPosition == MarketPosition.Flat)
            {
                int currentTradeCount = SystemPerformance.AllTrades.Count;
                if (currentTradeCount > lastTradeCount)
                {
                    Trade lastTrade = SystemPerformance.AllTrades[currentTradeCount - 1];
                    double tradePnL = lastTrade.ProfitCurrency;
                    cumulativePnL += tradePnL;

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

                    if (DebugMode)
                    {
                        int totalTrades = totalWins + totalLosses;
                        double winRate = totalTrades > 0 ? (double)totalWins / totalTrades * 100.0 : 0;
                        Print(string.Format("  RESULTADO: ${0:F2} | Acumulado: ${1:F2} | WR: {2:F0}% ({3}W/{4}L) | ConsecLoss: {5}",
                            tradePnL, cumulativePnL, winRate, totalWins, totalLosses, consecutiveLosses));
                    }
                }
            }
        }

        #region Properties

        // ================================================================
        // 1. TIMING
        // ================================================================
        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Entry Time (HHMMSS)", Order = 1, GroupName = "1. Timing")]
        public int EntryTime
        { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Force Exit Time (HHMMSS)", Order = 2, GroupName = "1. Timing")]
        public int ForceExitTime
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 120)]
        [Display(Name = "Trend Lookback (barras 1M)", Order = 3, GroupName = "1. Timing")]
        public int TrendLookbackBars
        { get; set; }

        // ================================================================
        // 2. VWAP
        // ================================================================
        [NinjaScriptProperty]
        [Range(0.1, 3.0)]
        [Display(Name = "Near VWAP Threshold (σ)", Order = 1, GroupName = "2. VWAP")]
        public double NearVWAPThreshold
        { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name = "Far VWAP Threshold (σ)", Order = 2, GroupName = "2. VWAP")]
        public double FarVWAPThreshold
        { get; set; }

        // ================================================================
        // 3. ESTOCASTICO
        // ================================================================
        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro Estocastico", Order = 1, GroupName = "3. Estocastico")]
        public bool UseStochFilter
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name = "Stoch Periodo K", Order = 2, GroupName = "3. Estocastico")]
        public int StochPeriodK
        { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Stoch Periodo D", Order = 3, GroupName = "3. Estocastico")]
        public int StochPeriodD
        { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Stoch Smooth", Order = 4, GroupName = "3. Estocastico")]
        public int StochSmooth
        { get; set; }

        [NinjaScriptProperty]
        [Range(60, 95)]
        [Display(Name = "Stoch Sobrecompra", Order = 5, GroupName = "3. Estocastico")]
        public int StochOverbought
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 40)]
        [Display(Name = "Stoch Sobreventa", Order = 6, GroupName = "3. Estocastico")]
        public int StochOversold
        { get; set; }

        // ================================================================
        // 4. TARGET / STOP
        // ================================================================
        [NinjaScriptProperty]
        [Range(20, 500)]
        [Display(Name = "Target (ticks)", Order = 1, GroupName = "4. Target-Stop")]
        public int TargetTicks
        { get; set; }

        [NinjaScriptProperty]
        [Range(20, 500)]
        [Display(Name = "Stop Loss (ticks)", Order = 2, GroupName = "4. Target-Stop")]
        public int StopTicks
        { get; set; }

        // ================================================================
        // 5. BREAKEVEN
        // ================================================================
        [NinjaScriptProperty]
        [Display(Name = "Usar Breakeven", Order = 1, GroupName = "5. Breakeven")]
        public bool UseBreakeven
        { get; set; }

        [NinjaScriptProperty]
        [Range(10, 200)]
        [Display(Name = "Breakeven Trigger (ticks)", Order = 2, GroupName = "5. Breakeven")]
        public int BreakevenTriggerTicks
        { get; set; }

        // ================================================================
        // 6. POSITION SIZING (Cuenta Fondeada)
        // ================================================================
        [NinjaScriptProperty]
        [Range(500, 100000)]
        [Display(Name = "Max Drawdown Limit ($)", Order = 1, GroupName = "6. Sizing")]
        public double MaxDrawdownLimit
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "Trades de Supervivencia", Order = 2, GroupName = "6. Sizing")]
        public int SurvivalTrades
        { get; set; }

        // ================================================================
        // 7. DEBUG
        // ================================================================
        [NinjaScriptProperty]
        [Display(Name = "Debug Mode", Order = 1, GroupName = "7. Debug")]
        public bool DebugMode
        { get; set; }

        #endregion
    }
}
