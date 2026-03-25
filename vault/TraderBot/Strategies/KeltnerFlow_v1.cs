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
#endregion

// Chart: 5-min MNQ | Todos los parámetros internos en ET
// Edge: Keltner Channel (volatilidad estructural) + pullback a banda + Volume Delta sintético
// Filtro de ruido: ATR actual < 70% del ATR baseline → mercado sin estructura → no operar

namespace NinjaTrader.NinjaScript.Strategies
{
    public class KeltnerFlow_v1 : Strategy
    {
        // ─────────────────────────────────────────────────
        #region Params — 1. Keltner Channel
        // ─────────────────────────────────────────────────

        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name = "EMA Period", GroupName = "1. Keltner Channel", Order = 1)]
        public int KeltnerPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 5.0)]
        [Display(Name = "ATR Multiplier", GroupName = "1. Keltner Channel", Order = 2)]
        public double KeltnerMultiplier { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "ATR Period", GroupName = "1. Keltner Channel", Order = 3)]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Trend Confirm Bars", GroupName = "1. Keltner Channel", Order = 4)]
        public int TrendConfirmBars { get; set; }

        // 0 = solo toca banda exacta | 0.5 = zona de 0.5×ATR alrededor de la banda
        [NinjaScriptProperty]
        [Range(0.0, 2.0)]
        [Display(Name = "Zone Tolerance (ATR)", GroupName = "1. Keltner Channel", Order = 5)]
        public double ZoneTolerance { get; set; }

        #endregion

        // ─────────────────────────────────────────────────
        #region Params — 2. Noise Filter
        // ─────────────────────────────────────────────────

        [NinjaScriptProperty]
        [Display(Name = "Use Noise Filter", GroupName = "2. Noise Filter", Order = 1)]
        public bool UseNoiseFilter { get; set; }

        // Si ATR actual < ATR_SMA50 * MinATRRatio → mercado choppy → no operar
        [NinjaScriptProperty]
        [Range(0.3, 2.0)]
        [Display(Name = "Min ATR Ratio (vs SMA50)", GroupName = "2. Noise Filter", Order = 2)]
        public double MinATRRatio { get; set; }

        #endregion

        // ─────────────────────────────────────────────────
        #region Params — 3. Volume Delta
        // ─────────────────────────────────────────────────

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "Delta SMA Period", GroupName = "3. Volume Delta", Order = 1)]
        public int DeltaSMAPeriod { get; set; }

        // barDelta >= Max(|deltaSma| * MinDeltaRatio, MinDeltaAbs) para confirmar entrada
        [NinjaScriptProperty]
        [Range(0.5, 4.0)]
        [Display(Name = "Min Delta Ratio", GroupName = "3. Volume Delta", Order = 2)]
        public double MinDeltaRatio { get; set; }

        [NinjaScriptProperty]
        [Range(0, 100000)]
        [Display(Name = "Min Delta Abs (contratos)", GroupName = "3. Volume Delta", Order = 3)]
        public double MinDeltaAbs { get; set; }

        #endregion

        // ─────────────────────────────────────────────────
        #region Params — 4. Risk Management
        // ─────────────────────────────────────────────────

        [NinjaScriptProperty]
        [Range(1.0, 8.0)]
        [Display(Name = "Target R:R", GroupName = "4. Risk Management", Order = 1)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 4.0)]
        [Display(Name = "Breakeven R", GroupName = "4. Risk Management", Order = 2)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Stop Buffer Ticks", GroupName = "4. Risk Management", Order = 3)]
        public int StopBufferTicks { get; set; }

        // SL estructural no puede ser mayor que MaxStopATR * ATR actual
        [NinjaScriptProperty]
        [Range(0.5, 8.0)]
        [Display(Name = "Max Stop ATR", GroupName = "4. Risk Management", Order = 4)]
        public double MaxStopATR { get; set; }

        [NinjaScriptProperty]
        [Range(3, 30)]
        [Display(Name = "Swing Lookback (bars)", GroupName = "4. Risk Management", Order = 5)]
        public int SwingLookback { get; set; }

        #endregion

        // ─────────────────────────────────────────────────
        #region Params — 5. Trade Management
        // ─────────────────────────────────────────────────

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max Trades Per Day", GroupName = "5. Trade Management", Order = 1)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Quantity", GroupName = "5. Trade Management", Order = 2)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "5. Trade Management", Order = 3)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "5. Trade Management", Order = 4)]
        public bool AllowShort { get; set; }

        #endregion

        // ─────────────────────────────────────────────────
        #region Params — 6. Session
        // ─────────────────────────────────────────────────

        [NinjaScriptProperty]
        [Display(Name = "Use Prime Hours Only", GroupName = "6. Session", Order = 1)]
        public bool UsePrimeHoursOnly { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime Start (ET HHMMSS)", GroupName = "6. Session", Order = 2)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime End (ET HHMMSS)", GroupName = "6. Session", Order = 3)]
        public int PrimeEnd { get; set; }

        #endregion

        // ─────────────────────────────────────────────────
        #region Private fields
        // ─────────────────────────────────────────────────

        private EMA emaCenter;
        private ATR atrIndicator;
        private SMA atrSma50;      // SMA(ATR, 50) — línea base para filtro de ruido

        // Delta sintético: rolling SMA circular
        private double[] deltaBuffer;
        private int      deltaIdx;
        private double   deltaSum;

        // Pending signal (patrón 2 barras: barra N toca zona → barra N+1 confirma)
        private bool   pendingLong;
        private bool   pendingShort;
        private double pendingSwingLow;
        private double pendingSwingHigh;
        private int    pendingBar;       // CurrentBar cuando se fijó el pending

        // Estado del trade
        private double   initialStop;
        private bool     breakevenSet;
        private int      tradesToday;
        private DateTime lastTradeDate;

        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "KeltnerFlow_v1 — Pullback a banda Keltner + Volume Delta sintético + filtro de ruido";
                Name        = "KeltnerFlow_v1";
                Calculate   = Calculate.OnBarClose;
                IsOverlay   = false;
                IsUnmanaged = false;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;
                Slippage = 1;

                // 1. Keltner
                KeltnerPeriod     = 20;
                KeltnerMultiplier = 2.0;
                ATRPeriod         = 14;
                TrendConfirmBars  = 3;
                ZoneTolerance     = 0.5;    // zona = banda ± 0.5×ATR

                // 2. Noise filter
                UseNoiseFilter = false;     // OFF por defecto — activar si hay mucho ruido
                MinATRRatio    = 0.7;

                // 3. Delta
                DeltaSMAPeriod = 20;
                MinDeltaRatio  = 1.3;
                MinDeltaAbs    = 0;

                // 4. Risk
                TargetRR        = 3.0;
                BreakevenR      = 1.0;
                StopBufferTicks = 5;
                MaxStopATR      = 3.0;
                SwingLookback   = 10;

                // 5. Trade mgmt
                MaxTradesPerDay = 3;
                Quantity        = 1;
                AllowLong       = true;
                AllowShort      = true;

                // 6. Session
                UsePrimeHoursOnly = true;
                PrimeStart = 93000;   // 9:30 AM ET
                PrimeEnd   = 153000;  // 3:30 PM ET
            }
            else if (State == State.DataLoaded)
            {
                emaCenter    = EMA(KeltnerPeriod);
                atrIndicator = ATR(ATRPeriod);
                atrSma50     = SMA(ATR(ATRPeriod), 50);

                deltaBuffer = new double[DeltaSMAPeriod];
                deltaIdx    = 0;
                deltaSum    = 0;

                pendingLong      = false;
                pendingShort     = false;
                pendingSwingLow  = 0;
                pendingSwingHigh = 0;
                pendingBar       = -1;

                initialStop   = 0;
                breakevenSet  = false;
                tradesToday   = 0;
                lastTradeDate = DateTime.MinValue;
            }
        }

        protected override void OnBarUpdate()
        {
            // Necesitamos suficientes barras para ATR(14) + SMA(50) + SwingLookback
            int warmup = Math.Max(KeltnerPeriod, Math.Max(ATRPeriod + 50, SwingLookback)) + 5;
            if (CurrentBar < warmup) return;

            // Reset contador diario al entrar en nuevo día
            if (Time[0].Date != lastTradeDate.Date)
                tradesToday = 0;

            // Calcular bandas Keltner
            double ema   = emaCenter[0];
            double atr   = atrIndicator[0];
            double upper = ema + KeltnerMultiplier * atr;
            double lower = ema - KeltnerMultiplier * atr;

            // Delta sintético: barra alcista → +Vol, barra bajista → -Vol
            double barDelta = Close[0] >= Open[0] ? Volume[0] : -Volume[0];

            // Actualizar buffer circular para SMA del delta
            deltaSum -= deltaBuffer[deltaIdx];
            deltaBuffer[deltaIdx] = barDelta;
            deltaSum += barDelta;
            deltaIdx = (deltaIdx + 1) % DeltaSMAPeriod;
            double deltaSma = deltaSum / DeltaSMAPeriod;

            // ── Si hay posición abierta, gestionar y salir ──
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManagePosition(atr);
                return;
            }

            // ── Gates globales ──
            if (!IsInPrimeHours())
            {
                pendingLong = pendingShort = false;   // pending expira fuera de horario
                return;
            }

            // Tendencia: pendiente de la EMA central
            bool bullTrend = emaCenter[0] > emaCenter[TrendConfirmBars];
            bool bearTrend = emaCenter[0] < emaCenter[TrendConfirmBars];

            // Umbral de delta mínimo (el mayor entre ratio y absoluto)
            double deltaMin = Math.Max(Math.Abs(deltaSma) * MinDeltaRatio, MinDeltaAbs);

            // ══════════════════════════════════════════════
            // PASO 1: Confirmar pending de la barra anterior
            // Pending expira si no se confirma en exactamente 1 barra
            // ══════════════════════════════════════════════
            if (pendingLong && CurrentBar == pendingBar + 1 && tradesToday < MaxTradesPerDay)
            {
                bool confirms = Close[0] > Open[0]     // barra alcista
                             && barDelta >= deltaMin;   // delta confirma presión compradora

                if (confirms)
                {
                    double stopDist = Close[0] - pendingSwingLow;
                    if (stopDist > 0 && stopDist <= atr * MaxStopATR)
                    {
                        EnterLong(Quantity, "KF_Long");
                        initialStop   = pendingSwingLow;
                        breakevenSet  = false;
                        tradesToday++;
                        lastTradeDate = Time[0];
                    }
                }
                pendingLong = false;   // expire — solo 1 barra de oportunidad
            }

            if (pendingShort && CurrentBar == pendingBar + 1 && tradesToday < MaxTradesPerDay)
            {
                bool confirms = Close[0] < Open[0]      // barra bajista
                             && barDelta <= -deltaMin;   // delta confirma presión vendedora

                if (confirms)
                {
                    double stopDist = pendingSwingHigh - Close[0];
                    if (stopDist > 0 && stopDist <= atr * MaxStopATR)
                    {
                        EnterShort(Quantity, "KF_Short");
                        initialStop   = pendingSwingHigh;
                        breakevenSet  = false;
                        tradesToday++;
                        lastTradeDate = Time[0];
                    }
                }
                pendingShort = false;  // expire
            }

            // ══════════════════════════════════════════════
            // PASO 2: Detectar nuevo contacto con zona Keltner
            // Zona LONG = EMA - KeltnerMult×ATR ... EMA - (KeltnerMult-ZoneTol)×ATR
            // Zona SHORT = EMA + (KeltnerMult-ZoneTol)×ATR ... EMA + KeltnerMult×ATR
            // ══════════════════════════════════════════════
            if (tradesToday < MaxTradesPerDay)
            {
                // Filtro de ruido (opcional)
                if (UseNoiseFilter && atr < atrSma50[0] * MinATRRatio) return;

                // LONG: precio entra en zona inferior
                if (AllowLong && bullTrend && Low[0] <= lower + atr * ZoneTolerance)
                {
                    double swingLow = Low[0];
                    for (int i = 1; i < SwingLookback && i < CurrentBar; i++)
                        swingLow = Math.Min(swingLow, Low[i]);

                    pendingLong      = true;
                    pendingShort     = false;
                    pendingBar       = CurrentBar;
                    pendingSwingLow  = swingLow - StopBufferTicks * TickSize;
                }
                // SHORT: precio entra en zona superior
                else if (AllowShort && bearTrend && High[0] >= upper - atr * ZoneTolerance)
                {
                    double swingHigh = High[0];
                    for (int i = 1; i < SwingLookback && i < CurrentBar; i++)
                        swingHigh = Math.Max(swingHigh, High[i]);

                    pendingShort     = true;
                    pendingLong      = false;
                    pendingBar       = CurrentBar;
                    pendingSwingHigh = swingHigh + StopBufferTicks * TickSize;
                }
            }
        }

        // ─────────────────────────────────────────────────
        private void ManagePosition(double currentAtr)
        // ─────────────────────────────────────────────────
        {
            double entry    = Position.AveragePrice;
            double stopDist = Math.Abs(entry - initialStop);
            if (stopDist <= 0) return;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                // Mover SL a BE cuando alcanza BreakevenR
                if (!breakevenSet && BreakevenR > 0 && High[0] >= entry + BreakevenR * stopDist)
                {
                    initialStop  = entry;
                    breakevenSet = true;
                }
                // Stop loss (SL inicial o BE)
                if (Low[0] <= initialStop)
                {
                    ExitLong(Quantity, "KF_Long_Stop", "KF_Long");
                    return;
                }
                // Profit target
                if (High[0] >= entry + TargetRR * stopDist)
                    ExitLong(Quantity, "KF_Long_Target", "KF_Long");
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                // Mover SL a BE
                if (!breakevenSet && BreakevenR > 0 && Low[0] <= entry - BreakevenR * stopDist)
                {
                    initialStop  = entry;
                    breakevenSet = true;
                }
                // Stop loss
                if (High[0] >= initialStop)
                {
                    ExitShort(Quantity, "KF_Short_Stop", "KF_Short");
                    return;
                }
                // Profit target
                if (Low[0] <= entry - TargetRR * stopDist)
                    ExitShort(Quantity, "KF_Short_Target", "KF_Short");
            }
        }

        // ─────────────────────────────────────────────────
        private bool IsInPrimeHours()
        // ─────────────────────────────────────────────────
        {
            if (!UsePrimeHoursOnly) return true;
            int t = ToTime(Time[0]);
            return t >= PrimeStart && t < PrimeEnd;
        }
    }
}
