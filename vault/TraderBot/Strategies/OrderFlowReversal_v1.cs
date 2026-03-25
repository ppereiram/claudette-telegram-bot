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

/*
 * OrderFlowReversal_v1
 * ====================
 * Concepto: Order flow sin Tick Replay — usa volumen por brick como proxy
 *           del flujo institucional.
 *
 * Lógica: Causa → Efecto → Confirmación
 *
 *   Absorption  = N bricks consecutivos en misma dirección con volumen CRECIENTE
 *                 (más esfuerzo por brick = alguien absorbe la presión contraria)
 *
 *   Exhaustion  = M bricks consecutivos en misma dirección con volumen DECRECIENTE
 *                 (el lado dominante pierde combustible)
 *
 *   Push        = Primer brick en dirección CONTRARIA con volumen > SMA(Vol) × MinRatio
 *                 (el otro lado toma control con presión real)
 *
 * BEARISH REVERSAL (SHORT):
 *   Absorption ↑ (bricks UP vol creciente)
 *   Exhaustion ↑ (bricks UP vol decreciente)
 *   Push       ↓ (brick DOWN vol alto)  ← ENTRY SHORT
 *   SL = max HIGH de toda la secuencia + buffer
 *   TP = entry - riesgo × TargetRR
 *
 * BULLISH REVERSAL (LONG):
 *   Absorption ↓ (bricks DOWN vol creciente)
 *   Exhaustion ↓ (bricks DOWN vol decreciente)
 *   Push       ↑ (brick UP vol alto)    ← ENTRY LONG
 *   SL = min LOW de toda la secuencia - buffer
 *   TP = entry + riesgo × TargetRR
 *
 * Chart recomendado: Renko 35-40 tick MNQ
 * AllowShort: ON — reversals son simétricos
 */

namespace NinjaTrader.NinjaScript.Strategies
{
    public class OrderFlowReversal_v1 : Strategy
    {
        // ── Indicadores ──────────────────────────────────────────────
        private SMA volSMA;

        // ML Filter (ZMQ)
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        // ── Estado ───────────────────────────────────────────────────
        private int      dailyTradeCount;
        private DateTime sessionDate = DateTime.MinValue;
        private double   entryPx, slPx;
        private bool     beApplied;
        private string   activeSig = "";

        // Timezone — ET incluye EST y EDT automáticamente
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        // ────────────────────────────────────────────────────────────
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                  = "Order Flow Reversal: Absorption → Exhaustion → Push en Renko sin Tick Replay";
                Name                         = "OrderFlowReversal_v1";
                Calculate                    = Calculate.OnBarClose;
                IsOverlay                    = true;
                BarsRequiredToTrade          = 30;
                StopTargetHandling           = StopTargetHandling.PerEntryExecution;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;
                Slippage                     = 1;

                // — Order Flow —
                AbsorptionBricks  = 3;     // bricks con volumen creciente (absorción)
                ExhaustionBricks  = 2;     // bricks con volumen decreciente (agotamiento)
                VolumeSMAPeriod   = 20;    // SMA de volumen para referencia del push
                MinVolRatioPush   = 1.3;   // push debe tener vol >= 1.3× SMA

                // — Risk / Reward —
                TargetRR          = 2.0;   // R:R objetivo
                BreakevenR        = 1.0;   // mover SL a BE cuando ganancia >= 1R
                StopBufferTicks   = 6;     // ticks de buffer sobre el extremo de la secuencia

                // — Trade Management —
                MaxTradesPerDay   = 1;
                Quantity          = 1;

                // — Dirección —
                AllowLong         = true;
                AllowShort        = true;

                // — Horario —
                UsePrimeHours     = true;
                PrimeStart        = 93000;   // 9:30 ET
                PrimeEnd          = 153000;  // 15:30 ET

                // — ML Filter —
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                volSMA = SMA(Volume, VolumeSMAPeriod);

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("OFR ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("OFR ML: Error al conectar ZMQ: {0}", ex.Message));
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

        // ────────────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            // Necesitamos al menos abs + exh + 1 barras históricas
            int minBars = AbsorptionBricks + ExhaustionBricks + 1;
            if (CurrentBar < BarsRequiredToTrade + minBars) return;

            // ── Reset diario ──────────────────────────────────────────
            if (Time[0].Date != sessionDate)
            {
                dailyTradeCount = 0;
                beApplied       = false;
                activeSig       = "";
                sessionDate     = Time[0].Date;
            }

            // ── Gestión de breakeven ───────────────────────────────────
            ManageBreakeven();

            // ── Gates ─────────────────────────────────────────────────
            if (Position.MarketPosition != MarketPosition.Flat) return;
            if (dailyTradeCount >= MaxTradesPerDay) return;

            if (UsePrimeHours)
            {
                int t = GetEtTime();
                if (t < PrimeStart || t >= PrimeEnd) return;
            }

            // ── Detectar patrones y entrar ─────────────────────────────
            if (AllowShort && IsBearishReversal())
                TryEnterShort();
            else if (AllowLong && IsBullishReversal())
                TryEnterLong();
        }

        // ────────────────────────────────────────────────────────────
        // BEARISH REVERSAL
        // ─────────────────────────────────────────────────────────────
        // Índices (0 = más reciente):
        //   [0]             = Push brick: DOWN, volumen alto
        //   [1 .. exh]      = Exhaustion: UP bricks, volumen DECRECIENTE hacia [0]
        //   [exh+1 .. total]= Absorption: UP bricks, volumen CRECIENTE hacia [exh+1]
        //
        // "Creciente hacia el presente" = decreciente en índices (index 3 > index 4 > index 5)
        // "Decreciente hacia el presente" = creciente en índices (index 1 < index 2)
        private bool IsBearishReversal()
        {
            int exh   = ExhaustionBricks;
            int total = AbsorptionBricks + ExhaustionBricks;

            // ── Push: brick actual debe ser DOWN con volumen alto ───────
            if (Close[0] >= Open[0]) return false;                              // no es DOWN
            if (volSMA[0] <= 0)      return false;
            if (Volume[0] < volSMA[0] * MinVolRatioPush) return false;          // vol insuficiente

            // ── Exhaustion: bricks [1..exh] deben ser UP con vol decreciente ──
            // Decreciente hacia el presente: Volume[1] < Volume[2] < ... < Volume[exh]
            for (int i = 1; i <= exh; i++)
            {
                if (Close[i] <= Open[i]) return false;                          // debe ser UP
                if (i < exh && Volume[i] >= Volume[i + 1]) return false;        // vol debe bajar
            }

            // ── Absorption: bricks [exh+1..total] deben ser UP con vol creciente ──
            // Creciente hacia el presente: Volume[exh+1] > Volume[exh+2] > ... > Volume[total]
            for (int i = exh + 1; i <= total; i++)
            {
                if (Close[i] <= Open[i]) return false;                          // debe ser UP
                if (i < total && Volume[i] <= Volume[i + 1]) return false;      // vol debe subir
            }

            return true;
        }

        // ────────────────────────────────────────────────────────────
        // BULLISH REVERSAL
        // ─────────────────────────────────────────────────────────────
        // Índices:
        //   [0]             = Push brick: UP, volumen alto
        //   [1 .. exh]      = Exhaustion: DOWN bricks, volumen DECRECIENTE hacia [0]
        //   [exh+1 .. total]= Absorption: DOWN bricks, volumen CRECIENTE hacia [exh+1]
        private bool IsBullishReversal()
        {
            int exh   = ExhaustionBricks;
            int total = AbsorptionBricks + ExhaustionBricks;

            // ── Push: brick actual debe ser UP con volumen alto ─────────
            if (Close[0] <= Open[0]) return false;                              // no es UP
            if (volSMA[0] <= 0)      return false;
            if (Volume[0] < volSMA[0] * MinVolRatioPush) return false;          // vol insuficiente

            // ── Exhaustion: bricks [1..exh] deben ser DOWN con vol decreciente ──
            for (int i = 1; i <= exh; i++)
            {
                if (Close[i] >= Open[i]) return false;                          // debe ser DOWN
                if (i < exh && Volume[i] >= Volume[i + 1]) return false;        // vol debe bajar
            }

            // ── Absorption: bricks [exh+1..total] deben ser DOWN con vol creciente ──
            for (int i = exh + 1; i <= total; i++)
            {
                if (Close[i] >= Open[i]) return false;                          // debe ser DOWN
                if (i < total && Volume[i] <= Volume[i + 1]) return false;      // vol debe subir
            }

            return true;
        }

        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                int    etTime   = GetEtTime();
                int    hour     = etTime / 10000;
                int    minute   = (etTime % 10000) / 100;
                int    dow      = (int)Time[0].DayOfWeek;
                double volRatio = volSMA[0] > 0 ? Volume[0] / volSMA[0] : 1.0;

                mlTradeId = string.Format("OFR_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"OrderFlowReversal_v1\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":50.0,\"adx\":25.0," +
                    "\"vol_ratio\":{2:F3},\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{3},\"minute\":{4},\"day_of_week\":{5},\"signal_type\":{6}}}",
                    mlTradeId, direction, volRatio, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("OFR ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (!allow) Print(string.Format("OFR ML bloqueado [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("OFR ML Error: {0} — permitiendo trade", ex.Message));
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
                    "{{\"type\":\"outcome\",\"strategy\":\"OrderFlowReversal_v1\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("OFR ML outcome error: {0}", ex.Message)); }
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

        // ────────────────────────────────────────────────────────────
        private void TryEnterShort()
        {
            int total = AbsorptionBricks + ExhaustionBricks;

            // SL = high más alto de toda la secuencia + buffer
            double seqHigh = double.MinValue;
            for (int i = 1; i <= total; i++)
                seqHigh = Math.Max(seqHigh, High[i]);

            double sl   = seqHigh + StopBufferTicks * TickSize;
            double risk = sl - Close[0];
            if (risk <= 0) return;

            double tp = Close[0] - risk * TargetRR;

            // ML gate
            if (UseMLFilter && !QueryMLFilter(-1, 0)) return;

            SetStopLoss(    "OFR_S", CalculationMode.Price, sl, false);
            SetProfitTarget("OFR_S", CalculationMode.Price, tp);
            EnterShort(Quantity, "OFR_S");

            entryPx       = Close[0];
            slPx          = sl;
            beApplied     = false;
            activeSig     = "OFR_S";
            dailyTradeCount++;

            // Visualización
            Draw.ArrowDown(this, "SE_" + CurrentBar, false, 0,
                           High[0] + 3 * TickSize, Brushes.OrangeRed);
            Draw.Line(this, "SL_S_" + CurrentBar, false,
                      total + 2, sl, 0, sl, Brushes.Red, DashStyleHelper.Dash, 1);
            Draw.Line(this, "TP_S_" + CurrentBar, false,
                      total + 2, tp, 0, tp, Brushes.DodgerBlue, DashStyleHelper.Dash, 1);

            // Marcar secuencia en chart
            for (int i = 1; i <= ExhaustionBricks; i++)
                Draw.Dot(this, "EXH_" + CurrentBar + "_" + i, false, i,
                         High[i] + TickSize, Brushes.Yellow);
            for (int i = ExhaustionBricks + 1; i <= total; i++)
                Draw.Dot(this, "ABS_" + CurrentBar + "_" + i, false, i,
                         High[i] + TickSize, Brushes.Cyan);
        }

        // ────────────────────────────────────────────────────────────
        private void TryEnterLong()
        {
            int total = AbsorptionBricks + ExhaustionBricks;

            // SL = low más bajo de toda la secuencia - buffer
            double seqLow = double.MaxValue;
            for (int i = 1; i <= total; i++)
                seqLow = Math.Min(seqLow, Low[i]);

            double sl   = seqLow - StopBufferTicks * TickSize;
            double risk = Close[0] - sl;
            if (risk <= 0) return;

            double tp = Close[0] + risk * TargetRR;

            // ML gate
            if (UseMLFilter && !QueryMLFilter(1, 0)) return;

            SetStopLoss(    "OFR_L", CalculationMode.Price, sl, false);
            SetProfitTarget("OFR_L", CalculationMode.Price, tp);
            EnterLong(Quantity, "OFR_L");

            entryPx       = Close[0];
            slPx          = sl;
            beApplied     = false;
            activeSig     = "OFR_L";
            dailyTradeCount++;

            // Visualización
            Draw.ArrowUp(this, "LE_" + CurrentBar, false, 0,
                         Low[0] - 3 * TickSize, Brushes.Lime);
            Draw.Line(this, "SL_L_" + CurrentBar, false,
                      total + 2, sl, 0, sl, Brushes.Red, DashStyleHelper.Dash, 1);
            Draw.Line(this, "TP_L_" + CurrentBar, false,
                      total + 2, tp, 0, tp, Brushes.DodgerBlue, DashStyleHelper.Dash, 1);

            // Marcar secuencia en chart
            for (int i = 1; i <= ExhaustionBricks; i++)
                Draw.Dot(this, "EXH_" + CurrentBar + "_" + i, false, i,
                         Low[i] - TickSize, Brushes.Yellow);
            for (int i = ExhaustionBricks + 1; i <= total; i++)
                Draw.Dot(this, "ABS_" + CurrentBar + "_" + i, false, i,
                         Low[i] - TickSize, Brushes.Cyan);
        }

        // ────────────────────────────────────────────────────────────
        private void ManageBreakeven()
        {
            if (beApplied || activeSig == "") return;
            if (Position.MarketPosition == MarketPosition.Flat) return;

            double risk = Math.Abs(entryPx - slPx);
            if (risk <= 0) return;

            double favor = Position.MarketPosition == MarketPosition.Long
                ? Close[0] - entryPx
                : entryPx  - Close[0];

            if (favor >= BreakevenR * risk)
            {
                SetStopLoss(activeSig, CalculationMode.Price, entryPx, false);
                beApplied = true;
            }
        }

        // ────────────────────────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Range(2, 8)]
        [Display(Name = "Absorption Bricks (vol creciente)", GroupName = "1. Order Flow", Order = 0)]
        public int AbsorptionBricks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5)]
        [Display(Name = "Exhaustion Bricks (vol decreciente)", GroupName = "1. Order Flow", Order = 1)]
        public int ExhaustionBricks { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "Vol SMA Period", GroupName = "1. Order Flow", Order = 2)]
        public int VolumeSMAPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name = "Min Vol Ratio (Push)", GroupName = "1. Order Flow", Order = 3)]
        public double MinVolRatioPush { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name = "Target R:R", GroupName = "2. Risk / Reward", Order = 0)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 3.0)]
        [Display(Name = "Breakeven (R)", GroupName = "2. Risk / Reward", Order = 1)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Range(2, 20)]
        [Display(Name = "Stop Buffer (ticks)", GroupName = "2. Risk / Reward", Order = 2)]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max Trades / Día", GroupName = "3. Trade Management", Order = 0)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Contratos", GroupName = "3. Trade Management", Order = 1)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "4. Dirección", Order = 0)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "4. Dirección", Order = 1)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Prime Hours", GroupName = "5. Horario", Order = 0)]
        public bool UsePrimeHours { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Inicio (HHMMSS)", GroupName = "5. Horario", Order = 1)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fin (HHMMSS)", GroupName = "5. Horario", Order = 2)]
        public int PrimeEnd { get; set; }

        // === 6. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML (ZMQ)", GroupName = "6. ML Filter", Order = 0)]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name = "Puerto Python (meta_brain.py)", GroupName = "6. ML Filter", Order = 1)]
        public int MLPort { get; set; }

        #endregion
    }
}
