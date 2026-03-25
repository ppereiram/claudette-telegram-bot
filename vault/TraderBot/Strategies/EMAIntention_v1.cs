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
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    // ====================================================================
    // EMAIntention v1.0
    //
    // Concepto del profesor:
    //   "Cuando el mercado esta fuerte en las primeras horas, espera que
    //    una vela de INTENCION cruce el EMA 21 acompanada de volumen alto.
    //    1:1 R:R, 100 ticks target, maximo 3 trades al dia."
    //
    // Dos modos de entrada (EntryMode):
    //   CROSSOVER: La vela actualmente cruza el EMA (momento exacto de ruptura)
    //   BOUNCE:    Precio cerca del EMA en direccion de tendencia, rebote
    //
    // Indicadores de apoyo (todos opcionales):
    //   ADX      → Solo opera cuando hay tendencia fuerte (evita chop)
    //   RSI      → Evita entradas en zonas extremas (overbought/oversold)
    //   EMA Slow → Filtra por tendencia de mayor escala (EMA 50/100/200)
    //   Volume   → Confirma "explosion" de volumen en la vela de intencion
    //   Cuerpo   → MinBodyRatio garantiza que es una vela de verdadera intencion
    // ====================================================================
    public class EMAIntention_v1 : Strategy
    {
        // ===== INDICADORES =====
        private EMA  emaPrincipal;       // EMA 21 (trigger)
        private EMA  emaTendencia;       // EMA lenta (filtro tendencia)
        private ATR  atr;
        private ADX  adx;
        private RSI  rsi;
        private SMA  volumeSMA;

        // ===== CONTROL DIARIO =====
        private int      tradesHoy        = 0;
        private DateTime lastSessionDate  = DateTime.MinValue;
        private double   dailyRealizedPnL = 0;
        private bool     maxLossHit       = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "EMA Intention v1.0 — Vela de intencion en EMA21 + filtros ADX/RSI/Volumen";
                Name        = "EMAIntention_v1";

                Calculate                              = Calculate.OnBarClose;
                EntriesPerDirection                    = 1;
                EntryHandling                          = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy           = true;
                ExitOnSessionCloseSeconds              = 30;
                StopTargetHandling                     = StopTargetHandling.PerEntryExecution;
                MaximumBarsLookBack                    = MaximumBarsLookBack.TwoHundredFiftySix;
                BarsRequiredToTrade                    = 30;
                Slippage                               = 1;
                StartBehavior                          = StartBehavior.WaitUntilFlat;
                TimeInForce                            = TimeInForce.Gtc;
                TraceOrders                            = false;
                RealtimeErrorHandling                  = RealtimeErrorHandling.StopCancelClose;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. EMA ===
                EMAPrincipalPeriod  = 21;     // La media del profesor
                UseModoCrossover    = true;    // true=Crossover, false=Bounce cerca de EMA
                BounceProximityATR  = 0.5;    // Para modo Bounce: dentro de 0.5x ATR del EMA

                // === 2. VELA DE INTENCION ===
                MinBodyRatio        = 0.55;   // Cuerpo >= 55% del rango total de la vela
                MinRangeATRMulti    = 0.4;    // Rango de la vela >= 0.4x ATR (evita dojis)
                RequireVolSpike     = true;    // Exigir volumen superior al promedio
                VolMultiplier       = 1.5;    // Volumen >= 1.5x SMA20 del volumen
                VolSMAPeriod        = 20;

                // === 3. FILTROS DE APOYO ===
                UseADX              = true;    // ADX: solo tradear cuando hay tendencia
                ADXPeriod           = 14;
                ADXMinThreshold     = 20.0;   // ADX > 20 = mercado direccional
                UseRSI              = true;    // RSI: evitar zonas extremas
                RSIPeriod           = 14;
                RSILongMax          = 65;     // No entrar long si RSI > 65 (overbought)
                RSIShortMin         = 35;     // No entrar short si RSI < 35 (oversold)
                UseTrendFilter      = true;    // Filtrar por EMA lenta
                TrendEMAPeriod      = 50;     // Long solo si Close > EMA50, Short si <EMA50

                // === 4. RIESGO ===
                Contratos           = 5;
                TargetTicks         = 100;    // 100 ticks = 25 pts MNQ
                RiskRewardRatio     = 1.0;    // 1:1 default (stop = target/R:R)
                MaxTradesPerDay     = 3;      // El profesor: no mas de 3
                MaxDailyLoss        = 500;    // $0 = desactivado

                // === 5. BREAKEVEN ===
                UseBreakeven        = true;
                BreakevenAtR        = 0.5;    // Mover a BE cuando ganas 0.5R (50 ticks)

                // === 6. HORARIO ===
                // "Primeras horas cuando el mercado esta fuerte"
                HoraInicio          = 93000;  // 9:30 AM EST
                HoraFin             = 113000; // 11:30 AM EST
                HoraCorte           = 110000; // No nuevas entradas despues de 11:00 AM

                // === 7. DIRECCION ===
                AllowLong           = true;
                AllowShort          = true;

                // === 8. DEBUG ===
                DebugMode           = false;
            }
            else if (State == State.DataLoaded)
            {
                emaPrincipal = EMA(EMAPrincipalPeriod);
                emaTendencia = EMA(TrendEMAPeriod);
                atr          = ATR(14);
                adx          = ADX(ADXPeriod);
                rsi          = RSI(RSIPeriod, 3);
                volumeSMA    = SMA(Volume, VolSMAPeriod);

                emaPrincipal.Plots[0].Brush = Brushes.Yellow;
                emaTendencia.Plots[0].Brush = Brushes.DodgerBlue;
                AddChartIndicator(emaPrincipal);
                AddChartIndicator(emaTendencia);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(TrendEMAPeriod + 5, 30))
                return;

            // === RESET DIARIO ===
            if (lastSessionDate != Time[0].Date)
            {
                lastSessionDate  = Time[0].Date;
                tradesHoy        = 0;
                dailyRealizedPnL = 0;
                maxLossHit       = false;

                if (DebugMode)
                    Print(string.Format("=== NUEVA SESION: {0} ===", Time[0].Date.ToShortDateString()));
            }

            // === GESTIONAR POSICION ABIERTA (siempre, independiente de horario) ===
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageBreakeven();
                return;
            }

            // === FILTROS DE OPERACION ===
            if (maxLossHit) return;
            if (tradesHoy >= MaxTradesPerDay) return;

            // Filtro horario
            int t = ToTime(Time[0]);
            if (t < HoraInicio || t > HoraFin || t >= HoraCorte) return;

            // === BUSCAR SETUP ===
            CheckForSetup();
        }

        private void CheckForSetup()
        {
            // ----------------------------------------------------------------
            // ANALISIS DE LA VELA DE INTENCION
            // Una vela de intencion tiene:
            //   1. Cuerpo grande (MinBodyRatio del rango)
            //   2. Rango suficiente (no un doji ni micro-vela)
            //   3. Volumen elevado (opcional)
            // ----------------------------------------------------------------
            double rango       = High[0] - Low[0];
            double cuerpo      = Math.Abs(Close[0] - Open[0]);
            double bodyRatio   = rango > 0 ? cuerpo / rango : 0;

            bool intencionAlcista  = Close[0] > Open[0]   // Vela alcista
                                  && bodyRatio >= MinBodyRatio  // Cuerpo grande
                                  && rango >= atr[0] * MinRangeATRMulti; // Rango significativo

            bool intencionBajista  = Close[0] < Open[0]   // Vela bajista
                                  && bodyRatio >= MinBodyRatio
                                  && rango >= atr[0] * MinRangeATRMulti;

            // Volumen de explosion (opcional)
            bool volOK = !RequireVolSpike || Volume[0] >= volumeSMA[0] * VolMultiplier;

            // ----------------------------------------------------------------
            // FILTROS DE APOYO (opcionales)
            // ----------------------------------------------------------------

            // ADX: mercado en tendencia (evita lateralizacion/chop)
            bool adxOK = !UseADX || adx[0] >= ADXMinThreshold;

            // EMA lenta: filtro de tendencia mayor
            bool tendenciaBull = !UseTrendFilter || Close[0] > emaTendencia[0];
            bool tendenciaBear = !UseTrendFilter || Close[0] < emaTendencia[0];

            // RSI: no en zonas extremas
            bool rsiLongOK  = !UseRSI || rsi[0] < RSILongMax;
            bool rsiShortOK = !UseRSI || rsi[0] > RSIShortMin;

            // ----------------------------------------------------------------
            // MODO CROSSOVER: La vela actualmente cruza el EMA 21
            // La intencion ES el cruce — precio estaba al otro lado y ahora lo cruza
            // Este es el concepto original del profesor
            // ----------------------------------------------------------------
            if (UseModoCrossover)
            {
                bool cruceLong  = Close[0] > emaPrincipal[0] && Close[1] <= emaPrincipal[1]; // Cruza hacia arriba
                bool cruceBear  = Close[0] < emaPrincipal[0] && Close[1] >= emaPrincipal[1]; // Cruza hacia abajo

                if (DebugMode && (cruceLong || cruceBear))
                    Print(string.Format("{0} CRUCE detectado | Dir:{1} | ADX:{2:F1} | RSI:{3:F0} | Body:{4:F0}% | Vol:{5:F0}/{6:F0}",
                        Time[0].ToShortTimeString(), cruceLong ? "BULL" : "BEAR",
                        adx[0], rsi[0], bodyRatio * 100, Volume[0], volumeSMA[0]));

                // LONG: cruce alcista + vela de intencion + filtros
                if (AllowLong && cruceLong && intencionAlcista && volOK && adxOK && tendenciaBull && rsiLongOK)
                    ExecutarEntrada("LONG");

                // SHORT: cruce bajista + vela de intencion + filtros
                else if (AllowShort && cruceBear && intencionBajista && volOK && adxOK && tendenciaBear && rsiShortOK)
                    ExecutarEntrada("SHORT");
            }
            // ----------------------------------------------------------------
            // MODO BOUNCE: Precio en tendencia, se acerca al EMA y rebota
            // La intencion NO cruza — confirma el soporte/resistencia del EMA
            // Mas conservador, para mercados que respetan la media
            // ----------------------------------------------------------------
            else
            {
                double distanciaEMA = Math.Abs(Close[0] - emaPrincipal[0]);
                bool cercaEMA = distanciaEMA <= atr[0] * BounceProximityATR;

                // LONG: Precio sobre EMA (tendencia alcista), cerca de ella, rebote alcista
                bool bounceLong = Close[0] > emaPrincipal[0]  // Sobre el EMA (tendencia up)
                               && cercaEMA                     // Pero cerca (pullback)
                               && Close[0] > Close[1]          // Este bar sube vs anterior
                               && Low[0] <= emaPrincipal[0] + atr[0] * BounceProximityATR; // Toco zona EMA

                // SHORT: Precio bajo EMA (tendencia bajista), cerca, rebote bajista
                bool bounceBear = Close[0] < emaPrincipal[0]
                               && cercaEMA
                               && Close[0] < Close[1]
                               && High[0] >= emaPrincipal[0] - atr[0] * BounceProximityATR;

                if (AllowLong && bounceLong && intencionAlcista && volOK && adxOK && tendenciaBull && rsiLongOK)
                    ExecutarEntrada("LONG");
                else if (AllowShort && bounceBear && intencionBajista && volOK && adxOK && tendenciaBear && rsiShortOK)
                    ExecutarEntrada("SHORT");
            }
        }

        private void ExecutarEntrada(string direccion)
        {
            // Calcular stop y target basados en ticks y R:R
            double targetDistance = TargetTicks * TickSize;
            double stopDistance   = targetDistance / RiskRewardRatio; // Para 1:1 → igual que target

            if (direccion == "LONG")
            {
                double stopPrice   = Close[0] - stopDistance;
                double targetPrice = Close[0] + targetDistance;

                EnterLong(Contratos, "LONG");
                SetStopLoss("LONG",     CalculationMode.Price, stopPrice,   false);
                SetProfitTarget("LONG", CalculationMode.Price, targetPrice);
            }
            else
            {
                double stopPrice   = Close[0] + stopDistance;
                double targetPrice = Close[0] - targetDistance;

                EnterShort(Contratos, "SHORT");
                SetStopLoss("SHORT",     CalculationMode.Price, stopPrice,   false);
                SetProfitTarget("SHORT", CalculationMode.Price, targetPrice);
            }

            tradesHoy++;

            if (DebugMode)
            {
                double riskDollars   = stopDistance * Contratos / TickSize * (TickSize * 2); // MNQ $0.50/tick
                Print(string.Format("*** {0} ENTRADA | EMA21={1:F2} | ADX={2:F1} | RSI={3:F0} | Vol={4:F0}/{5:F0} | Trades hoy={6}/{7}",
                    direccion, emaPrincipal[0], adx[0], rsi[0], Volume[0], volumeSMA[0], tradesHoy, MaxTradesPerDay));
                Print(string.Format("    Target={0} ticks | Stop={1:F0} ticks | R:R={2:F1}:1",
                    TargetTicks, stopDistance / TickSize, RiskRewardRatio));
            }
        }

        private void ManageBreakeven()
        {
            if (!UseBreakeven) return;

            double beDistance = TargetTicks * TickSize * BreakevenAtR; // Ej: 50 ticks para BreakevenAtR=0.5

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double profit = Close[0] - Position.AveragePrice;
                if (profit >= beDistance)
                {
                    double bePrecio = Position.AveragePrice + TickSize; // BE + 1 tick de beneficio
                    SetStopLoss("LONG", CalculationMode.Price, bePrecio, false);
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double profit = Position.AveragePrice - Close[0];
                if (profit >= beDistance)
                {
                    double bePrecio = Position.AveragePrice - TickSize;
                    SetStopLoss("SHORT", CalculationMode.Price, bePrecio, false);
                }
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (MaxDailyLoss <= 0) return;
            if (execution.Order == null) return;

            // Registrar P&L cuando cierra posicion
            if (marketPosition == MarketPosition.Flat && SystemPerformance.AllTrades.Count > 0)
            {
                var lastTrade = SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1];
                if (lastTrade.Exit.Time.Date == time.Date)
                {
                    dailyRealizedPnL += lastTrade.ProfitCurrency;

                    if (DebugMode)
                        Print(string.Format("Trade cerrado | P&L hoy: ${0:F2} | Limite: -${1:F2}",
                            dailyRealizedPnL, MaxDailyLoss));

                    if (dailyRealizedPnL <= -MaxDailyLoss)
                    {
                        maxLossHit = true;
                        Print(string.Format("*** LIMITE PERDIDA DIARIA: ${0:F2} ***", dailyRealizedPnL));
                    }
                }
            }
        }

        #region Properties

        // === 1. EMA ===
        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name="EMA Principal Periodo", Order=1, GroupName="1. EMA")]
        public int EMAPrincipalPeriod { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Modo Crossover (ON=Cruce / OFF=Bounce)", Order=2, GroupName="1. EMA")]
        public bool UseModoCrossover { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 2.0)]
        [Display(Name="Bounce: Proximidad EMA (x ATR)", Order=3, GroupName="1. EMA")]
        public double BounceProximityATR { get; set; }

        // === 2. VELA DE INTENCION ===
        [NinjaScriptProperty]
        [Range(0.30, 0.90)]
        [Display(Name="Min Body Ratio (cuerpo/rango)", Order=1, GroupName="2. Vela Intencion")]
        public double MinBodyRatio { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 2.0)]
        [Display(Name="Min Rango (x ATR)", Order=2, GroupName="2. Vela Intencion")]
        public double MinRangeATRMulti { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Require Volume Spike", Order=3, GroupName="2. Vela Intencion")]
        public bool RequireVolSpike { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 4.0)]
        [Display(Name="Volume Multiplier (x SMA)", Order=4, GroupName="2. Vela Intencion")]
        public double VolMultiplier { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name="Volume SMA Periodo", Order=5, GroupName="2. Vela Intencion")]
        public int VolSMAPeriod { get; set; }

        // === 3. FILTROS DE APOYO ===
        [NinjaScriptProperty]
        [Display(Name="Usar ADX (filtro tendencia)", Order=1, GroupName="3. Filtros Apoyo")]
        public bool UseADX { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ADX Periodo", Order=2, GroupName="3. Filtros Apoyo")]
        public int ADXPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(10.0, 40.0)]
        [Display(Name="ADX Minimo (>= = tendencia)", Order=3, GroupName="3. Filtros Apoyo")]
        public double ADXMinThreshold { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Usar RSI (evitar extremos)", Order=4, GroupName="3. Filtros Apoyo")]
        public bool UseRSI { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="RSI Periodo", Order=5, GroupName="3. Filtros Apoyo")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(55, 80)]
        [Display(Name="RSI Long Max (no entrar si >)", Order=6, GroupName="3. Filtros Apoyo")]
        public int RSILongMax { get; set; }

        [NinjaScriptProperty]
        [Range(20, 45)]
        [Display(Name="RSI Short Min (no entrar si <)", Order=7, GroupName="3. Filtros Apoyo")]
        public int RSIShortMin { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Usar EMA Lenta (filtro tendencia mayor)", Order=8, GroupName="3. Filtros Apoyo")]
        public bool UseTrendFilter { get; set; }

        [NinjaScriptProperty]
        [Range(20, 300)]
        [Display(Name="EMA Lenta Periodo (50/100/200)", Order=9, GroupName="3. Filtros Apoyo")]
        public int TrendEMAPeriod { get; set; }

        // === 4. RIESGO ===
        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name="Contratos", Order=1, GroupName="4. Riesgo")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(20, 500)]
        [Display(Name="Target Ticks", Order=2, GroupName="4. Riesgo")]
        public int TargetTicks { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 4.0)]
        [Display(Name="Risk/Reward Ratio (1.0 = 1:1)", Order=3, GroupName="4. Riesgo")]
        public double RiskRewardRatio { get; set; }

        [NinjaScriptProperty]
        [Range(1, 10)]
        [Display(Name="Max Trades por Dia", Order=4, GroupName="4. Riesgo")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name="Max Perdida Diaria $ (0=OFF)", Order=5, GroupName="4. Riesgo")]
        public double MaxDailyLoss { get; set; }

        // === 5. BREAKEVEN ===
        [NinjaScriptProperty]
        [Display(Name="Usar Breakeven", Order=1, GroupName="5. Breakeven")]
        public bool UseBreakeven { get; set; }

        [NinjaScriptProperty]
        [Range(0.2, 1.0)]
        [Display(Name="Breakeven en (fraccion de R)", Order=2, GroupName="5. Breakeven")]
        public double BreakevenAtR { get; set; }

        // === 6. HORARIO ===
        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Hora Inicio (HHMMSS)", Order=1, GroupName="6. Horario")]
        public int HoraInicio { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Hora Fin (HHMMSS)", Order=2, GroupName="6. Horario")]
        public int HoraFin { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Corte: No nuevas entradas (HHMMSS)", Order=3, GroupName="6. Horario")]
        public int HoraCorte { get; set; }

        // === 7. DIRECCION ===
        [NinjaScriptProperty]
        [Display(Name="Allow Long", Order=1, GroupName="7. Direccion")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Short", Order=2, GroupName="7. Direccion")]
        public bool AllowShort { get; set; }

        // === 8. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=1, GroupName="8. Debug")]
        public bool DebugMode { get; set; }

        #endregion
    }
}
