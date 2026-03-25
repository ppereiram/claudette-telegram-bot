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
// ZMQ (NetMQ) — solo se usa cuando UseMLFilter = true
using NetMQ;
using NetMQ.Sockets;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    public class BreadButter_ULTRA : Strategy
    {
        // Indicadores
        private EMA emaFast;
        private EMA emaMid;
        private ATR atr;
        private SMA volumeSMA;
        private RSI rsi;

        // ML Filter (ZMQ)
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        // Control de sesion
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

        // Timezone
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = @"Bread & Butter ULTRA v2 - Scalper agresivo con filtros RSI, ATR minimo y control de direccion";
                Name = "BreadButter_ULTRA";
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

                // === 1. GESTION DE RIESGO ===
                Contratos        = 15;
                MaxPerdidaDiaria = 300;
                MaxTradesPerDay  = 25;
                ATRMultiplierStop = 1.0;
                RiskRewardRatio  = 2.0;

                // === 2. EMAs ===
                EMAFastPeriod = 3;
                EMAMidPeriod  = 21;

                // === 3. MOMENTUM ===
                MomentumThreshold = 0.05;

                // === 4. VOLUMEN ===
                RequireVolumeSpike = false;
                MinVolumePercent   = 80;
                VolumeSMAPeriod    = 20;

                // === 5. ATR ===
                ATRPeriod    = 10;
                UseMinATR    = false;
                MinATRPoints = 3.0; // Saltar barras si ATR < 3 puntos (mercado dormido)

                // === 6. TRAILING ===
                ActivarTrailing       = false;
                TrailingActivacion    = 0.5;
                TrailingATRMultiplier = 0.4;

                // === 7. HORARIO (siempre ET — GetEtTimeSpan() maneja backtest vs live) ===
                TradingStartHour   = 9;   // 9:00 ET
                TradingStartMinute = 0;
                TradingEndHour     = 15;  // 15:30 ET
                TradingEndMinute   = 30;

                // === 8. SETUPS ===
                EnableMomentumBurst = true;
                EnableMicroReversal = true;
                EnableBreakoutScalp = true;
                EnableEMATouch      = true;

                // === 9. DIRECCION ===
                AllowLong  = true;
                AllowShort = true;

                // === 10. RSI FILTER ===
                UseRSIFilter  = false;
                RSIPeriod     = 14;
                RSILongMax    = 65; // No entrar Long si RSI > 65 (sobrecomprado)
                RSIShortMin   = 35; // No entrar Short si RSI < 35 (sobrevendido)

                // === 11. DEBUG ===
                DebugMode = false;

                // === 12. ML FILTER ===
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.Configure)
            {
                startTime = new TimeSpan(TradingStartHour, TradingStartMinute, 0);
                endTime   = new TimeSpan(TradingEndHour,   TradingEndMinute,   0);
            }
            else if (State == State.DataLoaded)
            {
                emaFast   = EMA(EMAFastPeriod);
                emaMid    = EMA(EMAMidPeriod);
                atr       = ATR(ATRPeriod);
                volumeSMA = SMA(Volume, VolumeSMAPeriod);
                rsi       = RSI(RSIPeriod, 1);

                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaMid.Plots[0].Brush  = Brushes.Orange;

                AddChartIndicator(emaFast);
                AddChartIndicator(emaMid);

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("ULTRA ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("ULTRA ML: Error al conectar ZMQ: {0}", ex.Message));
                        mlSocket = null;
                    }
                }
            }
            else if (State == State.Terminated)
            {
                if (mlSocket != null)
                {
                    try { mlSocket.Dispose(); NetMQConfig.Cleanup(); } catch { }
                    mlSocket = null;
                }
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(EMAMidPeriod, Math.Max(ATRPeriod, RSIPeriod)))
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

            // === VERIFICAR HORARIO (siempre ET — GetEtTimeSpan() maneja backtest vs live) ===
            TimeSpan barEt = GetEtTimeSpan();
            if (barEt < startTime || barEt > endTime)
                return;

            // === VERIFICAR LIMITES DIARIOS ===
            if (maxLossHit || maxTradesHit)
            {
                if (Position.MarketPosition != MarketPosition.Flat)
                {
                    ExitLong();
                    ExitShort();
                }
                return;
            }

            // === GESTION DE POSICION ABIERTA ===
            if (Position.MarketPosition != MarketPosition.Flat)
            {
                ManageTrailingStop();
                return;
            }

            // === SENALES DE ENTRADA ===
            CheckAggressiveEntries();
        }

        private TimeSpan GetEtTimeSpan()
        {
            if (State == State.Realtime)
                return TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone).TimeOfDay;
            return Time[0].TimeOfDay;
        }

        private void CheckAggressiveEntries()
        {
            // === FILTRO MinATR: saltar si el mercado esta dormido ===
            if (UseMinATR && atr[0] < MinATRPoints)
                return;

            // === CALCULAR MOMENTUM ===
            double priceChangePercent = 0;
            if (CurrentBar > 0)
                priceChangePercent = ((Close[0] - Close[1]) / Close[1]) * 100;

            // === VOLUMEN ===
            double avgVolume = volumeSMA[0];
            bool volumeOK = Volume[0] >= (avgVolume * MinVolumePercent / 100.0);
            if (!volumeOK && RequireVolumeSpike)
                return;

            // === TENDENCIA BASICA ===
            bool trendUp   = emaFast[0] > emaMid[0];
            bool trendDown = emaFast[0] < emaMid[0];

            // === FILTRO RSI (opcional) ===
            bool rsiLongOK  = !UseRSIFilter || (rsi[0] < RSILongMax);
            bool rsiShortOK = !UseRSIFilter || (rsi[0] > RSIShortMin);

            // === FILTROS DE DIRECCION ===
            bool canLong  = AllowLong  && rsiLongOK;
            bool canShort = AllowShort && rsiShortOK;

            if (DebugMode && CurrentBar % 30 == 0)
            {
                Print(string.Format("{0} | DeltaP:{1:F2}% | ATR:{2:F1} | RSI:{3:F0} | Trend:{4}",
                    Time[0], priceChangePercent, atr[0], rsi[0], trendUp ? "UP" : "DN"));
            }

            // === SETUP 1: MOMENTUM BURST ===
            // Entrada en impulso direccional fuerte
            if (EnableMomentumBurst)
            {
                bool burstLong  = priceChangePercent >  MomentumThreshold && trendUp   && Close[0] > Open[0];
                bool burstShort = priceChangePercent < -MomentumThreshold && trendDown && Close[0] < Open[0];

                if (canLong  && burstLong)  { ExecuteEntry("LONG",  "Momentum Burst"); return; }
                if (canShort && burstShort) { ExecuteEntry("SHORT", "Momentum Burst"); return; }
            }

            // === SETUP 2: MICRO REVERSAL ===
            // Entrada en rebote tras 2 barras en contra
            if (EnableMicroReversal && CurrentBar > 2)
            {
                bool microLong  = Close[2] > Close[1] && Close[1] < Close[0] &&
                                  Close[0] > emaFast[0] &&
                                  (Close[0] - Low[0]) > (High[0] - Close[0]); // cuerpo alcista

                bool microShort = Close[2] < Close[1] && Close[1] > Close[0] &&
                                  Close[0] < emaFast[0] &&
                                  (High[0] - Close[0]) > (Close[0] - Low[0]); // cuerpo bajista

                if (canLong  && microLong  && trendUp)   { ExecuteEntry("LONG",  "Micro Reversal"); return; }
                if (canShort && microShort && trendDown)  { ExecuteEntry("SHORT", "Micro Reversal"); return; }
            }

            // === SETUP 3: BREAKOUT SCALP ===
            // Ruptura de rango de consolidacion con volumen
            if (EnableBreakoutScalp && CurrentBar > 3)
            {
                double recentHigh = Math.Max(Math.Max(High[1], High[2]), High[3]);
                double recentLow  = Math.Min(Math.Min(Low[1],  Low[2]),  Low[3]);
                double range      = recentHigh - recentLow;

                bool breakLong  = Close[0] > recentHigh && range < (atr[0] * 1.5) && Volume[0] > avgVolume && trendUp;
                bool breakShort = Close[0] < recentLow  && range < (atr[0] * 1.5) && Volume[0] > avgVolume && trendDown;

                if (canLong  && breakLong)  { ExecuteEntry("LONG",  "Breakout Scalp"); return; }
                if (canShort && breakShort) { ExecuteEntry("SHORT", "Breakout Scalp"); return; }
            }

            // === SETUP 4: EMA TOUCH ===
            // Rebote clasico en EMA rapida con confirmacion de vela
            if (EnableEMATouch)
            {
                bool emaTouchLong  = Low[0]  <= emaFast[0] && Close[0] > emaFast[0] && trendUp   && Close[0] > Open[0];
                bool emaTouchShort = High[0] >= emaFast[0] && Close[0] < emaFast[0] && trendDown && Close[0] < Open[0];

                if (canLong  && emaTouchLong)  { ExecuteEntry("LONG",  "EMA Touch"); return; }
                if (canShort && emaTouchShort) { ExecuteEntry("SHORT", "EMA Touch"); return; }
            }
        }

        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                int    etTime   = ToTime(State == State.Realtime ? TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone) : Time[0]);
                int    hour     = etTime / 10000;
                int    minute   = (etTime % 10000) / 100;
                int    dow      = (int)Time[0].DayOfWeek;
                double volRatio = volumeSMA[0] > 0 ? Volume[0] / volumeSMA[0] : 1.0;
                double rsiVal   = rsi[0];

                mlTradeId = string.Format("ULTRA_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"BreadButter_ULTRA\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":{2:F1},\"adx\":25.0," +
                    "\"vol_ratio\":{3:F3},\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{4},\"minute\":{5},\"day_of_week\":{6},\"signal_type\":{7}}}",
                    mlTradeId, direction, rsiVal, volRatio, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("ULTRA ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (DebugMode || !allow) Print(string.Format("ULTRA ML [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("ULTRA ML Error: {0} — permitiendo trade", ex.Message));
                return true;
            }
        }

        private void LogMLOutcome(double pnl)
        {
            if (mlSocket == null || string.IsNullOrEmpty(mlTradeId)) return;
            try
            {
                int result = pnl > 0 ? 1 : -1;
                string json = string.Format(
                    "{{\"type\":\"outcome\",\"strategy\":\"BreadButter_ULTRA\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("ULTRA ML outcome error: {0}", ex.Message)); }
        }

        private void ExecuteEntry(string direction, string setupName)
        {
            // ML gate
            int mlDir  = direction == "LONG" ? 1 : -1;
            int mlSigt = setupName == "Momentum Burst" ? 0 : setupName == "Micro Reversal" ? 1 : setupName == "Breakout Scalp" ? 2 : 3;
            if (UseMLFilter && !QueryMLFilter(mlDir, mlSigt)) return;

            double stopPrice, targetPrice, riskPerContract;

            if (direction == "LONG")
            {
                stopPrice       = Close[0] - (atr[0] * ATRMultiplierStop);
                riskPerContract = Close[0] - stopPrice;
                targetPrice     = Close[0] + (riskPerContract * RiskRewardRatio);

                EnterLong(Contratos, "LONG");
                SetStopLoss("LONG",    CalculationMode.Price, stopPrice,   false);
                SetProfitTarget("LONG", CalculationMode.Price, targetPrice);

                tradesThisSession++;

                if (DebugMode)
                    Print(string.Format("*** LONG ({0}) @ {1:F2} | Stop:{2:F2} | Target:{3:F2} | RSI:{4:F0} | ATR:{5:F1} ***",
                        setupName, Close[0], stopPrice, targetPrice, rsi[0], atr[0]));
            }
            else
            {
                stopPrice       = Close[0] + (atr[0] * ATRMultiplierStop);
                riskPerContract = stopPrice - Close[0];
                targetPrice     = Close[0] - (riskPerContract * RiskRewardRatio);

                EnterShort(Contratos, "SHORT");
                SetStopLoss("SHORT",    CalculationMode.Price, stopPrice,   false);
                SetProfitTarget("SHORT", CalculationMode.Price, targetPrice);

                tradesThisSession++;

                if (DebugMode)
                    Print(string.Format("*** SHORT ({0}) @ {1:F2} | Stop:{2:F2} | Target:{3:F2} | RSI:{4:F0} | ATR:{5:F1} ***",
                        setupName, Close[0], stopPrice, targetPrice, rsi[0], atr[0]));
            }
        }

        private void ManageTrailingStop()
        {
            if (!ActivarTrailing)
                return;

            double entryPrice      = Position.AveragePrice;
            double currentPrice    = Close[0];
            double riskPerContract = atr[0] * ATRMultiplierStop;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double unrealizedPnL = (currentPrice - entryPrice) * Position.Quantity;
                double targetProfit  = riskPerContract * RiskRewardRatio * Position.Quantity;

                if (!trailActivated && unrealizedPnL >= (targetProfit * TrailingActivacion / RiskRewardRatio))
                {
                    trailActivated = true;
                    trailStopPrice = currentPrice - (atr[0] * TrailingATRMultiplier);
                    SetStopLoss("LONG", CalculationMode.Price, trailStopPrice, false);

                    if (DebugMode)
                        Print(string.Format("Trail LONG ON @ {0:F2} -> {1:F2}", currentPrice, trailStopPrice));
                }
                else if (trailActivated)
                {
                    double newTrail = currentPrice - (atr[0] * TrailingATRMultiplier);
                    if (newTrail > trailStopPrice)
                    {
                        trailStopPrice = newTrail;
                        SetStopLoss("LONG", CalculationMode.Price, trailStopPrice, false);
                    }
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double unrealizedPnL = (entryPrice - currentPrice) * Position.Quantity;
                double targetProfit  = riskPerContract * RiskRewardRatio * Position.Quantity;

                if (!trailActivated && unrealizedPnL >= (targetProfit * TrailingActivacion / RiskRewardRatio))
                {
                    trailActivated = true;
                    trailStopPrice = currentPrice + (atr[0] * TrailingATRMultiplier);
                    SetStopLoss("SHORT", CalculationMode.Price, trailStopPrice, false);

                    if (DebugMode)
                        Print(string.Format("Trail SHORT ON @ {0:F2} -> {1:F2}", currentPrice, trailStopPrice));
                }
                else if (trailActivated)
                {
                    double newTrail = currentPrice + (atr[0] * TrailingATRMultiplier);
                    if (newTrail < trailStopPrice)
                    {
                        trailStopPrice = newTrail;
                        SetStopLoss("SHORT", CalculationMode.Price, trailStopPrice, false);
                    }
                }
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId, double price, int quantity,
            MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            // Reset trailing al entrar
            if (execution.Order.Name == "LONG" || execution.Order.Name == "SHORT")
            {
                trailActivated = false;
                trailStopPrice = 0;
            }

            // Actualizar P&L diario (logica original — filtro natural de 1 trade/dia)
            double execPnL = execution.Commission + execution.Order.AverageFillPrice * execution.Quantity;
            dailyPnL += (marketPosition == MarketPosition.Flat) ? execPnL : -execPnL;

            // ML outcome: usar SystemPerformance para P&L real cuando se cierra posicion
            if (UseMLFilter && marketPosition == MarketPosition.Flat)
            {
                var allTrades = SystemPerformance.AllTrades;
                if (allTrades.Count > 0)
                    LogMLOutcome(allTrades[allTrades.Count - 1].ProfitCurrency);
            }

            if (dailyPnL <= -MaxPerdidaDiaria)
            {
                maxLossHit = true;
                if (DebugMode)
                    Print(string.Format("*** MAX LOSS HIT: ${0:F2} ***", dailyPnL));
            }

            if (tradesThisSession >= MaxTradesPerDay)
            {
                maxTradesHit = true;
                if (DebugMode)
                    Print(string.Format("*** MAX TRADES HIT: {0} ***", tradesThisSession));
            }

            if (DebugMode && marketPosition == MarketPosition.Flat)
                Print(string.Format("Exit | P&L sesion: ${0:F2} | Trades: {1}/{2}",
                    dailyPnL, tradesThisSession, MaxTradesPerDay));
        }

        #region Properties

        // === 1. RIESGO ===
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Contratos", Order=1, GroupName="1. Riesgo")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(100, 2000)]
        [Display(Name="Max Perdida Diaria ($)", Order=2, GroupName="1. Riesgo")]
        public int MaxPerdidaDiaria { get; set; }

        [NinjaScriptProperty]
        [Range(5, 50)]
        [Display(Name="Max Trades/Dia", Order=3, GroupName="1. Riesgo")]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Range(0.3, 2.0)]
        [Display(Name="ATR Stop Multiplier", Order=4, GroupName="1. Riesgo")]
        public double ATRMultiplierStop { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name="R/R Ratio", Order=5, GroupName="1. Riesgo")]
        public double RiskRewardRatio { get; set; }

        // === 2. EMAs ===
        [NinjaScriptProperty]
        [Range(2, 10)]
        [Display(Name="EMA Fast", Order=1, GroupName="2. EMAs")]
        public int EMAFastPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(10, 30)]
        [Display(Name="EMA Mid", Order=2, GroupName="2. EMAs")]
        public int EMAMidPeriod { get; set; }

        // === 3. MOMENTUM ===
        [NinjaScriptProperty]
        [Range(0.01, 0.50)]
        [Display(Name="Momentum Threshold %", Order=1, GroupName="3. Momentum")]
        public double MomentumThreshold { get; set; }

        // === 4. VOLUMEN ===
        [NinjaScriptProperty]
        [Display(Name="Require Volume Spike", Order=1, GroupName="4. Volumen")]
        public bool RequireVolumeSpike { get; set; }

        [NinjaScriptProperty]
        [Range(50, 150)]
        [Display(Name="Min Volume %", Order=2, GroupName="4. Volumen")]
        public int MinVolumePercent { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="Volume SMA", Order=3, GroupName="4. Volumen")]
        public int VolumeSMAPeriod { get; set; }

        // === 5. ATR ===
        [NinjaScriptProperty]
        [Range(5, 20)]
        [Display(Name="ATR Period", Order=1, GroupName="5. ATR")]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Usar ATR Minimo", Order=2, GroupName="5. ATR")]
        public bool UseMinATR { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 10.0)]
        [Display(Name="ATR Minimo (puntos)", Order=3, GroupName="5. ATR")]
        public double MinATRPoints { get; set; }

        // === 6. TRAILING ===
        [NinjaScriptProperty]
        [Display(Name="Enable Trailing", Order=1, GroupName="6. Trailing")]
        public bool ActivarTrailing { get; set; }

        [NinjaScriptProperty]
        [Range(0.3, 1.5)]
        [Display(Name="Trail Activation R", Order=2, GroupName="6. Trailing")]
        public double TrailingActivacion { get; set; }

        [NinjaScriptProperty]
        [Range(0.2, 1.0)]
        [Display(Name="Trail ATR Mult", Order=3, GroupName="6. Trailing")]
        public double TrailingATRMultiplier { get; set; }

        // === 7. HORARIO ===
        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name="Start Hour", Order=1, GroupName="7. Horario")]
        public int TradingStartHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name="Start Minute", Order=2, GroupName="7. Horario")]
        public int TradingStartMinute { get; set; }

        [NinjaScriptProperty]
        [Range(0, 23)]
        [Display(Name="End Hour", Order=3, GroupName="7. Horario")]
        public int TradingEndHour { get; set; }

        [NinjaScriptProperty]
        [Range(0, 59)]
        [Display(Name="End Minute", Order=4, GroupName="7. Horario")]
        public int TradingEndMinute { get; set; }

        // === 8. SETUPS ===
        [NinjaScriptProperty]
        [Display(Name="Momentum Burst", Order=1, GroupName="8. Setups")]
        public bool EnableMomentumBurst { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Micro Reversal", Order=2, GroupName="8. Setups")]
        public bool EnableMicroReversal { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Breakout Scalp", Order=3, GroupName="8. Setups")]
        public bool EnableBreakoutScalp { get; set; }

        [NinjaScriptProperty]
        [Display(Name="EMA Touch", Order=4, GroupName="8. Setups")]
        public bool EnableEMATouch { get; set; }

        // === 9. DIRECCION ===
        [NinjaScriptProperty]
        [Display(Name="Allow Long", Order=1, GroupName="9. Direccion")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Short", Order=2, GroupName="9. Direccion")]
        public bool AllowShort { get; set; }

        // === 10. RSI FILTER ===
        [NinjaScriptProperty]
        [Display(Name="Usar Filtro RSI", Order=1, GroupName="10. RSI Filter")]
        public bool UseRSIFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5, 21)]
        [Display(Name="RSI Period", Order=2, GroupName="10. RSI Filter")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(55, 80)]
        [Display(Name="RSI Long Max (no Long si >)", Order=3, GroupName="10. RSI Filter")]
        public int RSILongMax { get; set; }

        [NinjaScriptProperty]
        [Range(20, 45)]
        [Display(Name="RSI Short Min (no Short si <)", Order=4, GroupName="10. RSI Filter")]
        public int RSIShortMin { get; set; }

        // === 11. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=1, GroupName="11. Debug")]
        public bool DebugMode { get; set; }

        // === 12. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name="Activar Filtro ML (ZMQ)", Order=1, GroupName="12. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name="Puerto Python (meta_brain.py)", Order=2, GroupName="12. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
