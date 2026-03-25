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
    // ============================================================
    // BreadButterBALANCED v2.2
    //
    // CAMBIOS vs v2.1:
    // 1. BUG FIX: braces en OnBarUpdate (ExitShort() siempre ejecutaba)
    // 2. BUG FIX: volumeSMA cacheado en DataLoaded (no recrear cada barra)
    // 3. BUG FIX: entryATR fijo al abrir trade (risk consistente)
    // 4. NUEVO: AllowLong/AllowShort — default AllowShort=false (shorts PF=0.98)
    // 5. NUEVO: Breakeven en 1R (leccion v5_Apex)
    // 6. NUEVO: Trailing usa entryATR fijo (no ATR actual)
    // 7. NUEVO: UsePrimeHoursOnly (9:30-12:30 y 13:30-15:30)
    // 8. NUEVO: Defaults ajustados a params ganadores (ATR=2.5, R:R=4, MaxTrades=1)
    // 9. NUEVO: Ranges ampliados en Properties (ATR hasta 4.0, R:R hasta 6.0)
    // ============================================================
    public class BreadButterBALANCED_v22 : Strategy
    {
        // Indicadores (todos cacheados en DataLoaded)
        private EMA emaFast;
        private EMA emaSlow;
        private EMA emaHTF;
        private ATR atr;
        private RSI rsi;
        private SMA volumeSMA; // CACHEADO — no recrear en cada barra

        // Control de sesion
        private double dailyPnL = 0;
        private int tradesThisSession = 0;
        private DateTime lastSessionDate;
        private bool maxLossHit = false;
        private bool maxTradesHit = false;

        // Gestion del trade activo
        private double entryATR = 0;        // ATR fijo al momento de entrada
        private double dynamicStop = 0;
        private bool breakevenDone = false;
        private bool trailActivated = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Bread & Butter BALANCED v2.2 - Bugs corregidos + lecciones v5_Apex";
                Name = "BreadButterBALANCED_v22";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 1;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 20;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. RIESGO ===
                // Defaults = params ganadores del backtest (ATR=2.5, R:R=4, MaxTrades=1)
                Contratos        = 15;
                MaxPerdidaDiaria = 300;
                MaxTradesPerDay  = 1;     // 1 trade/dia = filtro de calidad
                ATRMultiplierStop = 2.5;  // Stop tecnico amplio
                RiskRewardRatio  = 4.0;  // Dejar correr los ganadores

                // === 2. INDICADORES ===
                EMAFastPeriod  = 21;
                EMASlowPeriod  = 40;
                EMAHTFPeriod   = 80;
                ATRPeriod      = 7;
                RSIPeriod      = 21;
                RSIOversold    = 40;
                RSIOverbought  = 60;

                // === 3. TRAILING ===
                ActivarTrailing       = false; // OFF por defecto (leccion v5_Apex)
                TrailingActivacion    = 1.5;   // Activa en 1.5R (da recorrido)
                TrailingATRMultiplier = 1.0;   // Trail ancho (1 ATR, no 0.5)
                ActivarBreakeven      = true;  // Mover a BE en 1R
                BreakevenR            = 1.0;

                // === 4. FILTROS ===
                MinVolumePercent        = 100;
                RequiereTendenciaFuerte = true;
                UsePrimeHoursOnly       = false; // Solo 9:30-12:30 y 13:30-15:30

                // === 5. DIRECCION ===
                AllowLong  = true;
                AllowShort = false; // Shorts PF=0.98 → OFF por defecto

                // === 6. DEBUG ===
                DebugMode = false;
            }
            else if (State == State.DataLoaded)
            {
                emaFast   = EMA(EMAFastPeriod);
                emaSlow   = EMA(EMASlowPeriod);
                emaHTF    = EMA(EMAHTFPeriod);
                atr       = ATR(ATRPeriod);
                rsi       = RSI(RSIPeriod, 3);
                volumeSMA = SMA(Volume, 20); // CACHEADO aqui, no en CheckForEntries

                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaSlow.Plots[0].Brush = Brushes.Orange;
                emaHTF.Plots[0].Brush  = Brushes.Red;

                AddChartIndicator(emaFast);
                AddChartIndicator(emaSlow);
                AddChartIndicator(emaHTF);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(EMAHTFPeriod, Math.Max(ATRPeriod, RSIPeriod)))
                return;

            // === RESET DIARIO ===
            if (lastSessionDate != Time[0].Date)
            {
                lastSessionDate   = Time[0].Date;
                dailyPnL          = 0;
                tradesThisSession = 0;
                maxLossHit        = false;
                maxTradesHit      = false;

                if (DebugMode)
                    Print(string.Format("=== NUEVA SESION: {0} ===", Time[0].Date.ToShortDateString()));
            }

            // === VERIFICAR LIMITES DIARIOS ===
            // BUG FIX: braces correctas — en v2.1 ExitShort() siempre ejecutaba
            if (maxLossHit || maxTradesHit)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong();
                    ExitShort();
                }
                return;
            }

            // === FILTRO HORAS PRIME (opcional) ===
            if (UsePrimeHoursOnly)
            {
                int t = ToTime(Time[0]);
                bool primeAM = (t >= 093000 && t <= 123000);
                bool primePM = (t >= 133000 && t <= 153000);
                if (!primeAM && !primePM)
                    return;
            }

            // === GESTION DE POSICION ABIERTA ===
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageTrailingStop();
                return;
            }

            // === SENALES DE ENTRADA ===
            CheckForEntries();
        }

        private void CheckForEntries()
        {
            // === FILTRO DE VOLUMEN (usa volumeSMA cacheado) ===
            bool volumeOK = Volume[0] >= (volumeSMA[0] * MinVolumePercent / 100.0);
            if (!volumeOK)
                return;

            // === DETECTAR TENDENCIA ===
            bool trendBullish = false;
            bool trendBearish = false;

            if (RequiereTendenciaFuerte)
            {
                // EMAs alineadas + HTF subiendo 3 barras consecutivas
                bool emasAlignedBull  = emaFast[0] > emaSlow[0] && emaSlow[0] > emaHTF[0];
                bool htfRisingStrong  = emaHTF[0] > emaHTF[1] && emaHTF[1] > emaHTF[2];
                trendBullish = Close[0] > emaHTF[0] && emasAlignedBull && htfRisingStrong;

                bool emasAlignedBear  = emaFast[0] < emaSlow[0] && emaSlow[0] < emaHTF[0];
                bool htfFallingStrong = emaHTF[0] < emaHTF[1] && emaHTF[1] < emaHTF[2];
                trendBearish = Close[0] < emaHTF[0] && emasAlignedBear && htfFallingStrong;
            }
            else
            {
                trendBullish = emaFast[0] > emaSlow[0];
                trendBearish = emaFast[0] < emaSlow[0];
            }

            if (DebugMode && CurrentBar % 100 == 0)
                Print(string.Format("{0} | Bull:{1} Bear:{2} | RSI:{3:F0} | Vol:{4:F0}/{5:F0} | ATR:{6:F1}",
                    Time[0], trendBullish, trendBearish, rsi[0], Volume[0], volumeSMA[0], atr[0]));

            // === SENAL LONG ===
            if (AllowLong && trendBullish)
            {
                bool entrySignal = CrossAbove(emaFast, emaSlow, 1) ||
                                   (Low[0] <= emaFast[0] && Close[0] > emaFast[0]);
                bool rsiOK       = rsi[0] < RSIOverbought;
                bool bullishBar  = Close[0] > Open[0];

                if (entrySignal && rsiOK && bullishBar)
                {
                    double risk   = atr[0] * ATRMultiplierStop;
                    double stop   = Close[0] - risk;
                    double target = Close[0] + (risk * RiskRewardRatio);

                    EnterLong(Contratos, "LONG");
                    SetStopLoss("LONG",    CalculationMode.Price, stop,   false);
                    SetProfitTarget("LONG", CalculationMode.Price, target);

                    entryATR      = atr[0]; // FIJO al momento de entrada
                    dynamicStop   = stop;
                    breakevenDone = false;
                    trailActivated = false;
                    tradesThisSession++;

                    if (DebugMode)
                        Print(string.Format("*** LONG @ {0:F2} | Stop:{1:F2} | Target:{2:F2} | ATR:{3:F1} | RSI:{4:F0} ***",
                            Close[0], stop, target, atr[0], rsi[0]));
                }
            }

            // === SENAL SHORT ===
            else if (AllowShort && trendBearish)
            {
                bool entrySignal = CrossBelow(emaFast, emaSlow, 1) ||
                                   (High[0] >= emaFast[0] && Close[0] < emaFast[0]);
                bool rsiOK      = rsi[0] > RSIOversold;
                bool bearishBar = Close[0] < Open[0];

                if (entrySignal && rsiOK && bearishBar)
                {
                    double risk   = atr[0] * ATRMultiplierStop;
                    double stop   = Close[0] + risk;
                    double target = Close[0] - (risk * RiskRewardRatio);

                    EnterShort(Contratos, "SHORT");
                    SetStopLoss("SHORT",    CalculationMode.Price, stop,   false);
                    SetProfitTarget("SHORT", CalculationMode.Price, target);

                    entryATR      = atr[0];
                    dynamicStop   = stop;
                    breakevenDone = false;
                    trailActivated = false;
                    tradesThisSession++;

                    if (DebugMode)
                        Print(string.Format("*** SHORT @ {0:F2} | Stop:{1:F2} | Target:{2:F2} | ATR:{3:F1} | RSI:{4:F0} ***",
                            Close[0], stop, target, atr[0], rsi[0]));
                }
            }
        }

        private void ManageTrailingStop()
        {
            double entryPrice = Position.AveragePrice;
            double currentPrice = Close[0];
            // USAR entryATR fijo — no recalcular con ATR actual
            double riskAmount = entryATR * ATRMultiplierStop;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double profit = currentPrice - entryPrice;

                // PASO 1: Mover a breakeven cuando alcanzamos BreakevenR
                if (ActivarBreakeven && !breakevenDone && profit >= riskAmount * BreakevenR)
                {
                    breakevenDone = true;
                    dynamicStop   = entryPrice + TickSize;
                    SetStopLoss("LONG", CalculationMode.Price, dynamicStop, false);

                    if (DebugMode)
                        Print(string.Format("BE activado Long @ {0:F2}", dynamicStop));
                }

                // PASO 2: Trailing cuando activamos
                if (ActivarTrailing && profit >= riskAmount * TrailingActivacion)
                {
                    trailActivated = true;
                    // Trail usa entryATR (fijo), no atr[0] actual
                    double newStop = currentPrice - (entryATR * TrailingATRMultiplier);
                    if (newStop > dynamicStop)
                    {
                        dynamicStop = newStop;
                        SetStopLoss("LONG", CalculationMode.Price, dynamicStop, false);
                    }
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double profit = entryPrice - currentPrice;

                // PASO 1: Breakeven
                if (ActivarBreakeven && !breakevenDone && profit >= riskAmount * BreakevenR)
                {
                    breakevenDone = true;
                    dynamicStop   = entryPrice - TickSize;
                    SetStopLoss("SHORT", CalculationMode.Price, dynamicStop, false);

                    if (DebugMode)
                        Print(string.Format("BE activado Short @ {0:F2}", dynamicStop));
                }

                // PASO 2: Trailing
                if (ActivarTrailing && profit >= riskAmount * TrailingActivacion)
                {
                    trailActivated = true;
                    double newStop = currentPrice + (entryATR * TrailingATRMultiplier);
                    if (newStop < dynamicStop)
                    {
                        dynamicStop = newStop;
                        SetStopLoss("SHORT", CalculationMode.Price, dynamicStop, false);
                    }
                }
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            // Reset estado del trade al entrar
            if (execution.Order.Name == "LONG" || execution.Order.Name == "SHORT")
            {
                trailActivated = false;
                breakevenDone  = false;
                dynamicStop    = 0;
            }

            // P&L diario (logica original — filtro natural de 1 trade/dia)
            double execPnL = execution.Commission + execution.Order.AverageFillPrice * execution.Quantity;
            dailyPnL += (marketPosition == MarketPosition.Flat) ? execPnL : -execPnL;

            if (dailyPnL <= -MaxPerdidaDiaria)
            {
                maxLossHit = true;
                if (DebugMode)
                    Print(string.Format("*** LIMITE PERDIDA: ${0:F2} ***", dailyPnL));
            }

            if (tradesThisSession >= MaxTradesPerDay)
            {
                maxTradesHit = true;
                if (DebugMode)
                    Print(string.Format("*** MAX TRADES: {0} ***", tradesThisSession));
            }

            if (DebugMode && marketPosition == MarketPosition.Flat)
                Print(string.Format("Exit | Trades hoy: {0}/{1} | P&L sesion: ${2:F2}",
                    tradesThisSession, MaxTradesPerDay, dailyPnL));
        }

        #region Properties

        // === 1. RIESGO ===
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Contratos MNQ", Order=1, GroupName="1. Riesgo")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(50, 2000)]
        [Display(Name="Max Perdida Diaria ($)", Order=2, GroupName="1. Riesgo")]
        public int MaxPerdidaDiaria { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name="Max Trades por Dia", Order=3, GroupName="1. Riesgo")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 4.0)]   // AMPLIADO — antes [0.5, 3.0] no permitia ATR=2.5+
        [Display(Name="ATR Multiplier Stop", Order=4, GroupName="1. Riesgo")]
        public double ATRMultiplierStop { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 6.0)]   // AMPLIADO — antes [1.0, 5.0], permite R:R=4+
        [Display(Name="Risk/Reward Ratio", Order=5, GroupName="1. Riesgo")]
        public double RiskRewardRatio { get; set; }

        // === 2. INDICADORES ===
        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name="EMA Rapida", Order=1, GroupName="2. Indicadores")]
        public int EMAFastPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(20, 100)]
        [Display(Name="EMA Lenta", Order=2, GroupName="2. Indicadores")]
        public int EMASlowPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(50, 200)]
        [Display(Name="EMA HTF", Order=3, GroupName="2. Indicadores")]
        public int EMAHTFPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ATR Periodo", Order=4, GroupName="2. Indicadores")]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="RSI Periodo", Order=5, GroupName="2. Indicadores")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(20, 45)]
        [Display(Name="RSI Sobreventa", Order=6, GroupName="2. Indicadores")]
        public int RSIOversold { get; set; }

        [NinjaScriptProperty]
        [Range(55, 80)]
        [Display(Name="RSI Sobrecompra", Order=7, GroupName="2. Indicadores")]
        public int RSIOverbought { get; set; }

        // === 3. TRAILING ===
        [NinjaScriptProperty]
        [Display(Name="Activar Trailing", Order=1, GroupName="3. Trailing")]
        public bool ActivarTrailing { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name="Trailing Activacion (R)", Order=2, GroupName="3. Trailing")]
        public double TrailingActivacion { get; set; }

        [NinjaScriptProperty]
        [Range(0.3, 3.0)]   // AMPLIADO — permite trail de 1.0 ATR (leccion v5_Apex)
        [Display(Name="Trailing ATR Multiplier", Order=3, GroupName="3. Trailing")]
        public double TrailingATRMultiplier { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Activar Breakeven", Order=4, GroupName="3. Trailing")]
        public bool ActivarBreakeven { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 2.0)]
        [Display(Name="Breakeven en (R)", Order=5, GroupName="3. Trailing")]
        public double BreakevenR { get; set; }

        // === 4. FILTROS ===
        [NinjaScriptProperty]
        [Range(0, 200)]
        [Display(Name="Min Volume (%)", Order=1, GroupName="4. Filtros")]
        public int MinVolumePercent { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Requiere Tendencia Fuerte", Order=2, GroupName="4. Filtros")]
        public bool RequiereTendenciaFuerte { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Solo Horas Prime (9:30-12:30 y 13:30-15:30)", Order=3, GroupName="4. Filtros")]
        public bool UsePrimeHoursOnly { get; set; }

        // === 5. DIRECCION ===
        [NinjaScriptProperty]
        [Display(Name="Allow Long", Order=1, GroupName="5. Direccion")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Short", Order=2, GroupName="5. Direccion")]
        public bool AllowShort { get; set; }

        // === 6. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=1, GroupName="6. Debug")]
        public bool DebugMode { get; set; }

        #endregion
    }
}
