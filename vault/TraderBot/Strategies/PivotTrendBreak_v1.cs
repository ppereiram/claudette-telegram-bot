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
 * PivotTrendBreak_v1
 * ==================
 * Concepto: Detecta automáticamente trendlines formadas por pivot points.
 *           Entra cuando el precio hace breakout de esa línea.
 *           SL y TP son DINÁMICOS y estructurales (basados en pivots reales).
 *           Solo entra si el R:R mínimo se cumple → expectancia positiva garantizada.
 *
 * LONG:  Breakout sobre trendline descendente (highs bajando) con volumen
 *        SL = swing LOW más reciente | TP = swing HIGH más reciente sobre entry
 *
 * SHORT: Breakdown bajo trendline ascendente (lows subiendo) con volumen
 *        SL = swing HIGH más reciente | TP = swing LOW más reciente bajo entry
 *
 * Chart recomendado: Renko 10-tick MNQ (bricks de 10 ticks = 2.5 puntos)
 * Optimizado para: MNQ, Renko 10, prime hours
 */

namespace NinjaTrader.NinjaScript.Strategies
{
    public class PivotTrendBreak_v1 : Strategy
    {
        // ── Clase interna pivot ──────────────────────────────────────
        private class PivotPoint
        {
            public double Price;
            public int    BarIndex;
            public bool   IsHigh;   // true = swing high | false = swing low
        }

        // ── Estado ──────────────────────────────────────────────────
        private List<PivotPoint> pivots;

        private PivotPoint ph_recent, ph_older;   // últimos 2 swing highs (trendline resistencia)
        private PivotPoint pl_recent, pl_older;   // últimos 2 swing lows  (trendline soporte)

        private double prevTlHighValue = double.NaN;  // valor trendline highs barra anterior
        private double prevTlLowValue  = double.NaN;  // valor trendline lows  barra anterior

        private SMA volSMA;

        // Timezone — ET cubre EST y EDT automáticamente (Windows "Eastern Standard Time" incluye DST)
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        // Retorna hora ET tanto en backtest (Time[0] ya es ET) como en live (convierte UTC→ET)
        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        // ML Filter (ZMQ)
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        // Trade state
        private int      dailyTradeCount;
        private DateTime sessionDate = DateTime.MinValue;
        private int      lastTradeBar;
        private double   entryPx, slPx, tpPx;
        private bool     beApplied;
        private string   activeSig = "";

        // ────────────────────────────────────────────────────────────
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description                  = "Breakout de trendlines por pivots — SL/TP dinámicos estructurales — R:R validado";
                Name                         = "PivotTrendBreak_v1";
                Calculate                    = Calculate.OnBarClose;
                IsOverlay                    = true;
                BarsRequiredToTrade          = 20;
                StopTargetHandling           = StopTargetHandling.PerEntryExecution;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;

                // — Pivot detection —
                PivotStrength         = 3;     // bricks cada lado para confirmar pivot
                MinPivotGapTicks      = 20;    // separación mínima entre pivots del mismo tipo (ticks)
                MaxPivotAgeBricks     = 80;    // bricks máximo de vida del pivot
                StopBufferTicks       = 4;     // ticks extra de buffer en el SL

                // — Expectancia —
                MinRR                 = 1.5;   // R:R mínimo para entrar

                // — Volumen —
                UseVolumeFilter       = true;
                VolumePeriod          = 20;
                MinVolRatio           = 1.3;   // volumen del brick >= 1.3× promedio

                // — Trade management —
                UseBreakeven          = true;
                BreakevenR            = 1.0;
                MaxTradesPerDay       = 3;
                CooldownBricks        = 5;
                Quantity              = 20;

                // — Dirección —
                AllowLong             = true;
                AllowShort            = true;

                // — Horario —
                UsePrimeHours         = true;
                PrimeStart            = 93000;
                PrimeEnd              = 153000;

                // — ML Filter —
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                pivots = new List<PivotPoint>();
                volSMA = SMA(Volume, VolumePeriod);

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("PTB ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("PTB ML: Error al conectar ZMQ: {0}", ex.Message));
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
            if (CurrentBar < BarsRequiredToTrade + PivotStrength + 2) return;

            // ── Reset diario ──────────────────────────────────────────
            if (Time[0].Date != sessionDate)
            {
                dailyTradeCount = 0;
                beApplied       = false;
                activeSig       = "";
                sessionDate     = Time[0].Date;
            }

            // ── 1. Detectar y almacenar nuevos pivots ─────────────────
            ScanForPivots();

            // ── 2. Actualizar referencias a los 2 últimos de cada tipo ─
            RefreshPivotRefs();

            // ── 3. Calcular valores actuales de las trendlines ─────────
            double tlHighNow = TrendlineValue(ph_recent, ph_older);   // resistencia (highs)
            double tlLowNow  = TrendlineValue(pl_recent, pl_older);   // soporte (lows)

            // ── 4. Dibujar trendlines en chart ─────────────────────────
            DrawTrendlines(tlHighNow, tlLowNow);

            // ── 5. Gestión de breakeven ───────────────────────────────
            ManageBreakeven();

            // ── 6. Si hay posición abierta, no buscar nuevos trades ────
            if (Position.MarketPosition != MarketPosition.Flat) goto UpdatePrev;

            // ── 7. Gates ───────────────────────────────────────────────
            if (dailyTradeCount >= MaxTradesPerDay) goto UpdatePrev;
            if (lastTradeBar > 0 && CurrentBar - lastTradeBar < CooldownBricks) goto UpdatePrev;

            if (UsePrimeHours)
            {
                int t = GetEtTime();
                if (t < PrimeStart || t >= PrimeEnd) goto UpdatePrev;
            }

            // ── 8. Filtro de volumen ───────────────────────────────────
            bool volOK = !UseVolumeFilter
                         || (volSMA[0] > 0 && Volume[0] >= volSMA[0] * MinVolRatio);

            // ── 9. LONG — breakout sobre trendline de highs ────────────
            // Condición: la trendline de highs debe ser DESCENDENTE
            //            (highs bajando = presión vendedora cediendo)
            if (AllowLong
                && !double.IsNaN(tlHighNow)
                && !double.IsNaN(prevTlHighValue)
                && ph_recent != null && ph_older != null
                && ph_recent.Price < ph_older.Price)          // trendline descendente
            {
                bool crossedAbove = Close[1] <= prevTlHighValue
                                 && Close[0]  > tlHighNow;

                if (crossedAbove && volOK)
                    TryEnterLong(Close[0]);
            }

            // ── 10. SHORT — breakdown bajo trendline de lows ───────────
            // Condición: la trendline de lows debe ser ASCENDENTE
            //            (lows subiendo = soporte que se rompe con fuerza)
            if (AllowShort
                && !double.IsNaN(tlLowNow)
                && !double.IsNaN(prevTlLowValue)
                && pl_recent != null && pl_older != null
                && pl_recent.Price > pl_older.Price)           // trendline ascendente
            {
                bool crossedBelow = Close[1] >= prevTlLowValue
                                 && Close[0]  < tlLowNow;

                if (crossedBelow && volOK)
                    TryEnterShort(Close[0]);
            }

            // ── 11. Actualizar valores previos de trendline ────────────
            UpdatePrev:
            prevTlHighValue = tlHighNow;
            prevTlLowValue  = tlLowNow;
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

                mlTradeId = string.Format("PTB_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"PivotTrendBreak_v1\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":50.0,\"adx\":25.0," +
                    "\"vol_ratio\":{2:F3},\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{3},\"minute\":{4},\"day_of_week\":{5},\"signal_type\":{6}}}",
                    mlTradeId, direction, volRatio, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("PTB ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (!allow) Print(string.Format("PTB ML bloqueado [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("PTB ML Error: {0} — permitiendo trade", ex.Message));
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
                    "{{\"type\":\"outcome\",\"strategy\":\"PivotTrendBreak_v1\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("PTB ML outcome error: {0}", ex.Message)); }
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

        // ── Intento de entrada LONG ──────────────────────────────────
        private void TryEnterLong(double entry)
        {
            // SL = swing low más reciente bajo el precio de entrada
            double sl = GetNearestLow(entry);
            if (double.IsNaN(sl)) return;
            sl -= StopBufferTicks * TickSize;

            // TP = swing high más reciente SOBRE el precio de entrada
            double tp = GetNearestHighAbove(entry);
            if (double.IsNaN(tp)) return;

            // Validar geometría
            if (sl >= entry || tp <= entry) return;

            double risk   = entry - sl;
            double reward = tp - entry;
            if (risk <= 0) return;

            double rr = reward / risk;
            if (rr < MinRR) return;

            // ML gate
            if (UseMLFilter && !QueryMLFilter(1, 0)) return;

            // Entrar
            SetStopLoss(   "PTB_L", CalculationMode.Price, sl, false);
            SetProfitTarget("PTB_L", CalculationMode.Price, tp);
            EnterLong(Quantity, "PTB_L");

            entryPx = entry;
            slPx    = sl;
            tpPx    = tp;
            beApplied    = false;
            activeSig    = "PTB_L";
            dailyTradeCount++;
            lastTradeBar = CurrentBar;

            // Marcar en chart
            Draw.ArrowUp(this, "LE_" + CurrentBar, false, 0, Low[0]  - 3 * TickSize, Brushes.Lime);
            Draw.Line(this, "SL_L_" + CurrentBar, false, 10, sl, 0, sl, Brushes.Red,       DashStyleHelper.Dash, 1);
            Draw.Line(this, "TP_L_" + CurrentBar, false, 10, tp, 0, tp, Brushes.DodgerBlue, DashStyleHelper.Dash, 1);
        }

        // ── Intento de entrada SHORT ─────────────────────────────────
        private void TryEnterShort(double entry)
        {
            // SL = swing high más reciente SOBRE el precio de entrada
            double sl = GetNearestHighAbove(entry);
            if (double.IsNaN(sl)) return;
            sl += StopBufferTicks * TickSize;

            // TP = swing low más reciente BAJO el precio de entrada
            double tp = GetNearestLow(entry);
            if (double.IsNaN(tp)) return;

            // Validar geometría
            if (sl <= entry || tp >= entry) return;

            double risk   = sl - entry;
            double reward = entry - tp;
            if (risk <= 0) return;

            double rr = reward / risk;
            if (rr < MinRR) return;

            // ML gate
            if (UseMLFilter && !QueryMLFilter(-1, 0)) return;

            // Entrar
            SetStopLoss(   "PTB_S", CalculationMode.Price, sl, false);
            SetProfitTarget("PTB_S", CalculationMode.Price, tp);
            EnterShort(Quantity, "PTB_S");

            entryPx = entry;
            slPx    = sl;
            tpPx    = tp;
            beApplied    = false;
            activeSig    = "PTB_S";
            dailyTradeCount++;
            lastTradeBar = CurrentBar;

            Draw.ArrowDown(this, "SE_" + CurrentBar, false, 0, High[0] + 3 * TickSize, Brushes.Red);
            Draw.Line(this, "SL_S_" + CurrentBar, false, 10, sl, 0, sl, Brushes.Red,       DashStyleHelper.Dash, 1);
            Draw.Line(this, "TP_S_" + CurrentBar, false, 10, tp, 0, tp, Brushes.DodgerBlue, DashStyleHelper.Dash, 1);
        }

        // ── Detección de pivots ──────────────────────────────────────
        private void ScanForPivots()
        {
            // Pivot High
            if (IsSwingHigh(PivotStrength))
            {
                double px  = High[PivotStrength];
                int    bar = CurrentBar - PivotStrength;

                if (!TooCloseToExisting(px, bar, isHigh: true))
                {
                    pivots.Add(new PivotPoint { Price = px, BarIndex = bar, IsHigh = true });
                    Draw.Dot(this, "PH_" + bar, false, PivotStrength,
                             High[PivotStrength] + TickSize, Brushes.Cyan);
                }
            }

            // Pivot Low
            if (IsSwingLow(PivotStrength))
            {
                double px  = Low[PivotStrength];
                int    bar = CurrentBar - PivotStrength;

                if (!TooCloseToExisting(px, bar, isHigh: false))
                {
                    pivots.Add(new PivotPoint { Price = px, BarIndex = bar, IsHigh = false });
                    Draw.Dot(this, "PL_" + bar, false, PivotStrength,
                             Low[PivotStrength] - TickSize, Brushes.Orange);
                }
            }

            // Limpiar pivots viejos
            pivots.RemoveAll(p => CurrentBar - p.BarIndex > MaxPivotAgeBricks);
        }

        // ── Referencias a los 2 pivots más recientes de cada tipo ────
        private void RefreshPivotRefs()
        {
            var highs = pivots.Where(p =>  p.IsHigh).OrderByDescending(p => p.BarIndex).ToList();
            var lows  = pivots.Where(p => !p.IsHigh).OrderByDescending(p => p.BarIndex).ToList();

            ph_recent = highs.Count >= 1 ? highs[0] : null;
            ph_older  = highs.Count >= 2 ? highs[1] : null;
            pl_recent = lows.Count  >= 1 ? lows[0]  : null;
            pl_older  = lows.Count  >= 2 ? lows[1]  : null;
        }

        // ── Valor de la trendline en el bar actual ───────────────────
        // recent = pivot más nuevo | older = pivot más viejo
        private double TrendlineValue(PivotPoint recent, PivotPoint older)
        {
            if (recent == null || older == null)             return double.NaN;
            if (recent.BarIndex == older.BarIndex)           return double.NaN;

            double slope = (recent.Price - older.Price) / (double)(recent.BarIndex - older.BarIndex);
            return recent.Price + slope * (CurrentBar - recent.BarIndex);
        }

        // ── Dibujar trendlines en el chart ───────────────────────────
        private void DrawTrendlines(double tlHighNow, double tlLowNow)
        {
            if (ph_recent != null && ph_older != null && !double.IsNaN(tlHighNow))
            {
                int barsAgoRecent = CurrentBar - ph_recent.BarIndex;
                int barsAgoOlder  = CurrentBar - ph_older.BarIndex;
                Draw.Line(this, "TL_H", false,
                          barsAgoOlder, ph_older.Price,
                          barsAgoRecent, ph_recent.Price,
                          Brushes.DodgerBlue, DashStyleHelper.Solid, 2);
            }

            if (pl_recent != null && pl_older != null && !double.IsNaN(tlLowNow))
            {
                int barsAgoRecent = CurrentBar - pl_recent.BarIndex;
                int barsAgoOlder  = CurrentBar - pl_older.BarIndex;
                Draw.Line(this, "TL_L", false,
                          barsAgoOlder, pl_older.Price,
                          barsAgoRecent, pl_recent.Price,
                          Brushes.Orange, DashStyleHelper.Solid, 2);
            }
        }

        // ── SL / TP helpers ──────────────────────────────────────────

        // Swing low más reciente por debajo de 'price'
        private double GetNearestLow(double price)
        {
            var candidate = pivots
                .Where(p => !p.IsHigh && p.Price < price)
                .OrderByDescending(p => p.BarIndex)
                .FirstOrDefault();
            return candidate != null ? candidate.Price : double.NaN;
        }

        // Swing high más reciente por encima de 'price'
        private double GetNearestHighAbove(double price)
        {
            var candidate = pivots
                .Where(p => p.IsHigh && p.Price > price)
                .OrderByDescending(p => p.BarIndex)
                .FirstOrDefault();
            return candidate != null ? candidate.Price : double.NaN;
        }

        // ── Gestión de breakeven ─────────────────────────────────────
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

        // ── Pivot detection helpers ──────────────────────────────────

        private bool IsSwingHigh(int barsAgo)
        {
            if (CurrentBar < barsAgo + PivotStrength + 1) return false;
            for (int i = 1; i <= PivotStrength; i++)
            {
                if (High[barsAgo - i] >= High[barsAgo]) return false;  // barra más nueva mayor → no es pivot
                if (High[barsAgo + i] >= High[barsAgo]) return false;  // barra más vieja mayor → no es pivot
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
            int minGapBricks = MinPivotGapTicks / (int)Math.Max(1, 10); // aproximado
            foreach (var p in pivots)
            {
                if (p.IsHigh == isHigh && Math.Abs(barIndex - p.BarIndex) < minGapBricks)
                    return true;
            }
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
        [Display(Name = "R:R Mínimo para entrar", GroupName = "2. Expectancia", Order = 0)]
        public double MinRR { get; set; }

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
        [Display(Name = "Activar Filtro ML (ZMQ)", GroupName = "7. ML Filter", Order = 0)]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name = "Puerto Python (meta_brain.py)", GroupName = "7. ML Filter", Order = 1)]
        public int MLPort { get; set; }

        #endregion
    }
}
