import zmq
import json
import joblib
import numpy as np
import warnings

warnings.filterwarnings("ignore")

print("1. Despertando a la IA...")
try:
    modelo_rf = joblib.load('modelo_rf_mnq.pkl')
    print("-> ¡Cerebro cargado con éxito! Precisión histórica: ~69%")
except:
    print("ERROR: No se encontró el archivo .pkl")
    exit()

# Configuramos la conexión ZeroMQ
context = zmq.Context()
socket = context.socket(zmq.REP)
socket.bind("tcp://*:5555")

print("2. Servidor IA activo. Escuchando a NinjaTrader en el puerto 5555...")
print("Esperando que tus estrategias pidan permiso para entrar...")

while True:
    try:
        # Esperamos el mensaje de NT8
        mensaje = socket.recv_string()
        datos_nt8 = json.loads(mensaje)
        
        # NT8 nos enviará las características de la vela actual y qué quiere hacer
        caracteristicas = np.array(datos_nt8["features"]).reshape(1, -1)
        intencion_estrategia = datos_nt8["signal_intent"] # 1 para Compra, -1 para Venta
        
        # La IA evalúa el mercado
        prediccion_ia = modelo_rf.predict(caracteristicas)[0]
        
        # LOGICA DE META-LABELING (El Semáforo)
        # Si la estrategia quiere comprar (1) y la IA predice que subirá (1) -> Aprobado
        # Si la estrategia quiere vender (-1) y la IA predice que bajará (-1) -> Aprobado
        # Si no están de acuerdo -> Denegado
        
        aprobado = (intencion_estrategia == prediccion_ia)
        
        respuesta = {"approved": aprobado}
        socket.send_string(json.dumps(respuesta))
        
        if aprobado:
            print(f"-> APROBADO: Estrategia y IA concuerdan en dirección {intencion_estrategia}")
        else:
            print(f"-> BLOQUEADO: Estrategia quería {intencion_estrategia}, IA dice peligro.")

    except Exception as e:
        print(f"Error: {e}")
        socket.send_string(json.dumps({"approved": False})) # Ante la duda, bloquear.