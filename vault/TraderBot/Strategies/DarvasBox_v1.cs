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
using NinjaTrader.Data;
using NinjaTrader.Gui;
using NinjaTrader.NinjaScript;
using NinjaTrader.NinjaScript.DrawingTools;
using NinjaTrader.NinjaScript.Indicators;
using NinjaTrader.NinjaScript.Strategies;
using NetMQ;
using NetMQ.Sockets;
#endregion

/*
 * DarvasBox_v1 — Nicolas Darvas Box Breakout
 * ─────────────────────────────────────────────
 * Concepto: precio forma un máximo local → consolida X barras sin superar ese máximo
 *           (forma una "caja") → breakout con volumen elevado = ENTRY LONG.
 *           Espejo inverso para SHORT: mínimo local → consolidación → breakdown.
 *
 * Chart recomendado: 5-min MNQ (probar también 15-min)
 * Slippage: 1 tick
 */

namespace NinjaTrader.NinjaScript.Strategies
{
    public class DarvasBox_v1 : Strategy
    {
        // ── Long box state ──
        private double longBoxTop;
        private double longBoxBottom;
        private int    longBoxStartBar;
        private bool   longBoxForming;
        private bool   longBoxConfirmed;

        // ── Short box state ──
        private double shortBoxBottom;
        private double shortBoxTop;
        private int    shortBoxStartBar;
        private bool   shortBoxForming;
        private bool   shortBoxConfirmed;

        // ── Trade state ──
        private double longStopPrice;
        private double shortStopPrice;
        private bool   longBeTriggered;
        private bool   shortBeTriggered;

        // ── Daily counter ──
        private int tradesToday;
        private int lastTradeDate;

        // ── Indicators ──
        private SMA volSma;

        // ── Timezone ──
        private TimeZoneInfo easternZone;

        // ── ML Filter ──
        private RequestSocket mlSocket      = null;
        private string        mlTradeId     = "";
        private string        mlEntryContext = "";

        protected override void OnStateChange()
        {
            if (State == State.SetDefaults)
            {
                Description  = "Darvas Box breakout v1 — consolidation box + volume confirmation";
                Name         = "DarvasBox_v1";
                Calculate    = Calculate.OnBarClose;
                EntriesPerDirection          = 1;
                EntryHandling                = EntryHandling.UniqueEntries;
                IsExitOnSessionCloseStrategy = true;
                ExitOnSessionCloseSeconds    = 30;

                BoxMinBars      = 3;
                BoxMaxBars      = 20;
                MinBoxSizeTicks = 10;
                MaxBoxSizeTicks = 80;
                TargetRR        = 3.0;
                BreakevenR      = 1.0;
                StopBufferTicks = 4;
                MaxTradesPerDay = 1;
                UseVolumeFilter = true;
                VolumePeriod    = 20;
                MinVolRatio     = 1.2;
                PrimeStart      = 93000;
                PrimeEnd        = 153000;
                AllowLong       = true;
                AllowShort      = true;
                Quantity        = 1;
                Slippage        = 1;

                // === 6. ML Filter ===
                UseMLFilter = false;
                MLPort      = 5556;
            }
            else if (State == State.DataLoaded)
            {
                easternZone = TimeZoneInfo.FindSystemTimeZoneById("Eastern Standard Time");
                volSma      = SMA(Volume, VolumePeriod);

                ResetLongBox();
                ResetShortBox();
                tradesToday      = 0;
                lastTradeDate    = 0;
                longBeTriggered  = false;
                shortBeTriggered = false;

                if (UseMLFilter)
                {
                    AsyncIO.ForceDotNet.Force();
                    mlSocket = new RequestSocket();
                    mlSocket.Connect("tcp://127.0.0.1:" + MLPort);
                    mlSocket.Options.SendTimeout    = TimeSpan.FromMilliseconds(400);
                    mlSocket.Options.ReceiveTimeout = TimeSpan.FromMilliseconds(400);
                }
            }
            else if (State == State.Terminated)
            {
                if (mlSocket != null) { try { mlSocket.Close(); } catch { } mlSocket = null; }
            }
        }

        // ── ML Filter ──────────────────────────────────────────────────────────
        private bool QueryMLFilter(int direction, int signalType)
        {
            if (mlSocket == null) return true;
            try
            {
                mlTradeId = Guid.NewGuid().ToString("N").Substring(0, 8);
                DateTime et = State == State.Realtime
                    ? TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, easternZone)
                    : Time[0];
                double volRatio = (volSma != null && volSma[0] > 0) ? Volume[0] / volSma[0] : 1.0;

                mlEntryContext = string.Format(
                    "{{\"type\":\"entry_query\",\"strategy\":\"DarvasBox_v1\"," +
                    "\"trade_id\":\"{0}\",\"direction\":{1}," +
                    "\"rsi\":50.0,\"adx\":25.0,\"vol_ratio\":{2}," +
                    "\"dist_htf\":0.0,\"ema_slope\":0.0," +
                    "\"hour\":{3},\"minute\":{4},\"day_of_week\":{5}," +
                    "\"signal_type\":{6}}}",
                    mlTradeId, direction,
                    volRatio.ToString("F3", System.Globalization.CultureInfo.InvariantCulture),
                    et.Hour, et.Minute, (int)et.DayOfWeek, signalType);

                mlSocket.SendFrame(mlEntryContext);
                string resp = mlSocket.ReceiveFrameString();

                int idx = resp.IndexOf("\"allow\":");
                if (idx >= 0)
                {
                    char c = resp[idx + 8];
                    return c == '1';
                }
                return true;
            }
            catch { return true; }
        }

        private void LogMLOutcome(double pnl)
        {
            if (mlSocket == null || mlTradeId == "") return;
            try
            {
                string msg = string.Format(
                    "{{\"type\":\"outcome\",\"strategy\":\"DarvasBox_v1\"," +
                    "\"trade_id\":\"{0}\",\"pnl\":{1}}}",
                    mlTradeId,
                    pnl.ToString("F2", System.Globalization.CultureInfo.InvariantCulture));
                mlSocket.SendFrame(msg);
                mlSocket.ReceiveFrameString();
                mlTradeId = "";
            }
            catch { mlTradeId = ""; }
        }

        protected override void OnExecutionUpdate(Execution execution, string executionId,
            double price, int quantity, MarketPosition marketPosition,
            string orderId, DateTime time)
        {
            if (!UseMLFilter) return;
            if (execution.Order == null || execution.Order.OrderState != OrderState.Filled) return;
            if (marketPosition == MarketPosition.Flat)
            {
                var all = SystemPerformance.AllTrades;
                if (all.Count > 0)
                    LogMLOutcome(all[all.Count - 1].ProfitCurrency);
            }
        }

        protected override void OnBarUpdate()
        {
            if (CurrentBar < Math.Max(BoxMaxBars, VolumePeriod) + 2)
                return;

            // ── Daily reset ──
            int etDate = GetEtDate();
            if (etDate != lastTradeDate)
            {
                tradesToday   = 0;
                lastTradeDate = etDate;
                ResetLongBox();
                ResetShortBox();
            }

            // ── Manage open position (sin restricción horaria en salidas) ──
            if (Position.MarketPosition == MarketPosition.Long)  { ManageLong();  return; }
            if (Position.MarketPosition == MarketPosition.Short) { ManageShort(); return; }

            // ── Hora prime + trade count ──
            int  etTime  = GetEtTime();
            bool inPrime = etTime >= PrimeStart && etTime <= PrimeEnd;
            if (!inPrime || tradesToday >= MaxTradesPerDay)
                return;

            bool volOk = !UseVolumeFilter || Volume[0] >= volSma[0] * MinVolRatio;

            // ═══════════════════════════════════════════════
            // LONG BOX
            // ═══════════════════════════════════════════════
            if (AllowLong)
            {
                if (!longBoxForming)
                {
                    // Detectar máximo local (más alto que los últimos BoxMinBars)
                    bool isLocalHigh = true;
                    int  lb = Math.Min(BoxMinBars, CurrentBar - 1);
                    for (int i = 1; i <= lb; i++)
                        if (High[i] >= High[0]) { isLocalHigh = false; break; }

                    if (isLocalHigh)
                    {
                        longBoxTop      = High[0];
                        longBoxBottom   = Low[0];
                        longBoxStartBar = CurrentBar;
                        longBoxForming  = true;
                        longBoxConfirmed = false;
                    }
                }
                else  // box en formación
                {
                    // Prioridad 1: breakout sobre caja confirmada
                    if (longBoxConfirmed && Close[0] > longBoxTop && volOk)
                    {
                        double sl   = longBoxBottom - StopBufferTicks * TickSize;
                        double dist = Close[0] - sl;
                        double tp   = Close[0] + dist * TargetRR;

                        longStopPrice   = sl;
                        longBeTriggered = false;

                        if (UseMLFilter && !QueryMLFilter(1, 0)) { ResetLongBox(); return; }
                        EnterLong(Quantity, "Long");
                        SetStopLoss("Long",    CalculationMode.Price, sl, false);
                        SetProfitTarget("Long", CalculationMode.Price, tp);
                        tradesToday++;
                        ResetLongBox();
                    }
                    // Prioridad 2: nuevo máximo → reiniciar caja
                    else if (High[0] > longBoxTop)
                    {
                        longBoxTop       = High[0];
                        longBoxBottom    = Low[0];
                        longBoxStartBar  = CurrentBar;
                        longBoxConfirmed = false;
                    }
                    // Prioridad 3: caja expiró
                    else if (CurrentBar - longBoxStartBar > BoxMaxBars)
                    {
                        ResetLongBox();
                    }
                    // Prioridad 4: consolidando — actualizar fondo y verificar confirmación
                    else
                    {
                        longBoxBottom = Math.Min(longBoxBottom, Low[0]);
                        double boxW   = (longBoxTop - longBoxBottom) / TickSize;

                        if (boxW > MaxBoxSizeTicks)
                            ResetLongBox();
                        else if (boxW >= MinBoxSizeTicks
                              && CurrentBar - longBoxStartBar >= BoxMinBars)
                            longBoxConfirmed = true;
                    }
                }
            }

            // ═══════════════════════════════════════════════
            // SHORT BOX
            // ═══════════════════════════════════════════════
            if (AllowShort)
            {
                if (!shortBoxForming)
                {
                    // Detectar mínimo local
                    bool isLocalLow = true;
                    int  lb = Math.Min(BoxMinBars, CurrentBar - 1);
                    for (int i = 1; i <= lb; i++)
                        if (Low[i] <= Low[0]) { isLocalLow = false; break; }

                    if (isLocalLow)
                    {
                        shortBoxBottom   = Low[0];
                        shortBoxTop      = High[0];
                        shortBoxStartBar = CurrentBar;
                        shortBoxForming  = true;
                        shortBoxConfirmed = false;
                    }
                }
                else
                {
                    // Prioridad 1: breakdown bajo caja confirmada
                    if (shortBoxConfirmed && Close[0] < shortBoxBottom && volOk)
                    {
                        double sl   = shortBoxTop + StopBufferTicks * TickSize;
                        double dist = sl - Close[0];
                        double tp   = Close[0] - dist * TargetRR;

                        shortStopPrice   = sl;
                        shortBeTriggered = false;

                        if (UseMLFilter && !QueryMLFilter(-1, 0)) { ResetShortBox(); return; }
                        EnterShort(Quantity, "Short");
                        SetStopLoss("Short",    CalculationMode.Price, sl, false);
                        SetProfitTarget("Short", CalculationMode.Price, tp);
                        tradesToday++;
                        ResetShortBox();
                    }
                    // Prioridad 2: nuevo mínimo → reiniciar caja
                    else if (Low[0] < shortBoxBottom)
                    {
                        shortBoxBottom   = Low[0];
                        shortBoxTop      = High[0];
                        shortBoxStartBar = CurrentBar;
                        shortBoxConfirmed = false;
                    }
                    // Prioridad 3: expiró
                    else if (CurrentBar - shortBoxStartBar > BoxMaxBars)
                    {
                        ResetShortBox();
                    }
                    // Prioridad 4: consolidando
                    else
                    {
                        shortBoxTop = Math.Max(shortBoxTop, High[0]);
                        double boxW = (shortBoxTop - shortBoxBottom) / TickSize;

                        if (boxW > MaxBoxSizeTicks)
                            ResetShortBox();
                        else if (boxW >= MinBoxSizeTicks
                              && CurrentBar - shortBoxStartBar >= BoxMinBars)
                            shortBoxConfirmed = true;
                    }
                }
            }
        }

        // ─────────────────────────────────────────
        // Position management
        // ─────────────────────────────────────────
        private void ManageLong()
        {
            if (BreakevenR <= 0 || longBeTriggered) return;
            double entry   = Position.AveragePrice;
            double beLevel = entry + (entry - longStopPrice) * BreakevenR;
            if (Close[0] >= beLevel)
            {
                SetStopLoss("Long", CalculationMode.Price, entry + TickSize, false);
                longBeTriggered = true;
            }
        }

        private void ManageShort()
        {
            if (BreakevenR <= 0 || shortBeTriggered) return;
            double entry   = Position.AveragePrice;
            double beLevel = entry - (shortStopPrice - entry) * BreakevenR;
            if (Close[0] <= beLevel)
            {
                SetStopLoss("Short", CalculationMode.Price, entry - TickSize, false);
                shortBeTriggered = true;
            }
        }

        // ─────────────────────────────────────────
        // Helpers
        // ─────────────────────────────────────────
        private void ResetLongBox()
        {
            longBoxForming   = false;
            longBoxConfirmed = false;
            longBoxTop       = double.MinValue;
            longBoxBottom    = double.MaxValue;
            longBoxStartBar  = 0;
        }

        private void ResetShortBox()
        {
            shortBoxForming   = false;
            shortBoxConfirmed = false;
            shortBoxBottom    = double.MaxValue;
            shortBoxTop       = double.MinValue;
            shortBoxStartBar  = 0;
        }

        private int GetEtTime()
        {
            if (State == State.Historical)
                return ToTime(Time[0]);
            return ToTime(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, easternZone));
        }

        private int GetEtDate()
        {
            if (State == State.Historical)
                return ToDay(Time[0]);
            return ToDay(TimeZoneInfo.ConvertTimeFromUtc(DateTime.UtcNow, easternZone));
        }

        // ─────────────────────────────────────────
        // Properties
        // ─────────────────────────────────────────
        #region Properties

        [NinjaScriptProperty]
        [Range(1, 50)]
        [Display(Name = "Box Min Bars", Description = "Barras de consolidación mínimas para confirmar caja",
                 GroupName = "1. Darvas Box", Order = 1)]
        public int BoxMinBars { get; set; }

        [NinjaScriptProperty]
        [Range(5, 200)]
        [Display(Name = "Box Max Bars", Description = "Barras máximas antes de que la caja expire",
                 GroupName = "1. Darvas Box", Order = 2)]
        public int BoxMaxBars { get; set; }

        [NinjaScriptProperty]
        [Range(1, 500)]
        [Display(Name = "Min Box Size (ticks)", Description = "Altura mínima de la caja — evita micro-consolidaciones",
                 GroupName = "1. Darvas Box", Order = 3)]
        public int MinBoxSizeTicks { get; set; }

        [NinjaScriptProperty]
        [Range(10, 5000)]
        [Display(Name = "Max Box Size (ticks)", Description = "Altura máxima — evita cajas demasiado anchas",
                 GroupName = "1. Darvas Box", Order = 4)]
        public int MaxBoxSizeTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1.0, 15.0)]
        [Display(Name = "Target R:R", GroupName = "2. Risk Management", Order = 1)]
        public double TargetRR { get; set; }

        [NinjaScriptProperty]
        [Range(0.0, 5.0)]
        [Display(Name = "Breakeven R", Description = "Mueve SL a entry cuando precio llega a entry + X×R  (0 = OFF)",
                 GroupName = "2. Risk Management", Order = 2)]
        public double BreakevenR { get; set; }

        [NinjaScriptProperty]
        [Range(0, 50)]
        [Display(Name = "Stop Buffer (ticks)", Description = "Ticks más allá del borde de la caja para el SL",
                 GroupName = "2. Risk Management", Order = 3)]
        public int StopBufferTicks { get; set; }

        [NinjaScriptProperty]
        [Range(1, 20)]
        [Display(Name = "Max Trades/Day", GroupName = "3. Trade Management", Order = 1)]
        public int MaxTradesPerDay { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Long", GroupName = "3. Trade Management", Order = 2)]
        public bool AllowLong { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Allow Short", GroupName = "3. Trade Management", Order = 3)]
        public bool AllowShort { get; set; }

        [NinjaScriptProperty]
        [Range(1, 100)]
        [Display(Name = "Quantity", GroupName = "3. Trade Management", Order = 4)]
        public int Quantity { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Use Volume Filter", GroupName = "4. Volume Filter", Order = 1)]
        public bool UseVolumeFilter { get; set; }

        [NinjaScriptProperty]
        [Range(3, 200)]
        [Display(Name = "Volume MA Period", GroupName = "4. Volume Filter", Order = 2)]
        public int VolumePeriod { get; set; }

        [NinjaScriptProperty]
        [Range(0.1, 10.0)]
        [Display(Name = "Min Volume Ratio", Description = "Barra de breakout debe tener Volume ≥ X × SMA(Volume)",
                 GroupName = "4. Volume Filter", Order = 3)]
        public double MinVolRatio { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime Start (ET HHMMSS)", GroupName = "5. Trading Hours", Order = 1)]
        public int PrimeStart { get; set; }

        [NinjaScriptProperty]
        [Display(Name = "Prime End (ET HHMMSS)", GroupName = "5. Trading Hours", Order = 2)]
        public int PrimeEnd { get; set; }

        // === 6. ML FILTER ===
        [NinjaScriptProperty]
        [Display(Name = "Activar Filtro ML", Order = 1, GroupName = "6. ML Filter")]
        public bool UseMLFilter { get; set; }

        [NinjaScriptProperty]
        [Range(1024, 65535)]
        [Display(Name = "Puerto ZMQ", Order = 2, GroupName = "6. ML Filter")]
        public int MLPort { get; set; }

        #endregion
    }
}
