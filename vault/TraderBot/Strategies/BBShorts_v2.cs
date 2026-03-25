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

// ─────────────────────────────────────────────────────────────────────────────
//  BBShorts_v2  —  Mean Reversion Shorts para MNQ
//
//  Concepto: en un mercado alcista el RUBBER BAND funciona mejor que seguir
//  tendencia bajista. Shortamos cuando el precio está SOBREEXTENDIDO al alza
//  (RSI > umbral + precio sobre VWAP + vela de rechazo) y esperamos que regrese
//  a equilibrio (VWAP o target ATR).
//
//  Diferencias clave vs v1:
//  - Sin trailing stop (destruía ganancias: Avg MFE $820, ETD $801)
//  - Entrada: RSI overbought + rechazo (vela hace nuevo high y cierra bajista)
//  - Salida: stop encima del high de la vela de rechazo + target fijo o VWAP
//  - Salida por tiempo: MaxBarsHeld para evitar trades que se van a ningún lado
//  - Sin EMA trend filter — en mean reversion el "trend" está en contra, es correcto
// ─────────────────────────────────────────────────────────────────────────────

namespace NinjaTrader.NinjaScript.Strategies
{
    public class BBShorts_v2 : Strategy
    {
        // ── Indicadores cacheados ──────────────────────────────────────────
        private EMA  emaFast;
        private EMA  emaSlow;
        private ATR  atrInd;
        private RSI  rsiInd;
        private SMA  volSMA;
        private Bollinger boll;

        // ── VWAP manual ────────────────────────────────────────────────────
        private double vwapNum;
        private double vwapDen;
        private double vwapValue;
        private DateTime vwapDate;

        // ── Control de sesión ──────────────────────────────────────────────
        private DateTime lastSessionDate;
        private bool     maxLossHit;
        private bool     maxTradesHit;
        private int      tradesHoy;

        // ── Tracking de entrada ────────────────────────────────────────────
        private int entryBar = -1;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "BB Shorts v2 — Mean Reversion: short RSI overbought + rechazo. Sin trailing.";
                Name        = "BBShorts_v2";

                Calculate              = Calculate.OnBarClose;
                EntriesPerDirection    = 1;
                EntryHandling          = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;
                IsFillLimitOnTouch     = false;
                MaximumBarsLookBack    = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution    = OrderFillResolution.Standard;
                Slippage               = 1;
                StartBehavior          = StartBehavior.WaitUntilFlat;
                TimeInForce            = TimeInForce.Gtc;
                TraceOrders            = false;
                RealtimeErrorHandling  = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling     = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade    = 25;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. RIESGO ===
                Contratos        = 5;
                MaxPerdidaDiaria = 300;
                MaxTradesPerDay  = 3;
                ATRMultiplierStop = 1.0;  // Stop ajustado: encima del high de rechazo + 1×ATR
                RiskRewardRatio  = 1.5;   // MR tiene WR alta, no necesita R:R extremo

                // === 2. SESIÓN ===
                // 10:00-14:30: evita caos del open Y volatilidad del close
                // Ajusta SessionStartTime=93000 para probar también el open
                SessionStartTime = 100000;  // 10:00 AM
                SessionEndTime   = 143000;  // 14:30 PM

                // === 3. INDICADORES ===
                EMAFastPeriod    = 21;
                EMASlowPeriod    = 50;
                ATRPeriod        = 14;
                RSIPeriod        = 7;     // RSI rápido: detecta overbought en tiempo real
                RSIEntradaShort  = 70;    // Umbral: RSI > 70 para considerar short
                BollingerPeriod  = 20;
                BollingerDesvio  = 2.0;   // Opcional: precio sobre banda superior BB

                // === 4. VWAP ===
                UsarVWAP        = true;   // Solo short cuando precio > VWAP (estirado)
                TargetVWAP      = true;   // Target primario = VWAP (más conservador)

                // === 5. SALIDA POR TIEMPO ===
                MaxBarsHeld     = 15;     // En 2-min = 30 minutos. En 1-min = 15 minutos

                // === 6. FILTROS ===
                MinVolumePercent = 100;   // Volumen normal — filtra barras de baja actividad
                UsarBollinger   = false;  // Activar para añadir filtro banda superior BB
                DebugMode       = false;
            }
            else if (State == State.DataLoaded)
            {
                emaFast = EMA(EMAFastPeriod);
                emaSlow = EMA(EMASlowPeriod);
                atrInd  = ATR(ATRPeriod);
                rsiInd  = RSI(RSIPeriod, 3);
                volSMA  = SMA(Volume, 20);
                boll    = Bollinger(BollingerDesvio, BollingerPeriod);

                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaSlow.Plots[0].Brush = Brushes.Orange;

                AddChartIndicator(emaFast);
                AddChartIndicator(emaSlow);

                vwapDate  = DateTime.MinValue;
                entryBar  = -1;
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(EMASlowPeriod, Math.Max(BollingerPeriod, RSIPeriod)) + 2)
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
                    Print("=== NUEVA SESIÓN: " + Time[0].Date.ToShortDateString() + " ===");
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
                // Salida por tiempo — evita marathones perdedores
                if (entryBar >= 0 && (CurrentBar - entryBar) >= MaxBarsHeld)
                {
                    ExitShort("SalidaTiempo", "SHORT");
                    if (DebugMode)
                        Print(string.Format("SALIDA TIEMPO @ {0:F2} | Bars: {1}",
                            Close[0], CurrentBar - entryBar));
                }
                return;
            }

            // ── Buscar entrada ────────────────────────────────────────────
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
            // ── 1. Filtro de volumen ──────────────────────────────────────
            if (Volume[0] < volSMA[0] * MinVolumePercent / 100.0)
                return;

            // ── 2. RSI sobrecomprado — el mercado está estirado al alza ──
            bool rsiSobrado  = rsiInd[0] > RSIEntradaShort;
            if (!rsiSobrado) return;

            // ── 3. RSI girando — el momentum empieza a fallar ─────────────
            // RSI cayó respecto a la barra anterior (pico confirmado)
            bool rsiGirando = rsiInd[0] < rsiInd[1];
            if (!rsiGirando) return;

            // ── 4. Precio sobre VWAP — estirado respecto a valor justo ───
            if (UsarVWAP && Close[0] <= vwapValue)
                return;

            // ── 5. Vela de rechazo (patrón clave) ─────────────────────────
            // La barra hizo un NUEVO MÁXIMO (intentó subir más)
            // pero CERRÓ BAJISTA (el intento falló — rechazo real)
            bool nuevoMaximo    = High[0] > High[1];
            bool cierreBajista  = Close[0] < Open[0];

            // La mecha superior es significativa (el precio subió pero lo rechazaron)
            double mechaSuperior = High[0] - Math.Max(Open[0], Close[0]);
            bool mechaSignif    = mechaSuperior >= (atrInd[0] * 0.2);  // al menos 20% del ATR

            if (!nuevoMaximo || !cierreBajista || !mechaSignif)
                return;

            // ── 6. Filtro Bollinger (opcional) ───────────────────────────
            // Precio sobre banda superior = más estirado aún
            if (UsarBollinger && Close[0] < boll.Upper[0])
                return;

            // ── 7. Calcular stop y target ─────────────────────────────────
            // Stop: encima del máximo de la vela de rechazo + ATR buffer
            double stopPrice = High[0] + (atrInd[0] * ATRMultiplierStop);
            double riskTicks = stopPrice - Close[0];

            // Target: ATR-based mínimo
            double targetATR  = Close[0] - (riskTicks * RiskRewardRatio);

            // Target VWAP: si VWAP está entre precio y target ATR, usar VWAP como primer target
            double targetFinal = targetATR;
            if (TargetVWAP && UsarVWAP && vwapValue < Close[0] && vwapValue > targetATR)
                targetFinal = vwapValue;

            // ── 8. Entrar ─────────────────────────────────────────────────
            EnterShort(Contratos, "SHORT");
            SetStopLoss("SHORT",     CalculationMode.Price, stopPrice,    false);
            SetProfitTarget("SHORT", CalculationMode.Price, targetFinal);

            entryBar = CurrentBar;
            tradesHoy++;

            if (DebugMode)
                Print(string.Format(
                    "*** SHORT @ {0:F2} | Stop: {1:F2} | Target: {2:F2} | RSI: {3:F1} | VWAP: {4:F2} | MechaSup: {5:F2} ***",
                    Close[0], stopPrice, targetFinal, rsiInd[0], vwapValue, mechaSuperior));
        }

        protected override void OnPositionUpdate(Position position, double averagePrice,
            int quantity, MarketPosition marketPosition)
        {
            if (marketPosition == MarketPosition.Flat)
                entryBar = -1;
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition,
            string orderId, DateTime time)
        {
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
                    Print(string.Format("*** MAX TRADES: {0} ***", tradesHoy));
            }
        }

        private double ObtenerPnLDiario()
        {
            double pnl  = 0;
            DateTime hoy = Time[0].Date;
            foreach (var trade in SystemPerformance.AllTrades)
                if (trade.Exit.Time.Date == hoy)
                    pnl += trade.ProfitCurrency;
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
        [Range(0.3, 3.0)]
        [Display(Name="ATR Multiplier Stop", Order=4, GroupName="1. Riesgo")]
        public double ATRMultiplierStop { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 5.0)]
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
        [Range(5, 30)]
        [Display(Name="ATR Período", Order=3, GroupName="3. Indicadores")]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(3, 20)]
        [Display(Name="RSI Período", Order=4, GroupName="3. Indicadores")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(60, 90)]
        [Display(Name="RSI Umbral Short (sobrecompra)", Order=5, GroupName="3. Indicadores")]
        public int RSIEntradaShort { get; set; }

        [NinjaScriptProperty]
        [Range(10, 30)]
        [Display(Name="Bollinger Período", Order=6, GroupName="3. Indicadores")]
        public int BollingerPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name="Bollinger Desviaciones", Order=7, GroupName="3. Indicadores")]
        public double BollingerDesvio { get; set; }

        // === 4. VWAP ===
        [NinjaScriptProperty]
        [Display(Name="Usar VWAP (precio > VWAP para short)", Order=1, GroupName="4. VWAP")]
        public bool UsarVWAP { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Target = VWAP (si está antes del ATR target)", Order=2, GroupName="4. VWAP")]
        public bool TargetVWAP { get; set; }

        // === 5. SALIDA POR TIEMPO ===
        [NinjaScriptProperty]
        [Range(5, 100)]
        [Display(Name="Max Barras en Trade", Order=1, GroupName="5. Salida Tiempo")]
        public int MaxBarsHeld { get; set; }

        // === 6. FILTROS ===
        [NinjaScriptProperty]
        [Range(0, 200)]
        [Display(Name="Min Volume (%)", Order=1, GroupName="6. Filtros")]
        public int MinVolumePercent { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Usar Bollinger (precio > banda sup)", Order=2, GroupName="6. Filtros")]
        public bool UsarBollinger { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=3, GroupName="6. Filtros")]
        public bool DebugMode { get; set; }

        #endregion
    }
}
