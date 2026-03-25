//
// MNQ Momentum Scalper v1.5
// =========================
// Automated scalping strategy for Micro E-mini Nasdaq 100 (MNQ)
//
// METHODOLOGY:
//   - Trend following with pullback entries (EMA 9/21/50 alignment)
//   - VWAP + EMA confluence for high-probability entries
//   - Strong-close candle confirmation (close in top/bottom 30% of range)
//   - ATR-based dynamic risk management
//   - 3-5-7 Rule: 3% risk/trade, 5% max exposure, 1.5:1 min R:R
//   - Dynamic position sizing based on account equity
//   - Partial profit taking (TP1) + trailing stop (TP2)
//   - Daily loss limits and consecutive loss protection
//
// RECOMMENDED SETUP:
//   - Instrument: MNQ (Micro E-mini Nasdaq 100)
//   - Timeframe:  2-minute chart
//   - Session:    US RTH (Regular Trading Hours)
//   - Account:    Minimum $5,000 recommended
//
// INSTALLATION:
//   1. Copy this file to: Documents\NinjaTrader 8\bin\Custom\Strategies\
//   2. In NinjaTrader: Tools > NinjaScript Editor > right-click Strategies folder > Compile
//   3. Apply to a 2-minute MNQ chart
//   4. ALWAYS backtest and run in Sim before going live
//
// ENTRY LOGIC (Long example):
//   1. EMA 9 > EMA 21 > EMA 50 (trend confirmed)
//   2. Price pulls back to VWAP or EMA 9 zone
//   3. Strong bullish candle: close in top 30% of range, above EMA 9 and VWAP
//   4. RSI between 30-70 (not exhausted)
//   5. ATR above minimum threshold (enough volatility)
//
// EXIT LOGIC:
//   - TP1: 1.5x ATR (50% position) - locks quick profit
//   - After TP1: Stop moves to breakeven + 2 ticks
//   - TP2: 2.0x ATR (50% position) OR trailing stop at 1.0x ATR
//   - Daily loss limit and consecutive loss circuit breaker
//
// POSITION SIZING (3-5-7 Rule):
//   - Risk per trade capped at 3% of account equity
//   - Total exposure capped at 5% of account equity
//   - Minimum reward:risk ratio of 1.5:1
//   - Contracts calculated dynamically from stop distance + account size
//   - Toggle UseDynamicSizing=false to use fixed contract counts
//

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
    public class MNQMomentumScalper : Strategy
    {
        #region Private Variables

        // Indicators
        private EMA emaFast;
        private EMA emaMid;
        private EMA emaSlow;
        private RSI rsi;
        private ATR atr;

        // VWAP (calculated manually for maximum compatibility)
        private double cumulativeTPV;
        private double cumulativeVol;
        private double vwapValue;

        // Trade management state
        private int    tradesToday;
        private double dailyPnL;
        private double currentTradePnL;
        private bool   tp1Filled;
        private bool   pendingBreakevenMove;
        private double trailStopPrice;
        private double currentEntryPrice;
        private int    currentDirection;   // 1 = long, -1 = short, 0 = flat
        private DateTime lastSessionDate;
        private int    consecutiveLosses;

        // 3-5-7 Rule: running equity tracking
        private double cumulativePnL;      // lifetime P&L for dynamic sizing
        private int    lastCalcTP1;        // last calculated contracts for logging
        private int    lastCalcTP2;

        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"MNQ Momentum Scalper - VWAP + EMA pullback scalping strategy with ATR-based risk management. "
                            + "Trades pullbacks to VWAP/EMA support in trending conditions with partial profit taking and trailing stops.";
                Name = "MNQMomentumScalper";

                // Execution settings
                Calculate                       = Calculate.OnBarClose;
                EntriesPerDirection              = 1;
                EntryHandling                    = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy     = true;
                ExitOnSessionCloseSeconds        = 30;
                IsFillLimitOnTouch               = false;
                MaximumBarsLookBack              = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution              = OrderFillResolution.Standard;
                Slippage                         = 1;
                StartBehavior                    = StartBehavior.WaitUntilFlat;
                TimeInForce                      = TimeInForce.Gtc;
                TraceOrders                      = true;
                RealtimeErrorHandling            = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling               = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade              = 50;
                IsInstantiatedOnEachOptimizationIteration = true;

                // ── 1. TREND ──
                FastEMAPeriod        = 9;
                MidEMAPeriod         = 21;
                SlowEMAPeriod        = 50;

                // ── 2. ENTRY ──
                RSIPeriod            = 14;
                RSILowerBound        = 30;   // v1.2: Wider range (was 35)
                RSIUpperBound        = 70;   // v1.2: Wider range (was 65)
                PullbackToleranceTicks = 10;  // v1.2: Slightly wider (was 8)

                // ── 3. VOLATILITY ──
                ATRPeriod            = 14;
                MinATRTicks          = 4;    // v1.2: More trades allowed (was 6)

                // ── 4. RISK MANAGEMENT ──
                StopLossATRMult      = 1.4;   // v1.5: More breathing room (each +0.1 = ~3% more WR)
                TakeProfit1ATRMult   = 1.5;   // v1.2: Keep - good balance
                TakeProfit2ATRMult   = 2.0;   // v1.4: More achievable (was 2.5) - hit more often
                TrailingStopATRMult  = 1.0;   // v1.4: Let winners breathe (was 0.8)
                BreakevenPlusTicks   = 2;
                ContractsTP1         = 1;     // Used when UseDynamicSizing = false
                ContractsTP2         = 1;     // Used when UseDynamicSizing = false

                // ── 6. POSITION SIZING (3-5-7 Rule) ──
                UseDynamicSizing     = true;
                StartingCapital      = 5000;
                AccountRiskPercent   = 3.0;   // 3% max risk per trade
                MaxExposurePercent   = 5.0;   // 5% max total exposure
                MinRewardRiskRatio   = 1.5;   // v1.4: Match natural R:R of TP2/Stop (2.0/1.3=1.54)

                // ── 5. SESSION & LIMITS ──
                SessionStartTime     = 93500;   // 9:35 AM ET
                SessionEndTime       = 153000;  // 3:30 PM ET
                MaxDailyTrades       = 8;
                DailyLossLimit       = 150.0;
                MaxConsecutiveLosses = 3;
            }
            else if (State == State.DataLoaded)
            {
                // Initialize indicators
                emaFast = EMA(FastEMAPeriod);
                emaMid  = EMA(MidEMAPeriod);
                emaSlow = EMA(SlowEMAPeriod);
                rsi     = RSI(RSIPeriod, 3);
                atr     = ATR(ATRPeriod);

                // Chart colors for visual reference
                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaMid.Plots[0].Brush  = Brushes.Gold;
                emaSlow.Plots[0].Brush = Brushes.Magenta;

                AddChartIndicator(emaFast);
                AddChartIndicator(emaMid);
                AddChartIndicator(emaSlow);
            }
        }

        // ═══════════════════════════════════════════════════════════════
        //  MAIN LOGIC - Called on every bar close
        // ═══════════════════════════════════════════════════════════════
        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade)
                return;

            // ── Daily reset ──
            CheckDailyReset();

            // ── VWAP ──
            UpdateVWAP();

            // ── Session time ──
            int barTime = ToTime(Time[0]);
            bool inTradingWindow = barTime >= SessionStartTime && barTime <= SessionEndTime;

            // ── Manage open position ──
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                if (pendingBreakevenMove)
                    ExecuteBreakevenMove();

                if (tp1Filled)
                    ManageTrailingStop();

                return;
            }

            // ══════════════════════════════════════════
            //  ENTRY FILTERS (all must pass)
            // ══════════════════════════════════════════

            if (!inTradingWindow)
                return;

            if (tradesToday >= MaxDailyTrades)
                return;

            if (dailyPnL <= -DailyLossLimit)
                return;

            if (consecutiveLosses >= MaxConsecutiveLosses)
                return;

            // Indicator values
            double emaF   = emaFast[0];
            double emaM   = emaMid[0];
            double emaS   = emaSlow[0];
            double rsiVal = rsi[0];
            double atrVal = atr[0];

            // Volatility filter
            if (atrVal < MinATRTicks * TickSize)
                return;

            // RSI filter
            if (rsiVal < RSILowerBound || rsiVal > RSIUpperBound)
                return;

            // ── Calculate risk levels in ticks ──
            double stopTicks = Math.Round(Math.Max(StopLossATRMult * atrVal / TickSize, 8));
            double tp1Ticks  = Math.Round(Math.Max(TakeProfit1ATRMult * atrVal / TickSize, 8));
            double tp2Ticks  = Math.Round(Math.Max(TakeProfit2ATRMult * atrVal / TickSize, 16));
            double tolerance = PullbackToleranceTicks * TickSize;

            // ── 3-5-7 Rule: Enforce minimum R:R on TP2 ──
            double minTp2Ticks = Math.Ceiling(stopTicks * MinRewardRiskRatio);
            tp2Ticks = Math.Max(tp2Ticks, minTp2Ticks);

            // ── 3-5-7 Rule: Dynamic position sizing ──
            int dynTP1, dynTP2;
            CalculatePositionSize(stopTicks, out dynTP1, out dynTP2);

            // ══════════════════════════════════════════
            //  LONG ENTRY (strong-close pullback)
            //  Pullback to EMA9/VWAP support zone
            //  with strong bullish close (top 30% of range)
            // ══════════════════════════════════════════
            double barRange = High[0] - Low[0];
            bool trendBullish = emaF > emaM && emaM > emaS;

            if (trendBullish && barRange > 0)
            {
                double supportZone  = Math.Min(emaFast[0], vwapValue);
                bool pullback       = Low[0] <= supportZone + tolerance;
                bool strongClose    = Close[0] >= Low[0] + 0.70 * barRange;  // close in top 30%
                bool aboveVWAP      = Close[0] > vwapValue;
                bool aboveEMA       = Close[0] > emaF;

                if (pullback && strongClose && aboveVWAP && aboveEMA)
                {
                    SetStopLoss("ScalpTP1", CalculationMode.Ticks, stopTicks, false);
                    SetStopLoss("ScalpTP2", CalculationMode.Ticks, stopTicks, false);
                    SetProfitTarget("ScalpTP1", CalculationMode.Ticks, tp1Ticks);
                    SetProfitTarget("ScalpTP2", CalculationMode.Ticks, tp2Ticks);

                    EnterLong(dynTP1, "ScalpTP1");
                    EnterLong(dynTP2, "ScalpTP2");

                    InitTradeState(1);
                    PrintEntry("LONG", atrVal, stopTicks, tp1Ticks, tp2Ticks);
                }
            }

            // ══════════════════════════════════════════
            //  SHORT ENTRY (strong-close pullback)
            //  Pullback to EMA9/VWAP resistance zone
            //  with strong bearish close (bottom 30% of range)
            // ══════════════════════════════════════════
            bool trendBearish = emaF < emaM && emaM < emaS;

            if (trendBearish && barRange > 0)
            {
                double resistanceZone = Math.Max(emaFast[0], vwapValue);
                bool pullback         = High[0] >= resistanceZone - tolerance;
                bool strongClose      = Close[0] <= High[0] - 0.70 * barRange;  // close in bottom 30%
                bool belowVWAP        = Close[0] < vwapValue;
                bool belowEMA         = Close[0] < emaF;

                if (pullback && strongClose && belowVWAP && belowEMA)
                {
                    SetStopLoss("ScalpTP1", CalculationMode.Ticks, stopTicks, false);
                    SetStopLoss("ScalpTP2", CalculationMode.Ticks, stopTicks, false);
                    SetProfitTarget("ScalpTP1", CalculationMode.Ticks, tp1Ticks);
                    SetProfitTarget("ScalpTP2", CalculationMode.Ticks, tp2Ticks);

                    EnterShort(dynTP1, "ScalpTP1");
                    EnterShort(dynTP2, "ScalpTP2");

                    InitTradeState(-1);
                    PrintEntry("SHORT", atrVal, stopTicks, tp1Ticks, tp2Ticks);
                }
            }
        }

        // ═══════════════════════════════════════════════════════════════
        //  EXECUTION TRACKING
        // ═══════════════════════════════════════════════════════════════
        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            // ── Track entry price ──
            if (execution.IsEntry)
            {
                currentEntryPrice = price;
                // Only count trade once (on first signal fill)
                if (execution.Order.Name == "ScalpTP1")
                    tradesToday++;
                return;
            }

            // ── Track exit P&L ──
            if (!execution.IsExit)
                return;

            double pnl;
            if (currentDirection == 1)
                pnl = (price - currentEntryPrice) * quantity * Instrument.MasterInstrument.PointValue;
            else
                pnl = (currentEntryPrice - price) * quantity * Instrument.MasterInstrument.PointValue;

            dailyPnL        += pnl;
            currentTradePnL += pnl;

            // ── Detect TP1 fill → activate breakeven + trailing ──
            if (execution.Order.FromEntrySignal == "ScalpTP1"
                && execution.Order.Name == "Profit target")
            {
                tp1Filled            = true;
                pendingBreakevenMove = true;
                Print(Time[0] + " | TP1 HIT at " + price.ToString("F2")
                    + " | +$" + pnl.ToString("F2"));
            }
            else
            {
                string exitType = execution.Order.Name;
                string sign     = pnl >= 0 ? "+" : "";
                Print(Time[0] + " | EXIT (" + exitType + ") from " + execution.Order.FromEntrySignal
                    + " at " + price.ToString("F2")
                    + " | " + sign + "$" + pnl.ToString("F2")
                    + " | Daily: $" + dailyPnL.ToString("F2"));
            }
        }

        // ═══════════════════════════════════════════════════════════════
        //  POSITION CLOSED → evaluate trade & reset state
        // ═══════════════════════════════════════════════════════════════
        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            if (marketPosition != MarketPosition.Flat)
                return;

            // Consecutive loss tracking (per trade, not per execution)
            if (currentTradePnL < 0)
                consecutiveLosses++;
            else if (currentTradePnL > 0)
                consecutiveLosses = 0;

            // 3-5-7 Rule: Update running equity
            cumulativePnL += currentTradePnL;
            double runningBalance = StartingCapital + cumulativePnL;

            Print("───────────────────────────────────────────");
            Print("  TRADE CLOSED | Net: $" + currentTradePnL.ToString("F2")
                + " | Daily P&L: $" + dailyPnL.ToString("F2")
                + " | Trades: " + tradesToday
                + " | Consec Losses: " + consecutiveLosses);
            Print("  Account: $" + runningBalance.ToString("F2")
                + " | Cumulative P&L: $" + cumulativePnL.ToString("F2"));
            Print("───────────────────────────────────────────");

            // Reset trade state
            currentDirection     = 0;
            tp1Filled            = false;
            pendingBreakevenMove = false;
            trailStopPrice       = 0;
            currentTradePnL      = 0;
        }

        // ═══════════════════════════════════════════════════════════════
        //  HELPER METHODS
        // ═══════════════════════════════════════════════════════════════
        #region Helpers

        private void InitTradeState(int direction)
        {
            currentDirection     = direction;
            tp1Filled            = false;
            pendingBreakevenMove = false;
            trailStopPrice       = 0;
            currentTradePnL      = 0;
        }

        /// <summary>
        /// Manual VWAP calculation. Resets each session.
        /// VWAP = Cumulative(TypicalPrice * Volume) / Cumulative(Volume)
        /// </summary>
        private void UpdateVWAP()
        {
            if (Bars.IsFirstBarOfSession)
            {
                cumulativeTPV = 0;
                cumulativeVol = 0;
            }

            double typicalPrice = (High[0] + Low[0] + Close[0]) / 3.0;
            double vol = Volume[0];

            if (vol > 0)
            {
                cumulativeTPV += typicalPrice * vol;
                cumulativeVol += vol;
            }

            vwapValue = cumulativeVol > 0
                ? cumulativeTPV / cumulativeVol
                : typicalPrice;
        }

        /// <summary>
        /// Reset counters at the start of each new trading day.
        /// Print daily summary for the previous day.
        /// </summary>
        private void CheckDailyReset()
        {
            if (Time[0].Date == lastSessionDate)
                return;

            // Print previous day summary
            if (lastSessionDate != DateTime.MinValue && tradesToday > 0)
            {
                double bal = StartingCapital + cumulativePnL;
                Print("═══════════════════════════════════════════");
                Print("  DAILY SUMMARY - " + lastSessionDate.ToShortDateString());
                Print("  Trades: " + tradesToday + " | Day P&L: $" + dailyPnL.ToString("F2"));
                Print("  Account: $" + bal.ToString("F2") + " | Cumulative: $" + cumulativePnL.ToString("F2"));
                Print("═══════════════════════════════════════════");
            }

            lastSessionDate      = Time[0].Date;
            tradesToday          = 0;
            dailyPnL             = 0;
            consecutiveLosses    = 0;
            tp1Filled            = false;
            pendingBreakevenMove = false;
            trailStopPrice       = 0;
            currentDirection     = 0;
            currentTradePnL      = 0;
        }

        /// <summary>
        /// After TP1 fills, move TP2's stop to breakeven + buffer ticks.
        /// Called from OnBarUpdate when pendingBreakevenMove is true.
        /// </summary>
        private void ExecuteBreakevenMove()
        {
            double bePrice;
            if (currentDirection == 1)
                bePrice = currentEntryPrice + BreakevenPlusTicks * TickSize;
            else
                bePrice = currentEntryPrice - BreakevenPlusTicks * TickSize;

            SetStopLoss("ScalpTP2", CalculationMode.Price, bePrice, false);
            trailStopPrice       = bePrice;
            pendingBreakevenMove = false;

            Print(Time[0] + " | STOP → BREAKEVEN+ at " + bePrice.ToString("F2"));
        }

        /// <summary>
        /// Trail TP2's stop using ATR distance. Only ratchets in the
        /// profitable direction (up for longs, down for shorts).
        /// </summary>
        private void ManageTrailingStop()
        {
            if (Position.MarketPosition == MarketPosition.Flat)
                return;

            double trailDistance = TrailingStopATRMult * atr[0];

            if (currentDirection == 1)
            {
                double newTrail = Close[0] - trailDistance;
                if (newTrail > trailStopPrice)
                {
                    trailStopPrice = newTrail;
                    SetStopLoss("ScalpTP2", CalculationMode.Price, trailStopPrice, false);
                }
            }
            else if (currentDirection == -1)
            {
                double newTrail = Close[0] + trailDistance;
                if (newTrail < trailStopPrice)
                {
                    trailStopPrice = newTrail;
                    SetStopLoss("ScalpTP2", CalculationMode.Price, trailStopPrice, false);
                }
            }
        }

        /// <summary>
        /// 3-5-7 Rule: Calculate position size based on account equity and risk limits.
        /// - 3% max risk per trade
        /// - 5% max total exposure
        /// - Minimum 2 contracts for partial exit strategy
        /// Falls back to fixed ContractsTP1/ContractsTP2 when UseDynamicSizing is off.
        /// </summary>
        private void CalculatePositionSize(double stopTicks, out int calcTP1, out int calcTP2)
        {
            if (!UseDynamicSizing)
            {
                calcTP1 = ContractsTP1;
                calcTP2 = ContractsTP2;
                lastCalcTP1 = calcTP1;
                lastCalcTP2 = calcTP2;
                return;
            }

            double accountBalance = StartingCapital + cumulativePnL;
            if (accountBalance <= 0)
            {
                calcTP1 = 1;
                calcTP2 = 1;
                lastCalcTP1 = calcTP1;
                lastCalcTP2 = calcTP2;
                return;
            }

            // 3% rule: max dollars at risk for this trade
            double maxRiskDollars  = accountBalance * (AccountRiskPercent / 100.0);
            double riskPerContract = stopTicks * TickSize * Instrument.MasterInstrument.PointValue;

            if (riskPerContract <= 0)
            {
                calcTP1 = 1;
                calcTP2 = 1;
                lastCalcTP1 = calcTP1;
                lastCalcTP2 = calcTP2;
                return;
            }

            int totalContracts = (int)Math.Floor(maxRiskDollars / riskPerContract);

            // 5% rule: total exposure cap (safety net when risk% is set high)
            double maxExposureDollars = accountBalance * (MaxExposurePercent / 100.0);
            int maxByExposure = (int)Math.Floor(maxExposureDollars / riskPerContract);
            totalContracts = Math.Min(totalContracts, maxByExposure);

            // Minimum 2 contracts for the partial exit strategy to work
            totalContracts = Math.Max(totalContracts, 2);

            // Split evenly between TP1 and TP2
            calcTP1 = totalContracts / 2;
            calcTP2 = totalContracts - calcTP1;

            lastCalcTP1 = calcTP1;
            lastCalcTP2 = calcTP2;
        }

        private void PrintEntry(string direction, double atrVal, double stopT, double tp1T, double tp2T)
        {
            double accountBalance  = StartingCapital + cumulativePnL;
            double riskPerContract = stopT * TickSize * Instrument.MasterInstrument.PointValue;
            int    totalContracts  = lastCalcTP1 + lastCalcTP2;
            double totalRisk       = totalContracts * riskPerContract;
            double riskPct         = accountBalance > 0 ? (totalRisk / accountBalance) * 100.0 : 0;
            double rr              = stopT > 0 ? tp2T / stopT : 0;

            Print("═══════════════════════════════════════════");
            Print("  " + direction + " ENTRY #" + tradesToday);
            Print("  Time:  " + Time[0]);
            Print("  Price: " + Close[0].ToString("F2") + " | VWAP: " + vwapValue.ToString("F2"));
            Print("  EMA9:  " + emaFast[0].ToString("F2")
                + " | EMA21: " + emaMid[0].ToString("F2")
                + " | EMA50: " + emaSlow[0].ToString("F2"));
            Print("  RSI:   " + rsi[0].ToString("F1")
                + " | ATR: " + (atrVal / TickSize).ToString("F0") + " ticks ("
                + atrVal.ToString("F2") + " pts)");
            Print("  Stop:  " + stopT + "t | TP1: " + tp1T + "t | TP2: " + tp2T + "t | R:R: " + rr.ToString("F2") + ":1");
            Print("  Size:  " + lastCalcTP1 + "+" + lastCalcTP2 + " = " + totalContracts
                + " contracts | Risk: $" + totalRisk.ToString("F2")
                + " (" + riskPct.ToString("F1") + "% of $" + accountBalance.ToString("F0") + ")");
            Print("  Daily: $" + dailyPnL.ToString("F2")
                + " | Trades: " + tradesToday
                + " | Consec L: " + consecutiveLosses);
            Print("───────────────────────────────────────────");
        }

        #endregion

        // ═══════════════════════════════════════════════════════════════
        //  CONFIGURABLE PARAMETERS
        //  All exposed in NinjaTrader's Strategy UI, grouped and ordered
        // ═══════════════════════════════════════════════════════════════
        #region Properties

        // ── 1. TREND ──

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Fast EMA Period",
            Description = "Fast EMA for short-term trend direction (default: 9)",
            Order = 1, GroupName = "1. Trend")]
        public int FastEMAPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Mid EMA Period",
            Description = "Mid EMA for medium-term trend direction (default: 21)",
            Order = 2, GroupName = "1. Trend")]
        public int MidEMAPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Slow EMA Period",
            Description = "Slow EMA for long-term trend direction (default: 50)",
            Order = 3, GroupName = "1. Trend")]
        public int SlowEMAPeriod { get; set; }

        // ── 2. ENTRY ──

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "RSI Period",
            Description = "RSI calculation period (default: 14)",
            Order = 1, GroupName = "2. Entry")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "RSI Lower Bound",
            Description = "Minimum RSI to allow entry - filters oversold reversals (default: 35)",
            Order = 2, GroupName = "2. Entry")]
        public int RSILowerBound { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100)]
        [Display(Name = "RSI Upper Bound",
            Description = "Maximum RSI to allow entry - filters overbought exhaustion (default: 65)",
            Order = 3, GroupName = "2. Entry")]
        public int RSIUpperBound { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Pullback Tolerance (Ticks)",
            Description = "How close price must get to VWAP/EMA support zone (default: 8)",
            Order = 4, GroupName = "2. Entry")]
        public int PullbackToleranceTicks { get; set; }

        // ── 3. VOLATILITY ──

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "ATR Period",
            Description = "ATR calculation period (default: 14)",
            Order = 1, GroupName = "3. Volatility")]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Min ATR (Ticks)",
            Description = "Minimum ATR in ticks required to trade - filters dead markets (default: 6)",
            Order = 2, GroupName = "3. Volatility")]
        public int MinATRTicks { get; set; }

        // ── 4. RISK MANAGEMENT ──

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Stop Loss (ATR x)",
            Description = "Stop loss distance as ATR multiplier (default: 1.5)",
            Order = 1, GroupName = "4. Risk Management")]
        public double StopLossATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Take Profit 1 (ATR x)",
            Description = "First partial target as ATR multiplier - locks quick profit (default: 1.0)",
            Order = 2, GroupName = "4. Risk Management")]
        public double TakeProfit1ATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Take Profit 2 (ATR x)",
            Description = "Second target / ceiling as ATR multiplier (default: 3.0)",
            Order = 3, GroupName = "4. Risk Management")]
        public double TakeProfit2ATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Trailing Stop (ATR x)",
            Description = "Trail distance after TP1 hit as ATR multiplier (default: 1.0)",
            Order = 4, GroupName = "4. Risk Management")]
        public double TrailingStopATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(0, 20)]
        [Display(Name = "Breakeven + Ticks",
            Description = "Extra ticks above breakeven after TP1 to cover commissions (default: 2)",
            Order = 5, GroupName = "4. Risk Management")]
        public int BreakevenPlusTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contracts TP1 (fixed)",
            Description = "Fixed contracts for TP1 - only used when UseDynamicSizing=false (default: 1)",
            Order = 6, GroupName = "4. Risk Management")]
        public int ContractsTP1 { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contracts TP2 (fixed)",
            Description = "Fixed contracts for TP2 - only used when UseDynamicSizing=false (default: 1)",
            Order = 7, GroupName = "4. Risk Management")]
        public int ContractsTP2 { get; set; }

        // ── 5. SESSION & LIMITS ──

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Session Start (HHMMSS)",
            Description = "Start time for new entries in exchange time (default: 93500 = 9:35 AM ET)",
            Order = 1, GroupName = "5. Session & Limits")]
        public int SessionStartTime { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Session End (HHMMSS)",
            Description = "Stop time for new entries in exchange time (default: 153000 = 3:30 PM ET)",
            Order = 2, GroupName = "5. Session & Limits")]
        public int SessionEndTime { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Max Daily Trades",
            Description = "Maximum number of entries per day (default: 8)",
            Order = 3, GroupName = "5. Session & Limits")]
        public int MaxDailyTrades { get; set; }

        [NinjaScriptProperty]
        [Range(0, double.MaxValue)]
        [Display(Name = "Daily Loss Limit ($)",
            Description = "Stop all trading after losing this amount in a day (default: $150)",
            Order = 4, GroupName = "5. Session & Limits")]
        public double DailyLossLimit { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Max Consecutive Losses",
            Description = "Stop trading after this many consecutive losing trades (default: 3)",
            Order = 5, GroupName = "5. Session & Limits")]
        public int MaxConsecutiveLosses { get; set; }

        // ── 6. POSITION SIZING (3-5-7 Rule) ──

        [NinjaScriptProperty]
        [Display(Name = "Use Dynamic Sizing",
            Description = "Calculate contracts from account equity and risk %. Disable to use fixed Contracts TP1/TP2 (default: true)",
            Order = 1, GroupName = "6. Position Sizing (3-5-7)")]
        public bool UseDynamicSizing { get; set; }

        [NinjaScriptProperty]
        [Range(500, double.MaxValue)]
        [Display(Name = "Starting Capital ($)",
            Description = "Initial account balance for position sizing calculations (default: $5,000)",
            Order = 2, GroupName = "6. Position Sizing (3-5-7)")]
        public double StartingCapital { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Risk Per Trade (%)",
            Description = "3-5-7 Rule: Max % of account to risk per trade (default: 3.0%)",
            Order = 3, GroupName = "6. Position Sizing (3-5-7)")]
        public double AccountRiskPercent { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 20.0)]
        [Display(Name = "Max Exposure (%)",
            Description = "3-5-7 Rule: Max % of account exposed across all positions (default: 5.0%)",
            Order = 4, GroupName = "6. Position Sizing (3-5-7)")]
        public double MaxExposurePercent { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Min Reward:Risk Ratio",
            Description = "3-5-7 Rule: Minimum R:R required to take a trade - TP2 auto-adjusts (default: 2.33)",
            Order = 5, GroupName = "6. Position Sizing (3-5-7)")]
        public double MinRewardRiskRatio { get; set; }

        #endregion
    }
}
