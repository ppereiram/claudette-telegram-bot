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
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
#endregion

/*
 * VolumeProfile_POC_v1 — POC Intradiario como Soporte/Resistencia
 * ─────────────────────────────────────────────────────────────────
 * Concepto: calcula el POC (Point of Control = precio con más volumen) de la sesión
 *           acumulando volumen por nivel de precio en barras de tiempo (sin Tick Replay).
 *
 * Setup LONG:  N barras consecutivas cerraron SOBRE el POC → precio retrocede a tocar
 *              la zona POC (Low ≤ pocPrice + PocZoneTicks) y cierra SOBRE el POC → ENTRY.
 *              SL = pocPrice - StopBufferTicks (estructural: si rompe el POC al cierre, error).
 *
 * Setup SHORT: espejo — N barras bajo POC → test al POC desde abajo → rechazo → SHORT.
 *
 * Chart recomendado: 5-min MNQ
 * Slippage: 1 tick
 */

namespace NinjaTrader.NinjaScript.Strategies
{
    public class VolumeProfile_POC_v1 : Strategy
    {
        // ── POC tracking ──
        private Dictionary<int, double> volByTick;  // tick index → cumulative volume
        private double pocPrice;
        private bool   pocValid;
        private int    pocSessionDate;   // qué día empezamos a trackear

        // ── Streak above/below POC ──
        private int barsAbovePoc;
        private int barsBelowPoc;

        // ── Trade state ──
        private double longStopPrice;
        private double shortStopPrice;
        private bool   longBeTriggered;
        private bool   shortBeTriggered;

        // ── Daily counter ──
        private int tradesToday;
        private int lastTradeDate;

        // ── Indicators ──
        private SMA volSma;
        private ATR atrIndicator;

        // ── Timezone ──
        private TimeZoneInfo easternZone;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description  = "VolumeProfile POC v1 — intraday POC as dynamic S/R";
                Name         = "VolumeProfile_POC_v1";
                Calculate    = Calculate.OnBarClose;
                EntriesPerDirection          = 1;
                EntryHandling                = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;

                PocTrackStart   = 90000;   // 9:00 ET — 30 min para estabilizar el POC
                PocZoneTicks    = 6;       // ±6 ticks = ±$1.50 de tolerancia
                MinBarsInTrend  = 3;       // 3 barras (15 min) sobre/bajo POC antes del test
                TargetRR        = 3.0;
                BreakevenR      = 1.0;
                StopBufferTicks = 5;
                MaxStopATR      = 3.0;     // skip si SL > 3×ATR desde entry
                MaxTradesPerDay = 1;
                AllowLong       = true;
                AllowShort      = true;
                InvertSignals   = false;   // true = operar dirección opuesta a la señal
                Quantity        = 1;
                UseVolumeFilter = true;
                VolumePeriod    = 20;
                MinVolRatio     = 1.2;
                PrimeStart      = 93000;
                PrimeEnd        = 153000;
                Slippage        = 1;
            }
            else if (State == State.DataLoaded)
            {
                easternZone  = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                volSma       = SMA(Volume, VolumePeriod);
                atrIndicator = ATR(14);

                volByTick        = new Dictionary<int, double>();
                pocPrice         = 0;
                pocValid         = false;
                pocSessionDate   = 0;
                barsAbovePoc     = 0;
                barsBelowPoc     = 0;
                tradesToday      = 0;
                lastTradeDate    = 0;
                longBeTriggered  = false;
                shortBeTriggered = false;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < VolumePeriod + 15)
                return;

            int etDate = GetEtDate();
            int etTime = GetEtTime();

            // ── Daily trade counter reset ──
            if (etDate != lastTradeDate)
            {
                tradesToday   = 0;
                lastTradeDate = etDate;
            }

            // ── POC session reset: nuevo día → limpiar histograma ──
            if (etDate != pocSessionDate && etTime >= PocTrackStart)
            {
                volByTick.Clear();
                pocPrice       = 0;
                pocValid       = false;
                pocSessionDate = etDate;
                barsAbovePoc   = 0;
                barsBelowPoc   = 0;
            }

            // ── Acumular volumen en el histograma desde PocTrackStart ──
            if (etTime >= PocTrackStart)
                UpdatePoc();

            // ── Gestionar posición abierta (sin restricción horaria en salidas) ──
            if (Position.MarketPosition == MarketPosition.Long)  { ManageLong();  return; }
            if (Position.MarketPosition == MarketPosition.Short) { ManageShort(); return; }

            if (!pocValid) return;

            // ── Actualizar streak de barras sobre/bajo POC (basado en barra ANTERIOR) ──
            // Usamos Close[1] para separar el "contexto previo" del "signal bar" actual
            if (CurrentBar >= 1)
            {
                if (Close[1] > pocPrice)
                {
                    barsAbovePoc++;
                    barsBelowPoc = 0;
                }
                else if (Close[1] < pocPrice)
                {
                    barsBelowPoc++;
                    barsAbovePoc = 0;
                }
                else
                {
                    barsAbovePoc = 0;
                    barsBelowPoc = 0;
                }
            }

            // ── Hora prime + trade count ──
            bool inPrime = etTime >= PrimeStart && etTime <= PrimeEnd;
            if (!inPrime || tradesToday >= MaxTradesPerDay)
                return;

            bool   volOk  = !UseVolumeFilter || Volume[0] >= volSma[0] * MinVolRatio;
            double curAtr = atrIndicator[0];
            double pocZone = PocZoneTicks * TickSize;

            // ═══════════════════════════════════════════════
            // Señales (detectadas independientemente de la dirección final)
            // ═══════════════════════════════════════════════
            bool longSignalActive  = AllowLong  && barsAbovePoc >= MinBarsInTrend
                                     && Low[0]  <= pocPrice + pocZone && Close[0] > pocPrice && volOk;
            bool shortSignalActive = AllowShort && barsBelowPoc >= MinBarsInTrend
                                     && High[0] >= pocPrice - pocZone && Close[0] < pocPrice && volOk;

            // ═══════════════════════════════════════════════
            // LONG signal → LONG (normal) o SHORT (invertido)
            // ═══════════════════════════════════════════════
            if (longSignalActive)
            {
                if (!InvertSignals)
                {
                    // Entrada LONG normal
                    double sl   = pocPrice - StopBufferTicks * TickSize;
                    double dist = Close[0] - sl;
                    if (dist > 0 && dist <= MaxStopATR * curAtr)
                    {
                        double tp = Close[0] + dist * TargetRR;
                        longStopPrice   = sl;
                        longBeTriggered = false;
                        EnterLong(Quantity, "Long");
                        SetStopLoss("Long",    CalculationMode.Price, sl, false);
                        SetProfitTarget("Long", CalculationMode.Price, tp);
                        tradesToday++;
                    }
                }
                else
                {
                    // INVERTIDO: señal long → entrar SHORT (stop estructural SOBRE el POC)
                    double sl   = pocPrice + StopBufferTicks * TickSize;
                    double dist = sl - Close[0];
                    if (dist > 0 && dist <= MaxStopATR * curAtr)
                    {
                        double tp = Close[0] - dist * TargetRR;
                        shortStopPrice   = sl;
                        shortBeTriggered = false;
                        EnterShort(Quantity, "Short");
                        SetStopLoss("Short",    CalculationMode.Price, sl, false);
                        SetProfitTarget("Short", CalculationMode.Price, tp);
                        tradesToday++;
                    }
                }
            }

            // ═══════════════════════════════════════════════
            // SHORT signal → SHORT (normal) o LONG (invertido)
            // ═══════════════════════════════════════════════
            if (shortSignalActive)
            {
                if (!InvertSignals)
                {
                    // Entrada SHORT normal
                    double sl   = pocPrice + StopBufferTicks * TickSize;
                    double dist = sl - Close[0];
                    if (dist > 0 && dist <= MaxStopATR * curAtr)
                    {
                        double tp = Close[0] - dist * TargetRR;
                        shortStopPrice   = sl;
                        shortBeTriggered = false;
                        EnterShort(Quantity, "Short");
                        SetStopLoss("Short",    CalculationMode.Price, sl, false);
                        SetProfitTarget("Short", CalculationMode.Price, tp);
                        tradesToday++;
                    }
                }
                else
                {
                    // INVERTIDO: señal short → entrar LONG (stop estructural BAJO el POC)
                    double sl   = pocPrice - StopBufferTicks * TickSize;
                    double dist = Close[0] - sl;
                    if (dist > 0 && dist <= MaxStopATR * curAtr)
                    {
                        double tp = Close[0] + dist * TargetRR;
                        longStopPrice   = sl;
                        longBeTriggered = false;
                        EnterLong(Quantity, "Long");
                        SetStopLoss("Long",    CalculationMode.Price, sl, false);
                        SetProfitTarget("Long", CalculationMode.Price, tp);
                        tradesToday++;
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // POC calculation (synthetic, sin Tick Replay)
        // Distribuye el volumen de cada barra uniformemente
        // entre Low y High (1 bucket por tick)
        // ─────────────────────────────────────────
        private void UpdatePoc()
        {
            int lowTick  = (int)Math.Round(Low[0]  / TickSize);
            int highTick = (int)Math.Round(High[0] / TickSize);
            int ticks    = Math.Max(1, highTick - lowTick);

            double volPerTick = Volume[0] / ticks;

            for (int i = lowTick; i <= highTick; i++)
            {
                if (!volByTick.ContainsKey(i))
                    volByTick[i] = 0;
                volByTick[i] += volPerTick;
            }

            // Hallar el tick con mayor volumen acumulado
            double maxVol  = 0;
            int    maxTick = 0;
            foreach (var kv in volByTick)
            {
                if (kv.Value > maxVol)
                {
                    maxVol  = kv.Value;
                    maxTick = kv.Key;
                }
            }

            pocPrice = maxTick * TickSize;
            pocValid  = true;
        }

        // ─────────────────────────────────────────
        // Position management
        // ─────────────────────────────────────────
        private void ManageLong()
        {
            if (BreakevenR <= 0 || longBeTriggered) return;
            double entry   = Position.AveragePrice;
            double beLevel = entry + (entry - longStopPrice) * BreakevenR;
            if (Close[0] >= beLevel)
            {
                SetStopLoss("Long", CalculationMode.Price, entry + TickSize, false);
                longBeTriggered = true;
            }
        }

        private void ManageShort()
        {
            if (BreakevenR <= 0 || shortBeTriggered) return;
            double entry   = Position.AveragePrice;
            double beLevel = entry - (shortStopPrice - entry) * BreakevenR;
            if (Close[0] <= beLevel)
            {
                SetStopLoss("Short", CalculationMode.Price, entry - TickSize, false);
                shortBeTriggered = true;
            }
        }

        // ─────────────────────────────────────────
        // Helpers
        // ─────────────────────────────────────────
        private int GetEtTime()
        {
            if (State == State.Historical)
                return ToTime(Time[0]);
            return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, easternZone));
        }

        private int GetEtDate()
        {
            if (State == State.Historical)
                return ToDay(Time[0]);
            return ToDay(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, easternZone));
        }

        // ─────────────────────────────────────────
        // Properties
        // ─────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Display(Name = "POC Track Start (ET HHMMSS)", Description = "Hora desde la que se acumula volumen para el POC",
                 GroupName = "1. POC Settings", Order = 1)]
        public int PocTrackStart { get; set; }

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "POC Zone (ticks)", Description = "Tolerancia alrededor del POC para contar como toque",
                 GroupName = "1. POC Settings", Order = 2)]
        public int PocZoneTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Min Bars In Trend", Description = "Barras previas que deben cerrar sobre/bajo el POC",
                 GroupName = "1. POC Settings", Order = 3)]
        public int MinBarsInTrend { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 15.0)]
        [Display(Name = "Target R:R", GroupName = "2. Risk Management", Order = 1)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Breakeven R", Description = "Mueve SL a entry cuando llega a entry + X×R  (0 = OFF)",
                 GroupName = "2. Risk Management", Order = 2)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Stop Buffer (ticks)", Description = "Ticks más allá del POC para el SL",
                 GroupName = "2. Risk Management", Order = 3)]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Max Stop ATR", Description = "Skip trade si distancia entry→SL > X × ATR(14)",
                 GroupName = "2. Risk Management", Order = 4)]
        public double MaxStopATR { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max Trades/Day", GroupName = "3. Trade Management", Order = 1)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "3. Trade Management", Order = 2)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "3. Trade Management", Order = 3)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Invert Signals", Description = "true = entrar en dirección OPUESTA a la señal (fading el sistema original)",
                 GroupName = "3. Trade Management", Order = 4)]
        public bool InvertSignals { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Quantity", GroupName = "3. Trade Management", Order = 4)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Use Volume Filter", GroupName = "4. Volume Filter", Order = 1)]
        public bool UseVolumeFilter { get; set; }

        [NinjaScriptProperty]
        [Range(3, 100)]
        [Display(Name = "Volume MA Period", GroupName = "4. Volume Filter", Order = 2)]
        public int VolumePeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Min Volume Ratio", Description = "Barra de señal debe tener Volume ≥ X × SMA(Volume)",
                 GroupName = "4. Volume Filter", Order = 3)]
        public double MinVolRatio { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime Start (ET HHMMSS)", GroupName = "5. Trading Hours", Order = 1)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime End (ET HHMMSS)", GroupName = "5. Trading Hours", Order = 2)]
        public int PrimeEnd { get; set; }

        #endregion
    }
}
