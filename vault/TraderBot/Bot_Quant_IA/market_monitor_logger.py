"""
market_monitor_logger.py
========================
Graba el contexto de mercado diario — MODO OBSERVACION (Marzo 2026)
Corre cada dia despues del cierre (4:30 PM ET)

Captura:
  - MAREA  (1D / 4H): tendencia macro
  - MAR    (1H / 30M): estado intraday
  - CHOPPY (15M):      Choppiness Index
  - tide_score: -3 (full bear) -> +3 (full bull)
  - sea_state: calm / moderate / rough
  - swim_ok: vale la pena operar ese dia?
  - market_breadth_score: confirmacion ES/YM/RTY vs NQ (-3 -> +3)
  - multi_osc_score: consenso RSI+MFI+Stoch (-3 -> +3)
  - macro_context: VIX + Fear&Greed + Calendario economico (Modulo 3)

Uso:
  python market_monitor_logger.py
  (o doble click en run_monitor.bat)

Output: market_logs/YYYY-MM-DD.json
"""

import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import requests
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── Configuracion NQ ──────────────────────────────────────────────────────────
TICKER     = "NQ=F"
LOG_DIR    = os.path.join(os.path.dirname(__file__), "market_logs")
EMA_PERIOD = 21
CI_PERIOD  = 14

WEIGHTS  = {"1D": 3.0, "4H": 2.0, "1H": 1.5, "30M": 1.0}
MAX_SCORE = sum(WEIGHTS.values())   # 7.5

BREADTH_TICKERS = {
    "ES":  "ES=F",
    "YM":  "YM=F",
    "RTY": "RTY=F",
}

OSC_OB = 70
OSC_OS = 30

# ── Configuracion Macro (Modulo 3) ────────────────────────────────────────────
VIX_ELEVATED        = 20
VIX_HIGH            = 25
VIX_EXTREME         = 30
NO_TRADE_WINDOW_MIN = 30   # minutos antes/despues de evento high-impact
FED_WINDOW_MIN      = 60   # ventana extra para eventos Fed
FED_KEYWORDS        = ["fed", "fomc", "powell", "federal reserve", "monetary policy"]


# ── Helpers: Tendencia ────────────────────────────────────────────────────────
def ema_slope(series: pd.Series, period: int = EMA_PERIOD, lookback: int = 3) -> int:
    if len(series) < period + lookback:
        return 0
    ema = series.ewm(span=period, adjust=False).mean()
    slope = ema.iloc[-1] - ema.iloc[-lookback]
    threshold = series.std() * 0.005
    if slope > threshold:
        return 1
    if slope < -threshold:
        return -1
    return 0


def choppiness_index(high, low, close, period: int = CI_PERIOD) -> float:
    if len(close) < period + 1:
        return 50.0
    tr = pd.concat([
        high - low,
        (high - close.shift(1)).abs(),
        (low  - close.shift(1)).abs()
    ], axis=1).max(axis=1)
    sum_atr  = tr.rolling(period).sum()
    hh       = high.rolling(period).max()
    ll       = low.rolling(period).min()
    range_hl = (hh - ll).replace(0, np.nan)
    ci = 100 * np.log10(sum_atr / range_hl) / np.log10(period)
    val = ci.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


# ── Helpers: Osciladores ──────────────────────────────────────────────────────
def calc_rsi(close, period: int = 14) -> float:
    if len(close) < period + 1:
        return 50.0
    delta    = close.diff()
    gain     = delta.where(delta > 0, 0.0)
    loss     = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


def calc_mfi(high, low, close, volume, period: int = 14) -> float:
    if len(close) < period + 1:
        return 50.0
    tp      = (high + low + close) / 3
    rmf     = tp * volume
    pos     = rmf.where(tp > tp.shift(1), 0.0)
    neg     = rmf.where(tp <= tp.shift(1), 0.0)
    pos_sum = pos.rolling(period).sum()
    neg_sum = neg.rolling(period).sum()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + mfr))
    val = mfi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


def calc_stoch(high, low, close, period: int = 14) -> float:
    if len(close) < period:
        return 50.0
    ll  = low.rolling(period).min()
    hh  = high.rolling(period).max()
    rng = (hh - ll).replace(0, np.nan)
    k   = 100 * (close - ll) / rng
    val = k.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


def osc_state(value: float, ob: int = OSC_OB, os_: int = OSC_OS) -> int:
    if value >= ob:
        return -1
    if value <= os_:
        return +1
    return 0


# ── Helpers: Datos ────────────────────────────────────────────────────────────
def get_ohlcv(ticker: str, interval: str, days_back: int) -> pd.DataFrame:
    end   = datetime.utcnow()
    start = end - timedelta(days=days_back)
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                     end=end.strftime("%Y-%m-%d"),
                     interval=interval, progress=False, auto_adjust=True)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.dropna()


def sea_state_label(ci: float) -> str:
    if ci < 38.2:
        return "calm"
    if ci < 61.8:
        return "moderate"
    return "rough"


# ── Modulo: Market Breadth ────────────────────────────────────────────────────
def compute_market_breadth(nq_trend: int) -> dict:
    breadth_slopes = {}
    trend_labels   = {1: "bull", -1: "bear", 0: "neutral"}

    for name, ticker in BREADTH_TICKERS.items():
        try:
            df = get_ohlcv(ticker, "1d", 365)
            if len(df) < EMA_PERIOD + 5:
                breadth_slopes[name] = 0
                continue
            breadth_slopes[name] = ema_slope(df["Close"])
            print(f"  [{name}] EMA slope = {trend_labels[breadth_slopes[name]]}")
        except Exception as e:
            print(f"  [{name}] ERROR: {e} -> neutral")
            breadth_slopes[name] = 0

    breadth_score     = sum(breadth_slopes.values())
    diverging         = [k for k, v in breadth_slopes.items() if v != nq_trend and v != 0]
    breadth_alignment = (breadth_score != 0) and (
        (nq_trend > 0 and breadth_score > 0) or
        (nq_trend < 0 and breadth_score < 0)
    )

    return {
        "market_breadth_score": breadth_score,
        "breadth_alignment":    breadth_alignment,
        "breadth_divergence":   diverging,
        "breadth_ES":           breadth_slopes.get("ES",  0),
        "breadth_YM":           breadth_slopes.get("YM",  0),
        "breadth_RTY":          breadth_slopes.get("RTY", 0),
    }


# ── Modulo: Multi-Oscillator Consensus ───────────────────────────────────────
def compute_multi_osc(df_1d: pd.DataFrame) -> dict:
    if len(df_1d) < 20:
        return {
            "rsi_1d": 50.0, "mfi_1d": 50.0, "stoch_1d": 50.0,
            "multi_osc_score": 0, "multi_osc_overlap": False,
            "multi_osc_label": "neutral"
        }

    rsi_val   = calc_rsi(df_1d["Close"])
    mfi_val   = calc_mfi(df_1d["High"], df_1d["Low"], df_1d["Close"], df_1d["Volume"])
    stoch_val = calc_stoch(df_1d["High"], df_1d["Low"], df_1d["Close"])

    rsi_st   = osc_state(rsi_val)
    mfi_st   = osc_state(mfi_val)
    stoch_st = osc_state(stoch_val)

    score   = rsi_st + mfi_st + stoch_st
    overlap = abs(score) >= 2

    if score >= 2:
        label = "oversold_consensus"
    elif score <= -2:
        label = "overbought_consensus"
    else:
        label = "neutral"

    print(f"  [OSC] RSI={rsi_val:.1f}({rsi_st:+d}) "
          f"MFI={mfi_val:.1f}({mfi_st:+d}) "
          f"Stoch={stoch_val:.1f}({stoch_st:+d}) "
          f"-> score={score:+d} {label}")

    return {
        "rsi_1d":            rsi_val,
        "mfi_1d":            mfi_val,
        "stoch_1d":          stoch_val,
        "multi_osc_score":   score,
        "multi_osc_overlap": overlap,
        "multi_osc_label":   label,
    }


# ── Modulo 3: Macro Context ───────────────────────────────────────────────────
def get_vix() -> dict:
    """VIX via yfinance — mismo mecanismo que NQ."""
    try:
        hist = yf.download("^VIX", period="5d", interval="1d",
                           progress=False, auto_adjust=True)
        hist.columns = [c[0] if isinstance(c, tuple) else c for c in hist.columns]
        hist = hist.dropna()
        if len(hist) < 2:
            raise ValueError("insuficiente data")

        vix_val  = round(float(hist["Close"].iloc[-1]), 2)
        vix_prev = round(float(hist["Close"].iloc[-2]), 2)

        if vix_val >= VIX_EXTREME:    category = "EXTREME"
        elif vix_val >= VIX_HIGH:     category = "HIGH"
        elif vix_val >= VIX_ELEVATED: category = "ELEVATED"
        else:                          category = "NORMAL"

        return {
            "value":      vix_val,
            "prev_close": vix_prev,
            "change":     round(vix_val - vix_prev, 2),
            "category":   category
        }
    except Exception as e:
        print(f"  [VIX] Error: {e} -> usando defaults")
        return {"value": None, "prev_close": None, "change": None, "category": "unknown"}


def get_fear_greed() -> dict:
    """
    Fear & Greed Index.
    Fuente primaria: CNN (endpoint interno, estable desde 2020).
    Fallback: Alternative.me (API publica oficial).
    """
    # --- Fuente primaria: CNN ---
    try:
        url  = "https://production.dataviz.cnn.io/index/fearandgreed/graphdata"
        resp = requests.get(url, timeout=10, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
            "Referer":    "https://edition.cnn.com/markets/fear-and-greed"
        })
        resp.raise_for_status()
        data   = resp.json()
        score  = round(float(data["fear_and_greed"]["score"]), 1)
        rating = data["fear_and_greed"]["rating"]
        source = "CNN"
    except Exception:
        # --- Fallback: Alternative.me ---
        try:
            url   = "https://api.alternative.me/fng/?limit=1"
            resp  = requests.get(url, timeout=10)
            resp.raise_for_status()
            data   = resp.json()["data"][0]
            score  = round(float(data["value"]), 1)
            rating = data["value_classification"]
            source = "Alternative.me"
        except Exception as e2:
            print(f"  [Fear&Greed] Ambas fuentes fallaron: {e2}")
            return {"score": None, "rating": "unknown", "signal": "unknown", "source": "error"}

    if score <= 15:    signal = "EXTREME_FEAR"
    elif score <= 30:  signal = "FEAR"
    elif score <= 55:  signal = "NEUTRAL"
    elif score <= 75:  signal = "GREED"
    else:              signal = "EXTREME_GREED"

    return {"score": score, "rating": rating, "signal": signal, "source": source}


def get_economic_calendar() -> list:
    """
    Calendario economico USD High-Impact — Forex Factory XML publico.
    Retorna lista de eventos con ventanas de no-trade calculadas en ET.
    Incluye eventos de hoy hasta 7 dias adelante.
    """
    url = "https://nfs.faireconomy.media/ff_calendar_thisweek.xml"
    try:
        resp = requests.get(url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
        resp.raise_for_status()
        root = ET.fromstring(resp.content)
    except Exception as e:
        print(f"  [Calendar] Error descarga Forex Factory: {e}")
        return []

    events = []
    now    = datetime.now()

    for ev in root.findall("event"):
        if ev.findtext("country", "") != "USD":
            continue
        if ev.findtext("impact", "") != "High":
            continue

        title    = ev.findtext("title", "").strip()
        date_str = ev.findtext("date", "")    # formato: "03-27-2026"
        time_str = ev.findtext("time", "").strip().lower()

        # Parsear datetime ET
        try:
            if time_str and time_str not in ("", "tentative", "all day"):
                # "8:30am" -> formato %I:%M%p
                time_fmt = time_str.replace(" ", "")
                dt = datetime.strptime(f"{date_str} {time_fmt}", "%m-%d-%Y %I:%M%p")
            else:
                # Sin hora exacta: asumir 8:30 AM (hora tipica de reportes USD)
                dt = datetime.strptime(date_str, "%m-%d-%Y").replace(hour=8, minute=30)
        except ValueError:
            continue

        # Solo esta semana
        if dt.date() < now.date():
            continue
        if dt.date() > (now + timedelta(days=7)).date():
            continue

        is_fed = any(kw in title.lower() for kw in FED_KEYWORDS)
        window = FED_WINDOW_MIN if is_fed else NO_TRADE_WINDOW_MIN

        no_trade_start = (dt - timedelta(minutes=window)).strftime("%H:%M")
        no_trade_end   = (dt + timedelta(minutes=window)).strftime("%H:%M")

        events.append({
            "title":             title,
            "date":              dt.strftime("%Y-%m-%d"),
            "time_et":           dt.strftime("%H:%M"),
            "is_fed":            is_fed,
            "window_minutes":    window,
            "no_trade_start":    no_trade_start,
            "no_trade_end":      no_trade_end,
            "no_trade_window":   f"{no_trade_start}-{no_trade_end}",
        })

    return sorted(events, key=lambda x: (x["date"], x["time_et"]))


def compute_macro_context(today_str: str) -> dict:
    """
    Combina VIX + Fear & Greed + Economic Calendar.
    El JSON del dia incluye:
      - today_events + no_trade_windows_today    (para hoy)
      - tomorrow_events + no_trade_windows_tomorrow (para manana — listos al abrir)
    """
    print("\n  [MACRO] Descargando VIX...")
    vix = get_vix()
    print(f"         VIX = {vix['value']} ({vix['category']})"
          + (f" cambio {vix['change']:+.2f}" if vix['change'] is not None else ""))

    print("  [MACRO] Descargando Fear & Greed...")
    fg = get_fear_greed()
    print(f"         F&G = {fg['score']} — {fg['signal']} [{fg['source']}]")

    print("  [MACRO] Descargando calendario (Forex Factory)...")
    calendar = get_economic_calendar()
    print(f"         {len(calendar)} eventos USD High-Impact esta semana")

    # Separar hoy / manana
    tomorrow_str    = (datetime.strptime(today_str, "%Y-%m-%d") + timedelta(days=1)).strftime("%Y-%m-%d")
    today_events    = [e for e in calendar if e["date"] == today_str]
    tomorrow_events = [e for e in calendar if e["date"] == tomorrow_str]

    for e in today_events:
        fed_tag = " [FED]" if e["is_fed"] else ""
        print(f"         HOY  {e['time_et']} {e['title']}{fed_tag} → NO-TRADE {e['no_trade_window']}")
    for e in tomorrow_events:
        fed_tag = " [FED]" if e["is_fed"] else ""
        print(f"         MANA {e['time_et']} {e['title']}{fed_tag} → NO-TRADE {e['no_trade_window']}")

    # Regimen operativo
    vix_val  = vix.get("value") or 15.0
    fg_score = fg.get("score") or 50.0

    avoid_shorts = vix_val >= VIX_HIGH or fg_score <= 25
    long_bias    = fg_score < 35

    fed_today = [e for e in today_events if e["is_fed"]]
    if fed_today:
        trade_mode = "WINDOWS_FED"          # ventanas extra largas
    elif today_events:
        trade_mode = "WINDOWS_ACTIVAS"      # ventanas normales
    elif vix_val >= VIX_EXTREME:
        trade_mode = "LONG_ONLY_REDUCED"    # solo longs, size reducido
    else:
        trade_mode = "NORMAL"

    reasons = []
    if today_events:
        reasons.append(f"{len(today_events)} evento(s) high-impact: "
                       + ", ".join(e["title"] for e in today_events))
    if vix_val >= VIX_HIGH:
        reasons.append(f"VIX {vix['category']} ({vix_val})")
    if fg_score <= 25:
        reasons.append(f"Fear&Greed {fg['signal']} ({fg_score}) → sin shorts")

    return {
        "vix":                          vix,
        "fear_greed":                   fg,
        "today_events":                 today_events,
        "tomorrow_events":              tomorrow_events,
        "no_trade_windows_today":       [e["no_trade_window"] for e in today_events],
        "no_trade_windows_tomorrow":    [e["no_trade_window"] for e in tomorrow_events],
        "events_today_count":           len(today_events),
        "trade_mode":                   trade_mode,
        "avoid_shorts":                 avoid_shorts,
        "long_bias":                    long_bias,
        "regime_reasons":               reasons,
    }


# ── Core ──────────────────────────────────────────────────────────────────────
def compute_market_context(date_str: str = None) -> dict:
    today = date_str or datetime.now().strftime("%Y-%m-%d")
    print(f"\n[MarketMonitor] Calculando contexto para {today}...")

    # --- Datos NQ por timeframe ---
    data = {}
    try:
        data["1D"]  = get_ohlcv(TICKER, "1d",  365)
        data["1H"]  = get_ohlcv(TICKER, "1h",  60)
        data["30M"] = get_ohlcv(TICKER, "30m", 30)
        data["15M"] = get_ohlcv(TICKER, "15m", 20)

        df_1h = data["1H"].copy()
        df_1h.index = pd.to_datetime(df_1h.index)
        data["4H"] = df_1h.resample("4h").agg({
            "Open": "first", "High": "max",
            "Low": "min",    "Close": "last",
            "Volume": "sum"
        }).dropna()
    except Exception as e:
        print(f"  [ERROR] Descarga NQ: {e}")
        return {}

    # --- Tendencias NQ ---
    trends       = {}
    trend_labels = {1: "bull", -1: "bear", 0: "neutral"}
    for tf in ["1D", "4H", "1H", "30M"]:
        df = data.get(tf)
        if df is None or len(df) < EMA_PERIOD + 5:
            trends[tf] = 0
            print(f"  [{tf}] insuficiente data -> neutral")
            continue
        t = ema_slope(df["Close"])
        trends[tf] = t
        print(f"  [{tf}] EMA slope = {trend_labels[t]}")

    # --- Choppiness ---
    df15   = data.get("15M", pd.DataFrame())
    ci_val = choppiness_index(df15["High"], df15["Low"], df15["Close"]) if len(df15) > CI_PERIOD else 50.0
    sea    = sea_state_label(ci_val)
    print(f"  [15M] Choppiness = {ci_val:.1f} -> {sea}")

    # --- tide_score ---
    raw_score  = sum(trends[tf] * WEIGHTS[tf] for tf in WEIGHTS)
    tide_score = round(raw_score / MAX_SCORE * 3, 2)
    print(f"  [TIDE] raw={raw_score:.1f} -> tide_score={tide_score:.2f}")

    swim_ok    = (sea != "rough") and (abs(tide_score) >= 0.5)
    last_price = round(float(data["1D"]["Close"].iloc[-1]), 2) if len(data["1D"]) > 0 else 0.0

    # --- Market Breadth ---
    print(f"\n  [BREADTH] Calculando confirmacion multi-mercado...")
    breadth = compute_market_breadth(nq_trend=trends["1D"])

    # --- Multi-Oscillator ---
    print(f"\n  [OSCILADORES] Calculando consenso RSI+MFI+Stoch...")
    multi_osc = compute_multi_osc(data["1D"])

    # --- Macro Context (Modulo 3) ---
    print(f"\n  [MACRO] Contexto economico externo...")
    macro = compute_macro_context(today)

    # --- Construir contexto completo ---
    context = {
        "fecha":         today,
        "timestamp":     datetime.now().isoformat(),
        "precio_cierre": last_price,

        "trend_1D":   trends["1D"],
        "trend_4H":   trends["4H"],
        "trend_1H":   trends["1H"],
        "trend_30M":  trends["30M"],

        "choppiness_15M": ci_val,
        "sea_state":      sea,
        "tide_score":     tide_score,
        "swim_ok":        swim_ok,

        **breadth,
        **multi_osc,

        "trend_1D_label":  trend_labels[trends["1D"]],
        "trend_4H_label":  trend_labels[trends["4H"]],
        "trend_1H_label":  trend_labels[trends["1H"]],
        "trend_30M_label": trend_labels[trends["30M"]],

        # Modulo 3 — bloque completo
        "macro_context": macro,

        "strategies_pnl": {},
        "all_won":        None,
        "all_lost":       None,
        "notes":          ""
    }

    return context


def save_log(context: dict) -> str:
    os.makedirs(LOG_DIR, exist_ok=True)
    fecha    = context.get("fecha", datetime.now().strftime("%Y-%m-%d"))
    filepath = os.path.join(LOG_DIR, f"{fecha}.json")

    # Preservar strategies_pnl y notes si ya existian
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            existing = json.load(f)
        if existing.get("strategies_pnl"):
            context["strategies_pnl"] = existing["strategies_pnl"]
        if existing.get("notes"):
            context["notes"] = existing["notes"]

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(context, f, indent=2, ensure_ascii=False)

    return filepath


def print_summary(context: dict):
    print("\n" + "="*60)
    print(f"  MARKET CONTEXT — {context['fecha']}")
    print("="*60)
    print(f"  NQ Cierre:     {context['precio_cierre']}")
    print(f"  1D / 4H:       {context['trend_1D_label']} / {context['trend_4H_label']}")
    print(f"  1H / 30M:      {context['trend_1H_label']} / {context['trend_30M_label']}")
    print(f"  Choppiness:    {context['choppiness_15M']:.1f} ({context['sea_state'].upper()})")
    print(f"  Tide Score:    {context['tide_score']:+.2f}")
    print(f"  Swim OK:       {'SI' if context['swim_ok'] else 'NO — MAR PICADO'}")
    print("-"*60)

    bs    = context['market_breadth_score']
    align = "OK CONFIRMADO" if context['breadth_alignment'] else "XX DIVERGENCIA"
    div   = context['breadth_divergence']
    print(f"  Breadth Score: {bs:+d}/3  {align}")
    print(f"  ES/YM/RTY:     {context['breadth_ES']:+d} / {context['breadth_YM']:+d} / {context['breadth_RTY']:+d}")
    if div:
        print(f"  Diverge:       {', '.join(div)}")

    ms    = context['multi_osc_score']
    label = context['multi_osc_label'].upper()
    print(f"  Multi-Osc:     {ms:+d}/3  [{label}]")
    print(f"  RSI/MFI/Stoch: {context['rsi_1d']:.1f} / {context['mfi_1d']:.1f} / {context['stoch_1d']:.1f}")

    # ── Macro Context ──
    mc = context.get("macro_context", {})
    if mc:
        vix_d = mc.get("vix", {})
        fg_d  = mc.get("fear_greed", {})
        print("-"*60)
        vix_str = f"{vix_d.get('value', 'N/A')} ({vix_d.get('category', '?')})"
        if vix_d.get("change") is not None:
            vix_str += f" {vix_d['change']:+.2f}"
        print(f"  VIX:           {vix_str}")
        print(f"  Fear & Greed:  {fg_d.get('score', 'N/A')} — {fg_d.get('signal', '?')}")
        print(f"  Trade Mode:    {mc.get('trade_mode', 'NORMAL')}")
        print(f"  Evitar Shorts: {'SI' if mc.get('avoid_shorts') else 'NO'}")
        print(f"  Sesgo Long:    {'SI' if mc.get('long_bias') else 'NO'}")

        windows_hoy = mc.get("no_trade_windows_today", [])
        if windows_hoy:
            events_hoy = mc.get("today_events", [])
            print(f"  NO-TRADE HOY:")
            for e in events_hoy:
                fed = " [FED]" if e["is_fed"] else ""
                print(f"    {e['time_et']}  {e['title']}{fed}  -> {e['no_trade_window']}")
        else:
            print(f"  NO-TRADE HOY:  (sin eventos high-impact)")

        windows_tmrw = mc.get("no_trade_windows_tomorrow", [])
        if windows_tmrw:
            events_tmrw = mc.get("tomorrow_events", [])
            print(f"  NO-TRADE MANA:")
            for e in events_tmrw:
                fed = " [FED]" if e["is_fed"] else ""
                print(f"    {e['time_et']}  {e['title']}{fed}  -> {e['no_trade_window']}")

        reasons = mc.get("regime_reasons", [])
        if reasons:
            print(f"  Alertas:")
            for r in reasons:
                print(f"    ! {r}")

    print("="*60)


# ── Entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    ctx = compute_market_context()
    if ctx:
        filepath = save_log(ctx)
        print_summary(ctx)
        print(f"\n  Log guardado: {filepath}")
        print("\n  TIP: Edita el JSON para agregar strategies_pnl del dia:")
        print('  "strategies_pnl": {"StatMeanCross": -393, "EMATrendRenko": -603, ...}')
    else:
        print("[ERROR] No se pudo calcular el contexto. Verificar conexion a internet.")
