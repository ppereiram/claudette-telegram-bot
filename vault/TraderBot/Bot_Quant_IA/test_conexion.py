"""
test_conexion.py — Verificar que NT8 y meta_brain.py estan hablando
===================================================================
Ejecutar ANTES de abrir NinjaTrader, o en cualquier momento para diagnosticar.

Uso:
    python test_conexion.py                  # test ping basico
    python test_conexion.py --full           # simula un trade completo
    python test_conexion.py --monitor        # modo monitor: muestra cada mensaje en tiempo real

Requisito: meta_brain.py debe estar corriendo (python meta_brain.py)
"""

import zmq
import json
import sys
import time
from datetime import datetime

PORT = 5556
TIMEOUT_MS = 1500   # 1.5 segundos (NT8 usa 500ms — usamos mas para diagnostico)


def send_recv(socket, msg, label=""):
    """Envia mensaje y espera respuesta. Retorna (response_dict, elapsed_ms) o (None, -1) si timeout."""
    start = time.time()
    socket.send_string(json.dumps(msg))
    if socket.poll(TIMEOUT_MS):
        raw = socket.recv_string()
        elapsed = (time.time() - start) * 1000
        return json.loads(raw), elapsed
    return None, -1


def test_ping(socket):
    print("\n[1] TEST PING — Verificando conexion con meta_brain.py")
    print("-" * 50)
    resp, ms = send_recv(socket, {"type": "ping", "strategy": "test"})
    if resp is None:
        print("  ✗ TIMEOUT — meta_brain.py NO responde")
        print("  Asegurate de que meta_brain.py esta corriendo:")
        print("  > python meta_brain.py")
        return False
    if resp.get("pong") == 1:
        print(f"  ✓ CONEXION OK — respuesta en {ms:.0f}ms")
        active = resp.get("strategies", [])
        if active:
            print(f"  Estrategias activas: {', '.join(active)}")
        else:
            print("  Estrategias activas: ninguna aun (esperando trades)")
        return True
    print(f"  ? Respuesta inesperada: {resp}")
    return False


def test_entry_query(socket):
    print("\n[2] TEST ENTRY QUERY — Simulando consulta de entrada")
    print("-" * 50)
    msg = {
        "type":        "entry_query",
        "strategy":    "BreadButter_ULTRA",
        "trade_id":    f"TEST_{datetime.now().strftime('%H%M%S')}",
        "direction":   1,
        "rsi":         48.5,
        "adx":         30.2,
        "vol_ratio":   1.4,
        "dist_htf":    0.002,
        "ema_slope":   0.3,
        "hour":        10,
        "minute":      15,
        "day_of_week": 2,
        "signal_type": 0
    }
    print(f"  Enviando: LONG | ADX={msg['adx']} | RSI={msg['rsi']} | VolRatio={msg['vol_ratio']}")
    resp, ms = send_recv(socket, msg)
    if resp is None:
        print("  ✗ TIMEOUT en entry_query")
        return None
    action = "PERMITE" if resp.get("allow") == 1 else "BLOQUEA"
    print(f"  ✓ Respuesta ({ms:.0f}ms): {action} | conf={resp.get('confidence', 0):.0%} | "
          f"fase={resp.get('phase')} | razon={resp.get('reason', '?')}")
    return msg.get("trade_id")


def test_outcome(socket, trade_id):
    print("\n[3] TEST OUTCOME — Enviando resultado del trade")
    print("-" * 50)
    msg = {
        "type":     "outcome",
        "strategy": "BreadButter_ULTRA",
        "id":       trade_id,
        "pnl":      87.50,
        "result":   1
    }
    print(f"  Enviando: trade_id={trade_id} | pnl=$87.50 | result=GANADOR")
    resp, ms = send_recv(socket, msg)
    if resp is None:
        print("  ✗ TIMEOUT en outcome")
        return False
    print(f"  ✓ Respuesta ({ms:.0f}ms): total={resp.get('total_trades')} trades | "
          f"WR={resp.get('win_rate', 0):.0%} | fase={resp.get('phase')}")
    return True


def test_bloqueado(socket):
    print("\n[4] TEST BLOQUEO — Verificando que el filtro rechaza condiciones malas")
    print("-" * 50)
    casos = [
        {"label": "ADX bajo (18)",       "adx": 18,  "rsi": 50, "vol_ratio": 1.0, "hour": 10, "dist_htf": 0.0},
        {"label": "RSI sobrecomprado",   "adx": 28,  "rsi": 78, "vol_ratio": 1.0, "hour": 10, "dist_htf": 0.0},
        {"label": "Volumen bajo (0.4x)", "adx": 28,  "rsi": 50, "vol_ratio": 0.4, "hour": 10, "dist_htf": 0.0},
        {"label": "Ultima hora (15h)",   "adx": 28,  "rsi": 50, "vol_ratio": 1.2, "hour": 15, "dist_htf": 0.0},
    ]
    for caso in casos:
        msg = {"type": "entry_query", "strategy": "TEST_FILTER",
               "trade_id": f"BLOCK_{datetime.now().strftime('%H%M%S%f')}",
               "direction": 1, "signal_type": 0, "minute": 0, "day_of_week": 1, "ema_slope": 0.0}
        msg.update({k: v for k, v in caso.items() if k != "label"})
        resp, ms = send_recv(socket, msg)
        if resp:
            action = "BLOQUEA" if resp.get("allow") == 0 else "PERMITE"
            status = "✓" if resp.get("allow") == 0 else "✗ (debia bloquear)"
            print(f"  {status} {caso['label']}: {action} — {resp.get('reason', '?')}")
        else:
            print(f"  ✗ {caso['label']}: TIMEOUT")


def monitor_mode(socket):
    print("\n[MONITOR] Mostrando todos los mensajes en tiempo real (Ctrl+C para salir)")
    print("  Activa las estrategias en NinjaTrader — los logs apareceran aqui")
    print("-" * 60)
    poller = zmq.Poller()
    poller.register(socket, zmq.POLLIN)
    while True:
        try:
            events = dict(poller.poll(timeout=5000))
            if socket in events:
                raw = socket.recv_string()
                msg = json.loads(raw)
                t   = datetime.now().strftime('%H:%M:%S')
                mtype = msg.get('type', '?')
                strat = msg.get('strategy', '?')
                if mtype == 'entry_query':
                    d = "L" if msg.get('direction', 1) == 1 else "S"
                    print(f"[{t}] QUERY  {strat:30s} | {d} | ADX={msg.get('adx',0):4.0f} | RSI={msg.get('rsi',0):4.0f}")
                elif mtype == 'outcome':
                    r = "WIN" if msg.get('result', 0) > 0 else "LOSS"
                    print(f"[{t}] RESULT {strat:30s} | {r} | PnL=${msg.get('pnl',0):7.2f}")
                elif mtype == 'ping':
                    print(f"[{t}] PING   {strat}")
                # Responder con allow=1 por default en monitor mode
                socket.send_string(json.dumps({"allow": 1, "confidence": 0.5, "pong": 1,
                                               "status": "ok", "ack": 1, "phase": "monitor"}))
            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] ... esperando mensajes de NT8 ...")
        except KeyboardInterrupt:
            print("\n  Monitor detenido.")
            break


def main():
    args = sys.argv[1:]
    monitor = "--monitor" in args
    full    = "--full" in args

    context = zmq.Context()
    socket  = context.socket(zmq.REQ)
    socket.setsockopt(zmq.RCVTIMEO, TIMEOUT_MS)
    socket.setsockopt(zmq.SNDTIMEO, 1000)
    socket.connect(f"tcp://localhost:{PORT}")

    print("=" * 60)
    print(f"  test_conexion.py — Puerto {PORT}")
    print(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)

    if monitor:
        # En modo monitor usamos PAIR para no consumir mensajes
        socket.close()
        context.term()
        print("\n  MODO MONITOR: conectando como observador pasivo")
        print("  NOTA: meta_brain.py debe estar corriendo en otra terminal")
        context2 = zmq.Context()
        sock2 = context2.socket(zmq.REQ)
        sock2.connect(f"tcp://localhost:{PORT}")
        monitor_mode(sock2)
        sock2.close()
        context2.term()
        return

    # Test basico siempre
    ok = test_ping(socket)

    if not ok:
        socket.close()
        context.term()
        sys.exit(1)

    if full:
        # Test completo: entry query + outcome + filtros de bloqueo
        trade_id = test_entry_query(socket)
        if trade_id:
            test_outcome(socket, trade_id)
        test_bloqueado(socket)

    print("\n" + "=" * 60)
    if ok:
        print("  RESULTADO: Bridge NT8 <-> Python OPERATIVO")
        print("  Puedes activar UseMLFilter=true en NinjaTrader")
    print("=" * 60)

    socket.close()
    context.term()


if __name__ == "__main__":
    main()
