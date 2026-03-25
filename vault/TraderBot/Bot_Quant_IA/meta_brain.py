"""
meta_brain.py — Servidor ML Unificado para todas las estrategias
================================================================
Puerto ZMQ: 5556

Maneja todas las estrategias por nombre. Cada estrategia tiene su propio
log CSV y modelo Random Forest. Se entrena con los outcomes reales de cada
estrategia por separado.

Tipos de mensaje desde NT8:

1. Entry Query:
   {"type": "entry_query", "strategy": "BreadButter_ULTRA",
    "direction": 1, "rsi": 50.0, "adx": 28.0, "vol_ratio": 1.3,
    "dist_htf": 0.002, "ema_slope": 0.35, "hour": 10, "minute": 30,
    "day_of_week": 2, "signal_type": 0, "trade_id": "ULTRA_20260304_093000"}
   → {"allow": 1, "confidence": 0.65, "phase": "heuristic", "reason": "..."}

2. Outcome:
   {"type": "outcome", "strategy": "BreadButter_ULTRA",
    "id": "ULTRA_20260304_093000", "pnl": 87.5, "result": 1}
   → {"ack": 1, "total_trades": 15, "win_rate": 0.60, "phase": "heuristic"}

3. Ping (test de conexion):
   {"type": "ping", "strategy": "test"}
   → {"pong": 1, "status": "ok", "strategies": [...lista de estrategias activas...]}

Fases por estrategia:
- Fase 1 (0-29 trades): filtro heurístico genérico
- Fase 2 (30+ trades): Random Forest entrenado en trade outcomes reales
  - Reentrenamiento cada MIN_FOR_RETRAIN trades nuevos

Para iniciar: python meta_brain.py
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
DATA_DIR        = "."          # directorio donde se guardan logs y modelos
MIN_FOR_META    = 30           # trades para activar ML
MIN_FOR_RETRAIN = 20           # trades nuevos para reentrenar

# Features universales (estrategias sin RSI/ADX envian valores neutros)
FEATURES = ['direction', 'rsi', 'adx', 'vol_ratio', 'dist_htf',
            'ema_slope', 'hour', 'minute', 'day_of_week', 'signal_type']

# Valores neutros por defecto (cuando la estrategia no tiene ese indicador)
FEATURE_DEFAULTS = {
    'direction': 1, 'rsi': 50.0, 'adx': 25.0, 'vol_ratio': 1.0,
    'dist_htf': 0.0, 'ema_slope': 0.0, 'hour': 10, 'minute': 0,
    'day_of_week': 1, 'signal_type': 0
}

# ==========================================
# 1. FILTRO HEURISTICO (Fase 1) — Generico
# ==========================================
def heuristic_filter(f):
    """
    Filtro heurístico genérico. Reglas minimas que aplican a cualquier estrategia.
    Retorna (allow: int, confidence: float, reason: str)
    """
    direction = f.get('direction', 1)
    rsi       = f.get('rsi', 50.0)
    adx       = f.get('adx', 25.0)
    vol_ratio = f.get('vol_ratio', 1.0)
    dist_htf  = f.get('dist_htf', 0.0)
    hour      = f.get('hour', 10)

    # Regla 1: ADX muy bajo = no hay tendencia
    # Solo si la estrategia envía ADX real (no neutro=25)
    if adx != 25.0 and adx < 20:
        return 0, 0.20, f"ADX bajo ({adx:.1f} < 20)"

    # Regla 2: RSI extremo para la dirección (sobreextensión)
    # Solo si la estrategia envía RSI real (no neutro=50)
    if rsi != 50.0:
        if direction == 1 and rsi > 75:
            return 0, 0.15, f"LONG sobrecomprado RSI={rsi:.1f}"
        if direction == -1 and rsi < 25:
            return 0, 0.15, f"SHORT sobrevendido RSI={rsi:.1f}"

    # Regla 3: Volumen muy bajo
    # Solo si la estrategia envía vol_ratio real (no neutro=1.0)
    if vol_ratio != 1.0 and vol_ratio < 0.5:
        return 0, 0.25, f"Volumen insuficiente ({vol_ratio:.2f}x)"

    # Regla 4: Sobreextensión vs EMA HTF
    if dist_htf != 0.0:
        if direction == 1 and dist_htf > 0.01:
            return 0, 0.30, f"LONG sobreextendido vs EMA ({dist_htf*100:.2f}%)"
        if direction == -1 and dist_htf < -0.01:
            return 0, 0.30, f"SHORT sobreextendido vs EMA ({dist_htf*100:.2f}%)"

    # Regla 5: Última hora de sesión
    if hour >= 15:
        return 0, 0.35, f"Ultima hora de sesion ({hour}:xx)"

    # Todo OK
    base_conf = 0.55
    if adx != 25.0:
        base_conf += (adx - 20) * 0.008
    if vol_ratio != 1.0:
        base_conf += (vol_ratio - 0.5) * 0.08
    confidence = min(base_conf, 0.85)
    return 1, round(confidence, 2), "Heuristicas OK"

# ==========================================
# 2. ESTADO POR ESTRATEGIA
# ==========================================
class StrategyBrain:
    """Estado ML independiente por estrategia"""

    def __init__(self, strategy_name):
        self.name = strategy_name
        safe_name = strategy_name.replace(" ", "_").replace("/", "_")
        self.log_file   = os.path.join(DATA_DIR, f"trade_log_{safe_name}.csv")
        self.model_file = os.path.join(DATA_DIR, f"modelo_meta_{safe_name}.pkl")

        self.trade_log        = self._load_trade_log()
        self.model            = self._load_model()
        self.last_retrain     = len(self.trade_log)
        self.phase            = "meta" if (self.model and len(self.trade_log) >= MIN_FOR_META) else "heuristic"
        self.pending_contexts = {}

        print(f"  [{strategy_name}] {len(self.trade_log)} trades | Fase: {self.phase.upper()}")

    def _load_trade_log(self):
        if os.path.exists(self.log_file):
            df = pd.read_csv(self.log_file)
            return df
        cols = FEATURES + ['trade_id', 'pnl', 'result', 'timestamp', 'phase']
        return pd.DataFrame(columns=cols)

    def _load_model(self):
        if os.path.exists(self.model_file):
            return joblib.load(self.model_file)
        return None

    def retrain(self):
        df = self.trade_log
        if len(df) < MIN_FOR_META:
            return
        X = df[FEATURES].values
        y = (df['result'] > 0).astype(int).values

        model = RandomForestClassifier(
            n_estimators=200, max_depth=4,
            min_samples_leaf=5, class_weight='balanced',
            random_state=42
        )
        model.fit(X, y)
        acc = accuracy_score(y, model.predict(X))
        w, l = y.sum(), len(y) - y.sum()

        joblib.dump(model, self.model_file)
        self.model = model
        self.last_retrain = len(df)
        print(f"  [{self.name}] Modelo reentrenado: {len(df)} trades ({w}W/{l}L), acc={acc:.1%}")

        imp = sorted(zip(FEATURES, model.feature_importances_), key=lambda x: -x[1])
        for feat, v in imp[:3]:
            print(f"    {feat}: {v:.3f}")

    def query(self, features):
        """Devuelve (allow, confidence, reason, phase)"""
        if self.phase == "meta" and self.model:
            X = np.array([[features.get(f, FEATURE_DEFAULTS[f]) for f in FEATURES]])
            proba = self.model.predict_proba(X)[0]
            win_prob = proba[1] if len(proba) > 1 else 0.5
            allow = 1 if win_prob >= 0.55 else 0
            return allow, round(win_prob, 3), "RandomForest meta-model", "meta"
        else:
            allow, conf, reason = heuristic_filter(features)
            return allow, conf, reason, "heuristic"

    def record_context(self, trade_id, features):
        self.pending_contexts[trade_id] = features.copy()

    def record_outcome(self, trade_id, pnl, result):
        context = self.pending_contexts.pop(trade_id, {})
        row = {f: context.get(f, FEATURE_DEFAULTS[f]) for f in FEATURES}
        row.update({
            'trade_id': trade_id, 'pnl': pnl, 'result': result,
            'timestamp': datetime.now().isoformat(), 'phase': self.phase
        })
        self.trade_log = pd.concat([self.trade_log, pd.DataFrame([row])], ignore_index=True)
        self.trade_log.to_csv(self.log_file, index=False)

        total = len(self.trade_log)
        new_since_retrain = total - self.last_retrain

        # Activar o reentrenar modelo
        if total >= MIN_FOR_META and new_since_retrain >= MIN_FOR_RETRAIN:
            self.retrain()
            if self.phase != "meta":
                self.phase = "meta"
                print(f"  [{self.name}] FASE META ACTIVADA ({total} trades)")
        elif total >= MIN_FOR_META and self.phase == "heuristic" and self.model is None:
            self.retrain()
            if self.model:
                self.phase = "meta"
                print(f"  [{self.name}] FASE META ACTIVADA ({total} trades)")

        wins = (self.trade_log['result'] > 0).sum()
        wr = wins / total if total > 0 else 0
        return total, round(wr, 3)

# ==========================================
# 3. SERVIDOR ZMQ PRINCIPAL
# ==========================================
def run_server():
    print("=" * 60)
    print("  Meta-Brain Unificado — Puerto ZMQ:", PORT)
    print("  Estrategias: todas (por nombre en JSON)")
    print("=" * 60)

    brains = {}   # strategy_name → StrategyBrain

    context = zmq.Context()
    socket  = context.socket(zmq.REP)
    socket.bind(f"tcp://*:{PORT}")
    print(f"\n  Escuchando en puerto {PORT}... (Ctrl+C para detener)\n")

    while True:
        try:
            msg_str  = socket.recv_string()
            msg      = json.loads(msg_str)
            msg_type = msg.get('type', 'entry_query')
            strategy = msg.get('strategy', 'Unknown')

            # ======= PING (test de conexion) =======
            if msg_type == 'ping':
                active = list(brains.keys())
                print(f"[{datetime.now().strftime('%H:%M:%S')}] PING recibido | Estrategias activas: {active or 'ninguna'}")
                response = {"pong": 1, "status": "ok", "strategies": active}

            # ======= CONSULTA DE ENTRADA =======
            elif msg_type == 'entry_query':
                if strategy not in brains:
                    brains[strategy] = StrategyBrain(strategy)
                brain = brains[strategy]

                allow, confidence, reason, phase = brain.query(msg)

                trade_id = msg.get('trade_id', f"{strategy}_{datetime.now().strftime('%H%M%S')}")
                brain.record_context(trade_id, msg)

                direction_str = "LONG" if msg.get('direction', 1) == 1 else "SHORT"
                action_str    = "PERMITE" if allow else "BLOQUEA"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {strategy} | {action_str} {direction_str} | "
                      f"conf={confidence:.0%} | ADX={msg.get('adx',0):.0f} | "
                      f"RSI={msg.get('rsi',0):.0f} | {reason}")

                response = {
                    "allow":      allow,
                    "confidence": confidence,
                    "phase":      phase,
                    "reason":     reason
                }

            # ======= RESULTADO DE TRADE =======
            elif msg_type == 'outcome':
                if strategy not in brains:
                    brains[strategy] = StrategyBrain(strategy)
                brain = brains[strategy]

                trade_id = msg.get('id', 'unknown')
                pnl      = float(msg.get('pnl', 0))
                result   = int(msg.get('result', 0))

                total, wr = brain.record_outcome(trade_id, pnl, result)
                result_str = "GANADOR" if result > 0 else "PERDEDOR"
                print(f"[{datetime.now().strftime('%H:%M:%S')}] {strategy} | Trade {result_str}: "
                      f"PnL=${pnl:.2f} | Total={total} | WR={wr:.0%}")

                response = {
                    "ack":          1,
                    "total_trades": total,
                    "win_rate":     wr,
                    "phase":        brain.phase
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
