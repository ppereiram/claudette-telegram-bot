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
  - swim_ok: ¿vale la pena operar ese dia?
  - market_breadth_score: confirmacion ES/YM/RTY vs NQ (-3 -> +3)
  - multi_osc_score: consenso RSI+MFI+Stoch (-3 -> +3)

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
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings("ignore")

# ── Configuracion ────────────────────────────────────────────────────────────
TICKER    = "NQ=F"          # E-mini Nasdaq = mismos precios que MNQ
LOG_DIR   = os.path.join(os.path.dirname(__file__), "market_logs")
EMA_PERIOD = 21
CI_PERIOD  = 14

# Pesos para tide_score
WEIGHTS = {"1D": 3.0, "4H": 2.0, "1H": 1.5, "30M": 1.0}
MAX_SCORE = sum(WEIGHTS.values())   # 7.5

# Tickers para market breadth (correlacionados con NQ)
BREADTH_TICKERS = {
    "ES":  "ES=F",   # S&P 500 Futures
    "YM":  "YM=F",   # Dow Jones Futures
    "RTY": "RTY=F",  # Russell 2000 Futures
}

# Umbrales osciladores
OSC_OB = 70   # overbought
OSC_OS = 30   # oversold


# ── Helpers: Tendencia ────────────────────────────────────────────────────────
def ema_slope(series: pd.Series, period: int = EMA_PERIOD, lookback: int = 3) -> int:
    """Direccion de la EMA: +1 alcista, -1 bajista, 0 neutral."""
    if len(series) < period + lookback:
        return 0
    ema = series.ewm(span=period, adjust=False).mean()
    slope = ema.iloc[-1] - ema.iloc[-lookback]
    threshold = series.std() * 0.05
    if slope > threshold:
        return 1
    if slope < -threshold:
        return -1
    return 0


def choppiness_index(high: pd.Series, low: pd.Series, close: pd.Series,
                     period: int = CI_PERIOD) -> float:
    """
    CI = 100 * log10(SumATR(N) / (Highest_High - Lowest_Low)) / log10(N)
    CI > 61.8 = choppy  |  CI < 38.2 = trending
    """
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
    range_hl = hh - ll
    range_hl = range_hl.replace(0, np.nan)
    ci = 100 * np.log10(sum_atr / range_hl) / np.log10(period)
    val = ci.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


# ── Helpers: Osciladores ──────────────────────────────────────────────────────
def calc_rsi(close: pd.Series, period: int = 14) -> float:
    """RSI clasico. Retorna el ultimo valor (0-100)."""
    if len(close) < period + 1:
        return 50.0
    delta = close.diff()
    gain  = delta.where(delta > 0, 0.0)
    loss  = (-delta).where(delta < 0, 0.0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()
    rs  = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    val = rsi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


def calc_mfi(high: pd.Series, low: pd.Series, close: pd.Series,
             volume: pd.Series, period: int = 14) -> float:
    """Money Flow Index. Retorna el ultimo valor (0-100)."""
    if len(close) < period + 1:
        return 50.0
    tp  = (high + low + close) / 3
    rmf = tp * volume
    pos = rmf.where(tp > tp.shift(1), 0.0)
    neg = rmf.where(tp <= tp.shift(1), 0.0)
    pos_sum = pos.rolling(period).sum()
    neg_sum = neg.rolling(period).sum()
    mfr = pos_sum / neg_sum.replace(0, np.nan)
    mfi = 100 - (100 / (1 + mfr))
    val = mfi.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


def calc_stoch(high: pd.Series, low: pd.Series, close: pd.Series,
               period: int = 14) -> float:
    """Stochastic %K. Retorna el ultimo valor (0-100)."""
    if len(close) < period:
        return 50.0
    ll = low.rolling(period).min()
    hh = high.rolling(period).max()
    rng = (hh - ll).replace(0, np.nan)
    k   = 100 * (close - ll) / rng
    val = k.iloc[-1]
    return round(float(val), 2) if not np.isnan(val) else 50.0


def osc_state(value: float, ob: int = OSC_OB, os_: int = OSC_OS) -> int:
    """Convierte valor de oscilador a estado: +1 oversold, -1 overbought, 0 neutral."""
    if value >= ob:
        return -1   # sobrecomprado = presion bajista
    if value <= os_:
        return +1   # sobrevendido = presion alcista
    return 0


# ── Helpers: Datos ────────────────────────────────────────────────────────────
def get_ohlcv(ticker: str, interval: str, days_back: int) -> pd.DataFrame:
    """Descarga OHLCV de yfinance."""
    end   = datetime.utcnow()
    start = end - timedelta(days=days_back)
    df = yf.download(ticker, start=start.strftime("%Y-%m-%d"),
                     end=end.strftime("%Y-%m-%d"),
                     interval=interval, progress=False, auto_adjust=True)
    df.columns = [c[0] if isinstance(c, tuple) else c for c in df.columns]
    return df.dropna()


def sea_state_label(ci: float) -> str:
    if ci < 38.2:
        return "calm"       # mercado trending — surfeable
    if ci < 61.8:
        return "moderate"   # transicion
    return "rough"          # choppy — no nadar


# ── Modulo: Market Breadth ────────────────────────────────────────────────────
def compute_market_breadth(nq_trend: int) -> dict:
    """
    Descarga ES, YM, RTY y calcula cuantos confirman la misma
    direccion que NQ. Retorna breadth_score y divergencias.

    breadth_score: -3 a +3 (cuantos de los 3 estan alcistas/bajistas)
    breadth_alignment: True si NQ concuerda con la mayoria
    """
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
            print(f"  [{name}] ERROR descarga: {e} -> neutral")
            breadth_slopes[name] = 0

    breadth_score     = sum(breadth_slopes.values())   # -3 a +3
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
    """
    Calcula RSI + MFI + Stochastic sobre datos diarios y
    retorna el consensus score.

    multi_osc_score: -3 (todo OB) a +3 (todo OS)
    multi_osc_overlap: True si abs(score) >= 2 (señal fuerte)
    """
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

    score   = rsi_st + mfi_st + stoch_st   # -3 a +3
    overlap = abs(score) >= 2

    if score >= 2:
        label = "oversold_consensus"    # bullish pressure
    elif score <= -2:
        label = "overbought_consensus"  # bearish pressure
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


# ── Core ─────────────────────────────────────────────────────────────────────
def compute_market_context(date_str: str = None) -> dict:
    today = date_str or datetime.now().strftime("%Y-%m-%d")
    print(f"\n[MarketMonitor] Calculando contexto para {today}...")

    # --- Descargar datos por timeframe ---
    data = {}
    try:
        data["1D"]  = get_ohlcv(TICKER, "1d",  365)
        data["1H"]  = get_ohlcv(TICKER, "1h",  60)
        data["30M"] = get_ohlcv(TICKER, "30m", 30)
        data["15M"] = get_ohlcv(TICKER, "15m", 20)

        # 4H: resamplear desde 1H
        df_1h = data["1H"].copy()
        df_1h.index = pd.to_datetime(df_1h.index)
        data["4H"] = df_1h.resample("4h").agg({
            "Open": "first", "High": "max",
            "Low": "min",    "Close": "last",
            "Volume": "sum"
        }).dropna()
    except Exception as e:
        print(f"  [ERROR] Descarga de datos NQ: {e}")
        return {}

    # --- Tendencias NQ por TF ---
    trends = {}
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

    # --- Choppiness Index (15M) ---
    df15  = data.get("15M", pd.DataFrame())
    ci_val = choppiness_index(df15["High"], df15["Low"], df15["Close"]) if len(df15) > CI_PERIOD else 50.0
    sea    = sea_state_label(ci_val)
    print(f"  [15M] Choppiness = {ci_val:.1f} -> {sea}")

    # --- tide_score ponderado ---
    raw_score  = sum(trends[tf] * WEIGHTS[tf] for tf in WEIGHTS)
    tide_score = round(raw_score / MAX_SCORE * 3, 2)
    print(f"  [TIDE] raw={raw_score:.1f} -> tide_score={tide_score:.2f}")

    # --- swim_ok ---
    swim_ok = (sea != "rough") and (abs(tide_score) >= 0.5)

    # --- Precio actual ---
    last_price = round(float(data["1D"]["Close"].iloc[-1]), 2) if len(data["1D"]) > 0 else 0.0

    # --- Market Breadth (ES, YM, RTY) ---
    print(f"\n  [BREADTH] Calculando confirmacion multi-mercado...")
    breadth = compute_market_breadth(nq_trend=trends["1D"])

    # --- Multi-Oscillator Consensus ---
    print(f"\n  [OSCILADORES] Calculando consenso RSI+MFI+Stoch...")
    multi_osc = compute_multi_osc(data["1D"])

    # --- Construir contexto ---
    context = {
        "fecha":         today,
        "timestamp":     datetime.now().isoformat(),
        "precio_cierre": last_price,

        # MAREA
        "trend_1D":   trends["1D"],
        "trend_4H":   trends["4H"],
        # MAR
        "trend_1H":   trends["1H"],
        "trend_30M":  trends["30M"],
        # CHOPPY
        "choppiness_15M": ci_val,
        "sea_state":      sea,

        # RESUMEN PRINCIPAL
        "tide_score":  tide_score,
        "swim_ok":     swim_ok,

        # MARKET BREADTH (ES / YM / RTY)
        **breadth,

        # MULTI-OSCILLATOR CONSENSUS
        **multi_osc,

        # Labels legibles
        "trend_1D_label":  trend_labels[trends["1D"]],
        "trend_4H_label":  trend_labels[trends["4H"]],
        "trend_1H_label":  trend_labels[trends["1H"]],
        "trend_30M_label": trend_labels[trends["30M"]],

        # Para llenar manualmente o via script al cierre
        "strategies_pnl": {},
        "all_won":        None,
        "all_lost":       None,
        "notes":          ""
    }

    return context


def save_log(context: dict) -> str:
    """Guarda el JSON en market_logs/YYYY-MM-DD.json"""
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

    # Market Breadth
    bs    = context['market_breadth_score']
    align = "OK CONFIRMADO" if context['breadth_alignment'] else "XX DIVERGENCIA"
    div   = context['breadth_divergence']
    print(f"  Breadth Score: {bs:+d}/3  {align}")
    print(f"  ES/YM/RTY:     {context['breadth_ES']:+d} / {context['breadth_YM']:+d} / {context['breadth_RTY']:+d}")
    if div:
        print(f"  Diverge:       {', '.join(div)}")

    # Multi-Osc
    ms    = context['multi_osc_score']
    label = context['multi_osc_label'].upper()
    print(f"  Multi-Osc:     {ms:+d}/3  [{label}]")
    print(f"  RSI/MFI/Stoch: {context['rsi_1d']:.1f} / {context['mfi_1d']:.1f} / {context['stoch_1d']:.1f}")
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
