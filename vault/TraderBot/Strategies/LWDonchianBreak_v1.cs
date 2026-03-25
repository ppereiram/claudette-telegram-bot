// LWDonchianBreak_v1.cs
// Estrategia de Larry Williams — Donchian Channel Breakout
//
// CONCEPTO: 3 filtros independientes para entrar solo en breakouts de alta probabilidad:
//   1. Donchian Channel (96 barras): ¿Es un nuevo máximo/mínimo de ~8 horas?
//   2. Williams %R (25 períodos): ¿Tiene momentum en la dirección correcta?
//   3. Volumen SMA (30 períodos): ¿Hay volumen real detrás del movimiento?
//
// REGLAS:
//   LONG:  Close > Donchian.Upper[bar anterior]   (breakout alcista confirmado al cierre)
//          + Williams%R > -50                       (momentum alcista)
//          + Volume > VolSMA                        (volumen sobre promedio)
//          + Close > Open                           (vela alcista)
//
//   SHORT: Close < Donchian.Lower[bar anterior]   (breakout bajista confirmado al cierre)
//          + Williams%R < -50                       (momentum bajista)
//          + Volume > VolSMA                        (volumen sobre promedio)
//          + Close < Open                           (vela bajista)
//
//   STOP:  ATR(14) × StopMultiple (CalculationMode.Ticks)
//   TARGET: TargetRR × stop
//   BE:    Mover stop a entrada cuando unrealized = BreakevenR × stop
//
// Chart: 5-min MNQ ##-## (sesión continua)
// ⚠️  IsExitOnSessionCloseStrategy = TRUE — intraday, compatible con Apex
// ⚠️  Params tiempo en formato ET (Eastern Time)
//
// Ref: Larry Williams World Cup Trading Championships (11,300% en 12 meses)
//      Su hija Michelle Williams ganó el campeonato de 1997 con la misma estrategia base

#region Using declarations
using System;
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

namespace NinjaTrader.NinjaScript.Strategies
{
    public class LWDonchianBreak_v1 : Strategy
    {
        #region Fields

        private DonchianChannel donchian;
        private WilliamsR       williamsR;
        private SMA             volSma;
        private ATR             atrIndicator;

        private int      tradesToday;
        private DateTime lastTradeDate;

        // Breakeven management
        private bool beMoved;
        private int  storedBeTicks;

        // Timezone
        private TimeZoneInfo EasternZone;

        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Larry Williams Donchian Channel Breakout: " +
                              "Donchian(133 = ~1 semana) + Williams%R(21) + Volumen(20). " +
                              "Chart: 15-min MNQ (##-##). AllowShort=OFF.";
                Name        = "LWDonchianBreak_v1";

                Calculate                    = Calculate.OnBarClose;
                EntriesPerDirection          = 1;
                EntryHandling                = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;
                MaximumBarsLookBack          = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution          = OrderFillResolution.Standard;
                Slippage                     = 1;
                StartBehavior                = StartBehavior.WaitUntilFlat;
                StopTargetHandling           = StopTargetHandling.PerEntryExecution;
                TraceOrders                  = false;

                // 01 - Trade Management
                Quantity        = 1;
                MaxTradesPerDay = 1;

                // 02 - Donchian Channel
                DonchianPeriod  = 133;     // 133 × 15min = ~5 días = breakout semanal

                // 03 - Williams %R (LWTI — Larry Williams Trade Index)
                WilliamsRPeriod = 21;      // momentum: >-50 = alcista, <-50 = bajista

                // 04 - Volume
                VolumeMAPeriod  = 20;      // volumen sobre su promedio de 20 barras = confirma

                // 05 - Stop / Target
                ATRPeriod    = 7;
                StopMultiple = 0.8;        // confirmado backtest — 15-min ATR es más amplio que 5-min
                TargetRR     = 3.0;        // confirmado backtest — sweet spot PF=1.61
                BreakevenR   = 1.0;

                // 06 - Direction — AllowShort=OFF: MNQ sesgo alcista, shorts = $0 en todos los tests
                AllowLong  = true;
                AllowShort = false;

                // 07 - Prime Hours (ET)
                UsePrimeHoursOnly = true;
                PrimeStart        = 93000;   // 9:30 ET
                PrimeEnd          = 153000;  // 15:30 ET
            }
            else if (State == State.DataLoaded)
            {
                EasternZone  = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                donchian     = DonchianChannel(DonchianPeriod);
                williamsR    = WilliamsR(WilliamsRPeriod);
                volSma       = SMA(Volume, VolumeMAPeriod);
                atrIndicator = ATR(ATRPeriod);
            }
        }

        // ── Timezone helper (backtest = Time[0] ya es ET; live = UTC→ET) ──────
        private int GetEtTime()
        {
            if (State == State.Historical)
                return ToTime(Time[0]);
            return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
        }

        // ── Main logic ────────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            // Suficientes barras para todos los indicadores
            int barsNeeded = Math.Max(DonchianPeriod,
                             Math.Max(WilliamsRPeriod,
                             Math.Max(VolumeMAPeriod, ATRPeriod))) + 5;
            if (CurrentBar < barsNeeded) return;

            // ── Reset contador diario ─────────────────────────────────────────
            if (Time[0].Date != lastTradeDate)
            {
                tradesToday   = 0;
                lastTradeDate = Time[0].Date;
            }

            int etTime = GetEtTime();

            // ── GESTIÓN DE POSICIÓN ABIERTA: mover stop a breakeven ───────────
            if (Position.MarketPosition == MarketPosition.Long)
            {
                if (!beMoved && storedBeTicks > 0)
                {
                    double profitTicks = (Close[0] - Position.AveragePrice) / TickSize;
                    if (profitTicks >= storedBeTicks)
                    {
                        SetStopLoss("LW_L", CalculationMode.Price, Position.AveragePrice, false);
                        beMoved = true;
                    }
                }
                return;  // no buscar nuevas entradas mientras en posición
            }

            if (Position.MarketPosition == MarketPosition.Short)
            {
                if (!beMoved && storedBeTicks > 0)
                {
                    double profitTicks = (Position.AveragePrice - Close[0]) / TickSize;
                    if (profitTicks >= storedBeTicks)
                    {
                        SetStopLoss("LW_S", CalculationMode.Price, Position.AveragePrice, false);
                        beMoved = true;
                    }
                }
                return;
            }

            // ── FILTROS ───────────────────────────────────────────────────────
            if (tradesToday >= MaxTradesPerDay) return;
            if (UsePrimeHoursOnly && (etTime < PrimeStart || etTime >= PrimeEnd)) return;

            // ── SEÑALES ───────────────────────────────────────────────────────
            // Donchian del bar ANTERIOR (evita comparar contra canal que incluye la vela actual)
            double upperPrev = donchian.Upper[1];
            double lowerPrev = donchian.Lower[1];

            // Williams %R: -100 (oversold) a 0 (overbought)
            // >-50 = momentum alcista (upper half), <-50 = momentum bajista (lower half)
            double wR = williamsR[0];

            // Volumen: la barra actual debe superar el promedio Y ser en la dirección correcta
            bool volAboveMA = Volume[0] > volSma[0];
            bool bullBar    = Close[0] > Open[0];   // vela verde = volumen "verde"
            bool bearBar    = Close[0] < Open[0];   // vela roja  = volumen "rojo"

            // ATR para stop loss dinámico
            double atr = atrIndicator[0];
            if (atr <= 0) return;

            int stopTicks   = Math.Max(4, (int)Math.Round(atr * StopMultiple / TickSize));
            int targetTicks = Math.Max(1, (int)Math.Round(stopTicks * TargetRR));
            int beTicks     = BreakevenR > 0
                                ? Math.Max(1, (int)Math.Round(stopTicks * BreakevenR))
                                : 0;

            // ── SEÑAL LONG ────────────────────────────────────────────────────
            // Nuevo máximo de 8 horas (breakout alcista) + momentum + volumen + vela alcista
            if (AllowLong
                && Close[0]  > upperPrev   // cierre sobre el máximo Donchian anterior
                && wR        > -50         // Williams %R en zona alcista
                && volAboveMA              // volumen sobre su promedio
                && bullBar)                // vela verde confirma dirección
            {
                storedBeTicks = beTicks;
                beMoved       = false;

                SetStopLoss   ("LW_L", CalculationMode.Ticks, stopTicks,   false);
                SetProfitTarget("LW_L", CalculationMode.Ticks, targetTicks);
                EnterLong(Quantity, "LW_L");
                tradesToday++;
            }
            // ── SEÑAL SHORT ───────────────────────────────────────────────────
            // Nuevo mínimo de 8 horas (breakout bajista) + momentum + volumen + vela bajista
            else if (AllowShort
                     && Close[0]  < lowerPrev  // cierre bajo el mínimo Donchian anterior
                     && wR        < -50         // Williams %R en zona bajista
                     && volAboveMA              // volumen sobre su promedio
                     && bearBar)                // vela roja confirma dirección
            {
                storedBeTicks = beTicks;
                beMoved       = false;

                SetStopLoss   ("LW_S", CalculationMode.Ticks, stopTicks,   false);
                SetProfitTarget("LW_S", CalculationMode.Ticks, targetTicks);
                EnterShort(Quantity, "LW_S");
                tradesToday++;
            }
        }

        // ── Reset al salir de posición ────────────────────────────────────────
        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            if (marketPosition == MarketPosition.Flat)
            {
                storedBeTicks = 0;
                beMoved       = false;
            }
        }

        // ── Parameters ────────────────────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Quantity (contratos)", GroupName = "01 - Trade Management", Order = 0)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Max Trades/Día", GroupName = "01 - Trade Management", Order = 1)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(5, 500)]
        [Display(Name = "Donchian Period (def. 96 = ~8h en 5-min)", GroupName = "02 - Donchian Channel", Order = 0)]
        public int DonchianPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(2, 100)]
        [Display(Name = "Williams %R Period (def. 25)", GroupName = "03 - Williams %R (LWTI)", Order = 0)]
        public int WilliamsRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(2, 100)]
        [Display(Name = "Volume MA Period (def. 30)", GroupName = "04 - Volume", Order = 0)]
        public int VolumeMAPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(2, 50)]
        [Display(Name = "ATR Period", GroupName = "05 - Stop / Target", Order = 0)]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Stop Múltiplo ATR", GroupName = "05 - Stop / Target", Order = 1)]
        public double StopMultiple { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 10.0)]
        [Display(Name = "Target R:R", GroupName = "05 - Stop / Target", Order = 2)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Breakeven R (0 = OFF)", GroupName = "05 - Stop / Target", Order = 3)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "06 - Direction", Order = 0)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "06 - Direction", Order = 1)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Solo Prime Hours", GroupName = "07 - Prime Hours (ET)", Order = 0)]
        public bool UsePrimeHoursOnly { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Prime Start (ET HHMMSS)", GroupName = "07 - Prime Hours (ET)", Order = 1)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name = "Prime End (ET HHMMSS)", GroupName = "07 - Prime Hours (ET)", Order = 2)]
        public int PrimeEnd { get; set; }

        #endregion
    }
}
