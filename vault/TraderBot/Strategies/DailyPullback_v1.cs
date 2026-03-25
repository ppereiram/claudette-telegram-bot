// DailyPullback_v1.cs
// Estrategia de Ivan Sherman (campeón World Cup Trading Championships 2023)
//
// REGLAS (extraídas del seminario y backtesting público):
//   1. Precio > SMA(200) diaria → tendencia alcista confirmada
//   2. N cierres consecutivos bajistas (Close[i] < Close[i+1]) — pullback
//      IMPORTANTE: es comparación de CIERRES, no de color de vela.
//      Un gap al alza con cierre > cierre anterior ROMPE la secuencia.
//   3. COMPRA en la apertura del día siguiente (NT8 fills al next open automáticamente)
//   4. SALIDA: cuando Close > SMA(5) → venta al open del día siguiente
//   5. STOP: close-to-close ATR(14) × StopMultiple (relativo al fill real)
//
// Chart: DIARIO (Day 1) — MNQ ##-## (contrato continuo)
// ⚠️  IsExitOnSessionCloseStrategy = FALSE — swing strategy, hold overnight
// ⚠️  Solo LONG. El sesgo alcista del MNQ hace los longs más fiables.
//
// Referencia video backtest: PF≈2.3-2.7 en SP500/16 años con stop vol ATR
// WR esperada: ~63-73% (muy superior al portafolio intraday — estrategia de alta WR)

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
    public class DailyPullback_v1 : Strategy
    {
        #region Fields

        private SMA smaTrend;       // SMA(SmaTrendPeriod) — filtro de tendencia
        private SMA smaExit;        // SMA(SmaExitPeriod)  — señal de salida

        private int storedSlTicks;  // stop calculado en el bar de señal (ticks)

        // ── Timezone ───────────────────────────────────────────────────────────
        private TimeZoneInfo EasternZone;

        #endregion

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Ivan Sherman: N cierres consecutivos bajistas + Close > SMA(200). " +
                              "Salida cuando Close > SMA(5). Stop: close-to-close ATR×múltiplo. " +
                              "Chart: Diario MNQ (##-##).";
                Name = "DailyPullback_v1";

                Calculate                          = Calculate.OnBarClose;
                EntriesPerDirection                = 1;
                EntryHandling                      = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy       = false;  // ← CRÍTICO: swing overnight
                MaximumBarsLookBack                = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                = OrderFillResolution.Standard;
                Slippage                           = 1;
                StartBehavior                      = StartBehavior.WaitUntilFlat;
                StopTargetHandling                 = StopTargetHandling.PerEntryExecution;
                TraceOrders                        = false;

                // 01 - Trade Management
                Quantity = 1;   // empezar con 1ct — escalar tras confirmar MaxDD

                // 02 - Trend & Exit
                SmaTrendPeriod = 200;   // SMA200: filtro tendencia alcista
                SmaExitPeriod  = 5;     // SMA5: señal de salida

                // 03 - Pullback
                ConsecDownDays = 3;     // Ivan Sherman: 3 días bajistas consecutivos

                // 04 - Stop Loss
                ATRPeriod    = 14;      // periodo para close-to-close ATR
                StopMultiple = 1.0;     // stop = ATR14 × 1.0 (probar 0.5 / 1.0 / 1.5 / 2.0)
            }
            else if (State == State.DataLoaded)
            {
                EasternZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                smaTrend    = SMA(SmaTrendPeriod);
                smaExit     = SMA(SmaExitPeriod);
            }
        }

        // ─── Close-to-close ATR ───────────────────────────────────────────────────
        // Ivan Sherman usa el promedio del movimiento close-to-close de los últimos N días
        // como medida de volatilidad para el stop loss.
        // Equivale a un ATR sin considerar High/Low — solo cierres.
        private double GetCloseToCloseATR(int period)
        {
            if (CurrentBar < period + 1) return 0;
            double sum = 0;
            for (int i = 0; i < period; i++)
                sum += Math.Abs(Close[i] - Close[i + 1]);
            return sum / period;
        }

        // ─── Main logic ───────────────────────────────────────────────────────────
        protected override void OnBarUpdate()
        {
            // Necesitamos suficientes barras para SMA200 + ATR14 + ConsecDownDays
            if (CurrentBar < SmaTrendPeriod + ATRPeriod + ConsecDownDays + 5) return;

            // ── SALIDA ─────────────────────────────────────────────────────────
            // Cuando estamos en posición long, monitorear el cruce SMA5
            if (Position.MarketPosition == MarketPosition.Long)
            {
                if (Close[0] > smaExit[0])
                {
                    // Exit al open del día siguiente (NT8 behavior con OnBarClose)
                    ExitLong("Exit_SMA5", "DP_L");
                }
                return;  // no buscar nuevas entradas mientras en posición
            }

            // ── ENTRADA ────────────────────────────────────────────────────────

            // REGLA 1: N cierres consecutivos bajistas
            // Comparación de CIERRES (no colores de vela). Un gap al alza rompe la secuencia.
            bool consecDown = true;
            for (int i = 0; i < ConsecDownDays; i++)
            {
                if (Close[i] >= Close[i + 1])
                {
                    consecDown = false;
                    break;
                }
            }
            if (!consecDown) return;

            // REGLA 2: Tendencia alcista confirmada (precio sobre SMA200)
            if (Close[0] <= smaTrend[0]) return;

            // REGLA 3: Calcular stop loss con close-to-close ATR
            double atr = GetCloseToCloseATR(ATRPeriod);
            if (atr <= 0) return;

            // Convertir a ticks (CalculationMode.Ticks = relativo al FILL real del próximo open)
            storedSlTicks = Math.Max(4, (int)Math.Round(atr * StopMultiple / TickSize));

            // ENTRADA: stop se aplica al precio real del fill (no al close de hoy)
            // NT8 con Calculate.OnBarClose → EnterLong se ejecuta al open del día siguiente
            SetStopLoss("DP_L", CalculationMode.Ticks, storedSlTicks, false);
            EnterLong(Quantity, "DP_L");

            // Marca visual en el chart (opcional — descomentar para ver señales)
            // Draw.Text(this, "E_" + CurrentBar, "↑ Buy", 0,
            //     Low[0] - 5 * TickSize, Brushes.LimeGreen);
        }

        // ─── Reset al salir de posición ───────────────────────────────────────────
        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            if (marketPosition == MarketPosition.Flat)
                storedSlTicks = 0;
        }

        // ─── Parameters ───────────────────────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Range(1, int.MaxValue)]
        [Display(Name = "Quantity (contratos)", GroupName = "01 - Trade Management", Order = 0)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Range(10, 500)]
        [Display(Name = "SMA Tendencia (ej. 200)", GroupName = "02 - Trend & Exit", Order = 0)]
        public int SmaTrendPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(2, 50)]
        [Display(Name = "SMA Salida (ej. 5)", GroupName = "02 - Trend & Exit", Order = 1)]
        public int SmaExitPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name = "Días Consecutivos Bajistas", GroupName = "03 - Pullback", Order = 0)]
        public int ConsecDownDays { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name = "ATR Period (close-to-close)", GroupName = "04 - Stop Loss", Order = 0)]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Stop Múltiplo ATR", GroupName = "04 - Stop Loss", Order = 1)]
        public double StopMultiple { get; set; }

        #endregion
    }
}
