(Statistical Arb Cointegración – la más robusta y market-neutral)
---
#region Using declarations
using System;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class NQ_ES_Spread : Strategy
    {
        private double beta = 1.68; // se recalcula cada día
        private double spreadMean, spreadStd;
        private double RiskDollars = 650;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = "NQ-ES Cointegration Spread - Apex 300K";
                Name                                        = "NQ_ES_Spread";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                BarsRequiredToTrade                         = 200;
                RiskDollars                                 = 650;
            }
            else if (State == State.Configure)
            {
                AddDataSeries("ES", PeriodType.Minute, 5); // Serie ES automática
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBars[0] < 200 || CurrentBars[1] < 200) return;

            // Recalcular beta y spread cada nuevo día
            if (IsFirstTickOfBar && ToTime(Time[0]) % 86400000 == 0)
                CalculateBetaAndSpreadStats();

            double spread = Closes[0][0] - beta * Closes[1][0];

            if (Position.MarketPosition == 0 && Math.Abs(spread - spreadMean) > 2.5 * spreadStd)
            {
                int size = CalculatePositionSize() / 2; // dollar-neutral
                if (spread > spreadMean + 2.5 * spreadStd)
                {
                    EnterShort(size, "NQShort");
                    EnterLong(size, "ESLong", 1);
                }
                else
                {
                    EnterLong(size, "NQLong");
                    EnterShort(size, "ESShort", 1);
                }
            }

            // Salida cuando spread cruza media
            if (Position.MarketPosition != 0 && Math.Abs(spread - spreadMean) < 0.3 * spreadStd)
            {
                ExitLong();
                ExitShort();
            }
        }

        private void CalculateBetaAndSpreadStats()
        {
            // Beta rolling simple (OLS último 200 barras)
            double sumX = 0, sumY = 0, sumXY = 0, sumX2 = 0;
            for (int i = 0; i < 200; i++)
            {
                double x = Closes[1][i]; // ES
                double y = Closes[0][i]; // NQ
                sumX += x; sumY += y; sumXY += x * y; sumX2 += x * x;
            }
            beta = (200 * sumXY - sumX * sumY) / (200 * sumX2 - sumX * sumX);

            // Spread stats
            double sumSpread = 0, sumSq = 0;
            for (int i = 0; i < 200; i++)
            {
                double sp = Closes[0][i] - beta * Closes[1][i];
                sumSpread += sp;
                sumSq += sp * sp;
            }
            spreadMean = sumSpread / 200;
            spreadStd = Math.Sqrt((sumSq / 200) - spreadMean * spreadMean);
        }

        private int CalculatePositionSize()
        {
            double stopPoints = 30;
            int size = (int)(RiskDollars / (stopPoints * 20));
            return Math.Max(1, Math.Min(size, 10));
        }
    }
}