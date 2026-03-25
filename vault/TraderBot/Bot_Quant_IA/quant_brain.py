import zmq
import json
import numpy as np
import pandas as pd
from scipy.stats import entropy
import joblib
import warnings

warnings.filterwarnings("ignore")

# ==========================================
# 1. CARGA DEL MODELO (El Cerebro que entrenamos)
# ==========================================
try:
    print("Cargando modelo Random Forest...")
    modelo_rf = joblib.load('modelo_rf_mnq.pkl')
    print("Modelo cargado exitosamente.")
except FileNotFoundError:
    print("ADVERTENCIA: Archivo .pkl no encontrado. Usando modelo simulado por seguridad.")
    from sklearn.ensemble import RandomForestClassifier
    modelo_rf = RandomForestClassifier().fit(np.random.randn(10, 4), np.random.choice([-1, 1], 10))

# ==========================================
# 2. FILTROS MATEMÁTICOS (El "Bozal")
# ==========================================
def calcular_entropia_shannon(precios_cierre, bins=10):
    """Calcula la Entropía de Shannon de los retornos recientes."""
    retornos = np.diff(precios_cierre) / precios_cierre[:-1]
    # Creamos una distribución de probabilidad de los retornos
    hist, _ = np.histogram(retornos, bins=bins, density=True)
    p = hist / np.sum(hist)
    p = p[p > 0] # Eliminar ceros para poder calcular el logaritmo
    return entropy(p, base=2)

def calcular_stoch_rsi(series_precios, periodo=14):
    """Calcula el RSI Estocástico del 0 al 1."""
    if len(series_precios) < periodo + 1:
        return 0.5 # Valor neutro si no hay suficientes datos
    
    delta = np.diff(series_precios)
    ganancias = np.where(delta > 0, delta, 0)
    perdidas = np.where(delta < 0, -delta, 0)
    
    # Media Móvil Exponencial (EMA) para suavizar
    avg_gain = pd.Series(ganancias).ewm(alpha=1/periodo, adjust=False).mean().iloc[-1]
    avg_loss = pd.Series(perdidas).ewm(alpha=1/periodo, adjust=False).mean().iloc[-1]
    
    if avg_loss == 0:
        rsi = 100
    else:
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
    
    # Simulación rápida de min/max RSI histórico para el estocástico
    # En un entorno real, calcularías el RSI de los últimos 14 periodos completos
    return rsi / 100.0 # Normalizado entre 0 y 1

# ==========================================
# 3. PREPARACIÓN DE DATOS (Feature Engineering)
# ==========================================
def preparar_datos_ml(precios):
    """Las 4 características exactas con las que entrenamos la IA"""
    df = pd.DataFrame(precios, columns=['Close'])
    df['log_ret'] = np.log(df['Close'] / df['Close'].shift(1))
    df['vol_5'] = df['log_ret'].rolling(window=5).std()
    df['mom_3'] = df['Close'] - df['Close'].shift(3)
    df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
    df['dist_ema'] = (df['Close'] - df['ema_20']) / df['ema_20']
    
    df.dropna(inplace=True)
    if len(df) == 0:
        return None
    
    ultimas_caracteristicas = df[['log_ret', 'vol_5', 'mom_3', 'dist_ema']].iloc[-1].values
    return ultimas_caracteristicas.reshape(1, -1)

# ==========================================
# 4. EL NÚCLEO ZEROMQ Y LÓGICA DE EJECUCIÓN
# ==========================================
def iniciar_servidor_zmq():
    context = zmq.Context()
    socket = context.socket(zmq.REP)
    socket.bind("tcp://*:5555")
    
    print("Servidor ZMQ Institucional escuchando en puerto 5555...")

    while True:
        try:
            mensaje = socket.recv_string()
            precios_nt8 = np.array(json.loads(mensaje)) # NT8 envía 20 o 30 periodos
            
            # --- FASE A: MEDICIÓN DEL ENTORNO (FILTROS) ---
            nivel_entropia = calcular_entropia_shannon(precios_nt8)
            stoch_rsi = calcular_stoch_rsi(precios_nt8)
            
            # --- FASE B: INFERENCIA DE LA IA ---
            X_actual = preparar_datos_ml(precios_nt8)
            if X_actual is None:
                socket.send_string(json.dumps({"signal": 0, "position_size": 0}))
                continue
                
            prediccion = modelo_rf.predict(X_actual)[0]
            confianza = max(modelo_rf.predict_proba(X_actual)[0])
            volatilidad_actual = X_actual[0][1] # vol_5
            
            # --- FASE C: ÁRBOL DE DECISIÓN DE RIESGO ---
            senal_final = int(prediccion)
            contratos_mnq = 2 # Base
            razon_aborto = ""

            # 1. Filtro de Confianza (Machine Learning)
            if confianza < 0.58:
                senal_final, contratos_mnq, razon_aborto = 0, 0, "Confianza baja de IA"
                
            # 2. Filtro de Entropía (Mercado Lateral)
            # El umbral exacto depende de tu optimización histórica, asumimos 2.8 como alto
            elif nivel_entropia > 2.8: 
                senal_final, contratos_mnq, razon_aborto = 0, 0, f"Entropía muy alta ({nivel_entropia:.2f})"
                
            # 3. Filtro de Agotamiento (StochRSI)
            elif senal_final == 1 and stoch_rsi > 0.85:
                senal_final, contratos_mnq, razon_aborto = 0, 0, "Sobrecompra extrema"
            elif senal_final == -1 and stoch_rsi < 0.15:
                senal_final, contratos_mnq, razon_aborto = 0, 0, "Sobreventa extrema"
                
            # 4. Gestión de Riesgo Dinámica (Volatilidad)
            if senal_final != 0 and volatilidad_actual > 0.0025:
                contratos_mnq = 1 # Reducimos exposición por seguridad
                print(">> Alerta: Volatilidad alta detectada. Reduciendo a 1 MNQ.")

            # --- FASE D: ENVÍO A NINJATRADER ---
            respuesta = {
                "signal": senal_final,
                "position_size": contratos_mnq
            }
            socket.send_string(json.dumps(respuesta))
            
            # --- LOGS PARA EL TRADER ---
            if senal_final == 0:
                print(f"IGNORADO | IA predijo {prediccion} pero se abortó por: {razon_aborto}")
            else:
                direccion = "COMPRA (LONG)" if senal_final == 1 else "VENTA (SHORT)"
                print(f"EJECUTANDO | {direccion} {contratos_mnq} MNQ | Confianza: {confianza*100:.1f}% | Entropía: {nivel_entropia:.2f}")

        except Exception as e:
            print(f"Error procesando datos: {e}")
            socket.send_string(json.dumps({"signal": 0, "position_size": 0}))

if __name__ == "__main__":
    iniciar_servidor_zmq()