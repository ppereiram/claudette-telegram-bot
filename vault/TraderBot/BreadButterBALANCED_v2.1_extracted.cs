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
    public class BreadButterBALANCED_v21 : Strategy
    {
        // Indicadores
        private EMA emaFast;
        private EMA emaSlow;
        private EMA emaHTF;
        private ATR atr;
        private RSI rsi;
        
        // Control de sesiÃ³n
        private double dailyPnL = 0;
        private int tradesThisSession = 0;
        private DateTime lastSessionDate;
        private bool maxLossHit = false;
        private bool maxTradesHit = false;
        
        // Trailing stop
        private double trailStopPrice = 0;
        private bool trailActivated = false;
        
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Bread & Butter BALANCED v2.1 - Filtros optimizados para mejor win rate";
                Name = "BreadButterBALANCED_v21";
                Calculate = Calculate.OnBarClose;
                EntriesPerDirection = 1;
                EntryHandling = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds = 30;
                IsFillLimitOnTouch = false;
                MaximumBarsLookBack = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution = OrderFillResolution.Standard;
                Slippage = 0;
                StartBehavior = StartBehavior.WaitUntilFlat;
                TimeInForce = TimeInForce.Gtc;
                TraceOrders = false;
                RealtimeErrorHandling = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade = 20;
                IsInstantiatedOnEachOptimizationIteration = true;
                
                // === GESTIÃN DE RIESGO ===
                Contratos = 15;
                MaxPerdidaDiaria = 300;
                MaxTradesPerDay = 5;
                ATRMultiplierStop = 1.5;
                RiskRewardRatio = 1.5;  // Cambiado de 2.0 a 1.5 para mejor win rate
                
                // === INDICADORES ===
                EMAFastPeriod = 21;
                EMASlowPeriod = 50;
                EMAHTFPeriod = 100;
                ATRPeriod = 14;
                RSIPeriod = 14;
                RSIOversold = 40;  // MÃ¡s estricto
                RSIOverbought = 60; // MÃ¡s estricto
                
                // === TRAILING STOP ===
                ActivarTrailing = true;
                TrailingActivacion = 1.2; // MÃ¡s rÃ¡pido
                TrailingATRMultiplier = 0.8; // MÃ¡s ajustado
                
                // === FILTROS ===
                MinVolumePercent = 100; // MÃ¡s estricto
                RequiereTendenciaFuerte = true; // Muy importante
                
                // === DEBUG ===
                DebugMode = true;
            }
            else if (State == State.Configure)
            {
            }
            else if (State == State.DataLoaded)
            {
                emaFast = EMA(EMAFastPeriod);
                emaSlow = EMA(EMASlowPeriod);
                emaHTF = EMA(EMAHTFPeriod);
                atr = ATR(ATRPeriod);
                rsi = RSI(RSIPeriod, 3);
                
                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaSlow.Plots[0].Brush = Brushes.Orange;
                emaHTF.Plots[0].Brush = Brushes.Red;
                
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
                lastSessionDate = Time[0].Date;
                dailyPnL = 0;
                tradesThisSession = 0;
                maxLossHit = false;
                maxTradesHit = false;
                
                if (DebugMode)
                    Print(string.Format("=== NUEVA SESIÃN: {0} ===", Time[0].Date.ToShortDateString()));
            }
            
            // === VERIFICAR LÃMITES DIARIOS ===
            if (maxLossHit || maxTradesHit)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                    ExitLong();
                    ExitShort();
                return;
            }
            
            // === GESTIÃN DE POSICIÃN ABIERTA ===
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageTrailingStop();
                return;
            }
            
            // === SEÃALES DE ENTRADA ===
            CheckForEntries();
        }
        
        private void CheckForEntries()
        {
            // === FILTRO DE VOLUMEN ===
            double avgVolume = SMA(Volume, 20)[0];
            bool volumeOK = Volume[0] >= (avgVolume * MinVolumePercent / 100.0);
            
            if (!volumeOK)
                return;
            
            // === DETECTAR TENDENCIA ===
            bool trendBullish = false;
            bool trendBearish = false;
            
            if (RequiereTendenciaFuerte)
            {
                // Tendencia alcista FUERTE: EMAs alineadas + HTF subiendo consistentemente
                bool emasAlignedBull = emaFast[0] > emaSlow[0] && emaSlow[0] > emaHTF[0];
                bool htfRisingStrong = emaHTF[0] > emaHTF[1] && emaHTF[1] > emaHTF[2];
                
                trendBullish = Close[0] > emaHTF[0] && emasAlignedBull && htfRisingStrong;
                
                // Tendencia bajista FUERTE: EMAs alineadas + HTF bajando consistentemente
                bool emasAlignedBear = emaFast[0] < emaSlow[0] && emaSlow[0] < emaHTF[0];
                bool htfFallingStrong = emaHTF[0] < emaHTF[1] && emaHTF[1] < emaHTF[2];
                
                trendBearish = Close[0] < emaHTF[0] && emasAlignedBear && htfFallingStrong;
            }
            else
            {
                // Sin filtro de tendencia fuerte, solo cruces
                trendBullish = emaFast[0] > emaSlow[0];
                trendBearish = emaFast[0] < emaSlow[0];
            }
            
            // Debug
            if (DebugMode && CurrentBar % 100 == 0)
            {
                Print(string.Format("{0} | Bull:{1} Bear:{2} | RSI:{3:F1} | Vol:{4:F0}/{5:F0}", 
                    Time[0], trendBullish, trendBearish, rsi[0], Volume[0], avgVolume));
            }
            
            // === SEÃAL LONG ===
            if (trendBullish)
            {
                // Cruce alcista O pullback a EMA
                bool entrySignal = CrossAbove(emaFast, emaSlow, 1) || 
                                  (Low[0] <= emaFast[0] && Close[0] > emaFast[0]);
                
                // RSI no sobrecomprado
                bool rsiOK = rsi[0] < RSIOverbought;
                
                // Vela alcista bÃ¡sica
                bool bullishBar = Close[0] > Open[0];
                
                if (entrySignal && rsiOK && bullishBar)
                {
                    double stopPrice = Close[0] - (atr[0] * ATRMultiplierStop);
                    double riskPerContract = Close[0] - stopPrice;
                    double targetPrice = Close[0] + (riskPerContract * RiskRewardRatio);
                    
                    EnterLong(Contratos, "LONG");
                    SetStopLoss("LONG", CalculationMode.Price, stopPrice, false);
                    SetProfitTarget("LONG", CalculationMode.Price, targetPrice);
                    
                    tradesThisSession++;
                    
                    if (DebugMode)
                        Print(string.Format("*** LONG @ {0:F2} | Stop: {1:F2} | Target: {2:F2} ***", 
                            Close[0], stopPrice, targetPrice));
                }
            }
            
            // === SEÃAL SHORT ===
            else if (trendBearish)
            {
                // Cruce bajista O pullback a EMA
                bool entrySignal = CrossBelow(emaFast, emaSlow, 1) || 
                                  (High[0] >= emaFast[0] && Close[0] < emaFast[0]);
                
                // RSI no sobrevendido
                bool rsiOK = rsi[0] > RSIOversold;
                
                // Vela bajista bÃ¡sica
                bool bearishBar = Close[0] < Open[0];
                
                if (entrySignal && rsiOK && bearishBar)
                {
                    double stopPrice = Close[0] + (atr[0] * ATRMultiplierStop);
                    double riskPerContract = stopPrice - Close[0];
                    double targetPrice = Close[0] - (riskPerContract * RiskRewardRatio);
                    
                    EnterShort(Contratos, "SHORT");
                    SetStopLoss("SHORT", CalculationMode.Price, stopPrice, false);
                    SetProfitTarget("SHORT", CalculationMode.Price, targetPrice);
                    
                    tradesThisSession++;
                    
                    if (DebugMode)
                        Print(string.Format("*** SHORT @ {0:F2} | Stop: {1:F2} | Target: {2:F2} ***", 
                            Close[0], stopPrice, targetPrice));
                }
            }
        }
        
        private void ManageTrailingStop()
        {
            if (!ActivarTrailing)
                return;
            
            double entryPrice = Position.AveragePrice;
            double currentPrice = Close[0];
            double riskPerContract = atr[0] * ATRMultiplierStop;
            
            if (Position.MarketPosition == MarketPosition.Long)
            {
                double unrealizedPnL = (currentPrice - entryPrice) * Position.Quantity;
                double targetProfit = riskPerContract * RiskRewardRatio * Position.Quantity;
                
                // Activar trailing cuando alcanza X veces el riesgo
                if (!trailActivated && unrealizedPnL >= (targetProfit * TrailingActivacion / RiskRewardRatio))
                {
                    trailActivated = true;
                    trailStopPrice = currentPrice - (atr[0] * TrailingATRMultiplier);
                    
                    if (DebugMode)
                        Print(string.Format("Trailing ACTIVADO @ {0:F2} | Trail: {1:F2}", currentPrice, trailStopPrice));
                }
                
                // Actualizar trailing stop
                if (trailActivated)
                {
                    double newTrailStop = currentPrice - (atr[0] * TrailingATRMultiplier);
                    if (newTrailStop > trailStopPrice)
                    {
                        trailStopPrice = newTrailStop;
                        SetStopLoss("LONG", CalculationMode.Price, trailStopPrice, false);
                    }
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double unrealizedPnL = (entryPrice - currentPrice) * Position.Quantity;
                double targetProfit = riskPerContract * RiskRewardRatio * Position.Quantity;
                
                if (!trailActivated && unrealizedPnL >= (targetProfit * TrailingActivacion / RiskRewardRatio))
                {
                    trailActivated = true;
                    trailStopPrice = currentPrice + (atr[0] * TrailingATRMultiplier);
                    
                    if (DebugMode)
                        Print(string.Format("Trailing ACTIVADO @ {0:F2} | Trail: {1:F2}", currentPrice, trailStopPrice));
                }
                
                if (trailActivated)
                {
                    double newTrailStop = currentPrice + (atr[0] * TrailingATRMultiplier);
                    if (newTrailStop < trailStopPrice)
                    {
                        trailStopPrice = newTrailStop;
                        SetStopLoss("SHORT", CalculationMode.Price, trailStopPrice, false);
                    }
                }
            }
        }
        
        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity, 
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order != null && execution.Order.OrderState == OrderState.Filled)
            {
                if (execution.Order.Name == "LONG" || execution.Order.Name == "SHORT")
                {
                    trailActivated = false;
                    trailStopPrice = 0;
                }
                
                // Actualizar P&L diario
                double execPnL = execution.Commission + execution.Order.AverageFillPrice * execution.Quantity;
                dailyPnL += (marketPosition == MarketPosition.Flat) ? execPnL : -execPnL;
                
                // Verificar lÃ­mite de pÃ©rdida
                if (dailyPnL <= -MaxPerdidaDiaria)
                {
                    maxLossHit = true;
                    if (DebugMode)
                        Print(string.Format("*** LÃMITE DE PÃRDIDA ALCANZADO: ${0:F2} ***", dailyPnL));
                }
                
                // Verificar lÃ­mite de trades
                if (tradesThisSession >= MaxTradesPerDay)
                {
                    maxTradesHit = true;
                    if (DebugMode)
                        Print(string.Format("*** MÃXIMO DE TRADES ALCANZADO: {0} ***", tradesThisSession));
                }
            }
        }
        
        #region Properties
        
        // === GESTIÃN DE RIESGO ===
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Contratos MNQ", Order=1, GroupName="1. Riesgo")]
        public int Contratos
        { get; set; }

        [NinjaScriptProperty]
        [Range(50, 1000)]
        [Display(Name="Max PÃ©rdida Diaria ($)", Order=2, GroupName="1. Riesgo")]
        public int MaxPerdidaDiaria
        { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name="Max Trades por DÃ­a", Order=3, GroupName="1. Riesgo")]
        public int MaxTradesPerDay
        { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 3.0)]
        [Display(Name="ATR Multiplier Stop", Order=4, GroupName="1. Riesgo")]
        public double ATRMultiplierStop
        { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name="Risk/Reward Ratio", Order=5, GroupName="1. Riesgo")]
        public double RiskRewardRatio
        { get; set; }
        
        // === INDICADORES ===
        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name="EMA RÃ¡pida", Order=1, GroupName="2. Indicadores")]
        public int EMAFastPeriod
        { get; set; }

        [NinjaScriptProperty]
        [Range(20, 100)]
        [Display(Name="EMA Lenta", Order=2, GroupName="2. Indicadores")]
        public int EMASlowPeriod
        { get; set; }

        [NinjaScriptProperty]
        [Range(50, 200)]
        [Display(Name="EMA HTF", Order=3, GroupName="2. Indicadores")]
        public int EMAHTFPeriod
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ATR PerÃ­odo", Order=4, GroupName="2. Indicadores")]
        public int ATRPeriod
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="RSI PerÃ­odo", Order=5, GroupName="2. Indicadores")]
        public int RSIPeriod
        { get; set; }

        [NinjaScriptProperty]
        [Range(20, 45)]
        [Display(Name="RSI Sobreventa", Order=6, GroupName="2. Indicadores")]
        public int RSIOversold
        { get; set; }

        [NinjaScriptProperty]
        [Range(55, 80)]
        [Display(Name="RSI Sobrecompra", Order=7, GroupName="2. Indicadores")]
        public int RSIOverbought
        { get; set; }
        
        // === TRAILING STOP ===
        [NinjaScriptProperty]
        [Display(Name="Activar Trailing", Order=1, GroupName="3. Trailing")]
        public bool ActivarTrailing
        { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name="Trailing ActivaciÃ³n (R)", Order=2, GroupName="3. Trailing")]
        public double TrailingActivacion
        { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 2.0)]
        [Display(Name="Trailing ATR Multiplier", Order=3, GroupName="3. Trailing")]
        public double TrailingATRMultiplier
        { get; set; }
        
        // === FILTROS ===
        [NinjaScriptProperty]
        [Range(0, 150)]
        [Display(Name="Min Volume (%)", Order=1, GroupName="4. Filtros")]
        public int MinVolumePercent
        { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Requiere Tendencia Fuerte", Order=2, GroupName="4. Filtros")]
        public bool RequiereTendenciaFuerte
        { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=3, GroupName="4. Filtros")]
        public bool DebugMode
        { get; set; }
        
        #endregion
    }
}
