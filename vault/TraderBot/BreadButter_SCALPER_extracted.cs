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
    public class BreadButter_SCALPER : Strategy
    {
        // Indicadores
        private EMA emaFast;
        private EMA emaSlow;
        private MACD macd;
        private ATR atr;
        private SMA volumeSMA;
        
        // Control de sesiÃ³n
        private double dailyPnL = 0;
        private int tradesThisSession = 0;
        private DateTime lastSessionDate;
        private bool maxLossHit = false;
        private bool maxTradesHit = false;
        
        // Trailing stop
        private double trailStopPrice = 0;
        private bool trailActivated = false;
        
        // Control de horario
        private TimeSpan startTime;
        private TimeSpan endTime;
        
        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Bread & Butter SCALPER - Estrategia agresiva para day trading con mÃºltiples entradas diarias";
                Name = "BreadButter_SCALPER";
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
                MaxTradesPerDay = 15; // MÃ¡s trades permitidos
                ATRMultiplierStop = 1.0; // Stop mÃ¡s ajustado
                RiskRewardRatio = 1.3; // Target mÃ¡s cercano
                
                // === MACD ===
                MACDFast = 12;
                MACDSlow = 26;
                MACDSmooth = 9;
                
                // === EMAs ===
                EMAFastPeriod = 9; // MÃ¡s rÃ¡pido para scalping
                EMASlowPeriod = 21;
                
                // === VOLUMEN ===
                VolumeSpikeMultiplier = 1.2; // MÃ¡s permisivo
                VolumeSMAPeriod = 14; // MÃ¡s reactivo
                
                // === ATR ===
                ATRPeriod = 14;
                
                // === TRAILING STOP ===
                ActivarTrailing = true;
                TrailingActivacion = 0.8; // Activa rÃ¡pido (0.8R)
                TrailingATRMultiplier = 0.6; // Trail ajustado
                
                // === HORARIO ===
                TradingStartHour = 8; // 8 AM
                TradingStartMinute = 30;
                TradingEndHour = 15; // 3 PM
                TradingEndMinute = 30;
                
                // === DIRECCIÓN ===
                AllowLong  = true;
                AllowShort = true;

                // === DEBUG ===
                DebugMode = false;
            }
            else if (State == State.Configure)
            {
                startTime = new TimeSpan(TradingStartHour, TradingStartMinute, 0);
                endTime = new TimeSpan(TradingEndHour, TradingEndMinute, 0);
            }
            else if (State == State.DataLoaded)
            {
                // EMAs
                emaFast = EMA(EMAFastPeriod);
                emaSlow = EMA(EMASlowPeriod);
                
                // MACD
                macd = MACD(MACDFast, MACDSlow, MACDSmooth);
                
                // ATR
                atr = ATR(ATRPeriod);
                
                // Volume SMA
                volumeSMA = SMA(Volume, VolumeSMAPeriod);
                
                // Colores
                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaSlow.Plots[0].Brush = Brushes.Orange;
                
                // Agregar a chart
                AddChartIndicator(emaFast);
                AddChartIndicator(emaSlow);
                AddChartIndicator(macd);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(EMASlowPeriod, Math.Max(ATRPeriod, MACDSlow + MACDSmooth)))
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
            
            // === VERIFICAR HORARIO ===
            TimeSpan currentTime = Time[0].TimeOfDay;
            bool withinTradingHours = currentTime >= startTime && currentTime <= endTime;
            
            if (!withinTradingHours)
                return;
            
            // === VERIFICAR LÃMITES DIARIOS ===
            if (maxLossHit || maxTradesHit)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong();
                    ExitShort();
                }
                return;
            }
            
            // === GESTIÃN DE POSICIÃN ABIERTA ===
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageTrailingStop();
                return;
            }
            
            // === SEÃALES DE ENTRADA ===
            CheckForScalpEntries();
        }
        
        private void CheckForScalpEntries()
        {
            // === FILTRO DE VOLUMEN ===
            double avgVolume = volumeSMA[0];
            double volumeRatio = Volume[0] / avgVolume;
            bool volumeSpike = volumeRatio >= VolumeSpikeMultiplier;
            
            // === MACD SIGNALS ===
            double macdValue = macd.Default[0];
            double macdAvg = macd.Avg[0];
            double macdDiff = macd.Diff[0];
            
            bool macdCrossUp = CrossAbove(macd.Default, macd.Avg, 1);
            bool macdCrossDown = CrossBelow(macd.Default, macd.Avg, 1);
            bool macdBullish = macdValue > macdAvg && macdDiff > 0;
            bool macdBearish = macdValue < macdAvg && macdDiff < 0;
            
            // === EMA TREND ===
            bool emaTrendBull = Close[0] > emaFast[0] && emaFast[0] > emaSlow[0];
            bool emaTrendBear = Close[0] < emaFast[0] && emaFast[0] < emaSlow[0];
            
            // Debug cada 50 barras
            if (DebugMode && CurrentBar % 50 == 0)
            {
                Print(string.Format("{0} | MACD:{1:F2}/{2:F2} | Vol:{3:F2}x | EMA:F={4:F0} S={5:F0}", 
                    Time[0], macdValue, macdAvg, volumeRatio, emaFast[0], emaSlow[0]));
            }
            
            // === SEÃAL LONG ===
            // Setup 1: MACD cruza arriba + tendencia EMA alcista
            // Setup 2: Price bounce en EMA rÃ¡pida + MACD alcista
            bool longSetup1 = macdCrossUp && emaTrendBull && volumeSpike;
            bool longSetup2 = Low[0] <= emaFast[0] && Close[0] > emaFast[0] && 
                             macdBullish && emaTrendBull && volumeSpike;
            
            if (AllowLong && (longSetup1 || longSetup2))
            {
                double stopPrice = Close[0] - (atr[0] * ATRMultiplierStop);
                double riskPerContract = Close[0] - stopPrice;
                double targetPrice = Close[0] + (riskPerContract * RiskRewardRatio);
                
                EnterLong(Contratos, "LONG");
                SetStopLoss("LONG", CalculationMode.Price, stopPrice, false);
                SetProfitTarget("LONG", CalculationMode.Price, targetPrice);
                
                tradesThisSession++;
                
                if (DebugMode)
                {
                    string setup = longSetup1 ? "MACD Cross" : "EMA Bounce";
                    Print(string.Format("*** LONG ({0}) @ {1:F2} | Stop: {2:F2} | Target: {3:F2} | Vol: {4:F2}x ***", 
                        setup, Close[0], stopPrice, targetPrice, volumeRatio));
                }
            }
            
            // === SEÃAL SHORT ===
            // Setup 1: MACD cruza abajo + tendencia EMA bajista
            // Setup 2: Price bounce en EMA rÃ¡pida + MACD bajista
            bool shortSetup1 = macdCrossDown && emaTrendBear && volumeSpike;
            bool shortSetup2 = High[0] >= emaFast[0] && Close[0] < emaFast[0] && 
                              macdBearish && emaTrendBear && volumeSpike;
            
            if (AllowShort && (shortSetup1 || shortSetup2))
            {
                double stopPrice = Close[0] + (atr[0] * ATRMultiplierStop);
                double riskPerContract = stopPrice - Close[0];
                double targetPrice = Close[0] - (riskPerContract * RiskRewardRatio);
                
                EnterShort(Contratos, "SHORT");
                SetStopLoss("SHORT", CalculationMode.Price, stopPrice, false);
                SetProfitTarget("SHORT", CalculationMode.Price, targetPrice);
                
                tradesThisSession++;
                
                if (DebugMode)
                {
                    string setup = shortSetup1 ? "MACD Cross" : "EMA Bounce";
                    Print(string.Format("*** SHORT ({0}) @ {1:F2} | Stop: {2:F2} | Target: {3:F2} | Vol: {4:F2}x ***", 
                        setup, Close[0], stopPrice, targetPrice, volumeRatio));
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
                
                // Activar trailing rÃ¡pido (0.8R)
                if (!trailActivated && unrealizedPnL >= (targetProfit * TrailingActivacion / RiskRewardRatio))
                {
                    trailActivated = true;
                    trailStopPrice = currentPrice - (atr[0] * TrailingATRMultiplier);
                    
                    if (DebugMode)
                        Print(string.Format("Trailing ACTIVADO @ {0:F2} | Trail: {1:F2}", currentPrice, trailStopPrice));
                }
                
                if (trailActivated)
                {
                    double newTrailStop = currentPrice - (atr[0] * TrailingATRMultiplier);
                    if (newTrailStop > trailStopPrice)
                    {
                        trailStopPrice = newTrailStop;
                        SetStopLoss("LONG", CalculationMode.Price, trailStopPrice, false);
                        
                        if (DebugMode && CurrentBar % 5 == 0)
                            Print(string.Format("Trail actualizado: {0:F2}", trailStopPrice));
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
                        
                        if (DebugMode && CurrentBar % 5 == 0)
                            Print(string.Format("Trail actualizado: {0:F2}", trailStopPrice));
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
                
                if (dailyPnL <= -MaxPerdidaDiaria)
                {
                    maxLossHit = true;
                    if (DebugMode)
                        Print(string.Format("*** LÃMITE DE PÃRDIDA ALCANZADO: ${0:F2} ***", dailyPnL));
                }
                
                if (tradesThisSession >= MaxTradesPerDay)
                {
                    maxTradesHit = true;
                    if (DebugMode)
                        Print(string.Format("*** MÃXIMO DE TRADES ALCANZADO: {0} ***", tradesThisSession));
                }
                
                // Print trade summary
                if (DebugMode && marketPosition == MarketPosition.Flat)
                {
                    Print(string.Format("Trade cerrado | P&L: ${0:F2} | Diario: ${1:F2} | Trades: {2}/{3}", 
                        execPnL, dailyPnL, tradesThisSession, MaxTradesPerDay));
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
        [Range(5, 50)]
        [Display(Name="Max Trades por DÃ­a", Order=3, GroupName="1. Riesgo")]
        public int MaxTradesPerDay
        { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 2.0)]
        [Display(Name="ATR Multiplier Stop", Order=4, GroupName="1. Riesgo")]
        public double ATRMultiplierStop
        { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name="Risk/Reward Ratio", Order=5, GroupName="1. Riesgo")]
        public double RiskRewardRatio
        { get; set; }
        
        // === MACD ===
        [NinjaScriptProperty]
        [Range(5, 20)]
        [Display(Name="MACD Fast", Order=1, GroupName="2. MACD")]
        public int MACDFast
        { get; set; }

        [NinjaScriptProperty]
        [Range(15, 40)]
        [Display(Name="MACD Slow", Order=2, GroupName="2. MACD")]
        public int MACDSlow
        { get; set; }

        [NinjaScriptProperty]
        [Range(5, 15)]
        [Display(Name="MACD Smooth", Order=3, GroupName="2. MACD")]
        public int MACDSmooth
        { get; set; }
        
        // === EMAs ===
        [NinjaScriptProperty]
        [Range(5, 20)]
        [Display(Name="EMA RÃ¡pida", Order=1, GroupName="3. EMAs")]
        public int EMAFastPeriod
        { get; set; }

        [NinjaScriptProperty]
        [Range(15, 50)]
        [Display(Name="EMA Lenta", Order=2, GroupName="3. EMAs")]
        public int EMASlowPeriod
        { get; set; }
        
        // === VOLUMEN ===
        [NinjaScriptProperty]
        [Range(1.0, 2.0)]
        [Display(Name="Volume Spike Multiplier", Order=1, GroupName="4. Volumen")]
        public double VolumeSpikeMultiplier
        { get; set; }

        [NinjaScriptProperty]
        [Range(10, 30)]
        [Display(Name="Volume SMA Period", Order=2, GroupName="4. Volumen")]
        public int VolumeSMAPeriod
        { get; set; }
        
        // === ATR ===
        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ATR PerÃ­odo", Order=1, GroupName="5. ATR")]
        public int ATRPeriod
        { get; set; }
        
        // === TRAILING STOP ===
        [NinjaScriptProperty]
        [Display(Name="Activar Trailing", Order=1, GroupName="6. Trailing")]
        public bool ActivarTrailing
        { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 2.0)]
        [Display(Name="Trailing ActivaciÃ³n (R)", Order=2, GroupName="6. Trailing")]
        public double TrailingActivacion
        { get; set; }

        [NinjaScriptProperty]
        [Range(0.3, 1.5)]
        [Display(Name="Trailing ATR Multiplier", Order=3, GroupName="6. Trailing")]
        public double TrailingATRMultiplier
        { get; set; }
        
        // === HORARIO ===
        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name="Trading Start Hour", Order=1, GroupName="7. Horario")]
        public int TradingStartHour
        { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name="Trading Start Minute", Order=2, GroupName="7. Horario")]
        public int TradingStartMinute
        { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name="Trading End Hour", Order=3, GroupName="7. Horario")]
        public int TradingEndHour
        { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name="Trading End Minute", Order=4, GroupName="7. Horario")]
        public int TradingEndMinute
        { get; set; }
        
        // === DIRECCIÓN ===
        [NinjaScriptProperty]
        [Display(Name="Allow Long", Order=1, GroupName="8. Dirección")]
        public bool AllowLong
        { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Short", Order=2, GroupName="8. Dirección")]
        public bool AllowShort
        { get; set; }

        // === DEBUG ===
        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=1, GroupName="9. Debug")]
        public bool DebugMode
        { get; set; }
        
        #endregion
    }
}
