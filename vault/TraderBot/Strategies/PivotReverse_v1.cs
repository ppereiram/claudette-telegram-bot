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
using NetMQ;
using NetMQ.Sockets;
#endregion

/*
 * PivotReverse_v1
 * ===============
 * Concepto: Detecta DOBLE TECHO (short) y DOBLE PISO (long) estructurales.
 *           Entra cuando el precio confirma la reversión rompiendo el nivel clave.
 *           SL y TP son estructurales (pivots reales). R:R mínimo validado.
 *
 * COMPLEMENTARIO a PivotTrendBreak_v1:
 *   PivotTrendBreak → entra cuando una trendline SE ROMPE (momentum)
 *   PivotReverse    → entra cuando el precio FALLA en hacer un nuevo extremo (reversión)
 *
 * SHORT (Doble Techo):
 *   PivotHigh #1 → SwingLow intermedio → PivotHigh #2 (MENOR que #1)
 *   Entrada: precio rompe BAJO el SwingLow intermedio
 *   SL = por encima de PivotHigh #2 + buffer
 *   TP = siguiente swing low estructural debajo del entry
 *
 * LONG (Doble Piso):
 *   PivotLow #1 → SwingHigh intermedio → PivotLow #2 (MAYOR que #1)
 *   Entrada: precio rompe SOBRE el SwingHigh intermedio
 *   SL = por debajo de PivotLow #2 - buffer
 *   TP = siguiente swing high estructural encima del entry
 *
 * Chart recomendado: Renko 25-tick MNQ (igual que PivotTrendBreak_v1)
 */

namespace NinjaTrader.NinjaScript.Strategies
{
    public class PivotReverse_v1 : Strategy
    {
        // ── Clase interna pivot ──────────────────────────────────────
        private class PivotPoint
        {
            public double Price;
            public int    BarIndex;
            public bool   IsHigh;
        }

        // ── Estado ──────────────────────────────────────────────────
        private List<PivotPoint> pivots;
        private SMA volSMA;
        private ATR atrIndicator;

        // ── ML Filter ────────────────────────────────────────────────
        private RequestSocket mlSocket      = null;
        private string        mlTradeId     = "";
        private string        mlEntryContext = "";

        // Timezone
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        // Trade state
        private int      dailyTradeCount;
        private DateTime sessionDate = DateTime.MinValue;
        private int      lastTradeBar;
        private double   entryPx, slPx, tpPx;
        private bool     beApplied;
        private string   activeSig = "";

        // Patrón SHORT — Doble Techo: ph1 → il (intermediate low) → ph2 (ph2.Price < ph1.Price)
        private PivotPoint ph1_s, il_s, ph2_s;

        // Patrón LONG — Doble Piso: pl1 → ih (intermediate high) → pl2 (pl2.Price > pl1.Price)
        private PivotPoint pl1_l, ih_l, pl2_l;

        // ────────────────────────────────────────────────────────────
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                  = "Doble Techo/Piso estructural con break confirmado — SL estructural + TP fijo R:R";
                Name                         = "PivotReverse_v1";
                Calculate                    = Calculate.OnBarClose;
                IsOverlay                    = true;
                BarsRequiredToTrade          = 20;
                StopTargetHandling           = StopTargetHandling.PerEntryExecution;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;

                // — Pivot detection —
                PivotStrength     = 3;
                MinPivotGapTicks  = 20;
                MaxPivotAgeBricks = 80;
                StopBufferTicks   = 4;

                // — Expectancia —
                TargetRR          = 3.0;   // TP fijo = riesgo × TargetRR (determinístico)
                MinRR             = 1.5;   // gate mínimo — rechaza si ATR-stop no da el R:R
                MaxStopATR        = 3.0;   // skip si SL > 3×ATR desde entry

                // — Volumen —
                UseVolumeFilter   = true;
                VolumePeriod      = 20;
                MinVolRatio       = 1.3;

                // — Trade management —
                UseBreakeven      = true;
                BreakevenR        = 1.0;
                MaxTradesPerDay   = 1;
                CooldownBricks    = 5;
                Quantity          = 1;    // ajustar tras ver MaxDD en backtest

                // — Dirección —
                AllowLong         = true;
                AllowShort        = true;

                // — Horario (ET) —
                UsePrimeHours     = true;
                PrimeStart        = 93000;
                PrimeEnd          = 153000;

                // — ML Filter —
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                pivots       = new List<PivotPoint>();
                volSMA       = SMA(Volume, VolumePeriod);
                atrIndicator = ATR(14);

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

        // ── ML Filter ────────────────────────────────────────────────
        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                mlTradeId = Guid.NewGuid().ToString("N").Substring(0, 8);
                DateTime et = State == State.Realtime
                    ? TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone)
                    : Time[0];
                double volRatio = (volSMA != null && volSMA[0] > 0) ? Volume[0] / volSMA[0] : 1.0;

                mlEntryContext = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"PivotReverse_v1\"," +
                    "\"trade_id\":\"{0}\",\"direction\":{1}," +
                    "\"rsi\":50.0,\"adx\":25.0,\"vol_ratio\":{2}," +
                    "\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{3},\"minute\":{4},\"day_of_week\":{5}," +
                    "\"signal_type\":{6}}}",
                    mlTradeId, direction,
                    volRatio.ToString("F3", System.Globalization.CultureInfo.InvariantCulture),
                    et.Hour, et.Minute, (int)et.DayOfWeek, signalType);

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
                    "{{\"type\":\"outcome\",\"strategy\":\"PivotReverse_v1\"," +
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

        // ────────────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            if (CurrentBar < BarsRequiredToTrade + PivotStrength + 2) return;

            // ── Reset diario ──────────────────────────────────────────
            if (Time[0].Date != sessionDate)
            {
                dailyTradeCount = 0;
                beApplied       = false;
                activeSig       = "";
                sessionDate     = Time[0].Date;
            }

            // ── 1. Detectar nuevos pivots ─────────────────────────────
            ScanForPivots();

            // ── 2. Actualizar estado de patrones ─────────────────────
            UpdatePatternState();

            // ── 3. Dibujar patrones en chart ─────────────────────────
            DrawPatterns();

            // ── 4. Gestión de breakeven ───────────────────────────────
            ManageBreakeven();

            // ── 5. Si hay posición abierta, no buscar nuevos trades ────
            if (Position.MarketPosition != MarketPosition.Flat) return;

            // ── 6. Gates ───────────────────────────────────────────────
            if (dailyTradeCount >= MaxTradesPerDay) return;
            if (lastTradeBar > 0 && CurrentBar - lastTradeBar < CooldownBricks) return;

            if (UsePrimeHours)
            {
                int t = GetEtTime();
                if (t < PrimeStart || t >= PrimeEnd) return;
            }

            // ── 7. Filtro de volumen ───────────────────────────────────
            bool volOK = !UseVolumeFilter
                         || (volSMA[0] > 0 && Volume[0] >= volSMA[0] * MinVolRatio);

            // ── 8. SHORT — Doble Techo: rompe bajo SwingLow intermedio ─
            if (AllowShort && ph2_s != null && il_s != null)
            {
                bool breaksDown = Close[1] >= il_s.Price && Close[0] < il_s.Price;
                if (breaksDown && volOK)
                    TryEnterShort(Close[0]);
            }

            // ── 9. LONG — Doble Piso: rompe sobre SwingHigh intermedio ─
            if (AllowLong && pl2_l != null && ih_l != null)
            {
                bool breaksUp = Close[1] <= ih_l.Price && Close[0] > ih_l.Price;
                if (breaksUp && volOK)
                    TryEnterLong(Close[0]);
            }
        }

        // ── Actualizar patrones de Doble Techo y Doble Piso ─────────
        private void UpdatePatternState()
        {
            var highs = pivots.Where(p =>  p.IsHigh).OrderBy(p => p.BarIndex).ToList();
            var lows  = pivots.Where(p => !p.IsHigh).OrderBy(p => p.BarIndex).ToList();

            // ─ PATRÓN SHORT: buscar el más reciente [H1 → IL → H2 donde H2 < H1] ─
            ph1_s = null; il_s = null; ph2_s = null;
            for (int i = highs.Count - 1; i >= 1; i--)
            {
                var h2 = highs[i];
                var h1 = highs[i - 1];
                if (h2.Price >= h1.Price) continue;           // H2 debe ser MENOR que H1
                if (h2.BarIndex - h1.BarIndex < 3) continue; // espacio mínimo entre highs
                if (CurrentBar - h2.BarIndex > MaxPivotAgeBricks) continue;

                // Buscar swing low entre h1 y h2
                var il = lows
                    .Where(l => l.BarIndex > h1.BarIndex && l.BarIndex < h2.BarIndex)
                    .OrderByDescending(l => l.BarIndex)
                    .FirstOrDefault();
                if (il == null) continue;

                ph1_s = h1; il_s = il; ph2_s = h2;
                break;
            }

            // ─ PATRÓN LONG: buscar el más reciente [L1 → IH → L2 donde L2 > L1] ─
            pl1_l = null; ih_l = null; pl2_l = null;
            for (int i = lows.Count - 1; i >= 1; i--)
            {
                var l2 = lows[i];
                var l1 = lows[i - 1];
                if (l2.Price <= l1.Price) continue;           // L2 debe ser MAYOR que L1
                if (l2.BarIndex - l1.BarIndex < 3) continue;
                if (CurrentBar - l2.BarIndex > MaxPivotAgeBricks) continue;

                // Buscar swing high entre l1 y l2
                var ih = highs
                    .Where(h => h.BarIndex > l1.BarIndex && h.BarIndex < l2.BarIndex)
                    .OrderByDescending(h => h.BarIndex)
                    .FirstOrDefault();
                if (ih == null) continue;

                pl1_l = l1; ih_l = ih; pl2_l = l2;
                break;
            }
        }

        // ── Entrada SHORT ─────────────────────────────────────────────
        private void TryEnterShort(double entry)
        {
            // SL estructural: por encima del segundo pivot high + buffer
            double sl   = ph2_s.Price + StopBufferTicks * TickSize;
            double risk = sl - entry;
            if (risk <= 0 || risk > MaxStopATR * atrIndicator[0]) return;

            // TP fijo: entry - risk × TargetRR  (determinístico, reproducible)
            double tp = entry - risk * TargetRR;

            // Gate de R:R mínimo (redundante con TargetRR ≥ MinRR, pero protege)
            if (TargetRR < MinRR) return;

            if (UseMLFilter && !QueryMLFilter(-1, 0)) return;
            SetStopLoss(   "PRV_S", CalculationMode.Price, sl, false);
            SetProfitTarget("PRV_S", CalculationMode.Price, tp);
            EnterShort(Quantity, "PRV_S");

            entryPx = entry; slPx = sl; tpPx = tp;
            beApplied = false; activeSig = "PRV_S";
            dailyTradeCount++;
            lastTradeBar = CurrentBar;

            Draw.ArrowDown(this, "SE_"  + CurrentBar, false, 0, High[0] + 3 * TickSize, Brushes.OrangeRed);
            Draw.Line(this, "SL_S_" + CurrentBar, false, 10, sl, 0, sl, Brushes.Red,        DashStyleHelper.Dash, 1);
            Draw.Line(this, "TP_S_" + CurrentBar, false, 10, tp, 0, tp, Brushes.DodgerBlue,  DashStyleHelper.Dash, 1);
        }

        // ── Entrada LONG ──────────────────────────────────────────────
        private void TryEnterLong(double entry)
        {
            // SL estructural: por debajo del segundo pivot low - buffer
            double sl   = pl2_l.Price - StopBufferTicks * TickSize;
            double risk = entry - sl;
            if (risk <= 0 || risk > MaxStopATR * atrIndicator[0]) return;

            // TP fijo: entry + risk × TargetRR  (determinístico, reproducible)
            double tp = entry + risk * TargetRR;

            if (TargetRR < MinRR) return;

            if (UseMLFilter && !QueryMLFilter(1, 0)) return;
            SetStopLoss(   "PRV_L", CalculationMode.Price, sl, false);
            SetProfitTarget("PRV_L", CalculationMode.Price, tp);
            EnterLong(Quantity, "PRV_L");

            entryPx = entry; slPx = sl; tpPx = tp;
            beApplied = false; activeSig = "PRV_L";
            dailyTradeCount++;
            lastTradeBar = CurrentBar;

            Draw.ArrowUp(this, "LE_"  + CurrentBar, false, 0, Low[0] - 3 * TickSize, Brushes.LimeGreen);
            Draw.Line(this, "SL_L_" + CurrentBar, false, 10, sl, 0, sl, Brushes.Red,        DashStyleHelper.Dash, 1);
            Draw.Line(this, "TP_L_" + CurrentBar, false, 10, tp, 0, tp, Brushes.DodgerBlue,  DashStyleHelper.Dash, 1);
        }

        // ── Detectar pivots ──────────────────────────────────────────
        private void ScanForPivots()
        {
            if (IsSwingHigh(PivotStrength))
            {
                double px  = High[PivotStrength];
                int    bar = CurrentBar - PivotStrength;
                if (!TooCloseToExisting(px, bar, true))
                {
                    pivots.Add(new PivotPoint { Price = px, BarIndex = bar, IsHigh = true });
                    Draw.Dot(this, "PH_" + bar, false, PivotStrength,
                             High[PivotStrength] + TickSize, Brushes.Cyan);
                }
            }

            if (IsSwingLow(PivotStrength))
            {
                double px  = Low[PivotStrength];
                int    bar = CurrentBar - PivotStrength;
                if (!TooCloseToExisting(px, bar, false))
                {
                    pivots.Add(new PivotPoint { Price = px, BarIndex = bar, IsHigh = false });
                    Draw.Dot(this, "PL_" + bar, false, PivotStrength,
                             Low[PivotStrength] - TickSize, Brushes.Orange);
                }
            }

            pivots.RemoveAll(p => CurrentBar - p.BarIndex > MaxPivotAgeBricks);
        }

        // ── Dibujar patrones en chart ────────────────────────────────
        private void DrawPatterns()
        {
            // Doble Techo — línea roja entre los dos highs + nivel de break (SwingLow)
            if (ph1_s != null && ph2_s != null && il_s != null)
            {
                Draw.Line(this, "DT_tops", false,
                    CurrentBar - ph1_s.BarIndex, ph1_s.Price,
                    CurrentBar - ph2_s.BarIndex, ph2_s.Price,
                    Brushes.OrangeRed, DashStyleHelper.Dot, 1);
                Draw.Line(this, "DT_neck", false,
                    CurrentBar - il_s.BarIndex + 3, il_s.Price,
                    CurrentBar,                      il_s.Price,
                    Brushes.OrangeRed, DashStyleHelper.Solid, 2);
            }

            // Doble Piso — línea verde entre los dos lows + nivel de break (SwingHigh)
            if (pl1_l != null && pl2_l != null && ih_l != null)
            {
                Draw.Line(this, "DB_bots", false,
                    CurrentBar - pl1_l.BarIndex, pl1_l.Price,
                    CurrentBar - pl2_l.BarIndex, pl2_l.Price,
                    Brushes.LimeGreen, DashStyleHelper.Dot, 1);
                Draw.Line(this, "DB_neck", false,
                    CurrentBar - ih_l.BarIndex + 3, ih_l.Price,
                    CurrentBar,                      ih_l.Price,
                    Brushes.LimeGreen, DashStyleHelper.Solid, 2);
            }
        }

        // ── Breakeven ────────────────────────────────────────────────
        private void ManageBreakeven()
        {
            if (!UseBreakeven || beApplied || activeSig == "") return;
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

        // ── Helpers estructurales ─────────────────────────────────────
        private double GetNearestLow(double price)
        {
            var c = pivots
                .Where(p => !p.IsHigh && p.Price < price)
                .OrderByDescending(p => p.BarIndex)
                .FirstOrDefault();
            return c != null ? c.Price : double.NaN;
        }

        private double GetNearestHighAbove(double price)
        {
            var c = pivots
                .Where(p => p.IsHigh && p.Price > price)
                .OrderByDescending(p => p.BarIndex)
                .FirstOrDefault();
            return c != null ? c.Price : double.NaN;
        }

        private bool IsSwingHigh(int barsAgo)
        {
            if (CurrentBar < barsAgo + PivotStrength + 1) return false;
            for (int i = 1; i <= PivotStrength; i++)
            {
                if (High[barsAgo - i] >= High[barsAgo]) return false;
                if (High[barsAgo + i] >= High[barsAgo]) return false;
            }
            return true;
        }

        private bool IsSwingLow(int barsAgo)
        {
            if (CurrentBar < barsAgo + PivotStrength + 1) return false;
            for (int i = 1; i <= PivotStrength; i++)
            {
                if (Low[barsAgo - i] <= Low[barsAgo]) return false;
                if (Low[barsAgo + i] <= Low[barsAgo]) return false;
            }
            return true;
        }

        private bool TooCloseToExisting(double price, int barIndex, bool isHigh)
        {
            int minGapBricks = MinPivotGapTicks / (int)Math.Max(1, 10);
            foreach (var p in pivots)
                if (p.IsHigh == isHigh && Math.Abs(barIndex - p.BarIndex) < minGapBricks)
                    return true;
            return false;
        }

        // ────────────────────────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Display(Name = "Pivot Strength (bricks c/lado)", GroupName = "1. Pivot Detection", Order = 0)]
        public int PivotStrength { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Min Gap entre pivots (ticks)", GroupName = "1. Pivot Detection", Order = 1)]
        public int MinPivotGapTicks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Max edad pivot (bricks)", GroupName = "1. Pivot Detection", Order = 2)]
        public int MaxPivotAgeBricks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Stop Buffer (ticks)", GroupName = "1. Pivot Detection", Order = 3)]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 15.0)]
        [Display(Name = "Target R:R (TP fijo)", Description = "TP = riesgo × TargetRR desde entry", GroupName = "2. Expectancia", Order = 0)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 5.0)]
        [Display(Name = "R:R Mínimo para entrar", Description = "Skip trade si TargetRR < este valor", GroupName = "2. Expectancia", Order = 1)]
        public double MinRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Max Stop ATR", Description = "Skip si SL > X × ATR(14)", GroupName = "2. Expectancia", Order = 2)]
        public double MaxStopATR { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar filtro de volumen", GroupName = "3. Volumen", Order = 0)]
        public bool UseVolumeFilter { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Período SMA Volumen", GroupName = "3. Volumen", Order = 1)]
        public int VolumePeriod { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Volumen mínimo (× promedio)", GroupName = "3. Volumen", Order = 2)]
        public double MinVolRatio { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Breakeven", GroupName = "4. Trade Management", Order = 0)]
        public bool UseBreakeven { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Breakeven (R)", GroupName = "4. Trade Management", Order = 1)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Max Trades/Día", GroupName = "4. Trade Management", Order = 2)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Cooldown (bricks)", GroupName = "4. Trade Management", Order = 3)]
        public int CooldownBricks { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Contratos", GroupName = "4. Trade Management", Order = 4)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "5. Dirección", Order = 0)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "5. Dirección", Order = 1)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Usar Prime Hours", GroupName = "6. Horario", Order = 0)]
        public bool UsePrimeHours { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Inicio (HHMMSS)", GroupName = "6. Horario", Order = 1)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Fin (HHMMSS)", GroupName = "6. Horario", Order = 2)]
        public int PrimeEnd { get; set; }

        // === 7. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML", Order = 1, GroupName = "7. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(1024, 65535)]
        [Display(Name = "Puerto ZMQ", Order = 2, GroupName = "7. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
