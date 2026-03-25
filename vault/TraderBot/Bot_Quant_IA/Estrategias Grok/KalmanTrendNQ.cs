(Trend Following Adaptativo – la que más uso en NQ)
---
#region Using declarations
using System;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class KalmanTrendNQ : Strategy
    {
        private EMA ema8;
        private EMA ema21;

        // Estado Kalman (velocity model)
        private double x0, x1;           // precio estado, velocidad
        private double p00, p01, p10, p11; // matriz covarianza 2x2
        private bool initialized = false;

        private double RiskDollars = 650;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                                 = "Kalman + EMA8/21 - Apex 300K ready";
                Name                                        = "KalmanTrendNQ";
                Calculate                                   = Calculate.OnBarClose;
                EntriesPerDirection                         = 1;
                EntryHandling                               = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy                = true;
                ExitOnSessionCloseSeconds                   = 30;
                IsFillLimitOnTouch                          = false;
                MaximumBarsLookBack                         = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                         = OrderFillResolution.Standard;
                Slippage                                    = 1;
                StartBehavior                               = StartBehavior.WaitUntilFlat;
                TimeInForce                                 = TimeInForce.Gtc;
                TraceOrders                                 = false;
                RealtimeErrorHandling                       = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                          = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                         = 100;
                RiskDollars                                 = 650;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBars[0] < 50) return;

            if (ema8 == null)
            {
                ema8 = EMA(8);
                ema21 = EMA(21);
            }

            // Inicialización Kalman
            if (!initialized)
            {
                x0 = Close[0];
                x1 = 0;
                p00 = 1; p01 = 0; p10 = 0; p11 = 1;
                initialized = true;
            }

            // Kalman Filter (constant velocity model) - hardcoded 2x2 para máxima velocidad
            double dt = 1.0;
            double Q = 1e-5;
            double R = 0.01;

            // Predict
            double x0_pred = x0 + x1 * dt;
            double x1_pred = x1;
            double p00_pred = p00 + 2 * p01 * dt + p11 * dt * dt + Q;
            double p01_pred = p01 + p11 * dt;
            double p10_pred = p01_pred;
            double p11_pred = p11 + Q;

            // Update
            double innovation = Close[0] - x0_pred;
            double S = p00_pred + R;
            double k0 = p00_pred / S;
            double k1 = p01_pred / S;

            x0 = x0_pred + k0 * innovation;
            x1 = x1_pred + k1 * innovation;

            p00 = p00_pred - k0 * p00_pred;
            p01 = p01_pred - k0 * p01_pred;
            p10 = p01;
            p11 = p11_pred - k1 * p01_pred;

            double kalmanVelocity = x1;

            // === ENTRADAS ===
            if (Position.MarketPosition == 0)
            {
                int size = CalculatePositionSize();
                if (kalmanVelocity > 0 && Close[0] > ema8[0] && ema8[0] > ema21[0])
                    EnterLong(size, "LongKalman");

                if (kalmanVelocity < 0 && Close[0] < ema8[0] && ema8[0] < ema21[0])
                    EnterShort(size, "ShortKalman");
            }

            // === SALIDAS ===
            if (Position.MarketPosition > 0 && kalmanVelocity < 0)
                ExitLong("ExitKalman");
            if (Position.MarketPosition < 0 && kalmanVelocity > 0)
                ExitShort("ExitKalman");
        }

        private int CalculatePositionSize()
        {
            double stopPoints = 40; // 40 puntos = ~$800 riesgo bruto antes de sizing
            int size = (int)(RiskDollars / (stopPoints * 20)); // NQ = $20 por punto
            size = Math.Max(1, Math.Min(size, 15)); // límite Apex seguro
            return size;
        }
    }
}