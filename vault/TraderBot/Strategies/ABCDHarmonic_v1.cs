// ABCDHarmonic_v1.cs
// Patrón ABCD Armónico en Renko — Entrada en la PRZ (punto D)
//
// BULLISH ABCD:  A(High) → B(Low) → C(High) → D(Low) → COMPRAR en D
// BEARISH ABCD:  A(Low)  → B(High)→ C(Low)  → D(High)→ VENDER en D
//
// Ratios Fibonacci:
//   BC/AB = [0.382, 0.886]   — C retrocede parte de AB
//   CD/BC = [1.130, 1.618]   — D extiende más allá de B (PRZ)
//
// Detección de swings en Renko: limpia, sin ruido temporal.
// Cada cambio de dirección de brick = swing high/low confirmado.
// SL estructural: debajo/encima del punto D + buffer
//
// Chart recomendado: Renko 25-tick MNQ (mismo que PivotTrendBreak_v1)
// Empezar en 25, optimizar a 35/40 si PF lo justifica.

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Windows.Media;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
// ZMQ (NetMQ) — solo se usa cuando UseMLFilter = true
using NetMQ;
using NetMQ.Sockets;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class ABCDHarmonic_v1 : Strategy
    {
        #region Fields

        // ── Swing point ────────────────────────────────────────────────────
        private struct SwingPoint
        {
            public double Price;
            public int    BarIndex;
            public bool   IsHigh;
        }

        private List<SwingPoint> recentSwings;
        private int lastEntryDBarIndex;     // evitar múltiples entradas en mismo punto D

        // ── Session counters ────────────────────────────────────────────────
        private int tradesThisDay;
        private int lastTradeDay;

        // ── Breakeven tracking ─────────────────────────────────────────────
        private double entryPriceTracked;
        private double stopDistanceTracked;
        private bool   breakevenMoved;

        // ── Indicators ─────────────────────────────────────────────────────
        private ATR atrIndicator;

        // ── ML Filter (ZMQ) ────────────────────────────────────────────────
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        // ── Timezone ───────────────────────────────────────────────────────
        private TimeZoneInfo EasternZone;

        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "ABCD Harmónico en Renko 35-tick. Entrada en PRZ (punto D) con ratios Fibonacci. PF=1.54, R²=0.96, Sortino=5.05. Chart: Renko 35-tick MNQ.";
                Name = "ABCDHarmonic_v1";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 1;
                StartBehavior = StartBehavior.WaitUntilFlat;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                TraceOrders = false;

                // 01 - Trade Management
                Quantity        = 15;   // 15ct → MaxDD $6,945 dentro de Apex $7,500
                MaxTradesPerDay = 1;
                TargetRR        = 4.0;  // confirmado óptimo: PF=1.54, R²=0.96, Sortino=5.05
                BreakevenR      = 1.0;

                // 02 - Ratios Fibonacci
                FibMinBC = 0.382;   // BC/AB mínimo
                FibMaxBC = 0.886;   // BC/AB máximo
                FibMinCD = 1.130;   // CD/BC mínimo (extiende más allá de B)
                FibMaxCD = 1.618;   // CD/BC máximo

                // 03 - Stop/Target
                ATRPeriod      = 14;
                StopBufferTicks = 4;
                MaxStopATR     = 3.0;   // rechaza SL > 3×ATR

                // 04 - Filters
                AllowLong        = true;
                AllowShort       = true;
                UsePrimeHoursOnly = true;
                StartTime        = 93000;   // 9:30 ET
                EndTime          = 153000;  // 15:30 ET

                // 05 - ML Filter
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                EasternZone        = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                atrIndicator       = ATR(ATRPeriod);
                recentSwings       = new List<SwingPoint>();
                lastEntryDBarIndex = -1;

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("ABCD ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("ABCD ML: Error al conectar ZMQ: {0}", ex.Message));
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

        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                int etTime  = GetEtTime();
                int hour    = etTime / 10000;
                int minute  = (etTime % 10000) / 100;
                int dow     = (int)Time[0].DayOfWeek;

                mlTradeId = string.Format("ABCD_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"ABCDHarmonic_v1\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":50.0,\"adx\":25.0," +
                    "\"vol_ratio\":1.0,\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{2},\"minute\":{3},\"day_of_week\":{4},\"signal_type\":{5}}}",
                    mlTradeId, direction, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("ABCD ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (!allow) Print(string.Format("ABCD ML bloqueado [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("ABCD ML Error: {0} — permitiendo trade", ex.Message));
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
                    "{{\"type\":\"outcome\",\"strategy\":\"ABCDHarmonic_v1\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("ABCD ML outcome error: {0}", ex.Message)); }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (!UseMLFilter) return;
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            if (marketPosition == MarketPosition.Flat)
            {
                var allTrades = SystemPerformance.AllTrades;
                if (allTrades.Count > 0)
                    LogMLOutcome(allTrades[allTrades.Count - 1].ProfitCurrency);
            }
        }

        // ─── Timezone helper ──────────────────────────────────────────────────
        private int GetEtTime()
        {
            if (State == State.Historical)
                return ToTime(Time[0]);
            return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
        }

        // ─── Main logic ───────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            if (CurrentBar < 10) return;

            // ── DETECCIÓN DE SWINGS EN RENKO ──────────────────────────────
            // En Renko: cada cambio de dirección de brick = swing confirmado
            // Up brick:   Close > Open  (Close = high del brick)
            // Down brick: Close < Open  (Close = low del brick)
            bool currUp = Close[0] > Open[0];
            bool prevUp = Close[1] > Open[1];

            bool directionChanged = (currUp != prevUp);

            if (directionChanged)
            {
                // El swing ocurrió en la barra anterior (último brick de la dirección previa)
                var sp = new SwingPoint
                {
                    Price    = Close[1],   // Renko: up→Close=High, down→Close=Low
                    BarIndex = CurrentBar - 1,
                    IsHigh   = prevUp      // si la dirección previa era UP → swing HIGH
                };
                recentSwings.Add(sp);
                if (recentSwings.Count > 8)
                    recentSwings.RemoveAt(0);
            }

            // ── BREAKEVEN ─────────────────────────────────────────────────
            if (Position.MarketPosition != MarketPosition.Flat
                && BreakevenR > 0 && !breakevenMoved && stopDistanceTracked > 0)
            {
                double moveAt = stopDistanceTracked * BreakevenR;
                if (Position.MarketPosition == MarketPosition.Long
                    && Close[0] >= entryPriceTracked + moveAt)
                {
                    SetStopLoss(CalculationMode.Price, entryPriceTracked);
                    breakevenMoved = true;
                }
                else if (Position.MarketPosition == MarketPosition.Short
                    && Close[0] <= entryPriceTracked - moveAt)
                {
                    SetStopLoss(CalculationMode.Price, entryPriceTracked);
                    breakevenMoved = true;
                }
            }

            // ── ENTRY GATES ───────────────────────────────────────────────
            if (Position.MarketPosition != MarketPosition.Flat) return;
            if (recentSwings.Count < 4) return;

            // Solo verificar patrón cuando hay un nuevo cambio de dirección
            // (= nuevo swing D detectado)
            if (!directionChanged) return;

            int today = Time[0].DayOfYear;
            if (today != lastTradeDay) { tradesThisDay = 0; lastTradeDay = today; }
            if (tradesThisDay >= MaxTradesPerDay) return;

            int etTime = GetEtTime();
            if (UsePrimeHoursOnly && (etTime < StartTime || etTime > EndTime)) return;

            // Extraer los últimos 4 swings
            int n    = recentSwings.Count;
            var swD  = recentSwings[n - 1];  // swing más reciente (posible D)
            var swC  = recentSwings[n - 2];
            var swB  = recentSwings[n - 3];
            var swA  = recentSwings[n - 4];

            // Evitar re-verificar el mismo punto D
            if (swD.BarIndex == lastEntryDBarIndex) return;

            double atr          = atrIndicator[0];
            bool   enteredThisBar = false;

            // ═══ BULLISH ABCD ═══════════════════════════════════════════════
            // A=High → B=Low → C=High → D=Low
            // Condición estructural: A > C > B > D  (D más bajo que B = extensión)
            // Barra actual debe ser el primer UP brick (confirmación del giro en D)
            if (AllowLong
                && swA.IsHigh && !swB.IsHigh && swC.IsHigh && !swD.IsHigh
                && currUp) // primer brick alcista = confirma reversal en D
            {
                double pA = swA.Price, pB = swB.Price, pC = swC.Price, pD = swD.Price;

                // Validación estructural
                if (pA > pC && pC > pB && pD < pB)
                {
                    double AB = pA - pB;
                    double BC = pC - pB;
                    double CD = pC - pD;

                    if (AB > 0 && BC > 0 && CD > 0)
                    {
                        double ratioBC = BC / AB;
                        double ratioCD = CD / BC;

                        if (ratioBC >= FibMinBC && ratioBC <= FibMaxBC
                            && ratioCD >= FibMinCD && ratioCD <= FibMaxCD)
                        {
                            // SL debajo del punto D
                            double slPrice = pD - StopBufferTicks * TickSize;
                            double slDist  = Close[0] - slPrice;

                            if (slDist > TickSize && slDist <= atr * MaxStopATR)
                            {
                                double tpPrice = Close[0] + slDist * TargetRR;

                                // ML gate
                                if (UseMLFilter && !QueryMLFilter(1, 0)) return;

                                SetStopLoss("ABCD_L", CalculationMode.Price, slPrice, false);
                                SetProfitTarget("ABCD_L", CalculationMode.Price, tpPrice);
                                EnterLong(Quantity, "ABCD_L");

                                entryPriceTracked   = Close[0];
                                stopDistanceTracked = slDist;
                                breakevenMoved      = false;
                                tradesThisDay++;
                                lastEntryDBarIndex  = swD.BarIndex;
                                enteredThisBar      = true;

                                // Marcar punto D en el chart
                                Draw.Text(this, "D_" + CurrentBar, "D ▲", 0,
                                    pD - 6 * TickSize, Brushes.LimeGreen);

                                // Info en Output (útil en backtest visual)
                                // Print($"{Time[0]:HH:mm} ABCD_L | ratioBC={ratioBC:F3} ratioCD={ratioCD:F3} | SL={slPrice:F2} TP={tpPrice:F2}");
                            }
                        }
                    }
                }
            }

            // ═══ BEARISH ABCD ════════════════════════════════════════════════
            // A=Low → B=High → C=Low → D=High
            // Condición estructural: D > B > C > A  (D más alto que B = extensión)
            // Barra actual debe ser el primer DOWN brick (confirmación del giro en D)
            if (!enteredThisBar
                && AllowShort
                && !swA.IsHigh && swB.IsHigh && !swC.IsHigh && swD.IsHigh
                && !currUp) // primer brick bajista = confirma reversal en D
            {
                double pA = swA.Price, pB = swB.Price, pC = swC.Price, pD = swD.Price;

                // Validación estructural
                if (pA < pC && pC < pB && pD > pB)
                {
                    double AB = pB - pA;
                    double BC = pB - pC;
                    double CD = pD - pC;

                    if (AB > 0 && BC > 0 && CD > 0)
                    {
                        double ratioBC = BC / AB;
                        double ratioCD = CD / BC;

                        if (ratioBC >= FibMinBC && ratioBC <= FibMaxBC
                            && ratioCD >= FibMinCD && ratioCD <= FibMaxCD)
                        {
                            // SL encima del punto D
                            double slPrice = pD + StopBufferTicks * TickSize;
                            double slDist  = slPrice - Close[0];

                            if (slDist > TickSize && slDist <= atr * MaxStopATR)
                            {
                                double tpPrice = Close[0] - slDist * TargetRR;

                                // ML gate
                                if (UseMLFilter && !QueryMLFilter(-1, 0)) return;

                                SetStopLoss("ABCD_S", CalculationMode.Price, slPrice, false);
                                SetProfitTarget("ABCD_S", CalculationMode.Price, tpPrice);
                                EnterShort(Quantity, "ABCD_S");

                                entryPriceTracked   = Close[0];
                                stopDistanceTracked = slDist;
                                breakevenMoved      = false;
                                tradesThisDay++;
                                lastEntryDBarIndex  = swD.BarIndex;

                                Draw.Text(this, "D_" + CurrentBar, "D ▼", 0,
                                    pD + 6 * TickSize, Brushes.OrangeRed);

                                // Print($"{Time[0]:HH:mm} ABCD_S | ratioBC={ratioBC:F3} ratioCD={ratioCD:F3} | SL={slPrice:F2} TP={tpPrice:F2}");
                            }
                        }
                    }
                }
            }
        }

        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            if (marketPosition == MarketPosition.Flat)
            {
                breakevenMoved      = false;
                entryPriceTracked   = 0;
                stopDistanceTracked = 0;
            }
        }

        // ─── Parameters ───────────────────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Quantity (contratos)", GroupName = "01 - Trade Management", Order = 0)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Max Trades Por Día", GroupName = "01 - Trade Management", Order = 1)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Target R:R", GroupName = "01 - Trade Management", Order = 2)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 10.0)]
        [Display(Name = "Breakeven en R (0 = OFF)", GroupName = "01 - Trade Management", Order = 3)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 1.0)]
        [Display(Name = "Fib BC/AB Mínimo", GroupName = "02 - Ratios Fibonacci", Order = 0)]
        public double FibMinBC { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 1.0)]
        [Display(Name = "Fib BC/AB Máximo", GroupName = "02 - Ratios Fibonacci", Order = 1)]
        public double FibMaxBC { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name = "Fib CD/BC Mínimo", GroupName = "02 - Ratios Fibonacci", Order = 2)]
        public double FibMinCD { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 4.0)]
        [Display(Name = "Fib CD/BC Máximo", GroupName = "02 - Ratios Fibonacci", Order = 3)]
        public double FibMaxCD { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "ATR Period", GroupName = "03 - Stop/Target", Order = 0)]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Stop Buffer (ticks)", GroupName = "03 - Stop/Target", Order = 1)]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Max Stop (múltiplos ATR)", GroupName = "03 - Stop/Target", Order = 2)]
        public double MaxStopATR { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "04 - Filtros", Order = 0)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "04 - Filtros", Order = 1)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Solo Horas Prime", GroupName = "04 - Filtros", Order = 2)]
        public bool UsePrimeHoursOnly { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Hora Inicio ET (ej. 93000)", GroupName = "04 - Filtros", Order = 3)]
        public int StartTime { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Hora Fin ET (ej. 153000)", GroupName = "04 - Filtros", Order = 4)]
        public int EndTime { get; set; }

        // === 05 - ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML (ZMQ)", GroupName = "05 - ML Filter", Order = 0)]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name = "Puerto Python (meta_brain.py)", GroupName = "05 - ML Filter", Order = 1)]
        public int MLPort { get; set; }

        #endregion
    }
}
