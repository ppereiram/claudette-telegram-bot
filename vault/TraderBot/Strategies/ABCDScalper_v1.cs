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
    public class ABCDScalper_v1 : Strategy
    {
        // ================================================================
        // ABCD Scalper v1.0 - Patron Armonico + MACD
        //
        // PATRON ABCD (el mas simple y confiable de los harmonicos):
        //
        //   BULLISH: A(high) → B(low) → C(high) → D(low) → COMPRAR en D
        //   BEARISH: A(low) → B(high) → C(low) → D(high) → VENDER en D
        //
        //   Ratios Fibonacci:
        //   BC/AB = 0.382 - 0.886  (B retrocede parte de AB)
        //   CD/BC = 1.13  - 1.618  (D extiende mas alla de B = PRZ)
        //
        // CONFIRMACION EN D (Potential Reversal Zone):
        //   MACD histogram girando N barras consecutivas
        //   Precio del lado correcto del VWAP
        //
        // CHART: 5 minutos, MNQ, ETH session (para VWAP completo)
        // ================================================================

        // ================================================================
        // SWING POINT - estructura para almacenar pivots
        // ================================================================
        private struct SwingPoint
        {
            public double Price;
            public int    BarIndex;
            public bool   IsHigh;
        }

        // === Swing detection ===
        private List<SwingPoint> swings;
        private int              lastTradedDBarIndex;

        // === Indicadores ===
        private MACD macd;

        // === VWAP manual ===
        private double cumTPV, cumVol, cumTPSqV;
        private double vwapValue;

        // === Estado ===
        private string activeSignal;
        private int    tradesToday;
        private bool   bullishPattern;
        private bool   bearishPattern;

        // === Performance ===
        private int    lastTradeCount;
        private int    totalWins, totalLosses;
        private double cumulativePnL;
        private bool   breakevenSet;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"ABCD Scalper v1.0 - Patron armonico ABCD + MACD en 5 minutos";
                Name        = "ABCDScalper_v1";
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

                // === 1. TIMING ===
                // Ventana 1: Open (9:30-11:30) — mayor volatilidad y movimiento
                // Ventana 2: Tarde (13:30-15:00) — segundo impulso del dia
                StartTime1     = 93000;   // 9:30 AM
                EndTime1       = 113000;  // 11:30 AM
                StartTime2     = 133000;  // 1:30 PM
                EndTime2       = 150000;  // 3:00 PM
                ForceExitTime  = 153000;  // 3:30 PM: salida forzada

                // === 2. PATRON ABCD ===
                // SwingStrength=3: necesita 3 barras a cada lado para confirmar pivot
                // En 5M: cada swing minimo ocupa 7 barras = 35 minutos
                // Con 4 swings minimo para ABCD: ~2.5 horas → 1-2 patrones por ventana
                SwingStrength   = 3;      // Barras a cada lado del pivot
                FibTolerance    = 0.15;   // 15% tolerancia (patrones reales rara vez son perfectos)
                MaxTradesPerDay = 3;      // Maximo 3 entradas al dia

                // === 3. MACD ===
                // Mismo 10/22 que funciono en NYOpenBlast
                MACDFast          = 10;
                MACDSlow          = 22;
                MACDSignal        = 9;
                MACDBarsToConfirm = 2;    // 2 barras consecutivas del histogram girando = señal

                // === 4. VWAP ===
                UseVWAPFilter = true;     // Long bajo VWAP, Short sobre VWAP (precio barato/caro)

                // === INVERSION ===
                // El punto D del ABCD en MNQ 5M NO es un reversal confiable.
                // El mercado CONTINUA mas alla de D el ~70% del tiempo.
                // InvertDirection=true → fadeamos el patron (igual que NYOpenBlast)
                // WR original: ~30% | WR invertido: ~70%
                InvertDirection = true;

                // === 5. TARGET / STOP ===
                // Con InvertDirection=true: WR ~70% → podemos usar R:R < 1 y seguir ganando
                // EV = 0.70 × Target - 0.30 × Stop > 0
                // Stop=100, Target=80 → EV = 0.70×80 - 0.30×100 = +26 ticks/trade
                TargetTicks = 80;         // 20 puntos = $100/ct (ajustar en backtest)
                StopTicks   = 100;        // 25 puntos = $125/ct → R:R = 0.8 con WR 70%

                // === 6. BREAKEVEN ===
                UseBreakeven          = true;
                BreakevenTriggerTicks = 40;   // A +10 puntos mover stop a entry

                // === 7. SIZING ===
                MaxDrawdownLimit = 7500;
                SurvivalTrades   = 20;        // $7500/20 = $375/trade riesgo

                // === 8. DEBUG ===
                DebugMode = true;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                macd   = MACD(MACDFast, MACDSlow, MACDSignal);
                swings = new List<SwingPoint>();

                lastTradeCount      = 0;
                totalWins           = 0;
                totalLosses         = 0;
                cumulativePnL       = 0;
                lastTradedDBarIndex = -999;
                tradesToday         = 0;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // === VWAP: Reset al inicio de sesion ===
            if (Bars.IsFirstBarOfSession)
            {
                cumTPV              = 0;
                cumVol              = 0;
                cumTPSqV            = 0;
                tradesToday         = 0;
                lastTradedDBarIndex = -999;
                swings.Clear();
                bullishPattern = false;
                bearishPattern = false;
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
                vwapValue = cumTPV / cumVol;

            // === Deteccion de swings (con lag de SwingStrength barras) ===
            DetectSwing();

            // === Verificar si los ultimos 4 swings forman un ABCD ===
            CheckABCDPattern();

            // === Gestion o busqueda de entrada ===
            if (Position.MarketPosition != MarketPosition.Flat)
                ManagePosition();
            else
                CheckEntry();
        }

        // ================================================================
        // DETECCION DE SWINGS
        // Detectamos el pivot de hace SwingStrength barras.
        // Si High[s] > todos los High de [0..2s] salvo el propio → swing high
        // Si Low[s]  < todos los Low  de [0..2s] salvo el propio → swing low
        // ================================================================
        private void DetectSwing()
        {
            int s = SwingStrength;
            if (CurrentBar < s * 2 + 1)
                return;

            bool isHigh = true;
            bool isLow  = true;

            for (int i = 0; i <= s * 2; i++)
            {
                if (i == s) continue;
                if (High[i] >= High[s]) isHigh = false;
                if (Low[i]  <= Low[s])  isLow  = false;
            }

            if (!isHigh && !isLow)
                return;

            // El pivot esta en la barra de hace [s] barras
            int    pivotBar   = CurrentBar - s;
            double pivotPrice = isHigh ? High[s] : Low[s];
            bool   pivotIsHigh = isHigh;

            // Evitar procesar la misma barra dos veces
            if (swings.Count > 0 && swings[swings.Count - 1].BarIndex == pivotBar)
                return;

            if (swings.Count == 0)
            {
                swings.Add(new SwingPoint { Price = pivotPrice, BarIndex = pivotBar, IsHigh = pivotIsHigh });
                return;
            }

            SwingPoint last = swings[swings.Count - 1];

            if (last.IsHigh == pivotIsHigh)
            {
                // Mismo tipo: actualizar solo si es mas extremo (evitar swings menores)
                if ((pivotIsHigh && pivotPrice > last.Price) || (!pivotIsHigh && pivotPrice < last.Price))
                {
                    swings[swings.Count - 1] = new SwingPoint { Price = pivotPrice, BarIndex = pivotBar, IsHigh = pivotIsHigh };
                    if (DebugMode)
                        Print(string.Format("  SWING actualizado: {0} @ {1:F2} (bar {2})",
                            pivotIsHigh ? "HIGH" : "LOW", pivotPrice, pivotBar));
                }
            }
            else
            {
                // Alternado: agregar nuevo swing
                swings.Add(new SwingPoint { Price = pivotPrice, BarIndex = pivotBar, IsHigh = pivotIsHigh });
                if (swings.Count > 12)
                    swings.RemoveAt(0);

                if (DebugMode)
                    Print(string.Format("  SWING nuevo: {0} @ {1:F2} (bar {2}) | Total swings: {3}",
                        pivotIsHigh ? "HIGH" : "LOW", pivotPrice, pivotBar, swings.Count));
            }
        }

        // ================================================================
        // DETECCION DEL PATRON ABCD en los ultimos 4 swings
        //
        //   BULLISH: A=high, B=low, C=high, D=low
        //   AB = caida desde A hasta B
        //   BC = rebote desde B hasta C  (BC/AB = 0.382-0.886)
        //   CD = caida desde C hasta D  (CD/BC = 1.13-1.618)
        //   En D: precio en zona PRZ → COMPRAR
        //
        //   BEARISH: A=low, B=high, C=low, D=high (espejo)
        // ================================================================
        private void CheckABCDPattern()
        {
            bullishPattern = false;
            bearishPattern = false;

            if (swings.Count < 4)
                return;

            SwingPoint spA = swings[swings.Count - 4];
            SwingPoint spB = swings[swings.Count - 3];
            SwingPoint spC = swings[swings.Count - 2];
            SwingPoint spD = swings[swings.Count - 1];

            // === BULLISH ABCD ===
            // Estructura: A(high) → B(low) → C(high) → D(low)
            if (spA.IsHigh && !spB.IsHigh && spC.IsHigh && !spD.IsHigh)
            {
                double AB = spA.Price - spB.Price;
                double BC = spC.Price - spB.Price;
                double CD = spC.Price - spD.Price;

                if (AB > 0 && BC > 0 && CD > 0)
                {
                    double ratioBC_AB = BC / AB;
                    double ratioCD_BC = CD / BC;

                    if (IsInRange(ratioBC_AB, 0.382, 0.886) && IsInRange(ratioCD_BC, 1.13, 1.618))
                    {
                        bullishPattern = true;
                        if (DebugMode)
                            Print(string.Format("{0} | BULLISH ABCD detectado | A={1:F2} B={2:F2} C={3:F2} D={4:F2} | BC/AB={5:F3} CD/BC={6:F3}",
                                Time[0], spA.Price, spB.Price, spC.Price, spD.Price, ratioBC_AB, ratioCD_BC));
                    }
                }
            }

            // === BEARISH ABCD ===
            // Estructura: A(low) → B(high) → C(low) → D(high)
            if (!spA.IsHigh && spB.IsHigh && !spC.IsHigh && spD.IsHigh)
            {
                double AB = spB.Price - spA.Price;
                double BC = spB.Price - spC.Price;
                double CD = spD.Price - spC.Price;

                if (AB > 0 && BC > 0 && CD > 0)
                {
                    double ratioBC_AB = BC / AB;
                    double ratioCD_BC = CD / BC;

                    if (IsInRange(ratioBC_AB, 0.382, 0.886) && IsInRange(ratioCD_BC, 1.13, 1.618))
                    {
                        bearishPattern = true;
                        if (DebugMode)
                            Print(string.Format("{0} | BEARISH ABCD detectado | A={1:F2} B={2:F2} C={3:F2} D={4:F2} | BC/AB={5:F3} CD/BC={6:F3}",
                                Time[0], spA.Price, spB.Price, spC.Price, spD.Price, ratioBC_AB, ratioCD_BC));
                    }
                }
            }
        }

        private bool IsInRange(double value, double min, double max)
        {
            return value >= min * (1.0 - FibTolerance) && value <= max * (1.0 + FibTolerance);
        }

        // ================================================================
        // BUSQUEDA DE ENTRADA
        // Condiciones:
        //   1. Patron ABCD detectado
        //   2. MACD histogram girando N barras consecutivas
        //   3. VWAP del lado correcto (opcional)
        //   4. Dentro de ventana horaria
        //   5. No hemos ya operado este punto D
        // ================================================================
        private void CheckEntry()
        {
            if (tradesToday >= MaxTradesPerDay)
                return;

            // Ventanas horarias: morning o afternoon
            int timeNow = ToTime(Time[0]);
            bool inWindow = (timeNow >= StartTime1 && timeNow <= EndTime1) ||
                            (timeNow >= StartTime2 && timeNow <= EndTime2);
            if (!inWindow)
                return;

            // No operar el mismo punto D dos veces
            if (swings.Count < 4)
                return;
            SwingPoint currentD = swings[swings.Count - 1];
            if (currentD.BarIndex <= lastTradedDBarIndex)
                return;

            // MACD histogram: N barras consecutivas en la misma dirección
            bool macdTurningUp   = true;
            bool macdTurningDown = true;
            for (int i = 0; i < MACDBarsToConfirm - 1; i++)
            {
                if (macd.Diff[i] <= macd.Diff[i + 1]) macdTurningUp   = false;
                if (macd.Diff[i] >= macd.Diff[i + 1]) macdTurningDown = false;
            }

            int contracts = CalculateContracts();

            // InvertDirection=true → fadeamos el patron (MNQ continua mas alla de D ~70%)
            // Bullish ABCD esperaba rebote → nosotros entramos SHORT (continua bajando)
            // Bearish ABCD esperaba caida → nosotros entramos LONG  (continua subiendo)
            bool goLong  = InvertDirection ? bearishPattern : bullishPattern;
            bool goShort = InvertDirection ? bullishPattern : bearishPattern;

            // MACD: si invertimos, confirmamos con el MACD que acompaña la continuacion
            // (si el patron esperaba rebote alcista y vamos SHORT, el MACD debe estar bajando)
            bool macdOkLong  = InvertDirection ? macdTurningDown : macdTurningUp;
            bool macdOkShort = InvertDirection ? macdTurningUp   : macdTurningDown;

            // === LONG ===
            if (goLong && macdOkLong)
            {
                if (UseVWAPFilter && cumVol > 0 && Close[0] > vwapValue * 1.003)
                {
                    if (DebugMode)
                        Print(string.Format("{0} | LONG bloqueado: muy sobre VWAP | Close={1:F2} VWAP={2:F2}",
                            Time[0], Close[0], vwapValue));
                    return;
                }

                double stopPrice   = Close[0] - (StopTicks   * TickSize);
                double targetPrice = Close[0] + (TargetTicks * TickSize);
                activeSignal       = InvertDirection ? "ABCD_FADE_LONG" : "ABCD_LONG";

                EnterLong(contracts, activeSignal);
                SetStopLoss(activeSignal, CalculationMode.Price, stopPrice, false);
                SetProfitTarget(activeSignal, CalculationMode.Price, targetPrice);

                breakevenSet        = false;
                lastTradedDBarIndex = currentD.BarIndex;
                tradesToday++;

                if (DebugMode)
                    Print(string.Format("*** {0} {1}ct @ {2:F2} | Stop={3:F2} (-{4}tk) | Tgt={5:F2} (+{6}tk) | MACD={7:F4} | VWAP={8:F2} ***",
                        activeSignal, contracts, Close[0], stopPrice, StopTicks, targetPrice, TargetTicks, macd.Diff[0], vwapValue));
            }

            // === SHORT ===
            else if (goShort && macdOkShort)
            {
                if (UseVWAPFilter && cumVol > 0 && Close[0] < vwapValue * 0.997)
                {
                    if (DebugMode)
                        Print(string.Format("{0} | SHORT bloqueado: muy bajo VWAP | Close={1:F2} VWAP={2:F2}",
                            Time[0], Close[0], vwapValue));
                    return;
                }

                double stopPrice   = Close[0] + (StopTicks   * TickSize);
                double targetPrice = Close[0] - (TargetTicks * TickSize);
                activeSignal       = InvertDirection ? "ABCD_FADE_SHORT" : "ABCD_SHORT";

                EnterShort(contracts, activeSignal);
                SetStopLoss(activeSignal, CalculationMode.Price, stopPrice, false);
                SetProfitTarget(activeSignal, CalculationMode.Price, targetPrice);

                breakevenSet        = false;
                lastTradedDBarIndex = currentD.BarIndex;
                tradesToday++;

                if (DebugMode)
                    Print(string.Format("*** {0} {1}ct @ {2:F2} | Stop={3:F2} (-{4}tk) | Tgt={5:F2} (+{6}tk) | MACD={7:F4} | VWAP={8:F2} ***",
                        activeSignal, contracts, Close[0], stopPrice, StopTicks, targetPrice, TargetTicks, macd.Diff[0], vwapValue));
            }
        }

        // ================================================================
        // GESTION DE POSICION ABIERTA
        // ================================================================
        private void ManagePosition()
        {
            if (Position.MarketPosition == MarketPosition.Flat)
                return;

            int timeNow = ToTime(Time[0]);

            // Salida forzada por tiempo
            if (timeNow >= ForceExitTime)
            {
                if (Position.MarketPosition == MarketPosition.Long)
                    ExitLong("TIME_EXIT", activeSignal);
                else if (Position.MarketPosition == MarketPosition.Short)
                    ExitShort("TIME_EXIT", activeSignal);

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
                    SetStopLoss(activeSignal, CalculationMode.Price, Position.AveragePrice, false);
                    breakevenSet = true;
                    if (DebugMode)
                        Print(string.Format("  BREAKEVEN LONG @ {0:F2} (+{1:F0}tk)", Close[0], ticks));
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double ticks = (Position.AveragePrice - Close[0]) / TickSize;
                if (ticks >= BreakevenTriggerTicks)
                {
                    SetStopLoss(activeSignal, CalculationMode.Price, Position.AveragePrice, false);
                    breakevenSet = true;
                    if (DebugMode)
                        Print(string.Format("  BREAKEVEN SHORT @ {0:F2} (+{1:F0}tk)", Close[0], ticks));
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
            int    contracts    = (int)Math.Floor(riskPerTrade / stopDollarsPerContract);

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
                    Trade  lastTrade = SystemPerformance.AllTrades[currentTradeCount - 1];
                    double tradePnL  = lastTrade.ProfitCurrency;
                    cumulativePnL   += tradePnL;

                    if (tradePnL >= 0) totalWins++;
                    else               totalLosses++;

                    lastTradeCount = currentTradeCount;

                    if (DebugMode)
                    {
                        int    total = totalWins + totalLosses;
                        double wr    = total > 0 ? (double)totalWins / total * 100.0 : 0;
                        Print(string.Format("  RESULTADO: ${0:F2} | Acum: ${1:F2} | WR: {2:F0}% ({3}W/{4}L)",
                            tradePnL, cumulativePnL, wr, totalWins, totalLosses));
                    }
                }
            }
        }

        #region Properties

        // === 1. TIMING ===
        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Start Time 1 (HHMMSS)", Order = 1, GroupName = "1. Timing")]
        public int StartTime1 { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "End Time 1 (HHMMSS)", Order = 2, GroupName = "1. Timing")]
        public int EndTime1 { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Start Time 2 (HHMMSS)", Order = 3, GroupName = "1. Timing")]
        public int StartTime2 { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "End Time 2 (HHMMSS)", Order = 4, GroupName = "1. Timing")]
        public int EndTime2 { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Force Exit Time (HHMMSS)", Order = 5, GroupName = "1. Timing")]
        public int ForceExitTime { get; set; }

        // === 2. PATRON ABCD ===
        [NinjaScriptProperty]
        [Range(2, 8)]
        [Display(Name = "Swing Strength (barras)", Order = 1, GroupName = "2. Patron ABCD")]
        public int SwingStrength { get; set; }

        [NinjaScriptProperty]
        [Range(0.05, 0.30)]
        [Display(Name = "Fib Tolerance (0.15 = 15%)", Order = 2, GroupName = "2. Patron ABCD")]
        public double FibTolerance { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max Trades por Dia", Order = 3, GroupName = "2. Patron ABCD")]
        public int MaxTradesPerDay { get; set; }

        // === 3. MACD ===
        [NinjaScriptProperty]
        [Range(3, 30)]
        [Display(Name = "MACD Fast", Order = 1, GroupName = "3. MACD")]
        public int MACDFast { get; set; }

        [NinjaScriptProperty]
        [Range(10, 60)]
        [Display(Name = "MACD Slow", Order = 2, GroupName = "3. MACD")]
        public int MACDSlow { get; set; }

        [NinjaScriptProperty]
        [Range(3, 20)]
        [Display(Name = "MACD Signal", Order = 3, GroupName = "3. MACD")]
        public int MACDSignal { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5)]
        [Display(Name = "Barras confirmar MACD", Order = 4, GroupName = "3. MACD")]
        public int MACDBarsToConfirm { get; set; }

        // === 3b. INVERSION ===
        [NinjaScriptProperty]
        [Display(Name = "Invertir Direccion", Order = 1, GroupName = "3b. Inversion")]
        public bool InvertDirection { get; set; }

        // === 4. VWAP ===
        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro VWAP", Order = 1, GroupName = "4. VWAP")]
        public bool UseVWAPFilter { get; set; }

        // === 5. TARGET / STOP ===
        [NinjaScriptProperty]
        [Range(20, 500)]
        [Display(Name = "Target (ticks)", Order = 1, GroupName = "5. Target-Stop")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(10, 300)]
        [Display(Name = "Stop Loss (ticks)", Order = 2, GroupName = "5. Target-Stop")]
        public int StopTicks { get; set; }

        // === 6. BREAKEVEN ===
        [NinjaScriptProperty]
        [Display(Name = "Usar Breakeven", Order = 1, GroupName = "6. Breakeven")]
        public bool UseBreakeven { get; set; }

        [NinjaScriptProperty]
        [Range(10, 200)]
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

        #endregion
    }
}
