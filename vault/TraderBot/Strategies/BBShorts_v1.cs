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
    public class BBShorts_v1 : Strategy
    {
        // ── Indicadores cacheados ──────────────────────────────────────────
        private EMA  emaFast;
        private EMA  emaSlow;
        private EMA  emaHTF;
        private ATR  atrInd;
        private RSI  rsiInd;
        private SMA  volSMA;

        // ── VWAP manual ────────────────────────────────────────────────────
        private double vwapNum   = 0;
        private double vwapDen   = 0;
        private double vwapValue = 0;
        private DateTime vwapDate;

        // ── Control de sesión ──────────────────────────────────────────────
        private DateTime lastSessionDate;
        private bool     maxLossHit    = false;
        private bool     maxTradesHit  = false;
        private int      tradesHoy     = 0;

        // ── Trailing ───────────────────────────────────────────────────────
        private double trailStopPrice  = 0;
        private bool   trailActivated  = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "BB Shorts v1 — Solo shorts, complementa NYOpenBlast (10:30-15:00)";
                Name        = "BBShorts_v1";

                Calculate              = Calculate.OnBarClose;
                EntriesPerDirection    = 1;
                EntryHandling          = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;
                IsFillLimitOnTouch     = false;
                MaximumBarsLookBack    = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution    = OrderFillResolution.Standard;
                Slippage               = 1;   // Realista: 1 tick slippage
                StartBehavior          = StartBehavior.WaitUntilFlat;
                TimeInForce            = TimeInForce.Gtc;
                TraceOrders            = false;
                RealtimeErrorHandling  = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling     = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade    = 20;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. RIESGO ===
                Contratos        = 5;
                MaxPerdidaDiaria = 300;
                MaxTradesPerDay  = 3;
                ATRMultiplierStop = 1.5;
                RiskRewardRatio  = 2.0;   // Mejorado de 1.5 → mayor asimetría

                // === 2. SESIÓN ===
                // Empieza DESPUÉS de NYOpenBlast (9:29-10:30)
                SessionStartTime = 103000;  // 10:30 AM
                SessionEndTime   = 150000;  // 15:00 PM

                // === 3. INDICADORES ===
                EMAFastPeriod  = 21;
                EMASlowPeriod  = 50;
                EMAHTFPeriod   = 100;
                ATRPeriod      = 14;
                RSIPeriod      = 14;
                RSIOversold    = 35;   // Ajustado para shorts
                RSIOverbought  = 65;

                // === 4. VWAP ===
                UsarVWAP = true;   // Solo shortar bajo VWAP

                // === 5. TRAILING ===
                ActivarTrailing        = false;  // OFF por defecto — probar sin él primero
                TrailingActivacion     = 1.2;
                TrailingATRMultiplier  = 0.8;

                // === 6. FILTROS ===
                MinVolumePercent       = 80;
                RequiereTendenciaFuerte = true;
                DebugMode              = false;
            }
            else if (State == State.DataLoaded)
            {
                emaFast = EMA(EMAFastPeriod);
                emaSlow = EMA(EMASlowPeriod);
                emaHTF  = EMA(EMAHTFPeriod);
                atrInd  = ATR(ATRPeriod);
                rsiInd  = RSI(RSIPeriod, 3);
                volSMA  = SMA(Volume, 20);

                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaSlow.Plots[0].Brush = Brushes.Orange;
                emaHTF.Plots[0].Brush  = Brushes.Red;

                AddChartIndicator(emaFast);
                AddChartIndicator(emaSlow);
                AddChartIndicator(emaHTF);

                vwapDate = DateTime.MinValue;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(EMAHTFPeriod, Math.Max(ATRPeriod, RSIPeriod)))
                return;

            // ── Actualizar VWAP ───────────────────────────────────────────
            ActualizarVWAP();

            // ── Reset diario ──────────────────────────────────────────────
            if (lastSessionDate != Time[0].Date)
            {
                lastSessionDate = Time[0].Date;
                maxLossHit      = false;
                maxTradesHit    = false;
                tradesHoy       = 0;

                if (DebugMode)
                    Print(string.Format("=== NUEVA SESIÓN: {0} ===", Time[0].Date.ToShortDateString()));
            }

            // ── Límites diarios ───────────────────────────────────────────
            if (maxLossHit || maxTradesHit)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong();
                    ExitShort();
                }
                return;
            }

            // ── Filtro de horario ─────────────────────────────────────────
            int horaActual = ToTime(Time[0]);
            if (horaActual < SessionStartTime || horaActual > SessionEndTime)
                return;

            // ── Gestión de posición abierta ───────────────────────────────
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                GestionarTrailing();
                return;
            }

            // ── Buscar entradas ───────────────────────────────────────────
            BuscarEntrada();
        }

        private void ActualizarVWAP()
        {
            if (Time[0].Date != vwapDate)
            {
                vwapDate = Time[0].Date;
                vwapNum  = 0;
                vwapDen  = 0;
            }
            double tp = (High[0] + Low[0] + Close[0]) / 3.0;
            vwapNum  += tp * Volume[0];
            vwapDen  += Volume[0];
            vwapValue  = (vwapDen > 0) ? vwapNum / vwapDen : Close[0];
        }

        private void BuscarEntrada()
        {
            // ── Filtro de volumen ─────────────────────────────────────────
            if (Volume[0] < volSMA[0] * MinVolumePercent / 100.0)
                return;

            // ── Filtro VWAP ───────────────────────────────────────────────
            // Para shorts: precio debe estar BAJO el VWAP
            if (UsarVWAP && Close[0] >= vwapValue)
                return;

            // ── Detectar tendencia bajista ────────────────────────────────
            bool trendBearish;
            if (RequiereTendenciaFuerte)
            {
                bool emasAlignedBear   = emaFast[0] < emaSlow[0] && emaSlow[0] < emaHTF[0];
                bool htfFallingStrong  = emaHTF[0] < emaHTF[1] && emaHTF[1] < emaHTF[2];
                trendBearish           = Close[0] < emaHTF[0] && emasAlignedBear && htfFallingStrong;
            }
            else
            {
                trendBearish = emaFast[0] < emaSlow[0];
            }

            if (!trendBearish) return;

            // ── Señal de entrada SHORT ────────────────────────────────────
            // Cruce bajista O pullback a la EMA rápida desde arriba
            bool entrySignal = CrossBelow(emaFast, emaSlow, 1) ||
                               (High[0] >= emaFast[0] && Close[0] < emaFast[0]);

            // RSI: no en zona de sobreventa extrema (posible rebote)
            bool rsiOK = rsiInd[0] > RSIOversold;

            // Confirmación de vela bajista
            bool velaCorta = Close[0] < Open[0];

            if (!entrySignal || !rsiOK || !velaCorta)
                return;

            double stopPrice   = Close[0] + (atrInd[0] * ATRMultiplierStop);
            double riskTicks   = stopPrice - Close[0];
            double targetPrice = Close[0] - (riskTicks * RiskRewardRatio);

            EnterShort(Contratos, "SHORT");
            SetStopLoss("SHORT",    CalculationMode.Price, stopPrice,   false);
            SetProfitTarget("SHORT", CalculationMode.Price, targetPrice);

            tradesHoy++;

            if (DebugMode)
                Print(string.Format("*** SHORT @ {0:F2} | Stop: {1:F2} | Target: {2:F2} | VWAP: {3:F2} | RSI: {4:F1} ***",
                    Close[0], stopPrice, targetPrice, vwapValue, rsiInd[0]));
        }

        private void GestionarTrailing()
        {
            if (!ActivarTrailing || Position.MarketPosition != MarketPosition.Short)
                return;

            double entryPrice   = Position.AveragePrice;
            double currentPrice = Close[0];
            double riskATR      = atrInd[0] * ATRMultiplierStop;
            double ganancia     = entryPrice - currentPrice;  // positivo = ganando

            // Activar trailing cuando ganancia ≥ TrailingActivacion × riesgo ATR
            if (!trailActivated && ganancia >= riskATR * TrailingActivacion)
            {
                trailActivated = true;
                trailStopPrice = currentPrice + (atrInd[0] * TrailingATRMultiplier);
                SetStopLoss("SHORT", CalculationMode.Price, trailStopPrice, false);

                if (DebugMode)
                    Print(string.Format("Trailing ACTIVADO @ {0:F2} | Trail stop: {1:F2}", currentPrice, trailStopPrice));
            }

            // Mover trailing stop hacia abajo (favor al short)
            if (trailActivated)
            {
                double nuevoTrail = currentPrice + (atrInd[0] * TrailingATRMultiplier);
                if (nuevoTrail < trailStopPrice)
                {
                    trailStopPrice = nuevoTrail;
                    SetStopLoss("SHORT", CalculationMode.Price, trailStopPrice, false);
                }
            }
        }

        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            // Reset trailing cuando la posición se cierra (stop o target)
            if (marketPosition == MarketPosition.Flat)
            {
                trailActivated = false;
                trailStopPrice = 0;
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            // Verificar límites solo cuando se cierra una posición
            if (execution.Order == null ||
                execution.Order.OrderState != OrderState.Filled ||
                marketPosition != MarketPosition.Flat)
                return;

            double todayPnL = ObtenerPnLDiario();

            if (todayPnL <= -MaxPerdidaDiaria)
            {
                maxLossHit = true;
                if (DebugMode)
                    Print(string.Format("*** LÍMITE DE PÉRDIDA: ${0:F2} ***", todayPnL));
            }

            if (tradesHoy >= MaxTradesPerDay)
            {
                maxTradesHit = true;
                if (DebugMode)
                    Print(string.Format("*** MÁXIMO DE TRADES: {0} ***", tradesHoy));
            }
        }

        private double ObtenerPnLDiario()
        {
            double pnl  = 0;
            DateTime hoy = Time[0].Date;
            foreach (var trade in SystemPerformance.AllTrades)
            {
                if (trade.Exit.Time.Date == hoy)
                    pnl += trade.ProfitCurrency;
            }
            return pnl;
        }

        #region Properties

        // === 1. RIESGO ===
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Contratos MNQ", Order=1, GroupName="1. Riesgo")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(50, 2000)]
        [Display(Name="Max Pérdida Diaria ($)", Order=2, GroupName="1. Riesgo")]
        public int MaxPerdidaDiaria { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name="Max Trades por Día", Order=3, GroupName="1. Riesgo")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 4.0)]
        [Display(Name="ATR Multiplier Stop", Order=4, GroupName="1. Riesgo")]
        public double ATRMultiplierStop { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name="Risk/Reward Ratio", Order=5, GroupName="1. Riesgo")]
        public double RiskRewardRatio { get; set; }

        // === 2. SESIÓN ===
        [NinjaScriptProperty]
        [Display(Name="Inicio Sesión (HHMMSS)", Order=1, GroupName="2. Sesión")]
        public int SessionStartTime { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Fin Sesión (HHMMSS)", Order=2, GroupName="2. Sesión")]
        public int SessionEndTime { get; set; }

        // === 3. INDICADORES ===
        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name="EMA Rápida", Order=1, GroupName="3. Indicadores")]
        public int EMAFastPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(20, 100)]
        [Display(Name="EMA Lenta", Order=2, GroupName="3. Indicadores")]
        public int EMASlowPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(50, 200)]
        [Display(Name="EMA HTF", Order=3, GroupName="3. Indicadores")]
        public int EMAHTFPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ATR Período", Order=4, GroupName="3. Indicadores")]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="RSI Período", Order=5, GroupName="3. Indicadores")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(20, 45)]
        [Display(Name="RSI Sobreventa", Order=6, GroupName="3. Indicadores")]
        public int RSIOversold { get; set; }

        [NinjaScriptProperty]
        [Range(55, 80)]
        [Display(Name="RSI Sobrecompra", Order=7, GroupName="3. Indicadores")]
        public int RSIOverbought { get; set; }

        // === 4. VWAP ===
        [NinjaScriptProperty]
        [Display(Name="Usar VWAP (solo short bajo VWAP)", Order=1, GroupName="4. VWAP")]
        public bool UsarVWAP { get; set; }

        // === 5. TRAILING ===
        [NinjaScriptProperty]
        [Display(Name="Activar Trailing", Order=1, GroupName="5. Trailing")]
        public bool ActivarTrailing { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 3.0)]
        [Display(Name="Trailing Activación (× ATR riesgo)", Order=2, GroupName="5. Trailing")]
        public double TrailingActivacion { get; set; }

        [NinjaScriptProperty]
        [Range(0.3, 2.0)]
        [Display(Name="Trailing ATR Multiplier", Order=3, GroupName="5. Trailing")]
        public double TrailingATRMultiplier { get; set; }

        // === 6. FILTROS ===
        [NinjaScriptProperty]
        [Range(0, 200)]
        [Display(Name="Min Volume (%)", Order=1, GroupName="6. Filtros")]
        public int MinVolumePercent { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Requiere Tendencia Fuerte", Order=2, GroupName="6. Filtros")]
        public bool RequiereTendenciaFuerte { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=3, GroupName="6. Filtros")]
        public bool DebugMode { get; set; }

        #endregion
    }
}
