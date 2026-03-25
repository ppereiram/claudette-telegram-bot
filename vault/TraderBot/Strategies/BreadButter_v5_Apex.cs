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
// Requiere NetMQ.dll en Documents\NinjaTrader 8\bin\Custom\
using NetMQ;
using NetMQ.Sockets;
#endregion

namespace NinjaTrader.NinjaScript.Strategies
{
    // ============================================================
    // BreadButter v5 Apex - 2-min MNQ
    //
    // Horarios siempre en ET (GetEtTime() funciona en backtest y live):
    //   Prime AM: 9:30 - 12:30 ET
    //   Prime PM: 13:30 - 15:30 ET
    //   CME Break: 16:45 - 18:00 ET
    // ============================================================
    public class BreadButter_v5_Apex : Strategy
    {
        // === TIMEZONE ===
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        // === INDICADORES ===
        private EMA emaFast;
        private EMA emaSlow;
        private EMA emaHTF;
        private ATR atr;
        private RSI rsi;
        private SMA volumeSMA;
        private ADX adx;

        // === GESTION DE SESION ===
        private double   dailyPnL          = 0;
        private int      tradesThisSession = 0;
        private DateTime lastSessionDate;
        private bool     stopTradingToday  = false;

        // === TRACKING DEL TRADE ACTIVO ===
        private double entryPrice         = 0;
        private double entryATR           = 0;
        private double dynamicStopPrice   = 0;
        private bool   breakevenActivated = false;
        private bool   trailActivated     = false;

        // === ML FILTER (ZMQ) ===
        // UseMLFilter = false por defecto → backtest idéntico al original
        // UseMLFilter = true  → consulta Python antes de cada entrada
        private RequestSocket mlSocket       = null;
        private string        mlEntryContext = "";  // contexto JSON guardado al entrar
        private string        mlTradeId      = "";  // ID único del trade para el log

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "Bread & Butter v5 Apex - 2 min MNQ, EMA + ADX + RSI | Horario Costa Rica";
                Name        = "BreadButter_v5_Apex";
                Calculate   = Calculate.OnBarClose;

                EntriesPerDirection                       = 1;
                EntryHandling                             = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy              = true;
                ExitOnSessionCloseSeconds                 = 30;
                IsFillLimitOnTouch                        = false;
                MaximumBarsLookBack                       = MaximumBarsLookBack.TwoHundredFiftySix;
                OrderFillResolution                       = OrderFillResolution.Standard;
                Slippage                                  = 1;
                StartBehavior                             = StartBehavior.WaitUntilFlat;
                TimeInForce                               = TimeInForce.Gtc;
                TraceOrders                               = false;
                RealtimeErrorHandling                     = RealtimeErrorHandling.StopCancelClose;
                StopTargetHandling                        = StopTargetHandling.PerEntryExecution;
                BarsRequiredToTrade                       = 201;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. SIZING ===
                FixedContracts   = 3;    // Apex $7,500: MaxDD=$6,510 (3ct × $2,170/ct)
                MaxPerdidaDiaria = 500;
                MaxTradesPerDay  = 1;    // 1 trade/dia — param ganador confirmado

                // === 2. FILTROS ===
                ADXThreshold   = 25;    // confirmado
                RSILongMax     = 65;    // confirmado
                RSIShortMin    = 35;    // confirmado
                MinVolumeRatio = 0.7;   // confirmado

                // === 3. GESTION DE TRADE ===
                StopLossATR    = 3.0;   // 3 ATR — param ganador (Stop=3ATR resuelve el ETD)
                TargetRatioRR  = 4.0;   // R:R=4 — param ganador
                BreakevenR     = 1.0;   // BE=1R confirmado
                EnableTrailing = false; // Trailing OFF — param ganador clave
                TrailStartR    = 1.5;
                TrailATRDist   = 1.0;

                // === 4. INDICADORES ===
                EMAFastPeriod  = 9;     // confirmado
                EMASlowPeriod  = 15;    // confirmado (no 20)
                EMAHTFPeriod   = 100;   // confirmado (no 200)
                ATRPeriod      = 7;     // confirmado (no 14)
                RSIPeriod      = 7;     // confirmado (no 14)
                ADXPeriod      = 21;    // confirmado (no 14)

                // === 5. HORARIO (siempre ET — GetEtTime() maneja la conversion) ===
                BlockGlobexBreak  = true;
                UsePrimeHoursOnly = true;  // ON confirmado

                // === 6. DEBUG ===
                DebugMode = false;

                // === 7. ML FILTER ===
                UseMLFilter = false;  // OFF por defecto (backtest normal)
                MLPort      = 5556;   // puerto del meta_brain_bbv5.py
            }
            else if (State == State.DataLoaded)
            {
                emaFast   = EMA(EMAFastPeriod);
                emaSlow   = EMA(EMASlowPeriod);
                emaHTF    = EMA(EMAHTFPeriod);
                atr       = ATR(ATRPeriod);
                rsi       = RSI(RSIPeriod, 3);
                volumeSMA = SMA(Volume, 20);
                adx       = ADX(ADXPeriod);

                emaFast.Plots[0].Brush = Brushes.Cyan;
                emaSlow.Plots[0].Brush = Brushes.Orange;
                emaHTF.Plots[0].Brush  = Brushes.Gray;

                AddChartIndicator(emaFast);
                AddChartIndicator(emaSlow);
                AddChartIndicator(emaHTF);

                // Inicializar socket ZMQ si ML está activado
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("BBv5 ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("BBv5 ML: Error al conectar ZMQ: {0}", ex.Message));
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
            if (CurrentBar < Math.Max(EMAHTFPeriod, 201))
                return;

            // Solo operar en tiempo real (no durante replay de reconexión)
            if (State != State.Realtime && State != State.Historical)
                return;

            // === RESET DIARIO ===
            if (lastSessionDate != Time[0].Date)
            {
                lastSessionDate   = Time[0].Date;
                dailyPnL          = 0;
                tradesThisSession = 0;
                stopTradingToday  = false;

                if (DebugMode)
                    Print(string.Format("=== NUEVA SESION: {0} ===", Time[0].Date.ToShortDateString()));
            }

            // === CIRCUIT BREAKER ===
            if (stopTradingToday)
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
                ManageTrade();
                return;
            }

            // === FILTRO HORARIO (siempre ET — GetEtTime() maneja backtest vs live) ===
            int t = GetEtTime();

            // CME Break: 16:45-18:00 ET
            if (BlockGlobexBreak && t >= 164500 && t < 180000)
                return;

            // Prime hours: 9:30-12:30 ET y 13:30-15:30 ET
            if (UsePrimeHoursOnly)
            {
                bool primeAM = (t >= 93000 && t <= 123000);
                bool primePM = (t >= 133000 && t <= 153000);
                if (!primeAM && !primePM)
                    return;
            }

            CheckForEntries();
        }

        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        private void CheckForEntries()
        {
            if (adx[0] < ADXThreshold)
                return;

            if (Volume[0] < volumeSMA[0] * MinVolumeRatio)
                return;

            bool bullTrend = Close[0] > emaHTF[0];
            bool bearTrend = Close[0] < emaHTF[0];

            bool bullCross    = CrossAbove(emaFast, emaSlow, 1);
            bool bearCross    = CrossBelow(emaFast, emaSlow, 1);
            bool bullPullback = Low[0]  <= emaSlow[0] && Close[0] > emaSlow[0] && emaFast[0] > emaSlow[0];
            bool bearPullback = High[0] >= emaSlow[0] && Close[0] < emaSlow[0] && emaFast[0] < emaSlow[0];

            if (DebugMode && CurrentBar % 50 == 0)
                Print(string.Format("{0} | ADX:{1:F0} | RSI:{2:F0} | Trend:{3} | Vol:{4:F2}x",
                    Time[0].ToShortTimeString(), adx[0], rsi[0],
                    bullTrend ? "BULL" : "BEAR", Volume[0] / volumeSMA[0]));

            // === LONG ===
            if (bullTrend && (bullCross || bullPullback) && rsi[0] < RSILongMax)
            {
                // ML Gate: consultar Python antes de entrar (solo si UseMLFilter=true)
                int signalType = bullCross ? 0 : 1;
                if (UseMLFilter && !QueryMLFilter(1, signalType))
                    return;

                double risk   = atr[0] * StopLossATR;
                double stop   = Close[0] - risk;
                double target = Close[0] + (risk * TargetRatioRR);

                EnterLong(FixedContracts, "Long");
                SetStopLoss("Long",     CalculationMode.Price, stop,   false);
                SetProfitTarget("Long", CalculationMode.Price, target);

                entryPrice         = Close[0];
                entryATR           = atr[0];
                dynamicStopPrice   = stop;
                breakevenActivated = false;
                trailActivated     = false;

                if (DebugMode)
                    Print(string.Format("*** LONG @ {0:F2} | SL:{1:F2} | TP:{2:F2} | ATR:{3:F1} | RSI:{4:F0}",
                        Close[0], stop, target, atr[0], rsi[0]));
            }
            // === SHORT ===
            else if (bearTrend && (bearCross || bearPullback) && rsi[0] > RSIShortMin)
            {
                // ML Gate: consultar Python antes de entrar (solo si UseMLFilter=true)
                int signalType = bearCross ? 0 : 1;
                if (UseMLFilter && !QueryMLFilter(-1, signalType))
                    return;

                double risk   = atr[0] * StopLossATR;
                double stop   = Close[0] + risk;
                double target = Close[0] - (risk * TargetRatioRR);

                EnterShort(FixedContracts, "Short");
                SetStopLoss("Short",     CalculationMode.Price, stop,   false);
                SetProfitTarget("Short", CalculationMode.Price, target);

                entryPrice         = Close[0];
                entryATR           = atr[0];
                dynamicStopPrice   = stop;
                breakevenActivated = false;
                trailActivated     = false;

                if (DebugMode)
                    Print(string.Format("*** SHORT @ {0:F2} | SL:{1:F2} | TP:{2:F2} | ATR:{3:F1} | RSI:{4:F0}",
                        Close[0], stop, target, atr[0], rsi[0]));
            }
        }

        // ============================================================
        // ML FILTER — ZMQ helpers
        // Solo se ejecutan cuando UseMLFilter = true
        // ============================================================

        /// <summary>
        /// Envía el contexto de mercado a Python y espera allow/block.
        /// Timeout 500ms → fail-safe permite el trade.
        /// </summary>
        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;

            try
            {
                int    etTime    = GetEtTime();
                int    hour      = etTime / 10000;
                int    minute    = (etTime % 10000) / 100;
                int    dow       = (int)Time[0].DayOfWeek;
                double distHTF   = emaHTF[0] > 0 ? (Close[0] - emaHTF[0]) / Close[0] : 0;
                double emaSlope  = atr[0]    > 0 ? (emaFast[0] - emaFast[Math.Min(2, CurrentBar)]) / atr[0] : 0;
                double volRatio  = volumeSMA[0] > 0 ? Volume[0] / volumeSMA[0] : 1.0;

                // Guardar ID único para correlacionar con el outcome
                mlTradeId = string.Format("{0}_{1}", direction > 0 ? "Long" : "Short",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                // Construir JSON (sin Newtonsoft — string format simple)
                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":{2:F1},\"adx\":{3:F1}," +
                    "\"vol_ratio\":{4:F3},\"dist_htf\":{5:F5},\"ema_slope\":{6:F4}," +
                    "\"hour\":{7},\"minute\":{8},\"day_of_week\":{9},\"signal_type\":{10}}}",
                    mlTradeId, direction, rsi[0], adx[0],
                    volRatio, distHTF, emaSlope,
                    hour, minute, dow, signalType);

                mlEntryContext = json;  // guardado para enviar con el outcome

                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(
                    System.TimeSpan.FromMilliseconds(500), out response);

                if (!received)
                {
                    Print("BBv5 ML: Timeout (500ms) — permitiendo trade");
                    return true;  // fail-safe
                }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");

                if (DebugMode || !allow)
                    Print(string.Format("BBv5 ML [{0}]: {1}", mlTradeId, response));

                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("BBv5 ML Error: {0} — permitiendo trade", ex.Message));
                return true;  // fail-safe
            }
        }

        /// <summary>
        /// Envía el resultado del trade a Python para que lo registre en el log.
        /// Se llama desde OnExecutionUpdate cuando se cierra la posición.
        /// </summary>
        private void LogMLOutcome(double pnl)
        {
            if (mlSocket == null || string.IsNullOrEmpty(mlTradeId)) return;

            try
            {
                int result = pnl > 0 ? 1 : -1;
                string json = string.Format(
                    "{{\"type\":\"outcome\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);

                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);

                if (DebugMode)
                    Print(string.Format("BBv5 ML outcome enviado: {0}", ack));

                mlTradeId      = "";
                mlEntryContext = "";
            }
            catch (Exception ex)
            {
                Print(string.Format("BBv5 ML outcome error: {0}", ex.Message));
            }
        }

        private void ManageTrade()
        {
            double currentPrice = Close[0];
            double riskAmount   = entryATR * StopLossATR;

            if (Position.MarketPosition == MarketPosition.Long)
            {
                double profit = currentPrice - entryPrice;

                if (!breakevenActivated && profit >= riskAmount * BreakevenR)
                {
                    breakevenActivated = true;
                    dynamicStopPrice   = entryPrice + TickSize;
                    SetStopLoss("Long", CalculationMode.Price, dynamicStopPrice, false);

                    if (DebugMode)
                        Print(string.Format("BE Long @ {0:F2}", dynamicStopPrice));
                }

                if (EnableTrailing && breakevenActivated && profit >= riskAmount * TrailStartR)
                {
                    trailActivated = true;
                    double newStop = currentPrice - (entryATR * TrailATRDist);
                    if (newStop > dynamicStopPrice)
                    {
                        dynamicStopPrice = newStop;
                        SetStopLoss("Long", CalculationMode.Price, dynamicStopPrice, false);
                    }
                }
            }
            else if (Position.MarketPosition == MarketPosition.Short)
            {
                double profit = entryPrice - currentPrice;

                if (!breakevenActivated && profit >= riskAmount * BreakevenR)
                {
                    breakevenActivated = true;
                    dynamicStopPrice   = entryPrice - TickSize;
                    SetStopLoss("Short", CalculationMode.Price, dynamicStopPrice, false);

                    if (DebugMode)
                        Print(string.Format("BE Short @ {0:F2}", dynamicStopPrice));
                }

                if (EnableTrailing && breakevenActivated && profit >= riskAmount * TrailStartR)
                {
                    trailActivated = true;
                    double newStop = currentPrice + (entryATR * TrailATRDist);
                    if (newStop < dynamicStopPrice)
                    {
                        dynamicStopPrice = newStop;
                        SetStopLoss("Short", CalculationMode.Price, dynamicStopPrice, false);
                    }
                }
            }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition,
            string orderId, DateTime time)
        {
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled)
                return;

            if (marketPosition == MarketPosition.Flat)
            {
                var allTrades = SystemPerformance.AllTrades;
                if (allTrades.Count > 0)
                {
                    double pnl = allTrades[allTrades.Count - 1].ProfitCurrency;
                    dailyPnL += pnl;
                    tradesThisSession++;

                    // Enviar resultado a Python para el log de meta-labeling
                    if (UseMLFilter) LogMLOutcome(pnl);

                    if (DebugMode)
                        Print(string.Format("Exit | P&L: ${0:F2} | Diario: ${1:F2} | Trades: {2}/{3}",
                            pnl, dailyPnL, tradesThisSession, MaxTradesPerDay));
                }

                if (dailyPnL <= -MaxPerdidaDiaria)
                {
                    stopTradingToday = true;
                    Print(string.Format("APEX: Limite diario ${0:F2}. Deteniendo.", dailyPnL));
                }

                if (tradesThisSession >= MaxTradesPerDay)
                {
                    stopTradingToday = true;
                    if (DebugMode)
                        Print(string.Format("Max trades: {0}", tradesThisSession));
                }

                entryPrice         = 0;
                entryATR           = 0;
                dynamicStopPrice   = 0;
                breakevenActivated = false;
                trailActivated     = false;
            }
        }

        #region Properties

        // === 1. SIZING ===
        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name="Contratos MNQ", Order=1, GroupName="1. Sizing")]
        public int FixedContracts { get; set; }

        [NinjaScriptProperty]
        [Range(100, 7500)]
        [Display(Name="Max Perdida Diaria ($)", Order=2, GroupName="1. Sizing")]
        public double MaxPerdidaDiaria { get; set; }

        [NinjaScriptProperty]
        [Range(1, 30)]
        [Display(Name="Max Trades Dia", Order=3, GroupName="1. Sizing")]
        public int MaxTradesPerDay { get; set; }

        // === 2. FILTROS ===
        [NinjaScriptProperty]
        [Range(10, 50)]
        [Display(Name="Minimo ADX", Order=1, GroupName="2. Filtros")]
        public double ADXThreshold { get; set; }

        [NinjaScriptProperty]
        [Range(50, 80)]
        [Display(Name="RSI Long Max", Order=2, GroupName="2. Filtros")]
        public int RSILongMax { get; set; }

        [NinjaScriptProperty]
        [Range(20, 50)]
        [Display(Name="RSI Short Min", Order=3, GroupName="2. Filtros")]
        public int RSIShortMin { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 2.0)]
        [Display(Name="Volumen Min (ratio vs SMA)", Order=4, GroupName="2. Filtros")]
        public double MinVolumeRatio { get; set; }

        // === 3. GESTION DE TRADE ===
        [NinjaScriptProperty]
        [Range(0.5, 4.0)]
        [Display(Name="Stop Loss ATR", Order=1, GroupName="3. Gestion Trade")]
        public double StopLossATR { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 5.0)]
        [Display(Name="Target R:R", Order=2, GroupName="3. Gestion Trade")]
        public double TargetRatioRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 2.0)]
        [Display(Name="Breakeven en (R)", Order=3, GroupName="3. Gestion Trade")]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Activar Trailing", Order=4, GroupName="3. Gestion Trade")]
        public bool EnableTrailing { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 3.0)]
        [Display(Name="Trail Inicio (R)", Order=5, GroupName="3. Gestion Trade")]
        public double TrailStartR { get; set; }

        [NinjaScriptProperty]
        [Range(0.3, 3.0)]
        [Display(Name="Trail Distancia (ATR)", Order=6, GroupName="3. Gestion Trade")]
        public double TrailATRDist { get; set; }

        // === 4. INDICADORES ===
        [NinjaScriptProperty]
        [Range(3, 20)]
        [Display(Name="EMA Rapida", Order=1, GroupName="4. Indicadores")]
        public int EMAFastPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(10, 50)]
        [Display(Name="EMA Lenta", Order=2, GroupName="4. Indicadores")]
        public int EMASlowPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(50, 300)]
        [Display(Name="EMA Tendencia (HTF)", Order=3, GroupName="4. Indicadores")]
        public int EMAHTFPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ATR Period", Order=4, GroupName="4. Indicadores")]
        public int ATRPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 21)]
        [Display(Name="RSI Period", Order=5, GroupName="4. Indicadores")]
        public int RSIPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(5, 30)]
        [Display(Name="ADX Period", Order=6, GroupName="4. Indicadores")]
        public int ADXPeriod { get; set; }

        // === 5. HORARIO ===
        [NinjaScriptProperty]
        [Display(Name="Bloquear CME Break (16:45-18:00 ET)", Order=1, GroupName="5. Horario ET")]
        public bool BlockGlobexBreak { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Solo Prime Hours (9:30-12:30 y 13:30-15:30 ET)", Order=2, GroupName="5. Horario ET")]
        public bool UsePrimeHoursOnly { get; set; }

        // === 6. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name="Debug Mode", Order=1, GroupName="6. Debug")]
        public bool DebugMode { get; set; }

        // === 7. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name="Activar Filtro ML (ZMQ)", Order=1, GroupName="7. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name="Puerto Python (meta_brain_bbv5.py)", Order=2, GroupName="7. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
