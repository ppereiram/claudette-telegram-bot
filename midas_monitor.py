"""
midas_monitor.py
================
Lee los market_logs del vault de Midas y genera un reporte diario.
Se integra al morning bulletin de las 6am CR.
"""

import os
import json
import glob
from datetime import datetime, timedelta
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

def _find_vault_path():
    """Busca el vault en múltiples ubicaciones posibles."""
    candidates = [
        os.environ.get("OBSIDIAN_VAULT_PATH", ""),
        "/opt/render/project/src/vault",
        os.path.join(os.path.dirname(__file__), "vault"),
        "vault",
    ]
    for p in candidates:
        if p and os.path.isdir(os.path.join(p, "TraderBot")):
            return p
    return candidates[1]  # fallback al default de Render

VAULT_PATH = _find_vault_path()
MARKET_LOGS_PATH = os.path.join(VAULT_PATH, "TraderBot", "Bot_Quant_IA", "market_logs")

# Umbrales de alerta
DRAWDOWN_ALERT = -2000   # PnL diario total bajo este valor = alerta

# Feriados NYSE 2025-2026 (mercado cerrado)
NYSE_HOLIDAYS = {
    # 2025
    "2025-01-01", "2025-01-20", "2025-02-17", "2025-04-18",
    "2025-05-26", "2025-07-04", "2025-09-01", "2025-11-27",
    "2025-12-25",
    # 2026
    "2026-01-01", "2026-01-19", "2026-02-16", "2026-04-03",
    "2026-05-25", "2026-07-03", "2026-09-07", "2026-11-26",
    "2026-12-25",
}


def is_market_closed(date: datetime) -> bool:
    """True si NYSE estaba cerrado ese día (fin de semana o feriado)."""
    if date.weekday() >= 5:  # sábado=5, domingo=6
        return True
    return date.strftime("%Y-%m-%d") in NYSE_HOLIDAYS


def _load_latest_json(prefix="strategies_pnl") -> dict | None:
    """Carga el JSON más reciente con el prefijo dado."""
    pattern = os.path.join(MARKET_LOGS_PATH, f"{prefix}_*.json")
    files = sorted(glob.glob(pattern))
    if not files:
        return None
    try:
        with open(files[-1], encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"midas_monitor: error leyendo {files[-1]}: {e}")
        return None


def _load_daily_json(date_str: str) -> dict | None:
    """Carga el JSON diario completo para una fecha dada (YYYY-MM-DD)."""
    path = os.path.join(MARKET_LOGS_PATH, f"{date_str}.json")
    if not os.path.exists(path):
        return None
    try:
        with open(path, encoding="utf-8-sig") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"midas_monitor: error leyendo {path}: {e}")
        return None


def _load_week_pnl() -> dict:
    """Carga los PnL de los últimos 7 días disponibles."""
    week_data = {}
    pattern = os.path.join(MARKET_LOGS_PATH, "strategies_pnl_*.json")
    files = sorted(glob.glob(pattern))[-7:]
    for f in files:
        try:
            with open(f, encoding="utf-8-sig") as fp:
                data = json.load(fp)
                date = data.get("fecha", Path(f).stem.replace("strategies_pnl_", ""))
                pnl = data.get("strategies_pnl", {})
                week_data[date] = sum(v for v in pnl.values() if isinstance(v, (int, float)))
        except:
            pass
    return week_data


def generate_midas_report() -> str:
    """
    Genera el reporte diario de Midas Monitor.
    Retorna string formateado para Telegram.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # Intentar cargar datos de hoy, si no hay usar ayer
    latest_pnl = _load_latest_json("strategies_pnl")
    daily = _load_daily_json(today) or _load_daily_json(yesterday)
    week_pnl = _load_week_pnl()

    if not latest_pnl:
        return (
            "⚠️ *MIDAS MONITOR — SIN DATOS*\n\n"
            "No se encontraron archivos de market_logs.\n"
            "Verifica que el sync_vault está corriendo correctamente."
        )

    fecha = latest_pnl.get("fecha", "desconocida")
    strategies = latest_pnl.get("strategies_pnl", {})

    # Calcular PnL total del día
    pnl_total = sum(v for v in strategies.values() if isinstance(v, (int, float)))

    # Separar ganadoras y perdedoras
    ganadoras = {k.replace("Sim", ""): v for k, v in strategies.items()
                 if isinstance(v, (int, float)) and v > 0}
    perdedoras = {k.replace("Sim", ""): v for k, v in strategies.items()
                  if isinstance(v, (int, float)) and v < 0}
    neutras = {k.replace("Sim", ""): v for k, v in strategies.items()
               if isinstance(v, (int, float)) and v == 0}

    # Top 3 ganadoras y perdedoras
    top_ganadoras = sorted(ganadoras.items(), key=lambda x: x[1], reverse=True)[:3]
    top_perdedoras = sorted(perdedoras.items(), key=lambda x: x[1])[:3]

    # PnL semanal
    pnl_semana = sum(week_pnl.values())
    dias_datos = len(week_pnl)

    # Estado del bot (respeta calendario NYSE)
    now = datetime.now()
    all_log_files = glob.glob(os.path.join(MARKET_LOGS_PATH, "*.json"))

    if is_market_closed(now):
        bot_status = "⚪ Mercado cerrado hoy"
        alertas_inactividad = False
    else:
        # Contar días hábiles sin datos
        dias_sin_datos = 0
        for i in range(7):
            d = now - timedelta(days=i)
            if is_market_closed(d):
                continue  # no cuenta como día sin datos
            d_str = d.strftime("%Y-%m-%d")
            if any(d_str in f for f in all_log_files):
                break
            dias_sin_datos += 1

        if dias_sin_datos == 0:
            bot_status = "🟢 Activo"
            alertas_inactividad = False
        else:
            bot_status = f"🔴 Sin datos hace {dias_sin_datos} día{'s' if dias_sin_datos > 1 else ''} hábil{'es' if dias_sin_datos > 1 else ''}"
            alertas_inactividad = dias_sin_datos >= 2

    # Alertas
    alertas = []
    if pnl_total < DRAWDOWN_ALERT:
        alertas.append(f"🚨 Drawdown severo: ${pnl_total:,.0f}")
    if alertas_inactividad:
        alertas.append(f"🚨 Bot posiblemente caído ({bot_status})")

    # Condición de mercado
    market_info = ""
    if daily:
        sea = daily.get("sea_state", "")
        swim = "✅ Nadar OK" if daily.get("swim_ok") else "⛔ No nadar"
        trend_1d = daily.get("trend_1D_label", "")
        trend_4h = daily.get("trend_4H_label", "")
        market_info = f"\n📊 *Mercado:* {sea} | {swim} | 1D:{trend_1d} 4H:{trend_4h}"

    # Construir reporte
    emoji_pnl = "🟢" if pnl_total >= 0 else "🔴"
    lines = [
        f"🤖 *MIDAS MONITOR — {fecha}*",
        f"",
        f"*Estado:* {bot_status}",
        f"*PnL Hoy:* {emoji_pnl} ${pnl_total:+,.1f}",
        f"*PnL Semana ({dias_datos}d):* {'🟢' if pnl_semana >= 0 else '🔴'} ${pnl_semana:+,.1f}",
    ]

    if market_info:
        lines.append(market_info)

    if top_ganadoras:
        lines.append(f"\n✅ *Top Ganadoras:*")
        for name, val in top_ganadoras:
            lines.append(f"  • {name.strip()}: +${val:,.1f}")

    if top_perdedoras:
        lines.append(f"\n❌ *Top Perdedoras:*")
        for name, val in top_perdedoras:
            lines.append(f"  • {name.strip()}: ${val:,.1f}")

    if neutras:
        lines.append(f"\n⚪ Sin actividad: {len(neutras)} estrategias")

    if alertas:
        lines.append(f"\n{'=' * 20}")
        for a in alertas:
            lines.append(a)

    # PnL diario de la semana
    if week_pnl:
        lines.append(f"\n📅 *Historial semanal:*")
        for d, p in sorted(week_pnl.items())[-5:]:
            em = "🟢" if p >= 0 else "🔴"
            lines.append(f"  {em} {d}: ${p:+,.0f}")

    return "\n".join(lines)


def check_midas_alerts() -> str | None:
    """
    Verifica alertas críticas de Midas.
    Retorna mensaje si hay alerta, None si todo está bien.
    """
    if is_market_closed(datetime.now()):
        return None  # No hay actividad esperada en fines de semana y feriados NYSE

    latest_pnl = _load_latest_json("strategies_pnl")
    if not latest_pnl:
        return "🚨 *MIDAS ALERTA*: No hay datos de market_logs. ¿Está corriendo el bot?"

    strategies = latest_pnl.get("strategies_pnl", {})
    pnl_total = sum(v for v in strategies.values() if isinstance(v, (int, float)))

    if pnl_total < DRAWDOWN_ALERT:
        return (
            f"🚨 *MIDAS ALERTA — DRAWDOWN*\n"
            f"PnL hoy: ${pnl_total:+,.1f}\n"
            f"Supera umbral de ${DRAWDOWN_ALERT:,}. Revisa las estrategias."
        )

    return None
