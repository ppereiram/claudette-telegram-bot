import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score, classification_report
import joblib
import warnings

warnings.filterwarnings("ignore")

print("1. Cargando datos históricos de NinjaTrader...")
# Cargamos el archivo. Asegúrate de que se llama exactamente mnq_1min.csv
df = pd.read_csv('mnq_1min.csv', names=['Date', 'Open', 'High', 'Low', 'Close', 'Volume'], header=0)
print(f"-> Datos cargados. Filas encontradas: {len(df)}")

print("2. Creando Ingeniería de Características (Features)...")
df['log_ret'] = np.log(df['Close'] / df['Close'].shift(1))
df['vol_5'] = df['log_ret'].rolling(window=5).std()
df['mom_3'] = df['Close'] - df['Close'].shift(3)
df['ema_20'] = df['Close'].ewm(span=20, adjust=False).mean()
df['dist_ema'] = (df['Close'] - df['ema_20']) / df['ema_20']

print("3. Creando la Variable Objetivo (Target)...")
df['target'] = np.where(df['Close'].shift(-1) > df['Close'], 1, -1)
df.dropna(inplace=True) # Limpiamos los nulos iniciales
print(f"-> Datos limpios y listos. Filas útiles: {len(df)}")

print("4. Dividiendo datos (Train / Test Split Cronológico)...")
split_index = int(len(df) * 0.80)
train = df.iloc[:split_index]
test = df.iloc[split_index:]

features = ['log_ret', 'vol_5', 'mom_3', 'dist_ema']

X_train = train[features]
y_train = train['target']
X_test = test[features]
y_test = test['target']

print("5. Entrenando el Bosque Aleatorio (Random Forest)...")
print("-> (Esto puede tardar unos segundos dependiendo de cuántos años de datos bajaste)")
modelo_rf = RandomForestClassifier(
    n_estimators=150,      
    max_depth=6,           
    min_samples_leaf=50,   
    random_state=42,
    n_jobs=-1              
)

modelo_rf.fit(X_train, y_train)

print("6. Evaluando el rendimiento de la IA en datos nunca vistos...")
predicciones = modelo_rf.predict(X_test)
precision = accuracy_score(y_test, predicciones)

print(f"\n=============================================")
print(f">>> PRECISIÓN DEL MODELO: {precision * 100:.2f}% <<<")
print(f"=============================================\n")
print("Reporte Detallado:")
print(classification_report(y_test, predicciones))

print("7. Guardando el cerebro de la IA...")
joblib.dump(modelo_rf, 'modelo_rf_mnq.pkl')
print("¡Archivo 'modelo_rf_mnq.pkl' guardado con éxito! Listo para la acción.")