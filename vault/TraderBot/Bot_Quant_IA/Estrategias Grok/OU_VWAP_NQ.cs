(Mean Reversion Intraday con VWAP + Z-Score)
---
#region Using declarations
using System;
using System.Collections.Generic;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class OU_VWAP_NQ : Strategy
    {
        private VWAP vwap;
        private double RiskDollars = 650;
        private List<double> deviationHistory = new List<double>();

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = "Mean Reversion VWAP + Z-Score - Apex 300K";
                Name                                        = "OU_VWAP_NQ";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                BarsRequiredToTrade                         = 100;
                RiskDollars                                 = 650;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBars[0] < 100) return;
            if (vwap == null) vwap = VWAP();

            double deviation = Close[0] - vwap[0];
            deviationHistory.Add(deviation);
            if (deviationHistory.Count > 200) deviationHistory.RemoveAt(0);

            double meanDev = deviationHistory.Average();
            double stdDev = Math.Sqrt(deviationHistory.Sum(d => Math.Pow(d - meanDev, 2)) / deviationHistory.Count);
            double zScore = stdDev > 0 ? (deviation - meanDev) / stdDev : 0;

            // Entrada (Z > 2.2 y half-life estimado rápido)
            if (Position.MarketPosition == 0 && Math.Abs(zScore) > 2.2)
            {
                int size = CalculatePositionSize();
                if (zScore < -2.2) EnterLong(size, "LongMR");
                if (zScore > 2.2) EnterShort(size, "ShortMR");
            }

            // Salida en VWAP o 50% recuperación
            if (Position.MarketPosition > 0 && Close[0] > vwap[0] * 0.995)
                ExitLong();
            if (Position.MarketPosition < 0 && Close[0] < vwap[0] * 1.005)
                ExitShort();
        }

        private int CalculatePositionSize()
        {
            double stopPoints = 25;
            int size = (int)(RiskDollars / (stopPoints * 20));
            return Math.Max(1, Math.Min(size, 12));
        }
    }
}