// MomentumZ_v1 — Momentum Normalizado por Volatilidad (Intraday Time-Series Momentum)
//
// Concepto quant:
//   MomScore = (Close[ahora] - Close[N barras atrás]) / ATR[0]
//
//   = "cuántos ATRs se movió el precio en las últimas N barras"
//   = equivalente intradiario del Sharpe ratio de momentum de AQR/Moskowitz
//
// Edge: Si el precio se movió 3+ ATRs en una dirección → no es ruido aleatorio,
//        es momentum estadísticamente significativo → lo seguimos.
//
// A diferencia de EMA crossover:
//   - Mide RETORNOS (cambio relativo), no precio absoluto
//   - Normalizado por VOLATILIDAD actual (adapta al régimen automáticamente)
//   - Sin lag → señal instantánea sobre ventana N
//   - Mercado flat (MomScore ≈ 0) → no entra. Impulso real (MomScore >> 3) → entra.
//
// Archivo: Strategies/MomentumZ_v1.cs

#region Using declarations
using System;
using System.ComponentModel;
using System.ComponentModel.DataAnnotations;
using NinjaTrader.Cbi;
using NinjaTrader.Data;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
using NetMQ;
using NetMQ.Sockets;
#endregion

namespace NinjaTrader.NinjaScript.Strategies.Trader_Bot
{
    public class MomentumZ_v1 : Strategy
    {
        // ── Indicators ───────────────────────────────────────────────────────
        private ATR atrInd;
        private SMA volSma;

        // ── Session Tracking ─────────────────────────────────────────────────
        private int      dailyTrades;
        private DateTime lastDate = DateTime.MinValue;

        // ── Cached signal value (for debugging) ─────────────────────────────
        private double lastMomScore;

        // ── ML Filter ────────────────────────────────────────────────────────
        private RequestSocket mlSocket      = null;
        private string        mlTradeId     = "";
        private string        mlEntryContext = "";

        // ====================================================================
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Momentum intradiario normalizado por volatilidad — MomScore = ΔPrecio/ATR | MNQ";
                Name        = "MomentumZ_v1";

                // 1. Momentum Signal
                LookbackBars  = 10;    // barras hacia atrás para medir el movimiento
                MomThreshold  = 3.0;   // señal mínima en ATRs para considerar "momentum significativo"

                // 2. Trade Management
                TargetRR        = 2.0;
                StopATRMult     = 1.5;   // stop un poco más amplio — momentum puede continuar antes de revertir
                ATRPeriod       = 14;
                MaxTradesPerDay = 1;
                Quantity        = 1;

                // 3. Volumen
                UseVolumeFilter = true;
                VolumePeriod    = 20;
                MinVolRatio     = 1.2;

                // 4. Dirección
                AllowLong  = true;
                AllowShort = true;

                // 5. Horario
                UsePrimeHours = true;
                PrimeStart    = 93000;
                PrimeEnd      = 153000;

                // 6. ML Filter
                UseMLFilter = false;
                MLPort      = 5556;

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

                if (UseMLFilter)
                {
                    AsyncIO.ForceDotNet.Force();
                    mlSocket = new RequestSocket();
                    mlSocket.Connect("tcp://127.0.0.1:" + MLPort);
                    mlSocket.Options.SendTimeout    = TimeSpan.FromMilliseconds(400);
                    mlSocket.Options.ReceiveTimeout = TimeSpan.FromMilliseconds(400);
                }
            }
            else if (State == State.Terminated)
            {
                if (mlSocket != null) { try { mlSocket.Close(); } catch { } mlSocket = null; }
            }
        }

        // ── ML Filter ────────────────────────────────────────────────────────
        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                mlTradeId = Guid.NewGuid().ToString("N").Substring(0, 8);
                double volRatio = (volSma != null && volSma[0] > 0) ? Volume[0] / volSma[0] : 1.0;
                double momSlope = lastMomScore; // MomScore normalizado en ATRs

                mlEntryContext = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"MomentumZ_v1\"," +
                    "\"trade_id\":\"{0}\",\"direction\":{1}," +
                    "\"rsi\":50.0,\"adx\":25.0,\"vol_ratio\":{2}," +
                    "\"dist_htf\":0.0,\"ema_slope\":{3}," +
                    "\"hour\":{4},\"minute\":{5},\"day_of_week\":{6}," +
                    "\"signal_type\":{7}}}",
                    mlTradeId, direction,
                    volRatio.ToString("F3", System.Globalization.CultureInfo.InvariantCulture),
                    momSlope.ToString("F3", System.Globalization.CultureInfo.InvariantCulture),
                    Time[0].Hour, Time[0].Minute, (int)Time[0].DayOfWeek, signalType);

                mlSocket.SendFrame(mlEntryContext);
                string resp = mlSocket.ReceiveFrameString();

                int idx = resp.IndexOf("\"allow\":");
                if (idx >= 0)
                {
                    char c = resp[idx + 8];
                    return c == '1';
                }
                return true;
            }
            catch { return true; }
        }

        private void LogMLOutcome(double pnl)
        {
            if (mlSocket == null || mlTradeId == "") return;
            try
            {
                string msg = string.Format(
                    "{{\"type\":\"outcome\",\"strategy\":\"MomentumZ_v1\"," +
                    "\"trade_id\":\"{0}\",\"pnl\":{1}}}",
                    mlTradeId,
                    pnl.ToString("F2", System.Globalization.CultureInfo.InvariantCulture));
                mlSocket.SendFrame(msg);
                mlSocket.ReceiveFrameString();
                mlTradeId = "";
            }
            catch { mlTradeId = ""; }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition,
            string orderId, DateTime time)
        {
            if (!UseMLFilter) return;
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            if (marketPosition == MarketPosition.Flat)
            {
                var all = SystemPerformance.AllTrades;
                if (all.Count > 0)
                    LogMLOutcome(all[all.Count - 1].ProfitCurrency);
            }
        }

        // ── Main Loop ────────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade) return;
            if (CurrentBar < LookbackBars)        return;

            // Reset diario
            if (Time[0].Date != lastDate)
            {
                dailyTrades = 0;
                lastDate    = Time[0].Date;
            }

            // ── Calcular MomScore ────────────────────────────────────────────
            // MomScore = (precio actual - precio N barras atrás) / ATR
            // Unidades: ATRs — completamente normalizado por régimen de volatilidad
            double atrVal = atrInd[0];
            if (atrVal <= 0) return;

            double priceNow  = Close[0];
            double priceBack = Close[LookbackBars];
            lastMomScore     = (priceNow - priceBack) / atrVal;

            // ── Filtros pre-entrada ──────────────────────────────────────────
            if (Position.MarketPosition != NinjaTrader.Cbi.MarketPosition.Flat) return;
            if (dailyTrades >= MaxTradesPerDay) return;

            if (UsePrimeHours)
            {
                int t = ToTime(Time[0]);
                if (t < PrimeStart || t >= PrimeEnd) return;
            }

            if (UseVolumeFilter && volSma[0] > 0 && Volume[0] < MinVolRatio * volSma[0])
                return;

            // ── LONG ─────────────────────────────────────────────────────────
            // MomScore > MomThreshold → el precio subió MomThreshold ATRs en N barras
            // → momentum alcista estadísticamente significativo → seguirlo
            if (AllowLong && lastMomScore > MomThreshold)
            {
                double sl   = priceNow - StopATRMult * atrVal;
                double risk = priceNow - sl;
                if (risk <= 0) return;
                double tp = priceNow + risk * TargetRR;

                if (UseMLFilter && !QueryMLFilter(1, 0)) return;
                EnterLong(Quantity, "MZLong");
                SetStopLoss   ("MZLong", CalculationMode.Price, sl, false);
                SetProfitTarget("MZLong", CalculationMode.Price, tp);
                dailyTrades++;
            }

            // ── SHORT ────────────────────────────────────────────────────────
            // MomScore < -MomThreshold → el precio bajó MomThreshold ATRs en N barras
            // → momentum bajista estadísticamente significativo → seguirlo
            else if (AllowShort && lastMomScore < -MomThreshold)
            {
                double sl   = priceNow + StopATRMult * atrVal;
                double risk = sl - priceNow;
                if (risk <= 0) return;
                double tp = priceNow - risk * TargetRR;

                if (UseMLFilter && !QueryMLFilter(-1, 0)) return;
                EnterShort(Quantity, "MZShort");
                SetStopLoss   ("MZShort", CalculationMode.Price, sl, false);
                SetProfitTarget("MZShort", CalculationMode.Price, tp);
                dailyTrades++;
            }
        }

        // ====================================================================
        #region Properties

        [NinjaScriptProperty]
        [Range(2, 100)]
        [Display(Name = "Lookback Bars (N)",
                 Description = "Barras hacia atrás para medir el movimiento del precio. Más alto = señal más lenta pero más significativa.",
                 GroupName = "1. Momentum Signal", Order = 1)]
        public int LookbackBars { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Momentum Threshold (ATRs)",
                 Description = "Señal mínima para entrar. 3.0 = el precio se movió 3 ATRs en N barras. Más alto = menos trades, más calidad.",
                 GroupName = "1. Momentum Signal", Order = 2)]
        public double MomThreshold { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Target R:R",
                 GroupName = "2. Trade Management", Order = 1)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 5.0)]
        [Display(Name = "Stop ATR Mult",
                 Description = "SL = entrada ± StopATRMult × ATR. Más ancho que KalmanZScore porque momentum puede continuar.",
                 GroupName = "2. Trade Management", Order = 2)]
        public double StopATRMult { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "ATR Period",
                 GroupName = "2. Trade Management", Order = 3)]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Max Trades/Día",
                 GroupName = "2. Trade Management", Order = 4)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Contratos",
                 GroupName = "2. Trade Management", Order = 5)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Filtro Volumen",
                 GroupName = "3. Volumen", Order = 1)]
        public bool UseVolumeFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name = "Periodo SMA Volumen",
                 GroupName = "3. Volumen", Order = 2)]
        public int VolumePeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 5.0)]
        [Display(Name = "Volumen mínimo (×SMA)",
                 GroupName = "3. Volumen", Order = 3)]
        public double MinVolRatio { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long",
                 GroupName = "4. Dirección", Order = 1)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short",
                 GroupName = "4. Dirección", Order = 2)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Prime Hours",
                 GroupName = "5. Horario", Order = 1)]
        public bool UsePrimeHours { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Inicio (HHMMSS)",
                 GroupName = "5. Horario", Order = 2)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Fin (HHMMSS)",
                 GroupName = "5. Horario", Order = 3)]
        public int PrimeEnd { get; set; }

        // === 6. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML", Order = 1, GroupName = "6. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(1024, 65535)]
        [Display(Name = "Puerto ZMQ", Order = 2, GroupName = "6. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
