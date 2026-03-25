// KalmanZScore_v1 — Mean Reversion Estadística Pura
// Concepto: Kalman Filter estima el "precio justo" (fair value) en tiempo real.
//           Cuando el precio se desvía > ZEntry sigmas → entrada contrarian.
//           No hay indicadores técnicos. Solo estadística y teoría de procesos estocásticos.
//
// Matemática detrás:
//   Proceso O-U (Ornstein-Uhlenbeck): dX = θ(μ - X)dt + σdW
//   El Kalman Filter es el estimador óptimo de μ(t) bajo ruido gaussiano.
//   Z-score = (precio - kalmanEstimate) / rollingStd(residuales)
//
// Edge: El mercado genera over/undershoot sistemático respecto al fair value.
//       A ±2σ, la probabilidad de reversión es estadísticamente elevada.
//
// Archivo: Strategies/KalmanZScore_v1.cs

#region Using declarations
using System;
using System.Collections.Generic;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using System.Linq;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
#endregion

namespace NinjaTrader.NinjaScript.Strategies.Trader_Bot
{
    public class KalmanZScore_v1 : Strategy
    {
        // ── Kalman Filter State ──────────────────────────────────────────────
        private double kX;      // estado estimado: precio justo actual
        private double kP;      // covarianza del error de estimación
        private bool   kInit;   // si el filtro ya fue inicializado

        // ── Z-Score Rolling Window ───────────────────────────────────────────
        private Queue<double> resWindow = new Queue<double>();
        private double zScore;
        private double prevZScore;   // Z del bar anterior (para crossover)

        // ── Indicators ───────────────────────────────────────────────────────
        private ATR atrInd;
        private SMA volSma;
        private ADX adxInd;

        // ── Session Tracking ─────────────────────────────────────────────────
        private int      dailyTrades;
        private DateTime lastDate = DateTime.MinValue;

        // ====================================================================
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Mean-reversion estadística pura — Kalman fair value + Z-score | MNQ";
                Name        = "KalmanZScore_v1";

                // 1. Kalman Filter
                KalmanQ = 0.001;   // process noise: velocidad de cambio del precio justo
                KalmanR = 0.1;     // measurement noise: ruido en las observaciones

                // 2. Z-Score
                ZLookback = 30;    // ventana para calcular std dev de residuales
                ZEntry    = 2.0;   // umbral de entrada en sigmas

                // 3. Trade Management
                TargetRR        = 2.0;   // R:R objetivo
                StopATRMult     = 1.0;   // SL = entry ± StopATRMult × ATR
                ATRPeriod       = 14;
                UseCrossover    = true;  // true = entrar en crossover de vuelta (confirmación); false = entrar en extremo
                MaxTradesPerDay = 1;
                Quantity        = 1;

                // 3b. Regime Filter (ADX)
                UseADXFilter    = true;   // solo operar cuando mercado está en rango
                ADXPeriod       = 14;
                MaxADX          = 25.0;  // ADX < MaxADX = ranging → operar; ADX > MaxADX = trending → skip

                // 4. Volumen
                UseVolumeFilter = true;
                VolumePeriod    = 20;
                MinVolRatio     = 1.2;   // volumen mínimo relativo al SMA

                // 5. Dirección
                AllowLong  = true;
                AllowShort = true;   // en mean-reversion AMBAS tienen edge simétrico

                // 6. Horario
                UsePrimeHours = true;
                PrimeStart    = 93000;   // 9:30 ET
                PrimeEnd      = 153000;  // 15:30 ET

                // NT8 internals
                Calculate                    = Calculate.OnBarClose;
                EntriesPerDirection          = 1;
                EntryHandling                = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;
                BarsRequiredToTrade          = 50;
                StopTargetHandling           = StopTargetHandling.PerEntryExecution;
                TraceOrders                  = false;
            }
            else if (State == State.DataLoaded)
            {
                atrInd = ATR(ATRPeriod);
                volSma = SMA(Volume, VolumePeriod);
                adxInd = ADX(ADXPeriod);
                kX     = 0;
                kP     = 1.0;
                kInit  = false;
                zScore     = 0;
                prevZScore = 0;
                resWindow.Clear();
            }
        }

        // ── Kalman Filter Update ─────────────────────────────────────────────
        // Ecuaciones del filtro escalar:
        //   Predict:  P_pred = P + Q
        //   Gain:     K = P_pred / (P_pred + R)
        //   Update:   x_new = x + K * (observation - x)
        //             P_new = (1 - K) * P_pred
        private void KalmanUpdate(double price)
        {
            if (!kInit)
            {
                kX    = price;
                kP    = 1.0;
                kInit = true;
                return;
            }

            double pPred = kP + KalmanQ;
            double gain  = pPred / (pPred + KalmanR);
            kX = kX + gain * (price - kX);
            kP = (1.0 - gain) * pPred;
        }

        // ── Z-Score Update ───────────────────────────────────────────────────
        // residual = precio actual - estimación Kalman (desviación del fair value)
        // Z = (residual - mean_residual) / std_residual
        private void ZScoreUpdate(double price)
        {
            double residual = price - kX;
            resWindow.Enqueue(residual);
            if (resWindow.Count > ZLookback)
                resWindow.Dequeue();

            if (resWindow.Count < 5)
            {
                zScore = 0;
                return;
            }

            double[] arr  = resWindow.ToArray();
            double   mean = arr.Average();
            double   std  = Math.Sqrt(arr.Select(r => (r - mean) * (r - mean)).Average());

            zScore = std < 1e-9 ? 0 : (residual - mean) / std;
        }

        // ── Main Loop ────────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;

            // Reset diario
            if (Time[0].Date != lastDate)
            {
                dailyTrades = 0;
                lastDate    = Time[0].Date;
            }

            // Actualizar modelos matemáticos en cada barra (independiente de si hay trade)
            KalmanUpdate(Close[0]);
            prevZScore = zScore;
            ZScoreUpdate(Close[0]);

            // Si ya estamos en trade → no abrir más
            if (Position.MarketPosition != NinjaTrader.Cbi.MarketPosition.Flat) return;

            // Cap diario
            if (dailyTrades >= MaxTradesPerDay) return;

            // Horario prime
            if (UsePrimeHours)
            {
                int t = ToTime(Time[0]);
                if (t < PrimeStart || t >= PrimeEnd) return;
            }

            // Filtro de volumen
            if (UseVolumeFilter && volSma[0] > 0 && Volume[0] < MinVolRatio * volSma[0])
                return;

            // Filtro de régimen: solo operar en mercado ranging (ADX bajo)
            if (UseADXFilter && adxInd[0] >= MaxADX) return;

            double price  = Close[0];
            double atrVal = atrInd[0];
            if (atrVal <= 0) return;

            // ── LONG ─────────────────────────────────────────────────────────
            // Modo Extremo:   Z < -ZEntry → precio por debajo del fair value, entramos ahora
            // Modo Crossover: prevZ < -ZEntry Y Z > -ZEntry → confirmación de reversión (precio volviendo)
            bool longSignal = UseCrossover
                ? (prevZScore < -ZEntry && zScore > -ZEntry)
                : (zScore < -ZEntry);

            if (AllowLong && longSignal)
            {
                double sl   = price - StopATRMult * atrVal;
                double risk = price - sl;
                if (risk <= 0) return;
                double tp = price + risk * TargetRR;

                EnterLong(Quantity, "KLong");
                SetStopLoss   ("KLong", CalculationMode.Price, sl, false);
                SetProfitTarget("KLong", CalculationMode.Price, tp);
                dailyTrades++;
            }

            // ── SHORT ────────────────────────────────────────────────────────
            // Modo Extremo:   Z > +ZEntry → precio por encima del fair value, entramos ahora
            // Modo Crossover: prevZ > +ZEntry Y Z < +ZEntry → confirmación de reversión (precio volviendo)
            bool shortSignal = UseCrossover
                ? (prevZScore > ZEntry && zScore < ZEntry)
                : (zScore > ZEntry);

            if (AllowShort && shortSignal)
            {
                double sl   = price + StopATRMult * atrVal;
                double risk = sl - price;
                if (risk <= 0) return;
                double tp = price - risk * TargetRR;

                EnterShort(Quantity, "KShort");
                SetStopLoss   ("KShort", CalculationMode.Price, sl, false);
                SetProfitTarget("KShort", CalculationMode.Price, tp);
                dailyTrades++;
            }
        }

        // ====================================================================
        #region Properties

        [NinjaScriptProperty]
        [Range(0.000001, 1.0)]
        [Display(Name = "Q — Process Noise",
                 Description = "Velocidad con que el precio justo cambia. Alto = más reactivo, bajo = más suavizado.",
                 GroupName = "1. Kalman Filter", Order = 1)]
        public double KalmanQ { get; set; }

        [NinjaScriptProperty]
        [Range(0.001, 100.0)]
        [Display(Name = "R — Measurement Noise",
                 Description = "Ruido en las observaciones de precio. Alto = el filtro confía menos en el precio puntual.",
                 GroupName = "1. Kalman Filter", Order = 2)]
        public double KalmanR { get; set; }

        [NinjaScriptProperty]
        [Range(5, 300)]
        [Display(Name = "Z Lookback (barras)",
                 Description = "Ventana de barras para calcular std dev de los residuales del Kalman.",
                 GroupName = "2. Z-Score", Order = 1)]
        public int ZLookback { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 5.0)]
        [Display(Name = "Z Entry Threshold",
                 Description = "Umbral de entrada en sigmas. 2.0 = el precio está 2σ lejos del fair value.",
                 GroupName = "2. Z-Score", Order = 2)]
        public double ZEntry { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Target R:R",
                 GroupName = "3. Trade Management", Order = 1)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 5.0)]
        [Display(Name = "Stop ATR Mult",
                 Description = "SL = entrada ± StopATRMult × ATR(period)",
                 GroupName = "3. Trade Management", Order = 2)]
        public double StopATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "ATR Period",
                 GroupName = "3. Trade Management", Order = 3)]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Crossover (confirmación)",
                 Description = "true = entra cuando Z CRUZA DE VUELTA el umbral (confirmación). false = entra en el extremo.",
                 GroupName = "3. Trade Management", Order = 4)]
        public bool UseCrossover { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Max Trades/Día",
                 GroupName = "3. Trade Management", Order = 5)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contratos",
                 GroupName = "3. Trade Management", Order = 6)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro ADX",
                 Description = "Solo opera cuando ADX < MaxADX (mercado ranging). Evita mean-reversion en tendencia.",
                 GroupName = "3b. Regime Filter", Order = 1)]
        public bool UseADXFilter { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "ADX Period",
                 GroupName = "3b. Regime Filter", Order = 2)]
        public int ADXPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 50.0)]
        [Display(Name = "Max ADX (ranging threshold)",
                 Description = "ADX < este valor = mercado ranging → operar. ADX > = tendencia → skip.",
                 GroupName = "3b. Regime Filter", Order = 3)]
        public double MaxADX { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro Volumen",
                 GroupName = "4. Volumen", Order = 1)]
        public bool UseVolumeFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name = "Periodo SMA Volumen",
                 GroupName = "4. Volumen", Order = 2)]
        public int VolumePeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 5.0)]
        [Display(Name = "Volumen mínimo (×SMA)",
                 GroupName = "4. Volumen", Order = 3)]
        public double MinVolRatio { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long",
                 GroupName = "5. Dirección", Order = 1)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short",
                 GroupName = "5. Dirección", Order = 2)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Prime Hours",
                 GroupName = "6. Horario", Order = 1)]
        public bool UsePrimeHours { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Inicio (HHMMSS)",
                 GroupName = "6. Horario", Order = 2)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Fin (HHMMSS)",
                 GroupName = "6. Horario", Order = 3)]
        public int PrimeEnd { get; set; }

        #endregion
    }
}
