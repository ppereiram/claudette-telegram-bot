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
    // ====================================================================
    // SuperTrendWave v1.1
    //
    // CAMBIOS vs v1.0:
    //   + Filtro de horas prime (UsePrimeHoursOnly)
    //     - Sesion mañana:  9:30 - 12:00 EST (mayor volumen y momentum)
    //     - Sesion tarde:  13:30 - 15:30 EST (vuelta del almuerzo)
    //     - Configurable via parametros para adaptar a cualquier horario
    //   + Proteccion de perdida diaria (MaxDailyLoss)
    //     - Detiene nuevas entradas cuando se alcanza el limite
    //     - Reset automatico cada sesion
    //     - Usa SystemPerformance para P&L preciso
    //   + Hora de corte (StopNewEntriesTime)
    //     - No abre nuevas posiciones despues de X hora
    //     - Posiciones abiertas se cierran al ExitOnSessionClose
    //
    // Parametros de partida sugeridos (5-min chart MNQ):
    //   ATR=14, Mult=3.0, MaxPyramid=5, MinBars=3, Vol=1.5x
    //   UsePrimeHoursOnly=true, MaxDailyLoss=300 (cuenta Apex $7500 DD)
    // ====================================================================
    public class SuperTrendWave : Strategy
    {
        // ===== TIMEZONE =====
        private static readonly TimeZoneInfo EasternZone =
            TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");

        // ===== SUPERTREND (calculado internamente) =====
        private Series<double> stUpper;
        private Series<double> stLower;
        private Series<double> stLine;
        private Series<int>    stDir;   // 1=alcista, -1=bajista

        // ===== INDICADORES =====
        private ATR atr;
        private SMA volumeSMA;

        // ===== ML Filter (ZMQ) =====
        private RequestSocket mlSocket    = null;
        private string        mlTradeId   = "";
        private string        mlEntryContext = "";

        // ===== ESTADO DEL TRADE =====
        private int  pyramidCount     = 0;
        private int  barsSinceEntry   = 0;
        private bool hadPullback      = false;
        private int  prevDir          = 0;

        // ===== CONTROL DIARIO =====
        private DateTime lastSessionDate  = DateTime.MinValue;
        private double   dailyRealizedPnL = 0;
        private bool     maxLossHit       = false;

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description = "SuperTrend Wave Rider v1.1 — trailing + piramidacion + horas prime + proteccion diaria";
                Name        = "SuperTrendWave";

                Calculate                              = Calculate.OnBarClose;
                EntriesPerDirection                    = 5;
                EntryHandling                          = EntryHandling.AllEntries;
                IsExitOnSessionCloseStrategy           = true;
                ExitOnSessionCloseSeconds              = 30;
                StopTargetHandling                     = StopTargetHandling.ByStrategyPosition;
                MaximumBarsLookBack                    = MaximumBarsLookBack.TwoHundredFiftySix;
                BarsRequiredToTrade                    = 20;
                Slippage                               = 1;
                StartBehavior                          = StartBehavior.WaitUntilFlat;
                TimeInForce                            = TimeInForce.Gtc;
                TraceOrders                            = false;
                RealtimeErrorHandling                  = RealtimeErrorHandling.StopCancelClose;
                IsInstantiatedOnEachOptimizationIteration = true;

                // === 1. RIESGO ===
                Contratos             = 5;
                AtrPeriod             = 14;
                SuperTrendMult        = 3.0;
                MaxDailyLoss          = 300;   // $0 = desactivado. Para Apex usar ~$200-300

                // === 2. PIRAMIDE ===
                AllowPyramid          = true;
                MaxPyramidLevels      = 5;
                MinBarsBetweenPyramid = 3;

                // === 3. FILTROS ===
                MinVolumeMultiplier   = 1.5;
                AllowLong             = true;
                AllowShort            = false; // MNQ estructuralmente alcista

                // === 4. HORARIO (siempre ET — GetEtTime() maneja backtest vs live) ===
                UsePrimeHoursOnly     = true;
                // Manana: 9:30-12:00 ET
                MorningStart          = 93000;
                MorningEnd            = 120000;
                // Tarde: 13:30-15:30 ET
                AfternoonStart        = 133000;
                AfternoonEnd          = 153000;
                // No abrir nuevas posiciones despues de las 15:45 ET
                StopNewEntriesTime    = 154500;

                // === 5. DEBUG ===
                DebugMode             = false;

                // === 6. ML FILTER ===
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                stUpper   = new Series<double>(this);
                stLower   = new Series<double>(this);
                stLine    = new Series<double>(this);
                stDir     = new Series<int>(this);

                atr       = ATR(AtrPeriod);
                volumeSMA = SMA(Volume, 20);

                // ML Filter
                if (UseMLFilter)
                {
                    try
                    {
                        AsyncIO.ForceDotNet.Force();
                        mlSocket = new RequestSocket();
                        mlSocket.Connect(string.Format("tcp://localhost:{0}", MLPort));
                        Print(string.Format("STW ML: Conectado a Python en puerto {0}", MLPort));
                    }
                    catch (Exception ex)
                    {
                        Print(string.Format("STW ML: Error al conectar ZMQ: {0}", ex.Message));
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
            // SuperTrend debe calcularse en CADA barra para construir historial
            CalculateSuperTrend();

            // No operar durante calentamiento
            if (CurrentBar < Math.Max(AtrPeriod + 5, 20))
            {
                prevDir = stDir[0];
                return;
            }

            // === RESET DIARIO ===
            if (lastSessionDate != Time[0].Date)
            {
                lastSessionDate  = Time[0].Date;
                dailyRealizedPnL = 0;
                maxLossHit       = false;

                if (DebugMode)
                    Print(string.Format("=== NUEVA SESION: {0} ===", Time[0].Date.ToShortDateString()));
            }

            // Routing principal
            if (Position.MarketPosition == MarketPosition.Long)
                ManageLong();
            else if (Position.MarketPosition == MarketPosition.Short)
                ManageShort();
            else
            {
                // Solo buscar entrada si no se alcanzo limite diario
                if (!maxLossHit)
                    CheckForEntry();
            }

            prevDir = stDir[0];
        }

        // ================================================================
        // HELPER: Obtener hora ET — consistente en backtest (Time[0]=ET) y live (UTC→ET)
        // ================================================================
        private int GetEtTime()
        {
            if (State == State.Realtime)
                return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, EasternZone));
            return ToTime(Time[0]);
        }

        // ================================================================
        // HELPER: ¿Estamos en horas prime? (params en hora CR = ET - 1h EST)
        // ================================================================
        private bool IsInPrimeHours()
        {
            if (!UsePrimeHoursOnly) return true;  // Filtro desactivado = siempre OK

            int t = GetEtTime();
            bool morning   = (t >= MorningStart   && t <= MorningEnd);
            bool afternoon = (t >= AfternoonStart  && t <= AfternoonEnd);
            return morning || afternoon;
        }

        // ================================================================
        // HELPER: ¿Podemos abrir nuevas posiciones ahora?
        // ================================================================
        private bool CanOpenNewEntry()
        {
            // Limite de perdida diaria
            if (maxLossHit) return false;

            // Hora de corte (StopNewEntriesTime en ET)
            if (GetEtTime() >= StopNewEntriesTime) return false;

            // Horas prime
            if (!IsInPrimeHours()) return false;

            return true;
        }

        // ================================================================
        // CÁLCULO SUPERTREND
        // ================================================================
        private void CalculateSuperTrend()
        {
            if (CurrentBar < 2 || atr[0] <= 0)
            {
                double safeATR = atr[0] > 0 ? atr[0] : 1;
                double mid     = (High[0] + Low[0]) / 2.0;
                stUpper[0] = mid + SuperTrendMult * safeATR;
                stLower[0] = mid - SuperTrendMult * safeATR;
                stDir[0]   = 1;
                stLine[0]  = stLower[0];
                return;
            }

            double midPrice = (High[0] + Low[0]) / 2.0;
            double basicUp  = midPrice + SuperTrendMult * atr[0];
            double basicDn  = midPrice - SuperTrendMult * atr[0];

            // Ratchet: banda superior solo baja, inferior solo sube
            stUpper[0] = (basicUp < stUpper[1] || Close[1] > stUpper[1]) ? basicUp : stUpper[1];
            stLower[0] = (basicDn > stLower[1] || Close[1] < stLower[1]) ? basicDn : stLower[1];

            if (stDir[1] == -1)
            {
                if (Close[0] > stUpper[0]) { stDir[0] = 1;  stLine[0] = stLower[0]; }
                else                        { stDir[0] = -1; stLine[0] = stUpper[0]; }
            }
            else
            {
                if (Close[0] < stLower[0]) { stDir[0] = -1; stLine[0] = stUpper[0]; }
                else                        { stDir[0] = 1;  stLine[0] = stLower[0]; }
            }
        }

        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                int etTime  = GetEtTime();
                int hour    = etTime / 10000;
                int minute  = (etTime % 10000) / 100;
                int dow     = (int)Time[0].DayOfWeek;
                double volRatio = volumeSMA[0] > 0 ? Volume[0] / volumeSMA[0] : 1.0;

                mlTradeId = string.Format("STW_{0}_{1}", direction > 0 ? "L" : "S",
                    Time[0].ToString("yyyyMMdd_HHmmss"));

                string json = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"SuperTrendWave\",\"trade_id\":\"{0}\"," +
                    "\"direction\":{1},\"rsi\":50.0,\"adx\":25.0," +
                    "\"vol_ratio\":{2:F3},\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{3},\"minute\":{4},\"day_of_week\":{5},\"signal_type\":{6}}}",
                    mlTradeId, direction, volRatio, hour, minute, dow, signalType);

                mlEntryContext = json;
                mlSocket.SendFrame(json);

                string response;
                bool received = mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out response);
                if (!received) { Print("STW ML: Timeout — permitiendo trade"); return true; }

                bool allow = response.Contains("\"allow\":1") || response.Contains("\"allow\": 1");
                if (!allow) Print(string.Format("STW ML bloqueado [{0}]: {1}", mlTradeId, response));
                return allow;
            }
            catch (Exception ex)
            {
                Print(string.Format("STW ML Error: {0} — permitiendo trade", ex.Message));
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
                    "{{\"type\":\"outcome\",\"strategy\":\"SuperTrendWave\",\"id\":\"{0}\",\"pnl\":{1:F2},\"result\":{2}}}",
                    mlTradeId, pnl, result);
                mlSocket.SendFrame(json);
                string ack;
                mlSocket.TryReceiveFrameString(System.TimeSpan.FromMilliseconds(500), out ack);
                mlTradeId = "";
            }
            catch (Exception ex) { Print(string.Format("STW ML outcome error: {0}", ex.Message)); }
        }

        // ================================================================
        // ENTRADA INICIAL
        // ================================================================
        private void CheckForEntry()
        {
            // Verificar todas las condiciones de horario y limites
            if (!CanOpenNewEntry()) return;

            bool volOK         = Volume[0] >= volumeSMA[0] * MinVolumeMultiplier;
            bool stFlippedBull = stDir[0] == 1  && prevDir == -1;
            bool stFlippedBear = stDir[0] == -1 && prevDir == 1;

            if (AllowLong && stFlippedBull && volOK && Close[0] > Open[0])
            {
                if (UseMLFilter && !QueryMLFilter(1, 0)) return;
                EnterLong(Contratos, "WAVE");
                SetStopLoss(CalculationMode.Price, stLine[0]);
                pyramidCount   = 1;
                barsSinceEntry = 0;
                hadPullback    = false;

                if (DebugMode)
                    Print(string.Format("{0} LONG ENTRADA | ST={1:F2} | Vol={2:F0}/{3:F0}",
                        Time[0], stLine[0], Volume[0], volumeSMA[0]));
            }
            else if (AllowShort && stFlippedBear && volOK && Close[0] < Open[0])
            {
                if (UseMLFilter && !QueryMLFilter(-1, 0)) return;
                EnterShort(Contratos, "WAVE");
                SetStopLoss(CalculationMode.Price, stLine[0]);
                pyramidCount   = 1;
                barsSinceEntry = 0;
                hadPullback    = false;

                if (DebugMode)
                    Print(string.Format("{0} SHORT ENTRADA | ST={1:F2} | Vol={2:F0}/{3:F0}",
                        Time[0], stLine[0], Volume[0], volumeSMA[0]));
            }
        }

        // ================================================================
        // GESTIÓN LONG
        // ================================================================
        private void ManageLong()
        {
            barsSinceEntry++;

            // SALIDA: SuperTrend flip a bajista
            if (stDir[0] == -1)
            {
                ExitLong();
                pyramidCount = 0;
                hadPullback  = false;
                if (DebugMode)
                    Print(string.Format("{0} LONG EXIT | ST flip | Close={1:F2}", Time[0], Close[0]));
                return;
            }

            // TRAILING: actualizar stop a SuperTrend (solo sube para longs)
            SetStopLoss(CalculationMode.Price, stLine[0]);

            // PIRAMIDE: solo si no se alcanzo limite y estamos en horas OK
            if (!AllowPyramid || pyramidCount >= MaxPyramidLevels) return;
            if (barsSinceEntry < MinBarsBetweenPyramid) return;
            if (!CanOpenNewEntry()) return;   // Respeta horas prime y limite diario

            if (!hadPullback && Low[0] < Low[1])
                hadPullback = true;

            if (hadPullback)
            {
                bool newImpulse = Close[0] > High[1]
                               && Close[0] > Open[0]
                               && Close[0] > stLine[0];
                bool volOK = Volume[0] >= volumeSMA[0] * MinVolumeMultiplier;

                if (newImpulse && volOK)
                {
                    EnterLong(Contratos, "WAVE_P" + pyramidCount);
                    pyramidCount++;
                    barsSinceEntry = 0;
                    hadPullback    = false;

                    if (DebugMode)
                        Print(string.Format("{0}   PIRAMIDE LONG #{1} | ST={2:F2}",
                            Time[0], pyramidCount, stLine[0]));
                }
            }
        }

        // ================================================================
        // GESTIÓN SHORT
        // ================================================================
        private void ManageShort()
        {
            barsSinceEntry++;

            // SALIDA: SuperTrend flip a alcista
            if (stDir[0] == 1)
            {
                ExitShort();
                pyramidCount = 0;
                hadPullback  = false;
                if (DebugMode)
                    Print(string.Format("{0} SHORT EXIT | ST flip | Close={1:F2}", Time[0], Close[0]));
                return;
            }

            SetStopLoss(CalculationMode.Price, stLine[0]);

            if (!AllowPyramid || pyramidCount >= MaxPyramidLevels) return;
            if (barsSinceEntry < MinBarsBetweenPyramid) return;
            if (!CanOpenNewEntry()) return;

            if (!hadPullback && High[0] > High[1])
                hadPullback = true;

            if (hadPullback)
            {
                bool newImpulse = Close[0] < Low[1]
                               && Close[0] < Open[0]
                               && Close[0] < stLine[0];
                bool volOK = Volume[0] >= volumeSMA[0] * MinVolumeMultiplier;

                if (newImpulse && volOK)
                {
                    EnterShort(Contratos, "WAVE_P" + pyramidCount);
                    pyramidCount++;
                    barsSinceEntry = 0;
                    hadPullback    = false;

                    if (DebugMode)
                        Print(string.Format("{0}   PIRAMIDE SHORT #{1} | ST={2:F2}",
                            Time[0], pyramidCount, stLine[0]));
                }
            }
        }

        // ================================================================
        // TRACKING DE P&L DIARIO (para MaxDailyLoss)
        // Se llama cuando una orden se ejecuta — usa P&L real del sistema
        // ================================================================
        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition, string orderId, DateTime time)
        {
            if (MaxDailyLoss <= 0) return;          // Proteccion diaria desactivada
            if (execution.Order == null) return;

            // Solo contabilizar cuando se CIERRA una posicion (marketPosition == Flat)
            // En piramidacion, la posicion pasa a Flat cuando el ULTIMO exit se ejecuta
            if (marketPosition == MarketPosition.Flat)
            {
                // Calcular P&L de este trade: (precio salida - precio entrada) * contratos * punto_valor
                // Usamos SystemPerformance para precision — funciona bien aqui porque
                // SuperTrendWave NO tiene el "filtro accidental" de las otras estrategias
                if (SystemPerformance.AllTrades.Count > 0)
                {
                    var lastTrade = SystemPerformance.AllTrades[SystemPerformance.AllTrades.Count - 1];
                    if (lastTrade.Exit.Time.Date == time.Date)
                    {
                        dailyRealizedPnL += lastTrade.ProfitCurrency;

                        // ML outcome
                        if (UseMLFilter) LogMLOutcome(lastTrade.ProfitCurrency);

                        if (DebugMode)
                            Print(string.Format("{0} P&L hoy: ${1:F2} | Limite: ${2:F2}",
                                time, dailyRealizedPnL, -MaxDailyLoss));

                        if (dailyRealizedPnL <= -MaxDailyLoss)
                        {
                            maxLossHit = true;
                            Print(string.Format("*** LIMITE PERDIDA DIARIA ALCANZADO: ${0:F2} ***",
                                dailyRealizedPnL));
                        }
                    }
                }
            }
        }

        #region Properties

        // === 1. RIESGO ===
        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name="Contratos por entrada", Order=1, GroupName="1. Riesgo")]
        public int Contratos { get; set; }

        [NinjaScriptProperty]
        [Range(3, 30)]
        [Display(Name="ATR Periodo", Order=2, GroupName="1. Riesgo")]
        public int AtrPeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.5, 8.0)]
        [Display(Name="SuperTrend Multiplicador ATR", Order=3, GroupName="1. Riesgo")]
        public double SuperTrendMult { get; set; }

        [NinjaScriptProperty]
        [Range(0, 5000)]
        [Display(Name="Max Perdida Diaria $ (0=OFF)", Order=4, GroupName="1. Riesgo")]
        public double MaxDailyLoss { get; set; }

        // === 2. PIRAMIDE ===
        [NinjaScriptProperty]
        [Display(Name="Activar Piramide", Order=1, GroupName="2. Piramide")]
        public bool AllowPyramid { get; set; }

        [NinjaScriptProperty]
        [Range(1, 5)]
        [Display(Name="Max Niveles Piramide", Order=2, GroupName="2. Piramide")]
        public int MaxPyramidLevels { get; set; }

        [NinjaScriptProperty]
        [Range(1, 15)]
        [Display(Name="Min Barras Entre Piramide", Order=3, GroupName="2. Piramide")]
        public int MinBarsBetweenPyramid { get; set; }

        // === 3. FILTROS ===
        [NinjaScriptProperty]
        [Range(0.0, 3.0)]
        [Display(Name="Vol Minimo (x SMA20)", Order=1, GroupName="3. Filtros")]
        public double MinVolumeMultiplier { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Long", Order=2, GroupName="3. Filtros")]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name="Allow Short", Order=3, GroupName="3. Filtros")]
        public bool AllowShort { get; set; }

        // === 4. HORARIO ===
        [NinjaScriptProperty]
        [Display(Name="Solo Horas Prime", Order=1, GroupName="4. Horario")]
        public bool UsePrimeHoursOnly { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Manana: Inicio (HHMMSS)", Order=2, GroupName="4. Horario")]
        public int MorningStart { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Manana: Fin (HHMMSS)", Order=3, GroupName="4. Horario")]
        public int MorningEnd { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Tarde: Inicio (HHMMSS)", Order=4, GroupName="4. Horario")]
        public int AfternoonStart { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Tarde: Fin (HHMMSS)", Order=5, GroupName="4. Horario")]
        public int AfternoonEnd { get; set; }

        [NinjaScriptProperty]
        [Range(0, 235959)]
        [Display(Name="Corte: No nuevas entradas despues de (HHMMSS)", Order=6, GroupName="4. Horario")]
        public int StopNewEntriesTime { get; set; }

        // === 5. DEBUG ===
        [NinjaScriptProperty]
        [Display(Name="Debug Mode (Output Window)", Order=1, GroupName="5. Debug")]
        public bool DebugMode { get; set; }

        // === 6. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name="Activar Filtro ML (ZMQ)", Order=1, GroupName="6. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(5000, 9999)]
        [Display(Name="Puerto Python (meta_brain.py)", Order=2, GroupName="6. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
