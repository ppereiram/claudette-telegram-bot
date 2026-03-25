# BOT "MIDAS" — Arquitectura del Brain
## Destino: Darwin/X 2027 — Pablo Pereira

---

## VISION
Un sistema de trading 100% autónomo que combina:
- Estrategias mecánicas validadas (backtest + WFO + Algoritmos Genéticos)
- Un brain que "siente" el mercado continuamente
- Matemáticas avanzadas: Markov + Von Neumann + Tit for Tat + Monte Carlo + Bayes + RF + RL + GA
- Meta: track record verificable → capital externo → Darwin/X

## STACK MATEMATICO COMPLETO

| Capa | Matemática | Fuente | Implementación |
|------|-----------|--------|---------------|
| Régimen macro | Cadenas de Markov → HMM (EM Online ρ=0.97, BIC n=3) | Renaissance/Simons | markov_regime.py → hmm_regime.py (Mayo) |
| Régimen volatilidad | GARCH(1,1) + Vol Percentile 252d | Engle 1982 + Bernut | garch_vol.py + vol_regime_percentile.py (Sem 1) |
| Régimen triple | 3 capas ortogonales: vol + corr NQ/ES + momentum | Narang | triple_regime_filter.py (Sem 1) |
| Señales intraday | Bayes actualización + Triple Screen Score | Von Neumann/Bernut | bayes_signal.py + triple_screen_score.py |
| Riesgo adversario | Minimax + Regret + Correlation Regime Detector | Von Neumann + Carver | regret_engine.py + correlation_monitor.py |
| Confianza dinámica | Tit for Tat + IC + Model Decay Monitor (t-stat) | Axelrod + Narang | tit_for_tat.py + autocritica_daily.py |
| Sombra del futuro | Parámetro w | Axelrod | markov_regime.py |
| Sizing seguro | Monte Carlo + Safe f (Apex $7,500) + HRP + Vol Target | Vince + Carver | monte_carlo_sizer.py + hrp_optimizer.py |
| Diversificación real | Alpha Orthogonalizer (PCA) + FDM | Narang + Carver | hrp_optimizer.py |
| Market Profile | VAH/VAL + POC Migration + IB + Excess/Poor | Dalton | market_profile_features.py (Sem 1) |
| Order Flow | CVD + Absorption + of_score | Valtos | order_flow_monitor.py (Sem 1-Mayo) |
| Validación estadística | Deflated Sharpe Ratio + GPR + PWDA + TWR | Bailey/Bernut/Vince | deflated_sr.py + gain_to_pain_selector.py |
| Preprocesamiento | Wavelet Denoising + STL Seasonal | Mallat + Joseph | wavelet_filter.py + market_monitor_logger.py |
| Decisión final | Random Forest + SHAP + Pattern Quality | ML + Shapley | brain_v2.py |
| CV financiero | Purging + Embargoing | López de Prado | cv_financial.py (Semana 4 Abril) |
| Datos sintéticos | TimeGAN | Yoon et al. NeurIPS 2019 | timegan_augment.py (Mayo) |
| Forecasting | N-HiTS + ForecastEnsemble meta-learner | Joseph | nhits_signal.py + ensemble_brain.py (Mayo) |
| Aprendizaje live | Reinforcement Learning + AdaptiveForecaster | Bellman + Joseph | brain_v3.py (Mayo) |
| Auto-optimización | Algoritmos Genéticos | Axelrod/Darwin | ga_optimizer.py (Junio) |
| Sentiment fundamental | Polymarket (prediction markets) | Taleb/skin-in-game | polymarket_sentiment.py (Mayo) |

---

## BRAIN OUTPUT FINAL (target Semana 4 Abril)

```python
{
    # === MAREA (macro) ===
    "tide_score": -1.8,          # -3 (bear) → +3 (bull)
    "trend_1D": -1, "trend_4H": -1,

    # === MAR (intraday) ===
    "trend_1H": -1, "trend_30M": -1,
    "sea_state": "moderate",     # calm / moderate / rough
    "choppiness_15M": 48.67,

    # === CADENAS DE MARKOV ===
    "prob_regime_tomorrow": {
        "bear_fuerte": 0.45,
        "bear_moderado": 0.30,
        "neutral": 0.20,
        "bull": 0.05
    },
    "regime_momentum": "deteriorating",  # improving / stable / deteriorating
    "markov_confidence_adj": 0.60,       # ajuste de sizing basado en régimen esperado mañana

    # === VON NEUMANN (minimax regret) ===
    "regret_risk": 0.85,          # 0=sin riesgo, 1=máximo arrepentimiento esperado
    "minimax_sizing": 0.40,       # sizing que minimiza el peor caso posible

    # === TIT FOR TAT (por estrategia) ===
    "tft_multipliers": {
        "StatMeanCross":      1.00,  # cooperando (ganando)
        "PivotTrendBreak":    0.80,
        "BreadButter_ULTRA":  0.60,
        "BreadButter_SCALPER": 1.00,
        "DarvasBox":          0.25,  # traicionando (perdiendo)
        "BBv5_Apex":          0.25,
        "OrderFlowReversal":  0.25,
        "SuperTrendWave":     0.60,
        "MomentumZ":          0.80,
        "ABCDHarmonic":       0.80
    },

    # === ML (Random Forest) ===
    "rf_allow": 1,
    "rf_confidence": 0.73,

    # === NEWS FILTER ===
    "news_window": False,
    "next_news_minutes": 180,

    # === MONTE CARLO RISK ===
    "portfolio_drawdown_pct": 0.15,  # 0-1, % del MaxDD consumido hoy
    "monte_carlo_sizing_adj": 1.0,   # 1.0 = normal, 0.5 = mitad, 0.25 = supervivencia

    # === SEASONALITY ===
    "fomc_week": False,
    "opex_week": False,
    "month_end": False,
    "session_phase": "mid",          # open / mid / close / pre

    # === OUTPUT FINAL ===
    "swim_ok": True,
    "contracts_multiplier": 0.35,    # producto de todos los ajustes
    "reason": "bear_regime + tft_penalty_DarvasBox + high_regret_risk"
}
```

---

## MÓDULOS DEL BRAIN (por orden de construcción)

### MÓDULO 1: Market Monitor (Semana 0 — YA ACTIVO desde 09/03/2026)
- **Archivo**: `Bot_Quant_IA/market_monitor_logger.py`
- **Datos**: yfinance NQ=F, 1D/4H/1H/30M/15M
- **Output**: `market_logs/YYYY-MM-DD.json`
- **Corre**: cada día después del cierre (4:30 PM ET) via `run_monitor.bat`
- **CRÍTICO**: estos logs son el combustible de Markov — NO saltarse ningún día

### MÓDULO 1b: Auto-Crítica Diaria (Agregar a market_monitor_logger.py — AHORA)

**Concepto:** Midas lleva su propio diario de errores. Cada día evalúa si su predicción
de ayer fue correcta, cuánto se equivocó y por qué. Este es el combustible de la mejora
continua — sin esto, Markov aprende de estados pero no de sus propios fallos de predicción.

**Origen:** Loop de auto-mejora de M27 (Minimax) — 100 rondas de failure analysis → 30% mejora.
Aplicado a Midas: cada día de trading = 1 ronda. 30 días = 30 rondas de auto-calibración.

```python
# Agregar al final de market_monitor_logger.py
# Corre cada día junto con el market_log normal

def generar_autocritica(fecha_hoy, fecha_ayer, logs_dir="market_logs"):
    """
    Compara la predicción de ayer con la realidad de hoy.
    Genera un registro de accuracy que alimenta la calibración de Markov.
    Este es el 'diario de errores' de Midas — aprende de sus propios fallos.
    """
    log_ayer = cargar_json(f"{logs_dir}/{fecha_ayer}.json")
    log_hoy  = cargar_json(f"{logs_dir}/{fecha_hoy}.json")
    pnl_hoy  = cargar_pnl_total(f"{logs_dir}/strategies_pnl_{fecha_hoy}.json")

    if not log_ayer or not log_hoy:
        return None  # No hay datos suficientes todavía

    pred_tide  = log_ayer.get("tide_score", 0)
    real_tide  = log_hoy.get("tide_score", 0)
    swim_ok    = log_ayer.get("swim_ok", True)

    # ¿Acertó en dirección?
    direccion_ok = (
        (pred_tide > 0.5  and pnl_hoy > 0)   or   # predijo bull, fue bull
        (pred_tide < -0.5 and pnl_hoy < 0)   or   # predijo bear, fue bear
        (abs(pred_tide) <= 0.5 and abs(pnl_hoy) < 300)  # predijo neutral, fue neutral
    )

    # ¿swim_ok fue correcto? (¿valía la pena operar?)
    swim_correcto = (swim_ok == True  and pnl_hoy > -200) or \
                    (swim_ok == False and pnl_hoy < -200)

    error_magnitud = abs(pred_tide - real_tide)

    # Clasificar el tipo de error para Markov
    if not direccion_ok:
        if pred_tide > 0 and pnl_hoy < -500:
            tipo_error = "FALSO_POSITIVO_BULL"   # dije que subía, cayó fuerte
        elif pred_tide < 0 and pnl_hoy > 500:
            tipo_error = "FALSO_POSITIVO_BEAR"   # dije que bajaba, subió fuerte
        else:
            tipo_error = "ERROR_MAGNITUD"         # dirección ok pero tamaño mal
    else:
        tipo_error = "CORRECTO"

    critica = {
        "fecha":              str(fecha_hoy),
        "prediccion_tide":    round(pred_tide, 3),
        "realidad_tide":      round(real_tide, 3),
        "error_magnitud":     round(error_magnitud, 3),
        "direccion_correcta": direccion_ok,
        "swim_ok_correcto":   swim_correcto,
        "tipo_error":         tipo_error,
        "pnl_real":           pnl_hoy,
        "leccion": (
            f"Predije tide={pred_tide:.1f}, ocurrió {real_tide:.1f}. "
            f"{'CORRECTO' if direccion_ok else tipo_error}. "
            f"PnL real: ${pnl_hoy:,.0f}."
        )
    }

    # Guardar autocrítica individual
    guardar_json(f"{logs_dir}/autocritica_{fecha_hoy}.json", critica)

    # Actualizar acumulado de accuracy (para calibración de Markov)
    actualizar_accuracy_historico(critica, logs_dir)

    print(f"[AUTO-CRÍTICA] {critica['leccion']}")
    return critica


def actualizar_accuracy_historico(critica_hoy, logs_dir):
    """
    Mantiene un registro rolling de accuracy de Midas.
    Este archivo es la 'memoria de errores' que Markov usa para calibrarse.
    """
    path = f"{logs_dir}/midas_accuracy_historico.json"
    historico = cargar_json(path) or {"predicciones": [], "stats": {}}

    historico["predicciones"].append(critica_hoy)

    # Mantener solo últimos 90 días
    if len(historico["predicciones"]) > 90:
        historico["predicciones"] = historico["predicciones"][-90:]

    # Calcular stats rolling
    n = len(historico["predicciones"])
    correctas = sum(1 for p in historico["predicciones"] if p["direccion_correcta"])
    errores = [p["error_magnitud"] for p in historico["predicciones"]]
    falsos_bull = sum(1 for p in historico["predicciones"] if p["tipo_error"] == "FALSO_POSITIVO_BULL")
    falsos_bear = sum(1 for p in historico["predicciones"] if p["tipo_error"] == "FALSO_POSITIVO_BEAR")

    historico["stats"] = {
        "n_dias":               n,
        "accuracy_direccion":   round(correctas / n, 3) if n > 0 else 0,
        "error_medio":          round(sum(errores) / n, 3) if n > 0 else 0,
        "falsos_positivos_bull": falsos_bull,
        "falsos_positivos_bear": falsos_bear,
        "sesgo": (
            "SOBREESTIMA_BULL" if falsos_bull > falsos_bear * 1.5 else
            "SOBREESTIMA_BEAR" if falsos_bear > falsos_bull * 1.5 else
            "CALIBRADO"
        ),
        "ultima_actualizacion": str(date.today())
    }

    guardar_json(path, historico)
    print(f"[ACCURACY] Dirección correcta: {historico['stats']['accuracy_direccion']*100:.1f}% "
          f"({n} días) | Sesgo: {historico['stats']['sesgo']}")
```

**Output diario adicional:** `market_logs/autocritica_YYYY-MM-DD.json`
**Output acumulado:** `market_logs/midas_accuracy_historico.json`

**Por qué esto es crítico para Markov:**
- Markov construye P(estado_mañana | estado_hoy) desde observaciones
- Con auto-crítica, también sabe cuándo **sus propias predicciones** estuvieron sesgadas
- Si `sesgo = "SOBREESTIMA_BULL"` → Markov ajusta: ser más conservador en predicciones bull
- Si accuracy < 50% en los últimos 10 días → régimen de mercado cambió → recalibrar toda la matriz

**Cuándo implementar:** AHORA — no espera a Abril. Solo necesita los logs que ya existen
desde 09/03. Retroactivamente puede generar las auto-críticas de las últimas 2 semanas.

---

### MÓDULO 2: Cadenas de Markov (Semana 1 Abril — necesita 30+ días de logs)
```python
# markov_regime.py
# Construir matriz de transición desde market_logs históricos
# Estados: bear_fuerte / bear_moderado / neutral / bull_moderado / bull_fuerte
# Input: tide_score diario
# Output: prob_regime_tomorrow + regime_momentum
# Requiere mínimo 30 observaciones para ser estadísticamente útil
```

### MÓDULO 3: News Filter (Semana 2 Abril)
```python
# news_calendar.py
# Fuente: Forex Factory API o scraper
# Eventos HIGH: FOMC, NFP, CPI, PPI, GDP, Jobless Claims, ISM, PCE
# Bloquea entradas ±30min de evento macro
# También marca: semanas FOMC, semanas OpEx (3er viernes), fin/inicio de mes
```

### MÓDULO 4: Tit for Tat (Semana 2 Abril)
```python
# tit_for_tat.py
# Ventana: últimos 5 trades por estrategia
# Lógica:
#   último trade ganó → multiplier 1.0
#   último trade perdió + win_rate_5 > 40% → multiplier 0.60
#   último trade perdió + win_rate_5 < 40% → multiplier 0.25
#   3+ pérdidas consecutivas → multiplier 0.10 (modo supervivencia)
# Reset: cuando la estrategia gana de nuevo → empieza a restaurar
# Input: strategies_pnl de market_logs diarios
```

### MÓDULO 5: Von Neumann Regret Score (Semana 3 Abril)
```python
# regret_engine.py
# regret_risk = f(tide_score, sea_state, tft_worst_multiplier, news_proximity)
# Si regret_risk > 0.7 → no entrar aunque RF diga sí
# minimax_sizing = contratos que minimizan pérdida máxima en peor escenario
# Asimetría: perder $1 duele 2x más que ganar $1 (Von Neumann utility)
```

### MÓDULO 6: Monte Carlo Risk Engine (Semana 3 Abril)
```python
# monte_carlo_sizer.py
# 10,000 simulaciones bootstrap de trade history real
# Output: safe_contracts, dd_p95, ruin_probability, kelly_fraction
# Dynamic sizing por drawdown actual:
#   DD < 20% MaxDD → sizing 100%
#   DD 20-50% → sizing 75%
#   DD 50-75% → sizing 50%
#   DD > 75% → sizing 25% (modo supervivencia)
```

### MÓDULO 7: Brain ML Upgrade (Semana 4 Abril)
```python
# brain_v2.py — Random Forest con contexto completo
# Features: todos los outputs de módulos 1-6 + indicadores técnicos de cada estrategia
# Output: {allow, confidence, contracts_multiplier, reason}
# NO binario — retorna probabilidad y el NT8 interpreta
```

---

## CONCEPTOS MATEMÁTICOS INTEGRADOS

### Cadenas de Markov
- Modelan transiciones de régimen: P(estado_mañana | estado_hoy)
- Memoria de 1 día (primer orden) — ampliar a 2 días si datos suficientes
- Alimentadas por market_logs diarios (tide_score como variable de estado)
- Permiten anticipar régimen ANTES de que cambie

### Von Neumann — Minimax
- No optimizamos para el mejor resultado esperado
- Optimizamos para minimizar el arrepentimiento en el peor caso
- Función de utilidad asimétrica: perder duele 2x más que ganar satisface
- Justifica el Sortino como métrica primaria (penaliza más pérdidas)
- El regret_risk bloquea trades aunque la esperanza matemática sea positiva

### Tit for Tat
- Cada estrategia tiene su propio "credit score" dinámico
- Empieza con confianza máxima (cooperación)
- Refleja el comportamiento reciente de la estrategia
- Se recupera cuando la estrategia gana de nuevo (perdona rápido)
- Implementa diversificación dinámica: reduce correlación en días malos

### Monte Carlo
- 10,000 simulaciones bootstrap del historial de trades
- Calcula P(ruina) = P(drawdown > $7,500 Apex limit)
- Determina sizing seguro al percentil 95
- Kelly Criterion ajustado para no reventar

---

## MÉTRICAS TARGET DARWIN/X 2027

| Métrica | Target mínimo | Target ideal | Darwin/X |
|---------|--------------|--------------|----------|
| Sharpe anual | > 1.0 | > 1.5 | > 2.0 |
| Sortino anual | > 2.0 | > 3.0 | > 4.0 |
| MaxDD | < $7,000 | < $5,000 | < $4,000 |
| Profit/mes (Apex) | > $2,000 | > $5,000 | > $8,000 |
| Win rate portafolio | > 30% | > 40% | — |
| Correlación entre estrategias | < 0.7 | < 0.5 | < 0.4 |
| P(ruin anual) | < 10% | < 5% | < 2% |

---

## MODULO NUEVO: Algoritmos Genéticos (Junio 2026)

### Objetivo: auto-evolucionar params de cada estrategia sin intervención manual

```python
# ga_optimizer.py
# Reemplaza el Walk-Forward manual para búsqueda de params óptimos

def fitness(bot_params, trade_history):
    """Función de aptitud — Axelrod + Von Neumann"""
    return (
        bot_params.sortino        * 0.40 +   # calidad retorno
        (1 - bot_params.max_dd / 7500) * 0.30 +  # supervivencia Apex
        bot_params.r_squared      * 0.20 +   # consistencia curva
        (1 - bot_params.ruin_prob) * 0.10    # Monte Carlo safety
    )

# Proceso evolutivo:
# 1. Población: 200 variantes de cada estrategia con params aleatorios
# 2. Backtest en datos out-of-sample (WFO guard anti-overfitting)
# 3. Top 50% sobreviven, bottom 50% eliminados
# 4. Crossover: mezclar params de dos ganadores
# 5. Mutación: pequeño cambio aleatorio en 1-2 params
# 6. 50 generaciones → params óptimos
# 7. Validar resultado en forward test antes de usar en paper

# Regla Axelrod crítica: "No seas demasiado astuto"
# GA puede over-fitear igual que grid search manual
# SIEMPRE validar con WFO: optimizar 2023-2024, testar 2025-2026
```

### La "Sombra del Futuro" en sizing (Axelrod + Markov):
```python
# w = prob de que el régimen actual continúe mañana (output del Markov)
# Valor de mantener posición alineada con régimen:
valor = ganancia_esperada / (1 - w)

# Si w=0.75 (régimen persistente) → valor × 4  → mantener/aumentar
# Si w=0.25 (régimen cambiando)   → valor × 1.33 → reducir/salir
# Brain usa w como multiplicador de sizing según alineación con régimen
```

## MODULO: Skinner Reward Shaping (brain_v3.py)
- Premiar PROCESO no solo resultado: proceso_score × P&L
- proceso_score evalúa: alineación con tide, CI favorable, respeto noticias, sizing correcto, ETD bajo
- Un trade perdedor bien ejecutado enseña más que un ganador por suerte
- Castigo explícito por mediocridad: si tft < 0.30 y 5+ días perdiendo → epsilon_override=0.50
- Moldeamiento gradual (shaping): fase1=solo tide, fase2=tide+CI, fase3=todo el contexto
- Ver función completa en: `Bot_Quant_IA/brain_v3_reward.py` (pendiente implementar Mayo)

## MÓDULO: Imitation Learning — Fase 0 de brain_v3 (ANTES del PPO)

### Concepto: los 30 millones de partidas humanas de AlphaGo
Las estrategias actuales validadas (StatMean, BBv5, PivotTrend, etc.) son el equivalente
de las partidas de Go profesionales. Antes de que el agente explore por su cuenta con RL,
debe IMITAR lo que ya funciona mediante Behavioral Cloning.

**Por qué es crítico:** sin esta fase, el agente empieza desde cero y tarda millones de
episodios en descubrir lo que tus estrategias ya saben. Con BC, arranca desde un estado
competente y el RL solo necesita refinarlo y superarlo.

```python
# imitation_learning.py — Fase 0 (Mayo, antes de brain_v3 PPO)
from imitation.algorithms import bc
from imitation.data import rollout

# Paso 1: Generar "demos" corriendo cada estrategia en histórico
# Cada demo = (observación_brain, acción_tomada) en cada bar
# acción_tomada = 0 (WAIT) si la estrategia no tenía señal
#                 1 (LONG) si la estrategia entró long
#                 2 (SHORT) si la estrategia entró short
#                 3 (CLOSE) si la estrategia cerró posición

def generar_demos_desde_estrategia(strategies_pnl_historico, market_logs_historico):
    """
    Reconstruye las decisiones de cada estrategia desde los PnL logs
    y las mapea al estado del brain en ese momento.
    """
    demos = []
    for fecha, pnl_data in strategies_pnl_historico.items():
        brain_state = market_logs_historico[fecha]  # tide, CI, etc.
        for trade in pnl_data['trades']:
            obs = brain_state_to_observation(brain_state)
            accion = trade_to_action(trade)  # LONG/SHORT/CLOSE
            demos.append((obs, accion))
    return demos

# Paso 2: Behavioral Cloning — el agente imita las decisiones históricas
bc_trainer = bc.BC(
    observation_space=env.observation_space,
    action_space=env.action_space,
    demonstrations=rollout.flatten_trajectories(demos),
    rng=np.random.default_rng(0),
)
bc_trainer.train(n_epochs=50)
bc_trainer.policy.save("midas_imitation_v1")

# Paso 3: Cargar como punto de partida del PPO (no entrenar desde cero)
model = PPO.load_from_imitation(bc_trainer.policy)
model.learn(total_timesteps=500_000)  # Solo refinamiento, converge mucho más rápido
```

**Ventaja clave:** Midas no necesita descubrir que "conviene no operar en FOMC" —
ya lo sabe porque lo aprendió de tus demos. El RL solo añade lo que tú no sabes.

---

## MÓDULO: Recurrent PPO con LSTM (brain_v3 — Mayo)

### Problema del PPO estándar
El observation space actual ([tide_score, CI, trends, hora, tft, markov_w, ...]) es
un vector estático: el agente solo ve el momento presente. Pero en trading, importa
el CONTEXTO de las últimas 2-4 horas dentro de la misma sesión.

Con LSTM, el agente tiene memoria interna que persiste dentro del episodio:
- Recuerda si la primera hora fue bajista aunque ahora parezca neutral
- Detecta divergencias entre sesiones (ayer fue bajista, hoy intenta subir)
- Mantiene estado de "confianza acumulada" a lo largo del día

```python
# brain_v3.py — usar RecurrentPPO en vez de PPO estándar
from sb3_contrib import RecurrentPPO  # pip install sb3-contrib

model = RecurrentPPO(
    "MlpLstmPolicy",
    vec_env,
    learning_rate=3e-4,
    n_steps=2048,
    batch_size=64,
    n_epochs=10,
    lstm_hidden_size=256,   # Estado oculto — "memoria de trabajo" del agente
    n_lstm_layers=2,        # LSTM apilado — capta patrones de diferente escala temporal
    gamma=0.99,
    gae_lambda=0.95,
    clip_range=0.2,
    ent_coef=0.01,
    tensorboard_log="./tb_logs/",
    verbose=1
)

# IMPORTANTE: al hacer predict en producción, hay que pasar el lstm_state
# y episode_start correctamente para mantener la memoria entre barras
lstm_states = None
episode_start = True

while sesion_activa:
    obs = get_brain_observation()
    action, lstm_states = model.predict(
        obs,
        state=lstm_states,
        episode_start=episode_start,
        deterministic=True
    )
    episode_start = False  # Solo True al inicio de cada sesión
    ejecutar_accion(action)
```

**Stack adicional necesario:**
```bash
pip install sb3-contrib  # RecurrentPPO no está en stable-baselines3 base
```

---

## MÓDULO: Criterio de Deployment — Ciclo Semanal de Re-entrenamiento

### El problema sin este criterio
Sin una regla explícita de cuándo reemplazar el modelo, hay dos errores posibles:
1. Desplegar un modelo peor que el actual (regresión)
2. Nunca desplegar porque "siempre podría mejorar" (parálisis)

### La regla: Sharpe × 1.05

```python
# weekly_retraining.py — ejecutar cada lunes antes de la apertura (Mayo+)

def ciclo_reentrenamiento_semanal():
    """
    Ciclo completo: re-entrenar → evaluar → decidir → desplegar o no.
    Equivalente al torneo de AlphaZero: el challenger debe ganar al campeón actual.
    """
    # 1. Cargar modelo actual (el campeón)
    campeon = RecurrentPPO.load("midas_campeon_actual")

    # 2. Fine-tuning con datos de las últimas 4 semanas (no desde cero)
    datos_frescos = cargar_datos_recientes(semanas=4)
    env_fresco = MidasTradingEnv(datos_frescos)
    challenger = campeon  # Copiar pesos del campeón, no empezar de cero
    challenger.set_env(SubprocVecEnv([lambda: env_fresco] * 4))
    challenger.learn(total_timesteps=200_000)  # Fine-tuning, no entrenamiento completo

    # 3. Evaluación en datos out-of-sample (últimas 2 semanas, sin entrenar)
    eval_env = MidasTradingEnv(cargar_datos_recientes(semanas=2))
    sharpe_campeon    = evaluar_sharpe(campeon,    eval_env, n_episodios=50)
    sharpe_challenger = evaluar_sharpe(challenger, eval_env, n_episodios=50)

    # 4. CRITERIO DE DEPLOYMENT: challenger gana solo si es >5% mejor
    UMBRAL = 1.05
    if sharpe_challenger > sharpe_campeon * UMBRAL:
        challenger.save("midas_campeon_actual")
        campeon.save(f"midas_archivo_{fecha_hoy()}")  # Guardar historial
        log(f"NUEVO CAMPEÓN desplegado. Sharpe: {sharpe_challenger:.3f} vs {sharpe_campeon:.3f}")
    else:
        log(f"Campeón actual se mantiene. Challenger: {sharpe_challenger:.3f} vs {sharpe_campeon:.3f}")

    # 5. Alertar si el campeón está degradándose (distribution shift)
    if sharpe_campeon < 0.8:  # Era >1.0, ahora <0.8 → mercado cambió
        log("⚠️ ALERTA: campeón actual degradado. Considerar re-entrenamiento completo.")

def evaluar_sharpe(model, env, n_episodios=50):
    retornos = []
    for _ in range(n_episodios):
        obs, _ = env.reset()
        pnl_episodio = 0
        lstm_states = None
        done = False
        while not done:
            action, lstm_states = model.predict(obs, state=lstm_states, deterministic=True)
            obs, reward, term, trunc, info = env.step(action)
            pnl_episodio += reward
            done = term or trunc
        retornos.append(pnl_episodio)
    arr = np.array(retornos)
    return arr.mean() / (arr.std() + 1e-8) * np.sqrt(252)
```

**Frecuencia:** cada lunes antes de la apertura (o viernes después del cierre).
**Historial:** guardar todos los modelos archivados — si el mercado regresa a un régimen anterior,
el modelo viejo puede ser mejor que el nuevo.

---

## VISION DEEPMIND — MIDAS ZERO (camino a 2027)

### La progresión AlphaGo → Midas:
| DeepMind | Midas | Fecha |
|---|---|---|
| DQN/Atari (features humanas) | Midas v2 RF + contexto | Abril 2026 |
| **BC Fase 0** (imitar estrategias) | **Imitation Learning desde PnL logs** | **Mayo 2026** |
| AlphaGo (datos históricos + RL) | Midas v3 RecurrentPPO + Skinner reward | Mayo-Jun 2026 |
| AlphaGo Zero (autodidacta puro) | Midas Zero (transformer raw) | 2027 |

### Clave: Midas no juega en papel en tiempo real — simula millones de sesiones en minutos
- 3 años de NQ histórico = 750 sesiones
- Cada episodio simulado = 0.1 segundos
- 1,000,000 episodios = 400 años de experiencia = ~28 horas de entrenamiento en laptop

### Stack técnico necesario:
```bash
pip install stable-baselines3 sb3-contrib gymnasium torch imitation
```
- `MidasTradingEnv(gym.Env)` — tablero de Go de Midas
- Observation: [tide_score, CI, trends, hora, tft_scores, drawdown, regret_risk, markov_w, ...]
- Actions: 0=WAIT, 1=LONG, 2=SHORT, 3=CLOSE, 4=REVERSE
- Reward: calcular_recompensa_skinner(pnl, contexto)
- Algoritmo: **RecurrentPPO** con LSTM — más memoria que PPO estándar
- Fase 0: **Behavioral Cloning** desde estrategias históricas antes de RL

### Niveles de evolución:
1. **Midas BC** (Mayo): Behavioral Cloning desde estrategias validadas → punto de partida competente
2. **Midas AlphaGo** (Mayo-Jun): RecurrentPPO + Skinner reward + ciclo semanal de reentrenamiento
3. **Midas AlphaGo Self-Play** (Oct 2026): League Training contra regímenes + criterio Sharpe ×1.05
4. **Midas Zero** (2027): MuZero 3-red architecture sin features humanas (ver abajo)

---

## TEMPERATURA τ — Training vs. Producción (brain_v3 Mayo+)

Concepto directo de MCTS/AlphaZero aplicado a Midas:

| Fase | τ | Comportamiento |
|------|---|----------------|
| Entrenamiento | τ = 1.0 | Exploración amplia: el agente prueba acciones menos probables para aprender |
| Evaluación/paper | τ = 0.3 | Semi-explotación: algo de exploración controlada |
| Live / Apex real | τ → 0 | Explotación pura: siempre ejecuta la acción con mayor valor Q |

```python
# En MidasTradingEnv — cómo aplicar τ al predict de producción:
def get_action(model, obs, lstm_states, tau=1.0):
    action_probs, lstm_states = model.predict(obs, state=lstm_states, deterministic=False)

    if tau < 0.1:
        # τ ≈ 0: pura explotación — acción con mayor probabilidad siempre
        return np.argmax(action_probs), lstm_states
    else:
        # τ > 0: suavizar distribución con temperatura
        logits = np.log(action_probs + 1e-8) / tau
        probs = np.exp(logits) / np.exp(logits).sum()
        return np.random.choice(len(probs), p=probs), lstm_states

# Uso práctico:
# - Durante entrenamiento:   get_action(model, obs, states, tau=1.0)
# - Durante paper trading:   get_action(model, obs, states, tau=0.3)
# - Durante Apex real:       get_action(model, obs, states, tau=0.05)
```

**Por qué importa:** sin τ explícito, el agente en producción puede seguir explorando aleatoriamente
y tomar trades que sabe que son subóptimos. τ → 0 en live garantiza que siempre usa su mejor criterio.

---

## LEAGUE TRAINING — Prevención de Strategy Collapse (Oct 2026)

### El problema del self-play puro
Si Midas solo juega contra sí mismo, puede especializarse en un tipo de mercado y colapsar
cuando el régimen cambia. AlphaStar lo resolvió con una liga de agentes con distintos objetivos.

### La liga de Midas: 3 ligas de regímenes
En vez de un solo entorno de entrenamiento, Midas entrena contra una liga simultánea:

```python
# league_training.py — Oct 2026
# Tres ligas paralelas, cada una representando un régimen distinto

LEAGUE_CONFIG = {
    "trending_league": {
        "datos": datos_con_tendencia_fuerte,      # 2017, 2020-rally, 2023
        "tide_score_range": (1.5, 3.0),           # bull/bear fuerte
        "peso_inicial": 0.33,
    },
    "volatile_league": {
        "datos": datos_alta_volatilidad,           # Mar2020, Oct2022, eventos FOMC
        "atr_percentile": ">80%",
        "peso_inicial": 0.33,
    },
    "mean_revert_league": {
        "datos": datos_choppy_laterales,           # consolidaciones 2015-2016, 2018
        "choppiness_range": (55, 75),              # CI alta → sin tendencia
        "peso_inicial": 0.33,
    },
}

def entrenar_con_liga(model, league_config, total_timesteps=2_000_000):
    """
    Alterna entrenamiento entre las 3 ligas.
    Si el agente colapsa en una liga, aumenta su peso para forzar re-aprendizaje.
    """
    for step in range(total_timesteps):
        # Muestrear liga según pesos actuales (ajustados por rendimiento)
        liga = sample_league(league_config)
        env = NQTradingEnv(liga["datos"])

        model.set_env(env)
        model.learn(total_timesteps=10_000)  # Mini-batch por liga

        # Evaluar rendimiento en cada liga
        for nombre, cfg in league_config.items():
            sharpe_liga = evaluar_sharpe(model, NQTradingEnv(cfg["datos"]))

            # Si está colapsando en una liga → aumentar su peso
            if sharpe_liga < 0.5:
                cfg["peso_inicial"] = min(cfg["peso_inicial"] * 1.2, 0.60)
                log(f"⚠️ Collapse detectado en {nombre}. Peso aumentado a {cfg['peso_inicial']:.2f}")
```

**Regla crítica:** Midas debe mantener Sharpe > 0.8 en las 3 ligas simultáneamente
antes de pasar a paper trading real. Si gana en trending pero colapsa en volatile → no está listo.

---

## MIDAS ZERO 2027 — Arquitectura MuZero

### Concepto: aprender el modelo del mercado desde adentro
AlphaZero necesita las reglas del juego programadas explícitamente.
MuZero las aprende solo. Midas Zero hace lo mismo con el mercado: no recibe features humanas
(tide_score, CI, etc.) — aprende su propia representación del mercado desde OHLCV crudo.

### Las 3 redes de Midas Zero:

```
INPUT: OHLCV crudo + Volume → sin indicadores, sin features humanas
  ↓
┌─────────────────────────────────────────────────────────────────┐
│ RED 1 — REPRESENTACIÓN: h(OHLCV) = estado_latente              │
│ "¿Qué está pasando en el mercado ahora mismo?"                 │
│ ResNet profundo → comprime 60 barras de OHLCV en vector latente│
└─────────────────────────────────────────────────────────────────┘
  ↓ estado_latente
┌─────────────────────────────────────────────────────────────────┐
│ RED 2 — DINÁMICA: g(estado, acción) = (pnl_esperado, sig_estado)│
│ "¿Qué pasaría si entro long/short/espero ahora?"               │
│ Imagina consecuencias sin ejecutar la acción en el mercado real │
│ Permite planificación interna tipo MCTS sin simulador externo   │
└─────────────────────────────────────────────────────────────────┘
  ↓ siguiente_estado_latente
┌─────────────────────────────────────────────────────────────────┐
│ RED 3 — PREDICCIÓN: f(estado) = (política, valor)              │
│ "¿Cuál es la mejor acción y qué tan buena es esta posición?"   │
│ Dual-head: política (distribución sobre WAIT/LONG/SHORT/CLOSE) │
│            valor (Sharpe esperado de la sesión restante)        │
└─────────────────────────────────────────────────────────────────┘
```

**Ventaja sobre brain_v3:** Midas Zero no depende de que tide_score o CI estén bien calculados.
Descubre sus propios "indicadores" internos en la red de representación. Más robusto a cambios
en el mercado porque no hereda los sesgos humanos del diseño de features.

**Prerequisito:** necesita brain_v3 funcionando bien en live primero.
Midas Zero es el objetivo 2027, no antes.

---

## MAPA COMPLETO DE IMPLEMENTACIÓN — 6 Libros Analizados (23/03/2026)

### Implementar AHORA (datos ya disponibles desde Feb/Mar 2026)

| # | Concepto | Fuente | Archivo | Urgencia |
|---|---|---|---|---|
| 1 | **Alpha Decay IC-rolling** — detecta degradación del edge antes que el Sortino | Grinold & Kahn | market_monitor_logger.py | 🔴 Esta semana |
| 2 | **Correlation Breakdown EWMA+CUSUM** — habría detectado 17/03 y 20/03 | ML Risk Mgmt | correlation_monitor.py | 🔴 Esta semana |
| 3 | **CUSUM Strategy Breakdown** — pausa estrategias con degradación estadística | Ernie Chan | market_monitor_logger.py | 🔴 Esta semana |
| 4 | **Kelly Multivariate** — sizing con matriz de correlación (previene 17/03) | Ernie Chan | monte_carlo_sizer.py | 🔴 Esta semana |

### Semana 1 Abril (junto con módulo Markov)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 5 | **EM Online HMM** con forgetting factor ρ=0.97 (actualización sin reentrenar) | HMM book | markov_regime.py |
| 6 | **Vector observación 3D** [ret, \|ret\|, Δvol] para HMM (+18% accuracy) | HMM book | markov_regime.py |
| 7 | **BIC para selección n_estados** (confirma 3 óptimo para Nasdaq) | HMM book | markov_regime.py |
| 8 | **Variance Ratio Test** — filtro mean reversion vs trend cada 60s | Ernie Chan | markov_regime.py |
| 9 | **Breadth efectivo** N/(1+(N-1)×ρ) — con 17 estrategias ρ=0.25 → Breadth≈5.5 | Grinold | hrp_optimizer.py |
| 10 | **Kalman Spread NQ/ES** — convierte market_breadth en feature estacionario | From Data | market_monitor_logger.py |
| 11 | **Autoencoder Anomaly Detection** — alerta cuando mercado sale del régimen conocido | Decoding QM | anomaly_detector.py |
| 12 | **CVaR/Expected Shortfall** — más robusto que VaR para fat tails del NQ | ML Risk | monte_carlo_sizer.py |

### Semana 2 Abril (junto con News Filter + TFT)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 13 | **Regime Persistence Filter** — 3 días consecutivos para confirmar cambio | HMM book | markov_regime.py |
| 14 | **Kalman Regime Tracker** — slope continuo (reemplaza tide_score estático 1x/día) | Ernie Chan | market_monitor_logger.py |
| 15 | **PSI Drift Detection** — detecta cuando features cambian distribución | From Data | autocritica_daily.py |
| 16 | **Transfer Coefficient TC** — IR real = TC×IC×√Breadth (con restricciones Apex) | Grinold | tit_for_tat.py |
| 17 | **Signal Combination IC-ponderada** — ponderar market_breadth+multi_osc por IC (no 1/N) | Grinold | brain_v2.py |
| 18 | **SVM Regime Classifier** — complementa HMM sin asumir gaussianidad de retornos | Decoding QM | markov_regime.py |
| 19 | **Stress Testing NQ** — validar estrategias bajo Covid crash, Bear 2022, FOMC extremo | ML Risk | stress_tester.py |

### Semana 3 Abril (junto con Monte Carlo Risk Engine)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 20 | **Kelly-HMM por régimen** — Half-Kelly condicional al estado bull/neutral/bear | HMM book | monte_carlo_sizer.py |
| 21 | **Marginal IR** — criterio matemático de admisión de nuevas estrategias | Ernie Chan | hrp_optimizer.py |
| 22 | **Dynamic Risk Limits** HMM — Quiet/Volatile/Crisis → límites automáticos | ML Risk | regret_engine.py |
| 23 | **Optimal weights Grinold** — λ = aversión riesgo unifica Von Neumann + Grinold | Grinold | regret_engine.py |

### Semana 4 Abril (junto con brain_v2 RF)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 24 | **Regime-Aware Ensemble** — pesos de estrategias varían por régimen (BULL≠BEAR≠SIDEWAYS) | Decoding QM | brain_v2.py |

### Mayo 2026

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 25 | **LSTM Drawdown Predictor** P(DD > $2,000 mañana) | ML Risk | brain_v3.py |
| 26 | **Log-Signature features** (Rough Path Theory) — geometría del path completo | From Data | brain_v2.py |
| 27 | **Order Imbalance Score** — microestructura intraday sin Level 2 | From Data | market_monitor_logger.py + NT8 |

---

### El insight más importante de los 6 libros combinados:

> **Con 17 estrategias y correlación promedio ρ=0.25 entre ellas,
> el Breadth efectivo real de Midas es ≈5.5, no 17.
> El IR teórico = IC×√17 es en realidad IC×√5.5 — casi la mitad.
> El foco de Mayo en adelante no es AGREGAR estrategias
> sino SUSTITUIR las correlacionadas por ortogonales (OBOrderFlow en 1-min).**

---

## CAPAS NUEVAS — Fuente: "ML for Algorithmic Trading" (Stefan Jansen, 2nd Ed.)

---

### CAPA: Deflated Sharpe Ratio — IMPLEMENTAR AHORA (antes de Abril)

**Problema que resuelve:** Con 17+ estrategias testeadas sobre los mismos datos históricos,
el Sortino/Sharpe del "mejor" backtest está inflado por múltiples comparaciones simultáneas.
Con 2 años de datos históricos, solo se pueden comparar ~7 estrategias con confianza estadística.

```python
# deflated_sr.py — aplicar retroactivamente al ranking actual del portfolio
# Fuente: Bailey & López de Prado (2014)

import numpy as np
from scipy.stats import norm

def deflated_sharpe_ratio(observed_sr, n_trials, sr_std, skew, kurtosis, T):
    """
    observed_sr: Sharpe anualizado observado de la estrategia
    n_trials:    número de estrategias testeadas con los mismos datos (17 en Midas)
    sr_std:      std del Sharpe a través de las n_trials estrategias
    skew:        asimetría de los retornos de la estrategia
    kurtosis:    exceso de kurtosis de los retornos
    T:           número de observaciones (días de backtest)
    """
    # Sharpe esperado del mejor de n_trials por azar puro
    E_max_sr = sr_std * (
        (1 - np.euler_gamma) * norm.ppf(1 - 1/n_trials) +
        np.euler_gamma * norm.ppf(1 - 1/(n_trials * np.e))
    )

    # Sharpe ajustado por no-normalidad de retornos
    sr_adj = observed_sr * np.sqrt(
        (1 - skew * observed_sr + (kurtosis - 1)/4 * observed_sr**2) / T
    )

    # DSR: probabilidad de que el SR observado sea real (no por suerte)
    dsr = norm.cdf((sr_adj - E_max_sr) / sr_std)
    return dsr

# Uso práctico sobre el portfolio actual:
# DSR > 0.95 → estrategia estadísticamente válida
# DSR < 0.95 → posible false alpha — necesita más datos antes de aumentar sizing
```

**Impacto inmediato:** Recalcular el Top 5 con DSR. El ranking por Sortino crudo puede cambiar.
StatMeanCross tiene Sortino=38 pero fue la estrategia más "buscada" → DSR puede ser menor de lo esperado.

---

### CAPA: GARCH(1,1) — Feature de Volatilidad (Semana 1 Abril, junto con Markov)

**Problema que resuelve:** El `tide_score` y el ATR capturan tendencia y rango, pero no
el **régimen de volatilidad condicional** — si el mercado está en modo "nervioso" (vol alta
persistente) o "tranquilo". GARCH(1,1) modela que la volatilidad de hoy depende de la
volatilidad de ayer y del shock de ayer.

```python
# garch_vol.py — agregar al market_monitor_logger.py
# pip install arch

from arch import arch_model
import pandas as pd

def calcular_garch_vol(returns_series, horizon=1):
    """
    returns_series: Serie de retornos diarios del NQ (Close to Close %)
    horizon:        días hacia adelante para la forecast
    Devuelve: volatilidad anualizada esperada para mañana
    """
    model = arch_model(returns_series * 100,  # escalar para estabilidad numérica
                       vol='GARCH', p=1, q=1,
                       dist='t')              # t-student: fat tails del mercado
    result = model.fit(disp='off', show_warning=False)

    forecast = result.forecast(horizon=horizon)
    vol_diaria = np.sqrt(forecast.variance.values[-1, 0]) / 100
    vol_anual  = vol_diaria * np.sqrt(252)

    # Clasificar régimen de volatilidad
    vol_percentile = calcular_percentil_historico(vol_diaria, returns_series)

    regime = (
        "LOW_VOL"    if vol_percentile < 25 else
        "NORMAL_VOL" if vol_percentile < 75 else
        "HIGH_VOL"   if vol_percentile < 90 else
        "EXTREME_VOL"
    )

    return {
        "garch_vol_daily":   round(vol_diaria, 5),
        "garch_vol_annual":  round(vol_anual, 4),
        "vol_percentile":    round(vol_percentile, 1),
        "vol_regime":        regime,
        "sizing_adj_garch":  (  # ajuste de sizing según régimen
            1.20 if regime == "LOW_VOL"    else
            1.00 if regime == "NORMAL_VOL" else
            0.60 if regime == "HIGH_VOL"   else
            0.25   # EXTREME_VOL → modo supervivencia
        )
    }
```

**Integración:** `garch_vol_regime` y `sizing_adj_garch` se agregan al output del market_log diario
y al brain output final como feature del Random Forest.

---

### CAPA: Information Coefficient (IC) — Actualización de Tit for Tat (Semana 2 Abril)

**Problema que resuelve:** El credit score de TFT actual usa solo PnL de los últimos 5 trades
(señal ruidosa). El IC mide la **habilidad predictiva real** de una estrategia: correlación
de Spearman entre la dirección de la señal y el retorno observado. Más robusto que PnL bruto.

```python
# actualizar tit_for_tat.py con IC como métrica adicional

from scipy.stats import spearmanr

def calcular_ic_estrategia(signals_history, returns_history, window=20):
    """
    signals_history: lista de 1 (Long), -1 (Short), 0 (Flat) de los últimos N trades
    returns_history: lista de retornos reales al cierre de cada trade
    window:          número de trades para calcular el IC rolling
    Devuelve: IC rolling (entre -1 y +1), donde >0.05 ya es útil en trading
    """
    if len(signals_history) < window:
        return 0.0  # insuficiente historia

    recent_signals = signals_history[-window:]
    recent_returns = returns_history[-window:]

    ic, p_value = spearmanr(recent_signals, recent_returns)

    # IC por azar esperado: ~0 con p > 0.05
    ic_significativo = ic if p_value < 0.05 else 0.0

    return round(ic_significativo, 4)

def tft_multiplier_con_ic(pnl_history, signals_history, returns_history):
    """
    Combina PnL reciente (TFT original) con IC para credit score más robusto.
    """
    # TFT original (PnL últimos 5 trades)
    tft_base = calcular_tft_base(pnl_history)

    # IC rolling 20 trades
    ic = calcular_ic_estrategia(signals_history, returns_history)

    # Multiplicador compuesto: TFT × (1 + IC bonus)
    # IC=0.10 → bonus 20% | IC=0.20 → bonus 40% | IC<0 → penalización
    ic_bonus = ic * 2.0   # escalar IC al rango del multiplier
    multiplier = tft_base * (1 + ic_bonus)

    return round(np.clip(multiplier, 0.10, 1.50), 3)
```

**Fundamental Law integration:** IR ≈ IC × √Breadth donde Breadth = trades/mes.
Estrategia con IC=0.05 y 200 trades/mes → IR esperado 0.71 → válida para el portfolio.

---

### CAPA: HRP (Hierarchical Risk Parity) — Sizing del Portfolio (Semana 3 Abril)

**Problema que resuelve:** El sizing actual es manual + Von Neumann. HRP detecta
**automáticamente** los clusters de correlación entre estrategias y asigna pesos
inversamente proporcionales a la varianza de cada cluster. Habría detectado
StatMean+EMATrend como un cluster y reducido su peso combinado antes del 17/03.

```python
# hrp_optimizer.py
# pip install PyPortfolioOpt

from pypfopt import HRPOpt
import pandas as pd

def calcular_hrp_weights(pnl_matrix_df):
    """
    pnl_matrix_df: DataFrame con PnL diario de cada estrategia (filas=días, cols=estrategias)
    Devuelve: dict con peso óptimo por estrategia (suman 1.0)
    """
    # HRP requiere matriz de retornos (aquí usamos PnL normalizado)
    returns = pnl_matrix_df.pct_change().dropna()

    hrp = HRPOpt(returns)
    hrp_weights = hrp.optimize()

    # Convertir a multipliers sobre el sizing base (no normalizar a 1.0 sino escalar)
    max_weight = max(hrp_weights.values())
    multipliers = {k: round(v / max_weight, 3) for k, v in hrp_weights.items()}

    return multipliers

def detectar_clusters_correlacion(pnl_matrix_df, threshold=0.70):
    """
    Detecta pares de estrategias con correlación > threshold.
    Salida: lista de clusters que deben tratarse como un solo slot.
    """
    corr_matrix = pnl_matrix_df.corr(method='spearman')
    clusters = []

    for i in range(len(corr_matrix)):
        for j in range(i+1, len(corr_matrix)):
            if abs(corr_matrix.iloc[i, j]) > threshold:
                clusters.append({
                    "estrategia_A": corr_matrix.index[i],
                    "estrategia_B": corr_matrix.columns[j],
                    "correlacion":  round(corr_matrix.iloc[i, j], 3),
                    "accion":       "TRATAR_COMO_UN_SLOT"
                })

    return clusters
```

**Integración:** HRP corre semanalmente sobre los `strategies_pnl` logs acumulados.
Los pesos HRP se combinan con TFT multipliers y GARCH sizing_adj para el `contracts_multiplier` final.

---

### CAPA: Wavelet Denoising — Preprocesamiento de Features (Semana 2 Abril)

**Problema que resuelve:** CI (Choppiness Index) y tide_score tienen ruido de alta frecuencia
que genera señales espurias en el Random Forest. Wavelet denoising elimina ese ruido
sin introducir lag (a diferencia de EMA) y sin perder los picos importantes (ATR spikes).

```python
# wavelet_filter.py — 3 líneas de código
# pip install PyWavelets

import pywt
import numpy as np

def wavelet_denoise(signal, wavelet='db6', level=2, threshold_mode='soft'):
    """
    signal:         array de valores de la feature (ej: serie de CI diarios)
    wavelet:        'db6' = Daubechies 6 (óptimo para series financieras)
    level:          niveles de descomposición (2 = elimina ruido fino)
    Devuelve: señal suavizada sin lag, preservando estructura de largo plazo
    """
    coeffs = pywt.wavedec(signal, wavelet, level=level)

    # Threshold universal (Donoho & Johnstone 1994)
    sigma = np.median(np.abs(coeffs[-1])) / 0.6745
    threshold = sigma * np.sqrt(2 * np.log(len(signal)))

    # Suavizar coeficientes de detalle (preservar aproximación)
    coeffs_denoised = [coeffs[0]] + [
        pywt.threshold(c, threshold, mode=threshold_mode)
        for c in coeffs[1:]
    ]

    return pywt.waverec(coeffs_denoised, wavelet)[:len(signal)]

# Aplicar a los features del brain antes de pasar al RF:
# ci_denoised        = wavelet_denoise(ci_series)
# tide_denoised      = wavelet_denoise(tide_series)
# breadth_denoised   = wavelet_denoise(breadth_series)
```

---

### CAPA: Purging + Embargoing en CV — Validación del brain_v2 (Semana 4 Abril)

**Problema que resuelve:** Al entrenar el Random Forest sobre los logs diarios, los labels
("¿fue buena decisión activar esta estrategia?") se evalúan sobre el PnL del día completo.
Sin Purging, hay look-ahead implícito que infla el R² artificialmente.
**Esta capa es lo que separa un R²=0.85 real de uno falso.**

```python
# cv_financial.py
# pip install timeseriescv  (o implementar manualmente)

from timeseriescv import CombPurgedKFoldCV
import numpy as np

def crear_cv_financiero(n_samples, n_splits=5, purge_gap=5, embargo_gap=3):
    """
    n_samples:   número de días de datos de entrenamiento
    purge_gap:   días a eliminar del training set que solapan con el test (5 días = 1 semana)
    embargo_gap: días buffer después del test set para evitar contaminación
    Devuelve: generador de splits (train_idx, test_idx) para usar con cross_val_score
    """
    cv = CombPurgedKFoldCV(
        n_splits=n_splits,
        n_test_splits=2,
        purge_gap=purge_gap,
        embargo_gap=embargo_gap
    )
    return cv

# Uso en brain_v2.py:
# cv = crear_cv_financiero(len(X_train))
# scores = cross_val_score(rf_model, X_train, y_train, cv=cv, scoring='r2')
# R² válido = scores.mean()  ← este es el número que importa
```

**Regla:** Si el R² con purging/embargoing cae por debajo de 0.85 → el modelo no tiene
suficiente señal real. Aumentar features o esperar más datos antes de deployar.

---

### CAPA: SHAP Values — Auto-Crítica Inteligente del brain_v2 (Semana 4 Abril)

**Problema que resuelve:** La auto-crítica diaria (Módulo 1b) sabe CUÁNDO se equivocó Midas
pero no POR QUÉ feature se equivocó. SHAP explica cada predicción individual del RF.

```python
# agregar a brain_v2.py después de entrenar el Random Forest

import shap

def analizar_decision_con_shap(rf_model, X_hoy, feature_names):
    """
    rf_model:      Random Forest entrenado
    X_hoy:         features del día actual (1 fila)
    feature_names: nombres de las features
    Devuelve: dict con contribución de cada feature a la decisión de hoy
    """
    explainer = shap.TreeExplainer(rf_model)
    shap_values = explainer.shap_values(X_hoy)

    # Para clasificación binaria (activar/no activar estrategia):
    contributions = dict(zip(feature_names, shap_values[1][0]))

    # Top 3 features que más influyeron hoy (positivas y negativas)
    sorted_contrib = sorted(contributions.items(), key=lambda x: abs(x[1]), reverse=True)

    return {
        "top_features_positivas": [(k, round(v, 4)) for k, v in sorted_contrib if v > 0][:3],
        "top_features_negativas": [(k, round(v, 4)) for k, v in sorted_contrib if v < 0][:3],
        "razon_decision":         f"{sorted_contrib[0][0]}={round(sorted_contrib[0][1],3)} "
                                  f"fue el factor dominante"
    }

# Integración con auto-crítica: si la decisión fue INCORRECTA,
# SHAP identifica qué feature "mintió" ese día → acumular en midas_accuracy_historico.json
# Después de 30 días: detectar si una feature tiene SHAP alto pero accuracy baja → feature degradada
```

---

### CAPA: TimeGAN — Datos Sintéticos para brain_v3 (Mayo 2026)

**Problema que resuelve:** Al iniciar el entrenamiento de brain_v3 (RecurrentPPO) en Mayo,
solo habrá ~45 días de paper trading como ground truth. TimeGAN genera 1,000 trayectorias
sintéticas de PnL diario por estrategia, preservando correlaciones reales entre estrategias,
fat tails, clustering de drawdowns y volatilidad autocorrelada.

```
# timegan_augment.py — Mayo 2026
# Fuente: Yoon, Jarrett, van der Schaar (NeurIPS 2019)
# Implementación: repositorio del libro ML4T (Stefan Jansen GitHub)

Arquitectura TimeGAN:
┌─────────────────────────────────────────────────┐
│ INPUT: 45 días × 17 estrategias × features      │
│  ↓                                              │
│ EMBEDDER: series temporales → espacio latente   │
│  ↓                                              │
│ GENERATOR: genera secuencias en espacio latente │
│  ↓                                              │
│ SUPERVISOR: preserva dinámicas temporales       │
│  ↓                                              │
│ DISCRIMINATOR: real vs. sintético               │
│  ↓                                              │
│ OUTPUT: 1,000 trayectorias sintéticas de 90 días│
│  con las mismas propiedades estadísticas        │
└─────────────────────────────────────────────────┘

Uso: pre-entrenar brain_v3 PPO en datos sintéticos (1,000 episodios × 90 días)
     → fine-tune con datos reales (45 episodios reales)
     Resultado: convergencia 10x más rápida, sin overfitting al período real
```

**Prerequisito:** Tener ≥30 días de strategies_pnl logs para que TimeGAN aprenda
las propiedades estadísticas reales. Ya disponibles desde Feb 2026.

---

## MAPA COMPLETO — Batch 2: 9 Libros Analizados (23/03/2026)
### 45 conceptos nuevos integrados al stack

---

### IMPLEMENTAR AHORA (urgente, datos disponibles)

| # | Concepto | Fuente | Archivo | Por qué urgente |
|---|---|---|---|---|
| 28 | **Triple Screen Score** — fix ventana ciega tide_score (4-7h → 60s) | Bernut | triple_screen_score.py | Bug en producción activo |
| 29 | **Safe f calibrado a Apex** — P(DD > $7,500) < 5% via bootstrap | Vince | monte_carlo_sizer.py | Reemplaza Half-Kelly con calibración real |
| 29b | **Portfolio Heat Monitor** — Σ(f_i × worst_loss_i / equity), gate en tiempo real | Vince | portfolio_heat_monitor.py | 5 líneas, bloquea escenario 17/03 |
| 29c | **Open Type Classifier** — 4 tipos de apertura Dalton, feature para primeras 2h | Dalton | open_type_classifier.py | Contexto estructural 9:30-11:00 ET faltante |
| 29d | **Conditional Pattern Probability (CPP)** — P(éxito\|tide_score+ATR+VWAP), implementable hoy | Pattern Rec | conditional_pattern_probability.py | Puente entre market_monitor y estrategias |
| 30 | **N efectivo de estrategias** — con ρ=0.25, ~5 independientes en MNQ | Carver | hrp_optimizer.py | Define cuántas estrategias tienen sentido |

---

### Semana 1 Abril (junto con Módulo Markov)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 31 | **Conformal Prediction Intervals** — IC empíricos calibrados, agnósticos a distribución fat-tail | Joseph | conformal_prediction.py |
| 32 | **Correlation Regime Detector** — Portfolio Stop dinámico 30-60min | Carver | correlation_monitor.py |
| 33 | **Model Decay Monitor** — rolling t-stat early warning (antes del drawdown) | Narang | autocritica_daily.py |
| 33b | **Alpha Decay Measurement** — ventana temporal de validez de señal (t+0/30/60/120s) | Narang | alpha_decay_analyzer.py |
| 34 | **Signal Half-Life Sizing** — escalar Kelly por half-life OU process | Narang | monte_carlo_sizer.py |
| 35 | **Triple Regime Filter** — 3 capas ortogonales (vol + corr NQ/ES + mom) | Narang | markov_regime.py |
| 35 | **Value Area High/Low (VAH/VAL) + POC** diario | Dalton | market_profile_features.py |
| 36 | **Initial Balance** — IB estrecho (<percentil 30) = alerta explosión | Dalton | market_profile_features.py |
| 36b | **Auction Rotation Factor (ARF)** — rotaciones bi/uni-direccionales, régimen balance vs trend | Dalton | auction_rotation_factor.py |
| 37 | **CVD Divergence** — precio sube / delta baja → absorción institucional | Valtos | order_flow_monitor.py |
| 38 | **Pattern Quality Score** — edge = hit_ratio − breakeven_hr por estrategia | Pattern Rec | pattern_quality.py |
| 38b | **Forward-Walk Pattern Validator** — degradation score por setup, early warning de decay | Pattern Rec | walkforward_pattern_validator.py |
| 39 | **Vol Regime Percentile** — percentil 252 días para position sizing | Bernut | vol_regime_percentile.py |
| 40 | **Gain-to-Pain Ratio (GPR)** — selector de portafolio más robusto que Sharpe | Bernut | gain_to_pain_selector.py |
| 41 | **DTosc MTF** — Stochastic dual timeframe, señal solo cuando coinciden | Miner | dtosc_mtf_score.py |
| 42 | **Momentum Position (MomPos)** — oscilador normalizado contra su propio rango | Miner | momentum_position.py |
| 43 | **Carry/Roll Yield** — sizing −50% en semana de rollover NQ | Carver | market_monitor_logger.py |
| 43b | **Forecast Scaling + Cap** — normalizar señales a [-20,+20], FDM corrige dilución | Carver | forecast_scaling.py |
| 43c | **Handcrafted Weights** — agrupar por ρ > 0.7, peso igual por grupo (>HRP con N<30) | Carver | handcrafted_weights.py |

---

### Semana 2 Abril (junto con News Filter + Tit for Tat)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 44 | **STL Seasonality intraday** — session_bias_score horario (9:30/10:00/14:00) | Joseph | market_monitor_logger.py |
| 44b | **Global Model Portfolio** — pooling cross-estrategias, detecta correlaciones proactivamente | Joseph | global_model_portfolio.py |
| 45 | **Alpha Orthogonalizer** — PCA + constraint ρ < 0.5 (resuelve 17/03 estructuralmente) | Narang | hrp_optimizer.py |
| 46 | **FDM (Forecast Diversification Multiplier)** — crédito de diversificación real | Carver | hrp_optimizer.py |
| 47 | **Profile Shape (D/P/b/I)** — forma del perfil predice tipo de sesión siguiente | Dalton | market_profile_features.py |
| 48 | **POC Migration** — sesgo direccional del fair value (independiente de EMAs) | Dalton | market_profile_features.py |
| 49 | **Absorption/Exhaustion Detection** — alto vol + precio quieto = institucional | Valtos | order_flow_monitor.py |
| 49b | **Single Prints** — TPOs solitarios sin vol = imanes de precio, destinos estructurales | Dalton | profile_structure_map.py |
| 50 | **Trade Quality Score (TQS)** — ConvictionScore 0-3 (=Arquitectura Elswee) | Miner | trade_quality_score.py |
| 51 | **Fibonacci Zone Filter** — entrada solo en zona ±0.5 ATR de Fibo key level | Miner | fibonacci_zone_filter.py |
| 52 | **Trend Intensity Index (TII)** — % bricks sobre MA (régimen, no sobrecompra) | Pattern Rec | market_monitor_logger.py |
| 52b | **Pattern Reliability Score (PRS)** — bootstrap rolling PF+winrate+consistency temporal | Pattern Rec | pattern_reliability_scorer.py |
| 52c | **Pattern Decay Analysis** — half-life del edge, cuándo re-validar post-rollover | Pattern Rec | pattern_decay_analyzer.py |
| 53 | **ATR Quality Filter** — señales válidas solo si rango > 1.5×ATR | Pattern Rec | market_monitor_logger.py |
| 54 | **Floor/Ceiling Mean Reversion Score** — percentil de precio relativo [0,1] | Bernut | floor_ceiling_score.py |

---

### Semana 3 Abril (junto con Monte Carlo Risk Engine)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 55 | **PWDA + MDV** — métricas P&L para evaluar RF (no accuracy), da_large_moves | Joseph | evaluate_brain_v2.py |
| 55b | **Quantile Loss / Pinball Loss** — Q10/Q50/Q90 dinámico, Kelly forward-looking | Joseph | quantile_forecaster.py |
| 56 | **Optimal f empírico** (Vince) — distribución real, worst loss como denominador | Vince | monte_carlo_sizer.py |
| 57 | **Geometric Mean Maximization** — ranking real de estrategias (supera PF/Sortino) | Vince | monte_carlo_sizer.py |
| 58 | **TWR Comparison** — Terminal Wealth Relative, comparador cross-estrategias | Vince | hrp_optimizer.py |
| 59 | **Portfolio f conjunto** — suma f individuales ≤ 1.0, correlación ajustada | Vince | monte_carlo_sizer.py |
| 59b | **Leverage Space Surface** — superficie n-dimensional TWR, captura interacción no-lineal de f | Vince | leverage_space_surface.py |
| 60 | **Vol Targeting EWMA-25** — contratos = (Capital × 20%) / (precio × vol_ewma × √252) | Carver | vol_target_sizing.py |
| 60b | **Cost-Adjusted SR** — SR_neto = SR_bruto − (coste × turnover × √252), filtro pre-inclusión | Carver | cost_adjusted_sr.py |
| 60c | **Carry Signal** — señal de trading spot/futuro NQ independiente, combinar con tide_score | Carver | carry_signal.py |
| 61 | **Volume Profile POC dinámico** — VAH/VAL en tiempo real intraday | Valtos | order_flow_monitor.py |
| 62 | **Excess/Poor High-Low** — extremos con poco vol = strong S/R día siguiente | Dalton | market_profile_features.py |
| 63 | **Symmetrical Target + RR Filter** — solo trades con RR ≥ 1.5 (ABCDHarmonic) | Pattern Rec | brain_v2.py |
| 63b | **Factor Risk Model intraday** — exposición a factores mom/vol/VWAP por estrategia, bloquea si Σ > threshold | Narang | factor_risk_model.py |
| 63c | **Stop Raid Pattern / Liquidity Sweep** — spike past swing + delta flip + reversión, estado Markov especial | Valtos | stop_raid_detector.py |
| 64 | **Swing ABC Pattern** — entry en onda C cuando HMM confirma régimen trending | Miner | swing_abc_pattern.py |
| 64b | **Renko Pattern Clusterer (DTW)** — familias de secuencias Renko similares, aumenta N estadístico | Pattern Rec | renko_pattern_clusterer.py |
| 65 | **Crowding/Short Interest Monitor** — COT NQ + skew opciones, detecta 17/03 | Bernut | crowding_risk_monitor.py |

---

### Semana 4 Abril (junto con Brain v2 RF)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 66 | **N-HiTS retornos** — multi-rate sampling Renko, forecast 3 bricks (supera LSTM) | Joseph | nhits_signal.py |
| 67 | **AdaptiveForecaster** — SGD online + RF base, peso dinámico según drift | Joseph | adaptive_brain.py |
| 68 | **Variable Selection Network (VSN)** — pesos dinámicos de features por timestep (no SHAP estático) | Joseph | variable_selection_network.py |
| 68b | **Robustness Testing Surface** — robustness_score = mean(PF_vecinos)/PF_óptimo ≥ 0.80 | Narang | robustness_tester.py |
| 69 | **Dynamic Position Size** — hit ratio reciente + half-Kelly por estrategia | Pattern Rec | monte_carlo_sizer.py |

---

### Mayo 2026

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| 69 | **ForecastEnsemble meta-learner** — Ridge régimen-aware sobre todos los módulos | Joseph | ensemble_brain.py |
| 70 | **Stacked Imbalances** (footprint) — 3+ niveles consecutivos bid/ask desequilibrio | Valtos | order_flow_monitor.py |
| 71 | **of_score compuesto** — CVD + Absorption + POC + Delta Rate → feature RF | Valtos | brain_v2.py |
| 71b | **Large Trader Fingerprint** — prints >500 contratos en tape, intención institucional | Valtos | large_trader_detector.py |
| 72 | **Implementation Shortfall Tracker** — IS real en producción live | Narang | execution_tracker.py |

---

### Insights clave del Batch 2 (no obvios)

> **Carver:** Con 17 estrategias en MNQ y ρ_media=0.25, el N_efectivo real es ~5.5.
> El Correlation Regime Detector (cada 30min) habría detenido el evento 17/03 a tiempo.
> FDM cuantifica exactamente cuánto crédito de diversificación tienes vs el que crees.

> **Vince:** A la derecha del f-óptimo, MÁS capital destruye MÁS capital.
> Safe f calibrado a Apex $7,500 es el único sizing matemáticamente sano.
> TWR es mejor ranking de estrategias que PF o Sortino para distribuciones fat-tailed.

> **Narang:** Model Decay Monitor detecta degradación por t-stat ANTES que el drawdown.
> Alpha Orthogonalizer (PCA) resuelve StatMean+EMATrend EMA(21) compartida a nivel estructural.
> Signal Half-Life distingue "estrategia rota" de "régimen adverso temporal".

> **Dalton:** IB estrecho (percentil <30%) precedió los peores días del diario.
> Excess High en el día anterior = resistencia fuerte al día siguiente (sin conjeturas).
> Profile shape P/b predice sesgo del día siguiente mejor que cualquier EMA.

> **Valtos:** Order flow en NQ es MÁS ruidoso que en ES. Señal/ruido máxima 9:30-11:00 ET.
> Absorción es el primer paso del ConvictionScore Elswee ya planificado.
> OBOrderFlow_v1.cs en 1-min (no Renko) confirma decisión ya documentada.

---

## MAPA COMPLETO — Batch 3: 7 Libros Analizados (23/03/2026)
### 35+ conceptos nuevos integrados al stack

### IMPLEMENTAR AHORA (urgencia máxima del Batch 3)

| # | Concepto | Fuente | Archivo | Urgencia |
|---|---|---|---|---|
| B3-1 | **Momentum Ignition Detector** (spike precio+vol → inhibir 2-3 bricks) | Johnson | anomaly_detector.py | 🔴 Explica 06/03 + 17/03 |
| B3-2 | **CAGR/MaxDD Calmar Ratio** (nuevo criterio primario de ranking, junto a Sortino) | Davey | strategies_portfolio.md | 🔴 Recalcular top 5 ahora |
| B3-3 | **Degradation Monitor 50%/75%** (live: reduce 50% en DD=50% hist; para en 75%) | Davey | autocritica_daily.py | 🔴 Módulo 1b ya planeado |

### Semana 1 Abril — Batch 3 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B3-4 | **CUSUM Filter** (event-driven sampling — reemplaza barras de tiempo fijo) | López de Prado | cusum_filter.py |
| B3-5 | **Triple Barrier Method** (etiquetado PT/SL/timeout para RF training) | López de Prado | triple_barrier.py |
| B3-6 | **BOCPD** (Bayesian Online Changepoint Detection — P(cambio_régimen) en tiempo real) | Prob. ML | bocpd_detector.py |
| B3-7 | **Feature Autoencoder** (compresión vector features, limpia ruido antes del RF) | Kaabar | feature_autoencoder.py |
| B3-8 | **Factor Timing Conditional** (predice CUÁNDO factor funciona, núcleo del Markov) | ML Factor | factor_timing_conditional.py |
| B3-9 | **Johansen Cointegration** (NQ/ES/YM/RTY — base estadística del market_breadth) | TS Cookbook | johansen_cointegration.py |
| B3-10 | **Rolling ACF + Ljung-Box** (monitor degradación temporal P&L por estrategia) | TS Cookbook | autocorr_drift_monitor.py |
| B3-11 | **Almgren-Chriss Scheduler** (escalonar entradas correlacionadas — fix 17/03) | Johnson | almgren_chriss_scheduler.py |
| B3-12 | **TCA Pre-trade Estimator** (costo esperado antes de ejecutar: spread+slip+comm) | Johnson | pre_trade_tca.py |
| B3-13 | **POV Liquidity Filter** (reducir sizing si vol barra < P10 del día) | Johnson | vol_regime_percentile.py |
| B3-14 | **Clustering Regímenes sin supervisión** (K-Means features → n=4 regímenes reales) | López de Prado | regime_clusterer.py |
| B3-15 | **WFO Efficiency Ratio** (OOS PF / IS PF ≥ 0.50 → estrategia robusta) | Davey | wfo_validator.py |

### Semana 2 Abril — Batch 3 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B3-16 | **Fractional Differentiation** (d≈0.3 — estacionariedad con memoria preservada) | López de Prado | wavelet_filter.py |
| B3-17 | **CNN Pattern Detector** (OHLC→imagen→conv → detecta setups visuales automáticamente) | Kaabar | cnn_pattern_detector.py |
| B3-18 | **Feature Crosses** (RSI×ATR, EMA_slope×vol_ratio — interacciones entre factores) | ML Factor | feature_crosses.py |
| B3-19 | **Granger Causality ES→MNQ** (lag 1-5 min, feature predictivo directo) | TS Cookbook | granger_causality_mnq.py |
| B3-20 | **Ruptures Change Points** (cambios estructurales en P&L intraday, más preciso que CUSUM) | TS Cookbook | ruptures_regime_detector.py |
| B3-21 | **Spread Decomposition** (adverse selection component del bid-ask spread) | Johnson | spread_decomposition.py |
| B3-22 | **Gaussian Processes intraday** (distribución completa de trayectorias — incertidumbre epistémica) | Prob. ML | gp_forecast.py |
| B3-23 | **Multi-Config Consistency** (≥70% configs vecinas PF>1 → no curve-fitted) | Davey | robustness_tester.py |

### Semana 3 Abril — Batch 3 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B3-24 | **Rolling Feature Importance SHAP** (qué factor domina AHORA, no histórico fijo) | ML Factor | rolling_feature_importance.py |
| B3-25 | **Entropy Pooling (Meucci)** (redistribución capital por escenarios con correlación adversa) | Prob. ML | entropy_pooling.py |
| B3-26 | **VAE Regime Detector** (espacio latente continuo de regímenes vs HMM discreto) | Kaabar | vae_regime_detector.py |
| B3-27 | **Portfolio MC Correlated** (MC samplea trades correlacionados, no independientes) | Davey | portfolio_mc_correlated.py |
| B3-28 | **Periodograma Espectral FFT** (ciclos dominantes MNQ intraday en minutos) | TS Cookbook | spectral_cycle_detector.py |

### Semana 4 Abril — Batch 3 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B3-29 | **Meta-Labeling** (RF predice si trade primario GANA — no predice dirección) | López de Prado | brain_v2.py |
| B3-30 | **MDI/MDA/SFI Feature Importance** (SFI: modelo por feature individual, anti-multicolinealidad) | López de Prado | brain_v2.py |
| B3-31 | **Bet Sizing Kelly-ML** (Kelly continuo desde prob RF → sizing proporcional a convicción) | López de Prado | monte_carlo_sizer.py |
| B3-32 | **Temporal Attention Layer** (ponderación dinámica de features por barra) | Kaabar | temporal_attention_layer.py |
| B3-33 | **Factor Graph Signals** (P(estrategia_activa\|régimen) para 15+ estrategias) | Prob. ML | factor_graph_signals.py |
| B3-34 | **Turnover-Penalized Loss** (penaliza cambios frecuentes de señal en entrenamiento RF) | ML Factor | turnover_penalized_trainer.py |

### Mayo — Batch 3 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B3-35 | **Hierarchical Bayesian Models** (priors compartidos entre estrategias con poco historial) | Prob. ML | hierarchical_bayes.py |
| B3-36 | **Error Decorrelation Ensemble** (meta-learner entrena sobre RESIDUOS, no predicciones) | ML Factor | error_decorrelation_ensemble.py |

---

### Stack actualizado (Batch 3) — FILAS AÑADIDAS a tabla principal

| Capa nueva | Matemática | Fuente | Implementación |
|---|---|---|---|
| Event sampling | CUSUM filter (acumulación de movimiento) | López de Prado | cusum_filter.py (Sem 1) |
| Etiquetado ML | Triple Barrier + Meta-Labeling | López de Prado | triple_barrier.py + brain_v2.py (Sem 4) |
| Estimación | Fractional Differentiation (d≈0.3) | López de Prado | wavelet_filter.py (Sem 2) |
| CV financiero | Purging + Embargoing + PurgedKFold integrado | López de Prado | cv_financial.py (Sem 4) |
| Changepoint | BOCPD (online changepoint Bayesiano) | Prob. ML | bocpd_detector.py (Sem 1) |
| Ejecución | Almgren-Chriss Scheduler (corr. catastrófica) | Johnson | almgren_chriss_scheduler.py (Sem 1) |
| Compresión | Feature Autoencoder → VAE Regime Detector | Kaabar | feature_autoencoder.py + vae.py (Sem 1+3) |
| Factor timing | Conditional Factor Timing Model | ML Factor | factor_timing_conditional.py (Sem 1) |
| Causalidad | Granger ES→MNQ + Johansen Cointegration | TS Cookbook | granger_causality_mnq.py (Sem 2) |
| Microestructura | Momentum Ignition + Spread Decomp. + POV | Johnson | anomaly_detector.py (AHORA) |

---

### Insights clave del Batch 3

> **López de Prado:** El pipeline CUSUM→TripleBarrier→MetaLabeling es el corazón de brain_v2.
> Sin Triple Barrier, el RF entrena sobre ruido (retornos a N barras fijas son labels incorrectos).
> Meta-Labeling convierte las estrategias Renko ACTUALES en el modelo primario — el RF no las reemplaza, las FILTRA.

> **Johnson:** Momentum Ignition explica los días -$11,920 (06/03) y -$8,906 (17/03) exactamente.
> El patrón: spike precio + spike vol → múltiples estrategias correlacionadas entran en la misma dirección → reversión brutal.
> Almgren-Chriss Scheduler es la solución matemática para el problema de ejecución simultánea.

> **Davey:** Sortino=38.73 de StatMeanCross en backtest es señal de alerta, no de celebración.
> Multi-Config Consistency Test sobre Renko 25/30/35/40/45 debe ejecutarse ANTES de asignarle sizing alto en Apex.
> Portfolio MC Correlated (con ρ real entre estrategias) dará un MaxDD P95 30-50% mayor que el MC actual.

> **Prob. ML:** BOCPD da P(changepoint_ahora) con cada nuevo tick — actúa como News Filter probabilístico.
> Entropy Pooling de Meucci es la solución "matemáticamente correcta" al problema de correlación adversa del portafolio.

> **TS Cookbook:** Granger ES→MNQ con lag 1-5 min es un feature predictivo directo de alta frecuencia.
> Johansen da la base estadística que al market_breadth_score le faltaba.

---

## MAPA COMPLETO — Batch 4: 7 Libros Analizados (23/03/2026)
### 60+ conceptos nuevos integrados al stack

### IMPLEMENTAR AHORA (urgencia máxima del Batch 4)

| # | Concepto | Fuente | Archivo | Urgencia |
|---|---|---|---|---|
| B4-1 | **Optimal Rebalancing Freq** (rebalancear cada ½ × half-life alpha, fix ventana ciega) | Chan | market_monitor_logger.py | 🔴 FIX documentado MEMORY.md |
| B4-2 | **Heartbeat Watchdog ZMQ** (reconexión automática, previene operar sin brain) | Donadio | heartbeat_watchdog.py | 🔴 Infraestructura crítica |
| B4-3 | **Pre-Trade Risk Gate** (firewall pre-orden: Daily Loss Limit, Max Contracts, Portfolio Heat) | Donadio | pre_trade_gate.py | 🔴 Habría limitado 06/03 + 17/03 |
| B4-4 | **Alert System Telegram 4 niveles** (INFO/WARNING/CRITICAL/EMERGENCY pausa bot) | Donadio | alert_system.py | 🔴 Monitoreo remoto inmediato |

### Semana 1 Abril — Batch 4 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B4-5 | **CORT Similarity** (correlación + orden temporal → detecta timing coincidente entre estrategias) | Marti | correlation_monitor.py |
| B4-6 | **Hayashi-Yoshida Correlation** (correlación real entre barras Renko asíncronas) | Marti | correlation_monitor.py |
| B4-7 | **GNPR Transform** (representación no-paramétrica rolling, robusto a cambios de escala) | Marti | wavelet_filter.py |
| B4-8 | **Wasserstein Distance Regime** (distancia continua al régimen normal — pre-alerta) | Marti | market_monitor_logger.py |
| B4-9 | **Network Contagio** (grafo rolling: densidad→1 predice drawdown sistémico) | ML Risk | network_contagio.py |
| B4-10 | **CDaR** (distribución de episodios DD: duración + magnitud para Darwin/X) | ML Risk | monte_carlo_sizer.py |
| B4-11 | **Signal Decay Rate** (half-life intraday del alpha, calibra latencia ZMQ vs edge) | Chan | autocritica_daily.py |
| B4-12 | **Regime-Conditional Stop** (stop/target asimétrico por percentil volatilidad) | Chan | monte_carlo_sizer.py |
| B4-13 | **Setup Quality Score** (checklist 5 condiciones: tide+ATR+news+vol+VWAP_dist) | Davey E&E | pre_trade_checklist.py |
| B4-14 | **Volatility Stop Percentil ATR** (distancia stop ajustada por %vol histórico) | Davey E&E | market_monitor_logger.py |
| B4-15 | **Anti-Martingala Condicional** (+25% en racha 3 wins + equity peak; -50% en 2 losses) | Davey E&E | portfolio_heat_monitor.py |
| B4-16 | **Order State Machine + Audit Log** (máquina de estados órdenes, trazabilidad .jsonl) | Donadio | order_state_machine.py |

### Semana 2 Abril — Batch 4 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B4-17 | **EVT/GPD Fat Tails** (cola izquierda NQ real: VaR(99%) 20-40% mayor que gaussiano) | ML Risk | monte_carlo_sizer.py |
| B4-18 | **MS-GARCH Regime Risk** (GARCH por estado: VaR condicional al régimen de volatilidad) | ML Risk | garch_vol.py |
| B4-19 | **GBT Drawdown Predictor** (LightGBM predice P(DD>$500) próximos 3 días con market_logs) | ML Risk | drawdown_predictor.py |
| B4-20 | **Copula Tail Dependence Clayton** (λ_L > 0.4 entre estrategias → 1 slot en Portfolio Heat) | ML Risk + Marti | correlation_monitor.py |
| B4-21 | **VPIN Flow Toxicity Score** (fracción volumen informado: >0.7 inhibe mean-reversion) | Capponi | vpin_flow_toxicity.py |
| B4-22 | **Adversarial Validation** (RF detecta drift multivariante train vs live automáticamente) | Capponi | autocritica_daily.py |
| B4-23 | **FinBERT Event Classifier** (ventana inhibición por tipo: Fed=30min, Geopolítico=60min) | Capponi | finbert_event_classifier.py |
| B4-24 | **Alpha-Stable Lévy Kelly** (corrección Kelly por α≈1.65 NQ: Kelly × 0.68) | Marti | monte_carlo_sizer.py |
| B4-25 | **PSI sobre features ML** (PSI del vector de features, detecta drift antes del output) | Impl. ML | meta_model_monitor.py |
| B4-26 | **Time Stop Régimen-Condicional** (N bricks para resolver: ADX<20→6, ADX>30→18) | Davey E&E | cada .cs estrategia |
| B4-27 | **Señal Contraria como Exit Primario** (exit type dinámico: objetivo en ranging, señal en trend) | Davey E&E | exit_regime_selector.py |
| B4-28 | **Scale-Out Estructural 1R/Runner** (50% en 1R, runner con trailing BE — reduce MaxDD 20-35%) | Davey E&E | ULTRA/MomentumZ .cs |
| B4-29 | **Intermarket Lagged Momentum** (DXY/RTY lag 1-3 días predice NQ intraday) | Chan | market_monitor_logger.py |

### Semana 3 Abril — Batch 4 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B4-30 | **MST Mantegna-Stanley** (árbol mínimo de correlaciones: hub = EMA(21) visualizable) | Marti | hrp_optimizer.py |
| B4-31 | **MI-Distance Clustering** (HRP con distancia de información mutua — no-lineal) | Marti | hrp_optimizer.py |
| B4-32 | **Feature Store Lightweight** (captura features en señal, no retroactivos — anti-leakage) | Impl. ML | feature_store.py |
| B4-33 | **Online SGD Corrector Híbrido** (RF batch + SGD online: capta drift en 3-5 trades vs 20) | Impl. ML | meta_brain_bbv5.py |
| B4-34 | **Kalman Adaptive Exit** (stop dinámico via velocidad Kalman — exit preventivo 2-3 bricks antes) | Chan | brain_v2.py |
| B4-35 | **Stochastic DD Signal** (DD extremo intraday estadísticamente revierte — no pánico) | Chan | monte_carlo_sizer.py |
| B4-36 | **LVaR Liquidity-Adjusted** (VaR ajustado por spread en barras thin market) | ML Risk | vol_regime_percentile.py |
| B4-37 | **Pullback Depth Gate** (0.5×ATR retroceso post-breakout antes de entrar) | Davey E&E | PivotTrend/Darvas .cs |
| B4-38 | **Structural Trailing Stop Swing** (trailing por swing N bricks contrarios — captura tendencias) | Davey E&E | EMATrend/MomentumZ .cs |
| B4-39 | **Risk Attribution SHAP** (SHAP sobre P&L negativo: ¿qué feature causó 06/03 y 17/03?) | ML Risk | risk_attribution.py |
| B4-40 | **Paper/Live Switch + Parity Check** (bloquea si hay posición abierta en cualquier estrategia) | Donadio | paper_live_switch.py |

### Semana 4 Abril — Batch 4 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B4-41 | **Isotonic Calibration → Kelly** (prob RF bien calibrada: 0.65 → win rate real, no comprimida) | Impl. ML | monte_carlo_sizer.py |
| B4-42 | **Financial Preprocessing Pipeline** (RobustScaler + winsorización dentro de Pipeline sklearn) | Impl. ML | meta_brain_bbv5.py |
| B4-43 | **XGBoost + Focal Loss** (supera RF en N<5000 con class imbalance; complementa meta-labeling) | Impl. ML | meta_brain_bbv5.py |
| B4-44 | **EV + MCC Financial Metrics** (ev_lift: ¿el meta-model añade EV? criterio go/no-go producción) | Impl. ML | evaluate_meta_model.py |
| B4-45 | **Champion/Challenger A/B** (challenger observa en silencio; promueve con Mann-Whitney U) | Impl. ML | champion_challenger.py |
| B4-46 | **Causal Do-Calculus Feature Filter** (ATE real del feature vs correlación espuria en RF) | Capponi | cv_financial.py |
| B4-47 | **Bar Magnification Test** (techo real de escalado contratos — límite antes de Apex) | Chan | deflated_sr.py |
| B4-48 | **Walk-Forward Anchored WFA** (IS siempre desde mismo origen — más robusto en bull NQ) | Chan | wfo_validator.py |
| B4-49 | **Execution Quality Report** (slippage real vs Slippage=1 del backtest — validación pre-Apex) | Donadio | execution_quality_report.py |

### Mayo — Batch 4 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B4-50 | **Contrastive Regime Embedder** (K días similares históricos → prior para sizing) | Capponi | contrastive_regime_embedder.py |
| B4-51 | **GNN Correlation Regime** (grafo neural: firma de correlaciones que precede a crash) | Capponi | gnn_correlation_regime.py |
| B4-52 | **Failed Breakout Reversal** (nueva estrategia: ruptura fallida + vol + delta flip → reversal) | Davey E&E | FailedBreakout_v1.cs |
| B4-53 | **Deep RL Execution Scheduler** (PPO aprende curva de impacto dinámica — reemplaza AC estático) | Capponi | rl_execution_scheduler.py |
| B4-54 | **Options Tail Hedge** (collar mensual ~$0 neto para Darwin/X cuenta propia) | Chan | hedge_manager.py |

---

### Stack actualizado (Batch 4) — FILAS AÑADIDAS a tabla principal

| Capa nueva | Matemática | Fuente | Implementación |
|---|---|---|---|
| Correlación asíncrona | CORT + Hayashi-Yoshida | Marti | correlation_monitor.py (Sem 1) |
| Corr. no-lineal | MI-Distance + MST Mantegna | Marti | hrp_optimizer.py (Sem 3) |
| Tail risk portafolio | Copula Clayton λ_L + EVT/GPD + MS-GARCH | ML Risk + Marti | monte_carlo_sizer.py (Sem 2-3) |
| Contagio sistémico | Network Grafo Contagio + CDaR | ML Risk | network_contagio.py (Sem 1) |
| Predicción DD | LightGBM GBT Drawdown Predictor | ML Risk | drawdown_predictor.py (Sem 2) |
| Flujo informado | VPIN Flow Toxicity | Capponi | vpin_flow_toxicity.py (Sem 2) |
| Drift ML | Adversarial Validation multivariante | Capponi | autocritica_daily.py (Sem 2) |
| NLP eventos | FinBERT ventana inhibición variable | Capponi | finbert_event_classifier.py (Sem 2) |
| Gestión posición | Scale-Out 1R/Runner + Time Stop + Structural Trailing | Davey E&E | estrategias .cs (Sem 2-3) |
| Pipeline ML | XGBoost + Feature Store + Isotonic Cal. + Champion/Challenger | Impl. ML | meta_brain_bbv5.py (Sem 3-4) |
| Infraestructura | Heartbeat + Pre-Trade Gate + Alert + State Machine | Donadio | watchdog/gate/alert (AHORA) |

---

### Insights clave del Batch 4

> **Chan:** El Concepto 1 (Optimal Rebalancing Freq) da la matemática exacta del fix para la ventana ciega de 4-7h del tide_score documentada en MEMORY.md. El intervalo correcto = ½ × alpha_half_life_minutes.
> Bar Magnification confirma que el escalado a 20ct en StatMeanCross necesita validación empírica antes de Apex.

> **Marti (basado en papers reales):** CORT detecta la correlación catastrófica del 17/03 mejor que Pearson porque captura el timing coincidente — no solo la magnitud. Hayashi-Yoshida da la correlación verdadera entre barras Renko asíncronas que Pearson subestima sistemáticamente.

> **ML Risk Mgmt:** Network Contagio + GBT Drawdown Predictor son los módulos más urgentes del batch porque: (1) el grafo habría mostrado densidad→1 antes del 17/03, y (2) el GBT puede entrenarse YA con los 30+ días de market_logs disponibles.

> **Capponi & Lehalle:** VPIN habría inhibido las entradas mean-reversion el 06/03 y 17/03 automáticamente. Adversarial Validation detecta el rollover MNQ March→June como cambio de distribución. FinBERT reemplaza el news filter binario con ventana variable calibrada.

> **Davey Entry & Exit:** Scale-Out 1R/Runner es el cambio de mayor impacto en MaxDD: reduce ULTRA ($6,903) y MomentumZ ($7,194) en 20-35% sin tocar la lógica de entrada. Failed Breakout Reversal es la 16ª estrategia candidata al portafolio.

> **Donadio & Ghosh:** Todo el stack matemático puede estar perfecto y el bot falla por conexión caída silenciosamente. Heartbeat + Pre-Trade Gate + Alert System son la capa de ingeniería que faltaba. IMPLEMENTAR ANTES de cualquier módulo de Abril.

---

## MAPA COMPLETO — Batch 5: 5 Libros Analizados (23/03/2026)
### 40+ conceptos nuevos integrados al stack

### IMPLEMENTAR AHORA (urgencia máxima del Batch 5)

| # | Concepto | Fuente | Archivo | Urgencia |
|---|---|---|---|---|
| B5-1 | **SSL Channel `ssl_score`** (+1/0/-1 — sin ventana ciega, reemplaza tide_score) | Kaabar BT | market_monitor_logger.py | 🔴 Fix documentado MEMORY.md |
| B5-2 | **OSRT** (Sharpe_OOS/Sharpe_IS > 0.50 + DD_OOS/DD_IS < 2.5x — criterio admisión faltante) | Kaabar BT | osrt_validator.py | 🔴 Criterio admisión faltante |
| B5-3 | **Latency Budget Tracking** (SLA por etapa ZMQ: t_send+t_transit+t_process — brain respondiendo stale) | HFT Sys | latency_monitor.py | 🔴 Prerequisito infraestructura |
| B5-4 | **Position Reconciliation Loop** (shadow book Python vs NT8 — detecta split post bug 20/03) | HFT Sys | position_reconciler.py | 🔴 Bug infraestructura activo |
| B5-5 | **Techo máximo señales** (5-8 trades/día/estrategia = límite de viabilidad con costos MNQ) | Kaabar BT | strategies_portfolio.md | 🟡 Análisis portafolio |

### Semana 1 Abril — Batch 5 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B5-4 | **Hurst Exponent rolling 100 bricks** (H>0.55=trending, H<0.45=mean-rev — feature HMM) | Kaabar BT | markov_regime.py |
| B5-5 | **PCR diario** (Put-Call Ratio via yfinance `^PCALL`/`^PCPUT` — sesgo direccional pre-apertura) | Kaabar BT | market_monitor_logger.py |
| B5-6 | **Ichimoku Kumo régimen** (+1=sobre cloud / 0=dentro cloud / -1=bajo cloud) | Kaabar BT | markov_regime.py |
| B5-6 | **VTS** (VIX Term Structure Slope: backwardation → panic → size×0.30 — leading vs GARCH) | Bouev | vix_term_structure.py |
| B5-7 | **IVR** (IV Rank + IV Percentile: >70=reversión favored; <30=momentum favored — feature RF) | Bouev | iv_rank_monitor.py |
| B5-8 | **Adversarial Regime Detector** (LightGBM AUC>0.70 reciente vs histórico → early warning antes del fallo) | AI Fin Mkts | adversarial_regime_detector.py |
| B5-9 | **HRSS** (Hit Ratio Stability Score: std(HR_rolling)/mean < 0.20 — base empírica TfT thresholds) | Kaabar BT | hit_ratio_stability.py |
| B5-8 | **CLCA** (Consecutive Loss Cluster: test KS vs dist. geométrica — detecta dependencia serial P&L) | Kaabar BT | consecutive_loss_cluster.py |
| B5-9 | **PSH 2D** (Parameter Sensitivity Heatmap: pico estrecho <3 celdas a PF>1.5 = overfitting) | Kaabar BT | param_sensitivity_heatmap.py |
| B5-10 | **SPM** (Symmetrical Performance Matrix: válido si PF>1 en MNQ+MES+NQ mismos params) | Kaabar BT | symmetrical_perf_matrix.py |
| B5-11 | **IMRT** (Intraday Momentum Reversal Threshold: |close-open|/σ > 2.3 → peso contrarian up) | Bacidore | imrt_score.py |
| B5-12 | **FRQS** (Fill Rate Quality Score: detecta slippage real > Slippage=1 por estrategia/hora/régimen) | Bacidore | fill_quality_monitor.py |
| B5-13 | **Arrival Price Benchmark** (drift arrival→fill mide costo real de latencia ZMQ en ticks) | Bacidore | arrival_price_tracker.py |
| B5-14 | **Adaptive Throttle Gate** (ATG: máx N señales en 10min — previene burst correlacionado 06/03) | HFT Sys | throttle_gate.py |
| B5-15 | **Sequence Number Gap** (seq_id en ZMQ — detecta pérdida silenciosa de mensajes bajo carga) | HFT Sys | servidor_ia.py |
| B5-16 | **Correlation Slots dinámicos** (correlación rolling: si >0.7 entre estrategias → solo 1 slot activo) | HFT Sys | correlation_monitor.py |

### Semana 2 Abril — Batch 5 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B5-16 | **GEX (Kaabar)** (GEX>0: mean-reverting; GEX<0: trending → pesos estrategias) | Kaabar BT | markov_regime.py |
| B5-17 | **COT Variable Barrier NQ** (Bollinger sobre COT CFTC → filtro semanal de sesgo L/S) | Kaabar BT | market_monitor_logger.py |
| B5-18 | **NSR Test** (Noise-to-Signal Ratio: PF_con_ruido/PF_original > 0.75 — fragilidad por ejecución) | Kaabar BT | nsr_backtest_test.py |
| B5-19 | **CARV** (Cross-Asset Regime Validation: edge válido si funciona en ES/YM/RTY misma lógica) | Kaabar BT | cross_asset_regime_val.py |
| B5-20 | **TDDT** (Trade Duration Distribution Test: Mann-Whitney U ganadores vs perdedores en Renko) | Kaabar BT | trade_duration_dist_test.py |
| B5-21 | **PCR-Vol + PCR-OI** (QQQ options: PCR>1.3=bullish contrarian; <0.7=bearish — posicionamiento) | Bouev | options_sentiment.py |
| B5-22 | **SKEW Index + Risk Reversal** (^SKEW>145 = tail_risk → contracts×0.50) | Bouev | options_sentiment.py |
| B5-23 | **VRP** (Volatility Risk Premium IV-RV: >5=sobrehedge=bullish; <-2=crash_warning) | Bouev | vrp_signal.py |
| B5-24 | **Cascade Risk Score** (eigenvalue(corr×size matrix): >0.70 → Portfolio Stop — resuelve 17/03) | AI Fin Mkts | cascade_risk_score.py |
| B5-25 | **Mean-Field Game Portfolio Stop** (campo medio N estrategias: intensity>0.65 → bloquea entradas) | AI Fin Mkts | mean_field_portfolio_stop.py |
| B5-26 | **OBIR** (Order Book Imbalance: bid_qty/(bid+ask) via Level 2 NT8 — intención latente pre-move) | HFT Sys | order_book_imbalance.py |
| B5-27 | **Session State Machine FSM** (IDLE→ACTIVE→THROTTLED→SUSPENDED→EOD — estados explícitos) | HFT Sys | session_state_machine.py |
| B5-26 | **PRA** (Participation Rate Adaptive: sizing = k% del vol/minuto — reduce slippage baja liquidez) | Bacidore | participation_rate_sizer.py |
| B5-20 | **Shortfall Decomposition 4 componentes** (Timing+Impact+Opportunity+Fees → TfT opportunity cost) | Bacidore | shortfall_decomposer.py |
| B5-21 | **Pre-Trade Cost Elasticity** (costo ∝ size^0.6 × vol × 1/ADV — no lineal, calibrado NQ) | Bacidore | pre_trade_cost_model.py |
| B5-22 | **Alpha Capture intraday** (50% alpha perdido en 2-3 min post-señal — medir latencia ZMQ→fill) | Bacidore | alpha_capture_tracker.py |

### Semana 3 Abril — Batch 5 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B5-28 | **Volume Clock** (reescalar tiempo a unidades de volumen → retornos más estacionarios para HMM) | Bacidore | volume_clock_resampler.py |
| B5-29 | **Execution Quality Score** (EQS: p50/p90/p99 slippage real por estrategia/hora — drift vs backtest) | HFT Sys | execution_quality.py |
| B5-30 | **IV Surface Slope por DTE** (IV_7d/IV_30d>1.15 = evento implícito → size×0.60, más preciso que calendar) | Bouev | iv_term_structure.py |
| B5-31 | **Gamma Exposure + Gamma Flip** (GEX nivel donde price behavior cambia: bajo flip → no longs) | Bouev | gamma_exposure.py |
| B5-32 | **AC Execution Scheduler** (turno 2min entre N estrategias en apertura — reduce impact colectivo) | AI Fin Mkts | execution_scheduler.py |

### Semana 4 Abril — Batch 5 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B5-33 | **MIC Feature Selection** (Maximal Information Coefficient — captura no-linealidades en features) | Kaabar BT | brain_v2.py |
| B5-34 | **OAM** (Options-Adjusted Momentum: PCR+VRP+momentum combinados → tide_score potenciado) | Bouev | options_adjusted_momentum.py |
| B5-35 | **Sparse Attention Regime** (2 attention heads: aprende qué días históricos son relevantes hoy) | AI Fin Mkts | sparse_attention_regime.py |
| B5-36 | **Counterfactual Explainer** (qué tan lejos estuvo un trade bloqueado de aprobarse — alibi lib) | AI Fin Mkts | counterfactual_explainer.py |

### Mayo — Batch 5 additions

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B5-37 | **Nash Q-Learning Anti-Correlación** (estrategias aprenden espontáneamente a no entrar juntas) | AI Fin Mkts | nash_q_learning.py |
| B5-38 | **Renko Path Signatures nivel 2** (25 features geometría path — invariante a tiempo Renko variable) | AI Fin Mkts | renko_signature_features.py |

---

### Stack actualizado (Batch 5 — Kaabar) — FILAS AÑADIDAS a tabla principal

| Capa nueva | Matemática | Fuente | Implementación |
|---|---|---|---|
| Régimen continuo | SSL Channel (MA highs/lows + zona neutral) | Kaabar BT | market_monitor_logger.py (AHORA) |
| Régimen estructural | Ichimoku Kumo (cloud + proyección 26p) | Kaabar BT | markov_regime.py (Sem 1) |
| Microestructura opciones | GEX (net gamma MM → trending/mean-rev) | Kaabar BT | markov_regime.py (Sem 2) |
| Feature selection no-lineal | MIC (Maximal Information Coefficient) | Kaabar BT | brain_v2.py (Sem 4) |
| Fundamental semanal | COT Variable Barrier + PCR diario | Kaabar BT | market_monitor_logger.py (Sem 1-2) |
| Admisión al portafolio | OSRT (IS/OOS ratio) + NSR Test + HRSS + CLCA | Kaabar BT | osrt_validator.py + nsr_test.py (AHORA+Sem 1) |
| Validación cross-instrumento | SPM + CARV (MNQ+MES+NQ cross-asset) | Kaabar BT | symmetrical_perf_matrix.py (Sem 1-2) |
| Robustez 2D | PSH (heatmap param1×param2 — pico estrecho = overfitting) | Kaabar BT | param_sensitivity_heatmap.py (Sem 1) |
| Microestructura ejecución | IMRT + FRQS + Arrival Price + PRA + Alpha Capture | Bacidore | imrt_score.py + fill_quality_monitor.py (Sem 1-2) |
| Modelo costos no-lineal | Pre-Trade Cost Elasticity (costo ∝ size^0.6) | Bacidore | pre_trade_cost_model.py (Sem 2) |
| IS descompuesto | Shortfall 4 componentes → Opportunity Cost al TfT | Bacidore | shortfall_decomposer.py (Sem 2) |
| Normalización temporal | Volume Clock (calendar time → volume time para HMM) | Bacidore | volume_clock_resampler.py (Sem 3) |
| Options intelligence | VTS + IVR + PCR + SKEW + VRP + GEX + IV Slope + OAM | Bouev | vix_term_structure.py + options_sentiment.py (Sem 1-4) |
| Correlación sistémica | Cascade Risk Score (eigenvalue) + MFG Portfolio Stop | AI Fin Mkts | cascade_risk_score.py + mean_field_portfolio_stop.py (Sem 2) |
| Régimen early-warning | Adversarial Regime Detector (AUC>0.70) | AI Fin Mkts | adversarial_regime_detector.py (Sem 1) |
| Explicabilidad XAI | Counterfactual Explainer (alibi lib) complementa SHAP | AI Fin Mkts | counterfactual_explainer.py (Sem 4) |
| Multi-agent RL | Nash Q-Learning anti-correlación emergente | AI Fin Mkts | nash_q_learning.py (Mayo) |
| Integridad infraestructura | Latency Budget + Position Reconciler + Seq# Gap | HFT Sys | latency_monitor.py + position_reconciler.py (AHORA) |
| Control señales | ATG + Correlation Slots dinámicos (correlación >0.7 = 1 slot) | HFT Sys | throttle_gate.py + correlation_monitor.py (Sem 1) |
| Estado bot | Session State Machine FSM + OBIR Level 2 | HFT Sys | session_state_machine.py (Sem 2) |
| Slippage live | EQS percentiles p50/p90/p99 por estrategia | HFT Sys | execution_quality.py (Sem 3) |

---

### Insights clave del Batch 5 (Kaabar)

> **Ley de Degradación por Frecuencia:** 100+ backtests confirman que sistemas con >3,000 señales/período tienen expectancy ≤ 0 en índices con costos reales. El Filtro Accidental (ULTRA/SCALPER = 1 trade/día) es la implementación involuntaria de esta ley. Techo máximo recomendado para MNQ: 5-8 trades/día/estrategia.

> **OSRT — criterio de admisión faltante:** Los criterios actuales (R² > 0.85, MaxDD < $7,500) no miden degradación IS→OOS de forma normalizada. OSRT = Sharpe_OOS/Sharpe_IS > 0.50 llena este gap. Implementar AHORA antes de paper trading Apex.

> **Backtest validation stack (nueva capa):** HRSS + CLCA dan la base empírica para calibrar los thresholds del Tit-for-Tat (cuándo desactivar una estrategia) con datos del backtest, no heurística. SPM + CARV previenen aceptar estrategias que solo funcionan en MNQ por over-fitting al rollover/tick-size específico.

> **SSL Channel vs tide_score actual:** El SSL calcula cada barra (sin ventana ciega de 4-7h). La zona neutral actúa como filtro de régimen automático — análogo al BreadButter BALANCED que no opera sin dirección clara.

> **GEX + régimen:** GEX>0 (mean-reverting) → MMs compran caídas y venden subidas → estrategias trend-following pierden. Correlacionar GEX diario con P&L histórico del portafolio para validar antes de implementar.

> **Hallazgos negativos (evitar en Midas):** RSI standalone, MACD cross-zero, Stochastic solo, CCI, SAR señal, BB contrarian, candlestick patterns, Awesome Oscillator → todos con expectancy negativa confirmada. Solo features secundarios del RF.

> **AI for Financial Markets:** Cascade Risk Score es el concepto de mayor ROI del batch: 15 líneas de código, usa la matriz de correlación ya planificada, y produce un número único que resume el riesgo sistémico del portafolio. El 17/03 habría tenido cascade_score ≈ 1.0 cuando StatMean+EMATrend+BBv5 entraron juntos. Adversarial Regime Detector se implementa en 2 horas con los market_logs existentes y da early-warning antes del primer fallo. Estos dos son los conceptos a implementar primero de todo el Batch 5.

> **Bacidore (Practitioners Guide):** IMRT (|close-open|/σ > 2.3) captura intradía cuando el mercado ya se movió demasiado — señal de reversión que el Renko actual no detecta. FRQS + Arrival Price juntos revelan cuándo el slippage real destruye el edge de estrategias con PF ajustado (SCALPER, BALANCED).

> **HFT Systems:** Position Reconciler + Latency Budget son AHORA porque operan sin ellos significa operar con datos posiblemente incorrectos. Sequence Number Gap es barato de implementar y previene el escenario silencioso más peligroso de ZMQ.

---

## MAPA COMPLETO — Batch 6: Carpeta Telegram (23/03/2026)
### Market Profile + Order Flow + Game Theory + HFT + Misc

### IMPLEMENTAR AHORA (urgencia máxima del Batch 6)

| # | Concepto | Fuente | Archivo | Urgencia |
|---|---|---|---|---|
| B6-0a | **VWAP SD Bands intraday** (±1σ/2σ: régimen dinámico por sesión — fix ventana ciega 4-7h tide_score) | Trader Dale | vwap_regime_intraday.py | 🔴 Fix documentado MEMORY.md |
| B6-0b | **CVD Monitor** (proxy (C-O)×Vol → divergencia precio/flujo en Renko — habría alertado 17/03) | Trader Dale | cvd_monitor.py | 🟡 Proxy ahora, tick data Mayo |
| B6-0c | **Units Correlation Cap** (MaxCorrelatedUnits=6 en C# NinjaScript — regla Turtle sin ML) | Curtis Faith | correlation_units_cap.cs | 🔴 **habría limitado 17/03** |
| B6-0d | **Comeback Ratio DD Ladder** (sizing intraday determinista: si DD=$3k → size×0.25 matemáticamente) | Survival Guide | portfolio_heat_monitor.py | 🔴 **habría cortado 06/03** |

### Semana 1 Abril — Batch 6 additions (Market Profile + Aldridge/LIT + Trader Dale)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B6-7 | **VAH/VAL Context** (open fuera del VA → 80% prob viaje al otro extremo — imán estructural) | Dalton/Steidlmayer | market_profile_features.py |
| B6-8 | **Initial Balance Expansion** (IB range 9:30-10:30 ET: extensión >1.5x = día tendencia real) | Dalton/Steidlmayer | market_profile_features.py |
| B6-9 | **POC Migration** (dirección migración del POC hora a hora = sesgo institucional del día) | Dalton/Steidlmayer | market_profile_features.py |
| B6-15 | **FVG Quantifier** (Fair Value Gap 3-velas: gap>0 = imán retorno 50-70% — feature price action RF) | LIT Trap | fvg_detector.py |
| B6-16 | **CHoCH Detector** (Change of Character: break swing + vol>P75 = cambio estructura intraday) | LIT Trap | choch_detector.py |
| B6-17 | **HFT Participation Rate** (vol/tick ratio: alto = flow genuino; bajo = HFT noise → gate apertura) | Aldridge | order_flow_monitor.py |
| B6-22 | **RRG** (Relative Rotation Graph: JdK RS-Ratio + RS-Momentum NQ vs ES/YM/RTY — reemplaza breadth) | CMT III | rrg_breadth_score.py |
| B6-27 | **Poor High / Poor Low** (último 10% rango <20% vol → subasta incompleta → retorno >60% prob) | Trader Dale | market_profile_features.py |
| B6-32 | **ADF+Hurst+OU Gate** (3 tests combinados: si falla 1 → StatMeanCross no opera ese día) | Chan vol.1 | mean_reversion_gate.py |
| B6-33 | **Signal Staleness Filter** (barras_desde_breakout > umbral → señal inválida → skip entry) | Curtis Faith | signal_staleness_filter.py |
| B6-34 | **Condition Map** (árbol exhaustivo pre-mercado: VIX+5%+news+bear → ALL size×0.25, sin ML) | Trading No Pred. | condition_map.py |

### Semana 2 Abril — Batch 6 additions (Binmore + Market Profile + Trader Dale)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B6-1 | **ESS** (Evolutionarily Stable Strategy: co-existencia EMA(21)-sharing strategies → inestable) | Binmore | ess_strategy_selector.py |
| B6-2 | **Folk Theorem** (δ mínimo para cooperación: en alta vol δ cae → portfolio cooperativo se rompe) | Binmore | folk_theorem_cooperation.py |
| B6-10 | **Excess vs Poor High/Low** (calidad del extremo previo: single prints = rechazo; múltiples TPOs = re-test) | Dalton/Steidlmayer | market_profile_features.py |
| B6-11 | **Single Prints** (agujeros en perfil TPO → subasta pendiente → imán retorno ~70%) | Dalton/Steidlmayer | market_profile_features.py |
| B6-12 | **TFP Control Score** (OTP institutional vs Local: +1=OTP bull / -1=OTP bear / 0=Local choppy) | Dalton/Steidlmayer | tfp_control_detector.py |
| B6-18 | **Liquidity Pool Map** (swing H/L + round numbers + wick extremos = zonas stop hunt previas) | LIT Trap | liquidity_pool_map.py |
| B6-19 | **Adverse Selection Tracker** (midprice drift post-entry: cada estrategia vs flow informado) | Aldridge | adverse_selection_tracker.py |
| B6-20 | **Cross-Asset Lead-Lag intraday** (CCF ES→MNQ lag 2-30s — extensión intraday del breadth) | Aldridge | lead_lag_detector.py |
| B6-21 | **Inducement Score** (minor swing + vol<P60 + cierre-3-bricks = pre-filtro Failed Breakout) | LIT Trap | inducement_score.py |
| B6-23 | **PAS** (Portfolio Alignment Score: alineación estructural prospectiva vs régimen HMM) | CMT III | portfolio_alignment_score.py |
| B6-24 | **Intermarket Divergence Score** (NQ vs SOX/HYG/VIX/DXY: corr < P20 = alerta régimen) | CMT III | intermarket_divergence_score.py |
| B6-28 | **Absorption Detector** (delta en POC/VWAP absorbido → reversión alta prob — mejora OFR_v1) | Trader Dale | absorption_detector.py |
| B6-29 | **IB Classifier** (initiative: IB<0.75×ATR5 + expansión unilateral → tendencia real del día) | Trader Dale | initial_balance_classifier.py |
| B6-30 | **POC Migration** (POC sube durante sesión = valor construido; oscila = chop → no trend) | Trader Dale | market_profile_features.py |
| B6-35 | **Exit Signal Asymmetry** (time decay: cuanto más tiempo abierto → trailing más ajustado) | Chan vol.1 | trade_time_decay_exit.py |

### Semana 3 Abril — Batch 6 additions (Binmore + Market Profile)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B6-3 | **Correlated Equilibrium** (brain como correlacionador central: Pareto-superior a Nash — solución 17/03) | Binmore | correlated_equilibrium_router.py |
| B6-4 | **Revelation Principle + Mecanismo IC** (Sharpe rolling sizing = mecanismo que extrae tipo real) | Binmore | mechanism_design_incentives.py |
| B6-13 | **Profile Shape D/P/b/B** (perfil B = doble distribución = chop destructor → size×0.25 todo portafolio) | Dalton/Steidlmayer | market_profile_features.py |
| B6-14 | **Auction Rotation Factor** (rotaciones aceptadas vs rechazadas: auction_state = accepting/balanced) | Dalton/Steidlmayer | market_profile_features.py |
| B6-25 | **Basel Traffic Light + Kupiec POF** (validación rolling 250 días del modelo VaR/CVaR) | FRM Book 2 | var_model_validator.py |

### Semana 4 Abril — Batch 6 additions (Binmore)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B6-5 | **Bayesian Game tipos ocultos** (cada estrategia tiene tipo privado: sesgo en régimen actual) | Binmore | bayesian_game_portfolio.py |
| B6-26 | **Spectral Risk Measures** (φ(p) weighting: peor 1% pesa 10x > peor 5% — calibrado a Apex $7,500) | FRM Book 2 | spectral_risk_measure.py |

### Mayo — Batch 6 additions (Binmore + FRM)

| # | Concepto | Fuente | Archivo |
|---|---|---|---|
| B6-6 | **Signaling Game + Separating Eq.** (test Cho-Kreps: señal separadora real vs pooling/ruido) | Binmore | signaling_game_regime.py |
| B6-31 | **Footprint Imbalance** (bid vs ask ejecutado por nivel: >3:1 = S/R persistente — requiere tick NT8) | Trader Dale | footprint_imbalance.py |

---

### Stack actualizado (Batch 6 — Binmore parcial)

| Capa nueva | Matemática | Fuente | Implementación |
|---|---|---|---|
| Fix ventana ciega | VWAP SD Bands intraday (±1σ/2σ/3σ dinámico por sesión cada 5min) | Trader Dale | vwap_regime_intraday.py (AHORA) |
| CVD flujo | CVD proxy (C-O)×Vol → divergencia precio/flujo → tick data Mayo | Trader Dale | cvd_monitor.py (AHORA→Mayo) |
| Estructura de subasta | VAH/VAL + IB + POC + Single Prints + TFP + Profile Shape | Dalton/Steidlmayer | market_profile_features.py + tfp_control_detector.py (Sem 1-3) |
| Price action cuantificado | FVG + CHoCH + Liquidity Pool + Inducement Score | LIT Trap | fvg_detector.py + choch_detector.py (Sem 1-2) |
| Microestructura HFT | HFT Participation Rate + Adverse Selection + Lead-Lag | Aldridge | order_flow_monitor.py + adverse_selection_tracker.py (Sem 1-2) |
| Breadth institucional | RRG (reemplaza market_breadth_score) + Intermarket Divergence | CMT III | rrg_breadth_score.py + intermarket_divergence_score.py (Sem 1-2) |
| Alineación portafolio | PAS (prospectivo, complementa TfT reactivo) | CMT III | portfolio_alignment_score.py (Sem 2) |
| Validación modelo riesgo | Basel TL + Kupiec POF + Christoffersen clustering | FRM Book 2 | var_model_validator.py (Sem 3) |
| Riesgo espectral | Spectral Risk Measures φ(p) Apex-calibrado | FRM Book 2 | spectral_risk_measure.py (Mayo) |
| Selección evolutiva | ESS (estabilidad co-existencia estrategias) | Binmore | ess_strategy_selector.py (Sem 2) |
| Cooperación formal | Folk Theorem δ-descuento | Binmore | folk_theorem_cooperation.py (Sem 2) |
| Coordinación central | Correlated Equilibrium (brain router) | Binmore | correlated_equilibrium_router.py (Sem 3) |
| Mecanismo incentivos | Revelation Principle IC | Binmore | mechanism_design_incentives.py (Sem 3) |
| Información incompleta | Bayesian Game + Signaling | Binmore | bayesian_game_portfolio.py + signaling.py (Sem 4 + Mayo) |

---

### Insights clave del Batch 6

**Trader Dale (VWAP + Order Flow + Volume Profile):**
- VWAP SD Bands **resuelve directamente** el bug de ventana ciega 4-7h de `tide_score` — no requiere datos nuevos, solo yfinance 1-min cada 5min. Implementar AHORA.
- CVD proxy `(Close-Open)×Volume` captura flujo institucional sin tick data — correlación >0.85 con CVD real en MNQ 1-min. Funcional desde Semana 1; full tick data en Mayo vía NT8 ZMQ.
- Absorption Detector en POC/VWAP mejora directamente `OrderFlowReversal_v1` (PF=2.20 → proyectado >3.0). Mayor impacto de todo el batch en estrategias existentes.
- Initial Balance Classifier: los días 06/03 (-$11,920) y 17/03 (-$8,906) tenían IB de tendencia unilateral → habrían activado modo tendencia → StatMean + BBv5 corregidos.

**Dalton/Steidlmayer (Market Profile × 5 libros):**
- NT8 tiene Market Profile nativo exportable vía C# → ZMQ → Python. No necesita reconstrucción tick-level. VAH/VAL/POC disponibles desde Semana 1.
- Profile Shape B (doble distribución) es el peor escenario para el portafolio — `size×0.25` todo el portafolio ese día. Fácil de detectar: POC bimodal + oscilación VA. Coste bajo, beneficio alto.
- Single Prints (~70% prob retorno): contexto directo para filtrar entradas en dirección de los agujeros. Parecido a imán pero cuantificado.
- TFP Control Score: si OTP institucional controla → operar con tendencia; si Local → evitar breakouts.

**Ken Binmore (Game Theory):**
- **Correlated Equilibrium** es la justificación matemática de por qué el brain centralizador (Midas) supera a estrategias independientes. El 17/03 fue exactamente el fallo de Nash descentralizado (3 estrategias siguieron señal idéntica). El brain como correlacionador es la solución correcta.
- **ESS**: estrategias coexisten si tienen nichos distintos (Renko=señal, IB=sesión, OFR=microestructura). Eliminar una que "falla" puede crear invasión de otra peor — monitorear siempre la diversidad del portafolio.
- Folk Theorem: la cooperación entre estrategias (no apostar contra la propia posición) requiere δ alto. En alta volatilidad δ cae → el portafolio cooperativo se fragmenta → señal para reducir size global.

**Aldridge HFT + LIT Trap:**
- Cross-Asset Lead-Lag ES→MNQ (lag 2-30s): en barra 1-min de MNQ ya está incorporado el movimiento de ES. Útil como filtro de entrada: si ES lleva >5 ticks en misma dirección en últimos 30s, la señal MNQ es tardía.
- FVG + CHoCH cuantificados dan la dimensión de precio del LIT framework. Combinados con Liquidity Pool Map: si precio se mueve hacia pool de stops Y hay CHoCH → probabilidad de reversión >65%.
- Inducement Score: pre-filtro para entradas de ULTRA. Si score >0.7, la señal es probablemente un stop hunt → no entrar o esperar confirmación CHoCH.
- Adverse Selection Tracker por estrategia: métrica clave para detectar si una estrategia está siendo consistentemente "comida" por flujo informado → señal para suspenderla en ese régimen.

**CMT III (RRG + Intermarket):**
- RRG reemplaza completamente `market_breadth_score` — en lugar de conteo binario bullish/bearish, da cuadrante rotacional (improving/leading/weakening/lagging) para NQ vs sector. Más información, misma fuente de datos (yfinance).
- Intermarket Divergence Score: NQ+5% pero HYG-2% = divergencia crédito/equity → alta prob corrección inminente. Este patrón precedió el 06/03 y 17/03.
- PAS (Portfolio Alignment Score): fuerza un chequeo prospectivo antes de abrir sesión — cuántas estrategias apuntan en la misma dirección del régimen macro vs cuántas van contra. Complementa TfT (reactivo) con visión anticipatoria.

**FRM Book 2 (Riesgo cuantitativo):**
- Basel Traffic Light: 3+ excepciones VaR/semana = amarillo → reducir size 50%. 5+ = rojo → parar. Métrica operativa directa para el brain.
- Spectral Risk Measures: ponderar el peor 1% de días 10x más que el peor 5% da un capital reserve más conservador y más alineado con Apex $7,500 limit. Superior al CVaR flat.

**Chan vol1 + Turtle + Trading No Predictivo + Survival Guide:**
- **Units Correlation Cap** (Turtle): límite duro `MaxCorrelatedUnits=6` es la regla operativa más simple y de mayor impacto inmediato. Sin ML, sin Python, directo en C#. El 17/03 tenían 3 estrategias Long en correlación >0.8 → habrían contado como 6+ unidades → trade nunca hubiera abierto.
- **Comeback Ratio**: `CR = 1/(1-loss) - 1` — si DD acumulado es 20%, necesitas 25% para recuperar. Escalar size DOWN linealmente con CR es determinista y opera como freno automático. El 06/03 (-$11,920 en 1 día) habría sido frenado en -$4,000 por el ladder.
- ADF+Hurst+OU Gate: tres tests simultáneos como "licencia de operación diaria" para StatMeanCross_v1. Si el mercado no es mean-reverting ese día → la mejor estrategia simplemente no abre. Protección asimétrica de alto valor.
- Condition Map: árbol pre-mercado exhaustivo sin ML. Ejemplo: `si VIX>30 + news FOMC + tendencia bear → ALL size×0.25`. Cubre los edge cases que los modelos nunca ven porque son raros — exactamente los días de mayor pérdida.

---

## CALENDARIO CRÍTICO

| Fecha | Hito |
|-------|------|
| 09/03/2026 | Primer market_log grabado. Step Lock BBv5 activo. |
| 01/04/2026 | Inicio Semana 0: análisis completo de marzo |
| 07/04/2026 | Semana 1: Markov básico + market_monitor completo |
| 14/04/2026 | Semana 2: News filter + Tit for Tat |
| 21/04/2026 | Semana 3: Monte Carlo Risk Engine |
| 28/04/2026 | Semana 4: Brain v2 con todos los módulos |
| Mayo-Jun | Brain proactivo, correlación, stress testing |
| Jul-Sep | Apex real — prerequisitos cumplidos |
| 2027 | Darwin/X — track record 6-12 meses verificable |

---

## FILOSOFÍA DEL PROYECTO
> "La marea (1D/4H) define el campo de batalla.
>  El mar (1H/30M) define si vale la pena pelear.
>  La ola (señal) define el momento exacto.
>  Markov predice hacia dónde va la marea mañana.
>  Von Neumann decide si el riesgo vale el arrepentimiento.
>  Tit for Tat confía en quien se lo merece.
>  El brain Midas integra todo y decide.
>  Pablo ejecuta el sueño."
>
> Un sistema que sabe cuándo NO operar vale más que uno que siempre opera.
> El underdog más peligroso es el que no para de aprender.

**El bot se llama MIDAS. El objetivo es Darwin/X 2027.**
