"""
meta_brain_bbv5.py — Servidor ML para BreadButter_v5_Apex
==========================================================
Puerto ZMQ: 5556 (base quant_brain usa 5555)

Recibe dos tipos de mensajes de NT8:

1. {"type": "entry_query", "direction": 1, "rsi": 45.2, "adx": 28.1,
    "vol_ratio": 1.3, "dist_htf": 0.002, "ema_slope": 0.35,
    "hour": 10, "minute": 30, "day_of_week": 2, "signal_type": 0}
   → Responde: {"allow": 1, "confidence": 0.65, "phase": "heuristic"}

2. {"type": "outcome", "id": "Long_20260304_093000",
    "pnl": 87.5, "result": 1, "context": {...}}
   → Responde: {"ack": 1, "total_trades": 15}

Fases del modelo:
- Fase 1 (0-29 trades): filtro heurístico basado en reglas confirmadas de BBv5
- Fase 2 (30+ trades): Random Forest entrenado en trade outcomes reales
  - Reentrenamiento automático cada MIN_FOR_RETRAIN trades nuevos

Para iniciar: python meta_brain_bbv5.py
"""

import zmq
import json
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score
import joblib
import os
import warnings
from datetime import datetime

warnings.filterwarnings("ignore")

# ==========================================
# CONFIGURACION
# ==========================================
PORT            = 5556
TRADE_LOG_FILE  = "trade_log_bbv5.csv"
META_MODEL_FILE = "modelo_meta_bbv5.pkl"
MIN_FOR_META    = 30    # trades necesarios para activar modelo ML
MIN_FOR_RETRAIN = 20    # trades nuevos para reentrenar

# Features en orden exacto (debe coincidir con el log y el C#)
FEATURES = ['direction', 'rsi', 'adx', 'vol_ratio', 'dist_htf',
            'ema_slope', 'hour', 'minute', 'day_of_week', 'signal_type']

# ==========================================
# 1. FILTRO HEURISTICO (Fase 1)
# Basado en lo que sabemos que funciona en BBv5
# ==========================================
def heuristic_filter(f):
    """
    Reglas heurísticas basadas en params confirmados de BBv5.
    Replica la intuición del trader: "cuando siento que se va a voltear".
    Retorna (allow: int, confidence: float, reason: str)
    """
    direction   = f.get('direction', 1)
    rsi         = f.get('rsi', 50.0)
    adx         = f.get('adx', 20.0)
    vol_ratio   = f.get('vol_ratio', 1.0)
    dist_htf    = f.get('dist_htf', 0.0)   # (Close - EMA100) / Close
    hour        = f.get('hour', 10)

    # Regla 1: ADX muy bajo = no hay tendencia = BBv5 falla
    if adx < 22:
        return 0, 0.20, f"ADX muy bajo ({adx:.1f} < 22)"

    # Regla 2: RSI extremo para la direccion = sobreextension
    if direction == 1 and rsi > 72:
        return 0, 0.15, f"LONG sobrecomprado RSI={rsi:.1f}"
    if direction == -1 and rsi < 28:
        return 0, 0.15, f"SHORT sobrevendido RSI={rsi:.1f}"

    # Regla 3: Volumen muy bajo = falta de participacion
    if vol_ratio < 0.6:
        return 0, 0.25, f"Volumen insuficiente ({vol_ratio:.2f}x)"

    # Regla 4: Precio muy lejos del EMA100 = retroceso probable
    # dist_htf > 0.008 (0.8%) = precio 0.8% por encima de EMA100 en Long
    if direction == 1 and dist_htf > 0.008:
        return 0, 0.30, f"LONG sobreextendido vs EMA100 ({dist_htf*100:.2f}%)"
    if direction == -1 and dist_htf < -0.008:
        return 0, 0.30, f"SHORT sobreextendido vs EMA100 ({dist_htf*100:.2f}%)"

    # Regla 5: Ultima hora de sesion = liquidez baja, spreads amplios
    if hour >= 15:
        return 0, 0.35, f"Ultima hora de sesion ({hour}:xx)"

    # Todo OK: permite el trade
    confidence = min(0.55 + (adx - 22) * 0.01 + (vol_ratio - 0.6) * 0.15, 0.85)
    return 1, round(confidence, 2), "Heuristicas OK"

# ==========================================
# 2. META-MODELO (Fase 2 — ML real)
# ==========================================
def load_meta_model():
    """Carga el modelo si existe"""
    if os.path.exists(META_MODEL_FILE):
        model = joblib.load(META_MODEL_FILE)
        print(f"  Meta-modelo cargado: {META_MODEL_FILE}")
        return model
    return None

def retrain_meta_model(trade_log_df):
    """
    Reentrena el Random Forest con el historial acumulado de trades.
    Target: result = 1 (ganador) o 0 (perdedor)
    """
    if len(trade_log_df) < MIN_FOR_META:
        print(f"  Insuficientes trades para meta-model ({len(trade_log_df)} < {MIN_FOR_META})")
        return None

    X = trade_log_df[FEATURES].values
    y = (trade_log_df['result'] > 0).astype(int).values  # 1=winner, 0=loser

    model = RandomForestClassifier(
        n_estimators=200,
        max_depth=4,            # conservador para evitar overfitting
        min_samples_leaf=5,     # mínimo 5 trades por hoja
        class_weight='balanced',
        random_state=42
    )
    model.fit(X, y)

    train_acc = accuracy_score(y, model.predict(X))
    winners = y.sum()
    losers = len(y) - winners

    joblib.dump(model, META_MODEL_FILE)
    print(f"  Meta-modelo reentrenado: {len(trade_log_df)} trades "
          f"({winners}W/{losers}L), train_acc={train_acc:.1%}")

    # Feature importance
    importance = sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1])
    print("  Feature importance:")
    for feat, imp in importance[:5]:
        print(f"    {feat}: {imp:.3f}")

    return model

def query_meta_model(model, f):
    """Query el meta-modelo. Retorna (allow, confidence)"""
    X = np.array([[f.get(feat, 0.0) for feat in FEATURES]])
    proba = model.predict_proba(X)[0]
    # proba[1] = probabilidad de ganar
    win_prob = proba[1] if len(proba) > 1 else 0.5
    allow = 1 if win_prob >= 0.55 else 0
    return allow, round(win_prob, 3)

# ==========================================
# 3. GESTION DEL LOG DE TRADES
# ==========================================
def load_trade_log():
    """Carga el historial de trades o crea DataFrame vacío"""
    if os.path.exists(TRADE_LOG_FILE):
        df = pd.read_csv(TRADE_LOG_FILE)
        print(f"  Trade log cargado: {len(df)} trades")
        return df
    cols = FEATURES + ['trade_id', 'pnl', 'result', 'timestamp', 'phase']
    return pd.DataFrame(columns=cols)

def save_trade_to_log(trade_log, trade_id, context, pnl, result, phase):
    """Agrega un trade al log y guarda el CSV"""
    row = {feat: context.get(feat, 0.0) for feat in FEATURES}
    row.update({
        'trade_id':  trade_id,
        'pnl':       pnl,
        'result':    result,
        'timestamp': datetime.now().isoformat(),
        'phase':     phase
    })
    trade_log = pd.concat([trade_log, pd.DataFrame([row])], ignore_index=True)
    trade_log.to_csv(TRADE_LOG_FILE, index=False)
    return trade_log

# ==========================================
# 4. SERVIDOR ZMQ PRINCIPAL
# ==========================================
def run_server():
    print("=" * 55)
    print("  BreadButter_v5 Meta-Brain — Puerto ZMQ:", PORT)
    print("=" * 55)

    # Cargar estado inicial
    trade_log  = load_trade_log()
    meta_model = load_meta_model()
    last_retrain_count = len(trade_log)

    # Contextos de entradas pendientes (esperando resultado)
    pending_contexts = {}

    # Fase actual
    phase = "meta" if (meta_model and len(trade_log) >= MIN_FOR_META) else "heuristic"
    print(f"  Fase activa: {phase.upper()} ({len(trade_log)}/{MIN_FOR_META} trades)")
    print("-" * 55)

    context = zmq.Context()
    socket  = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{PORT}")
    print(f"  Escuchando en puerto {PORT}... (Ctrl+C para detener)\n")

    while True:
        try:
            msg_str = socket.recv_string()
            msg     = json.loads(msg_str)
            msg_type = msg.get('type', 'entry_query')

            # ======= CONSULTA DE ENTRADA =======
            if msg_type == 'entry_query':
                features = msg  # el mismo dict contiene las features

                if phase == "meta" and meta_model:
                    allow, confidence = query_meta_model(meta_model, features)
                    reason = "RandomForest meta-model"
                else:
                    allow, confidence, reason = heuristic_filter(features)

                # Guardar contexto para cuando llegue el outcome
                trade_context_key = features.get('trade_id', f"trade_{datetime.now().strftime('%H%M%S')}")
                pending_contexts[trade_context_key] = features.copy()

                direction_str = "LONG" if features.get('direction', 1) == 1 else "SHORT"
                action_str    = "PERMITE" if allow else "BLOQUEA"

                print(f"[{datetime.now().strftime('%H:%M:%S')}] {action_str} {direction_str} | "
                      f"conf={confidence:.0%} | ADX={features.get('adx',0):.0f} | "
                      f"RSI={features.get('rsi',0):.0f} | {reason}")

                response = {
                    "allow":      allow,
                    "confidence": confidence,
                    "phase":      phase,
                    "reason":     reason
                }

            # ======= RESULTADO DE TRADE =======
            elif msg_type == 'outcome':
                trade_id = msg.get('id', 'unknown')
                pnl      = float(msg.get('pnl', 0))
                result   = int(msg.get('result', 0))

                # Recuperar contexto de entrada
                context_data = pending_contexts.pop(trade_id, msg.get('context', {}))

                trade_log = save_trade_to_log(
                    trade_log, trade_id, context_data, pnl, result, phase
                )

                total = len(trade_log)
                wins  = (trade_log['result'] > 0).sum()
                wr    = wins / total if total > 0 else 0

                result_str = "GANADOR" if result > 0 else "PERDEDOR"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Trade {result_str}: "
                      f"PnL=${pnl:.2f} | Total={total} trades | WR={wr:.0%}")

                # Verificar si hay que reentrenar
                new_since_retrain = total - last_retrain_count
                if total >= MIN_FOR_META and new_since_retrain >= MIN_FOR_RETRAIN:
                    print(f"\n  >> Reentrenando modelo ({new_since_retrain} trades nuevos)...")
                    meta_model = retrain_meta_model(trade_log)
                    last_retrain_count = total
                    if meta_model and phase != "meta":
                        phase = "meta"
                        print(f"  >> Cambiando a FASE META ({total} trades acumulados)\n")

                # Activar fase meta si llegamos al mínimo
                elif total >= MIN_FOR_META and phase == "heuristic" and meta_model is None:
                    print(f"\n  >> {total} trades acumulados. Entrenando primer meta-modelo...")
                    meta_model = retrain_meta_model(trade_log)
                    if meta_model:
                        phase = "meta"
                        last_retrain_count = total
                        print(f"  >> FASE META ACTIVADA\n")

                response = {
                    "ack":          1,
                    "total_trades": total,
                    "win_rate":     round(wr, 3),
                    "phase":        phase
                }

            else:
                response = {"error": f"tipo desconocido: {msg_type}"}

            socket.send_string(json.dumps(response))

        except KeyboardInterrupt:
            print("\n  Servidor detenido por el usuario.")
            break
        except json.JSONDecodeError as e:
            print(f"  Error JSON: {e}")
            socket.send_string(json.dumps({"allow": 1, "confidence": 0.5, "error": "json_error"}))
        except Exception as e:
            print(f"  Error inesperado: {e}")
            try:
                socket.send_string(json.dumps({"allow": 1, "confidence": 0.5, "error": str(e)}))
            except Exception:
                pass

    socket.close()
    context.term()


if __name__ == "__main__":
    run_server()
