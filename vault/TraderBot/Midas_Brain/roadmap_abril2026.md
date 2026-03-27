# ROADMAP POST-MARZO — Inicio 01/04/2026
## "El 60% que falta para Darwin/X"

---

## DIARIO DE TRADING — Semanas 1-3 de Recolección de Data
### "Todo buen trader lleva su bitácora"
> **Período total**: 02/03 al 20/03/2026 | 15 días hábiles | 710 trades
> **Balance del período**: +$366 (esencialmente breakeven) — el sistema sobrevivió sus primeras semanas sin colapsar
> **Peor día**: 06/03 (-$11,920) | **Mejor día**: 13/03 (+$7,191)
> **Fuente de datos**: CSV exportado de NinjaTrader 8 (columna cumulative profit)
> **Bug de infraestructura**: strategies_pnl_*.json sobreescribidos a cero el 20/03/2026 por auto_push_pnl.bat — fuente de verdad es siempre el CSV de NT8

---

### 02/03/2026 (Lunes) — SEMANA 1, DÍA 1: Bautismo del Portafolio
**Resultado del día:** Datos en NT8 CSV (reconstruir con export)
**Contexto:** Primer lunes operativo con el portafolio completo. Contrato MNQ 03-26 activo.
**Observaciones:** Día de calibración — el sistema arranca con todas las estrategias simuladas corriendo simultáneamente por primera vez. Sin grandes eventos macroeconómicos confirmados.
**Nota operativa:** El inicio del período. Referencia de baseline para medir evolución.

---

### 03/03/2026 (Martes) — SEMANA 1, DÍA 2
**Resultado del día:** Datos en NT8 CSV
**Observaciones:** Segunda sesión. Portafolio en modo observación.

---

### 04/03/2026 (Miércoles) — SEMANA 1, DÍA 3
**Resultado del día:** Datos en NT8 CSV
**Observaciones:** Mitad de semana. Evaluar si B&Bv5 generó algún trade outlier.

---

### 05/03/2026 (Jueves) — SEMANA 1, DÍA 4: EMATrendRenko confirmada
**Resultado del día:** Datos en NT8 CSV
**Contexto:** EMATrendRenko_v1 confirmada en backtest el 05/03 con RegimeFilter ON (PF=2.29, Sortino=6.75). StatMeanCross confirmada el 06/03.
**Nota:** Esta semana fue de confirmaciones importantes en backtesting — el portafolio se expandió de ~15 a 17 estrategias. El foco estaba en validación, no solo en P&L diario.

---

### 06/03/2026 (Viernes) — SEMANA 1, DÍA 5: EL DÍA MÁS DURO ⚠️
**Resultado del día:** **-$11,920** (PEOR DÍA DEL PERÍODO — superó a 17/03)
**Qué pasó:** Pérdida catastrófica. B&Bv5 fue identificado como el swing factor principal del portafolio — sus outliers (positivos o negativos) definen los días extremos. StatMeanCross confirmada en backtest este mismo día, pero el paper trading ya mostraba volatilidad sistémica.
**Mercado:** Probable régimen de alta volatilidad o evento macro sin filtro activo. El tide_score nocturno no capturó el riesgo intraday.
**Lección anticipada:** Este día llegó ANTES de que las lecciones de correlación fueran formalmente registradas. La pérdida de 06/03 fue mayor que la del 17/03 pero sin el análisis forense que hicimos después. **Es el día que debería haber disparado la alarma de correlación.**
**Correctivo diseñado (retrospectivo):** Portfolio Stop Global ($LimiteDiario) habría cortado las pérdidas. KDL Gate 2.5 podría haber detectado el momentum adverso. Capa 6 Correlación habría reducido sizing.

---

### 09/03/2026 (Lunes) — SEMANA 2, DÍA 6: Recuperación post-shock
**Resultado del día:** Datos en NT8 CSV
**Contexto:** Primera sesión después del -$11,920 del viernes. Psicológicamente importante — el sistema en paper trading no tiene ego, pero el trader sí. El valor del paper trading: permite observar recuperaciones sin el daño emocional del capital real.
**Observación:** Si el sistema se recupera tras el peor día, la robustez está demostrada.

---

### 10/03/2026 (Martes) — SEMANA 2, DÍA 7
**Resultado del día:** Datos en NT8 CSV
**Nota operativa:** Continúa el contrato MNQ 03-26. Rollover a MNQ 06-26 programado para 16/03.

---

### 11/03/2026 (Miércoles) — SEMANA 2, DÍA 8: Primer Evento de Correlación Documentado
**Resultado del día:** Datos en NT8 CSV
**Evento identificado:** A las **9:44 AM** — StatMeanCross y EMATrendRenko dispararon en la **misma dirección simultáneamente**. Primer registro confirmado del patrón de correlación. Ambos perdieron juntos.
**Diferencia con 17/03:** Solo 2 estrategias afectadas (vs 3 el 17/03). La pérdida fue contenida pero el patrón ya estaba presente.
**Valor de este dato:** Este evento del 11/03 es el PRIMERO de 3 eventos correlacionados en el período. Confirma que el patrón es sistémico y no accidental. StatMean y EMATrend comparten señales de entrada similares (EMA como componente central en ambas).
**Raíz técnica:** StatMeanCross usa EMA(21) para crossover. EMATrendRenko usa EMA(21) como soporte/resistencia. Misma EMA = misma señal en el mismo brick de Renko.

---

### 12/03/2026 (Jueves) — SEMANA 2, DÍA 9
**Resultado del día:** Datos en NT8 CSV
**Contexto:** Día previo al mejor día del período.

---

### 13/03/2026 (Viernes) — SEMANA 2, DÍA 10: EL MEJOR DÍA ⭐
**Resultado del día:** **+$7,191** (MEJOR DÍA DEL PERÍODO)
**Qué pasó:** Día en que el portafolio funcionó como fue diseñado — múltiples estrategias operando en condiciones favorables, probablemente en la misma dirección que el mercado (no en contra). B&Bv5 aportó un trade ganador significativo.
**Mercado:** Probablemente tendencia clara intraday (tide_score positivo/negativo coherente con intraday). Sea state "calm" o "moderate" = condiciones óptimas.
**Lección:** El portafolio tiene el potencial de generar +$7,000 en un solo día — el mismo potencial que genera los -$11,920. La diferencia es la alineación con el mercado. **El objetivo de Midas es capturar más días como este y reducir los días opuestos.**
**Ironía del período:** Este +$7,191 ayudó a recuperar el -$11,920 del 06/03 y el -$8,906 del 17/03. Sin el 13/03, el período habría sido catastrófico.

---

### 14/03/2026 (Sábado) — NO HAY SESIÓN
*(Futuros MNQ operan L-V en horario ETH. Fin de semana 2.)*

---

### 16/03/2026 (Lunes) — SEMANA 3, DÍA 11: ROLLOVER DE CONTRATO
**Resultado del día:** Datos en NT8 CSV
**Evento operativo crítico:** Cambio de contrato MNQ 03-26 → MNQ 06-26 a partir de esta fecha.
**Impacto en datos:** El rollover puede causar gaps en los datos de backtesting históricos. Las estrategias en Renko que dependen de datos de precio continuos pueden mostrar comportamiento diferente en los primeros días del nuevo contrato.
**Alerta del roadmap:** Los resultados de backtest varían significativamente entre MNQ 03-26 y MNQ 06-26 (observado en PivotReverse) — hay que re-validar estrategias con el nuevo contrato cuando se acumule suficiente data.
**Nota:** Primera semana del nuevo contrato. Período de adaptación.

---

### 17/03/2026 — LECCIÓN 01: Correlación Catastrófica
**Resultado del día:** -$8,906 (peor día registrado)
**Qué pasó:** StatMeanCross, EMATrendRenko y BreadButter_v5_Apex entraron Long simultáneamente a las 10:05 AM en pleno mercado bajista. Todos perdieron juntos. PivotReverse Short también falló. Solo BreadButter_SCALPER terminó positivo.
**Patrón identificado:** Múltiples estrategias del mismo lado en el mismo momento = pérdida amplificada. Sin correlación → pérdida individual. Con correlación → catástrofe.
**Mercado:** trend_4H=Bull pero intraday bajista. tide_score=0.8 (swim_ok=True) — el monitor no lo detectó.
**Correctivo diseñado:** KDL Capa 6 (Correlación de Portafolio) — si N estrategias están en el mismo lado simultáneamente → reducir sizing o bloquear tardías. **Deploy: Semana 6 de recolección.**
**Correctivo adicional:** KDL Gate 2.5 (Trend Phase Detector) — slope del EMA habría detectado "Continue bajista" a las 10:05 AM → bloqueado todos los longs.

---

### 20/03/2026 — LECCIÓN 02: Correlación Confirmada (patrón se repite)
**Resultado del día:** +$1,616 (salvado por BreadButter_v5_Apex)
**Qué pasó (AM):** StatMeanCross y EMATrendRenko dispararon SHORT simultáneamente a las **9:46:32 AM exacto** — misma barra, mismo lado, ambos perdieron (-$820 combinado). Mismo patrón del 17/03 pero en dirección opuesta.
**Qué pasó (PM):** DarvasBox Short (+$2,168) + BreadButter_v5_Apex Short supervisado (+$4,200) rescataron el día.
**Mercado:** Claramente bajista todo el día (24,450 → 24,090). Las estrategias longs de la mañana (MomentumZ, PivotTrend) fallaron por ir contra la tendencia diaria.
**Confirmación:** El patrón de correlación aparece en AMBAS direcciones (longs el 17/03, shorts el 20/03) → es sistémico, no casualidad.
**Estado Capa 6:** URGENTE. Ya tiene 2 evidencias en 3 días de observación.

---

### 20/03/2026 — LECCIÓN 03: El Valor de la Supervisión Humana
**Qué pasó:** BreadButter_v5_Apex tomó un Short a las 2:01 PM (24,203). El usuario lo supervisó y cerró manualmente a las 2:51 PM (24,097) → +$4,200 bruto en 50 minutos.
**Exit type = "Close"** (manual) vs el exit automático habitual (Stop loss o Profit target).
**Pregunta para el roadmap:** ¿El exit automático habría capturado más o menos? El MFE fue $3,269 (precio fue hasta ~24,097 y el cierre fue ahí). El ETD fue $543 — lo que devolvió desde el pico. La supervisión humana capturó casi todo el MFE.
**Insight para Midas:** El RL/PPO (Capa 11 — Mayo) aprenderá exactamente este tipo de decisión: cuándo el trailing stop debe ajustarse según momentum vs cuándo salir fijo. El humano hoy fue mejor que el algoritmo. El algoritmo aprenderá de este trade.
**Lección:** En mercados con tendencia diaria clara + ConvictionScore alto → dejar correr más. Midas deberá detectar esto automáticamente.

---

### 18/03/2026 (Miércoles) — SEMANA 3, DÍA 13
**Resultado del día:** Datos en NT8 CSV (archivo 2026-03-18.json disponible en market_logs)
**Contexto:** Tercer día post-rollover MNQ 06-26. Sistema estabilizándose con el nuevo contrato.
**Observación:** Sin eventos de correlación documentados para este día. Operativa de portafolio normal.
**Nota:** Un día "aburrido" en paper trading es una victoria — significa que ningún evento sistémico malo ocurrió. Los días sin drama son los que construyen el P&L consistente.

---

### 19/03/2026 (Jueves) — SEMANA 3, DÍA 14
**Resultado del día:** Datos en NT8 CSV (archivo 2026-03-19.json disponible en market_logs)
**Contexto:** Penúltimo día de la semana. Mañana (20/03) terminará la Semana 3 de recolección — a mitad del período de 6 semanas.
**Observación:** Sin eventos de correlación documentados para este día.
**Preparación para el análisis de mitad de período (W6):** Los patrones ya visibles a esta altura: B&Bv5 como swing factor principal, StatMean+EMA como par de correlación sistémica, y el éxito de las estrategias de tendencia en días trending.

---

## RESUMEN DE PERÍODO 02/03 - 20/03/2026
| Semana | Días | P&L estimado | Evento notable |
|--------|------|-------------|----------------|
| S1 (02-06/03) | 5 | Dominado por -$11,920 del 06/03 | EMATrend y StatMean confirmadas en BT |
| S2 (09-13/03) | 5 | Recuperación; +$7,191 el 13/03 | Rollover próximo; 1er evento correlación 11/03 |
| S3 (16-20/03) | 5 | Mixto; -$8,906 el 17/03; +$1,616 el 20/03 | Rollover MNQ 06-26; 2 eventos correlación |
| **TOTAL** | **15** | **+$366** | **3 eventos correlación documentados** |

**Análisis de varianza del período:**
- **B&Bv5** = factor de swing dominante (días extremos → B&Bv5 involucrado)
- **StatMean + EMATrend** = par de correlación sistémica (misma EMA(21) base)
- **Días buenos**: portafolio alineado con tendencia diaria + no correlación
- **Días malos**: correlación + contra-tendencia + sin Portfolio Stop activo
- **Bug de infraestructura confirmado**: tide_score medido al EOD (1x/día) → ventana ciega de 4-7 horas intraday. Fix en Semana 6: medir tide_score cada 60 segundos via ZMQ.

---

## SEMANA 0 — Análisis de Marzo (01/04 - 04/04)
**Antes de construir nada: entender qué pasó en marzo**

### Tareas:
1. **Exportar trade history** de todas las cuentas sim desde NT8
   - Archivo CSV por estrategia: fecha, hora, dirección, contratos, P&L, duración
2. **Análisis de correlación de marzo**
   - ¿Qué días perdieron todas las estrategias juntas?
   - ¿Coincidieron con noticias? ¿con CI alto?
   - Matriz de correlación entre estrategias
3. **Evaluación del brain BBv5**
   - Trades aprobados vs bloqueados
   - ¿Cuándo acertó? ¿cuándo falló? ¿tiene patrón?
4. **Walk-Forward Validation** de top 5 estrategias
   - Optimizar en 2023-2024 → testar en 2025-2026
   - Si PF cae >30%, la estrategia tiene overfitting → ajustar params o descartar
   - Estrategias a validar: StatMeanCross, PivotTrendBreak, ULTRA, EMATrendRenko, OrderFlowReversal

### Output esperado:
- Informe de correlación de marzo
- Lista de estrategias validadas WFO vs descartadas
- Patrones identificados en los días malos

---

## SEMANA 1 — Infraestructura del Brain Ambiental (07/04 - 11/04)
**Construir el sistema nervioso que "siente el mercado" continuamente**

### Entregable principal: `market_monitor.py`

```python
# Proceso que corre en background, publica cada 60 segundos:
{
  # MAREA (macro)
  "trend_1D":  +1/-1/0,   # EMA slope o ADX+DM diario
  "trend_4H":  +1/-1/0,

  # MAR (intraday)
  "trend_1H":  +1/-1/0,
  "trend_30M": +1/-1/0,
  "choppiness_15M": 58.4,  # CI calculado en 15-min

  # CONTEXTO
  "news_window": True/False,   # ±30min evento macro
  "next_news_minutes": 45,     # minutos hasta próxima noticia
  "session_phase": "open",     # open/mid/close/pre
  "vix_proxy": 18.3,           # volatilidad realizada sintética

  # RESUMEN EJECUTIVO
  "tide_score": -2,            # -3 (full bear) → +3 (full bull)
  "sea_state":  "rough",       # calm/moderate/rough
  "swim_ok":    False,         # ¿vale la pena operar ahora?
  "confidence_multiplier": 0.4 # cuánto del sizing normal aplicar
}
```

### Tareas semana 1:
1. Conectar a fuente de datos OHLCV para múltiples TFs (yfinance o datos NT8 via CSV)
2. Calcular EMA slope + ADX+DM para 1D, 4H, 1H, 30M
3. Implementar Choppiness Index: `CI = 100 * log10(SumATR(N) / (High(N)-Low(N))) / log10(N)`
4. Implementar tide_score ponderado:
   - 1D: peso 3 | 4H: peso 2 | 1H: peso 1.5 | 30M: peso 1
5. Publicar via ZMQ socket para que el brain consuma

### [RL] Experience Replay para Markov (añadir a Semana 1):
- **Concepto DQN aplicado**: No entrenar la matriz de transición Markov con ventana deslizante secuencial. Las muestras consecutivas están altamente correlacionadas — el bar 1001 predice el bar 1002 solo por proximidad, no por causalidad real.
- **Implementación**: Construir un `replay_buffer` de `(estado_mercado_t, estado_mercado_t+1)` con capacidad 50,000 transiciones. Samplear mini-batches de 256 registros aleatorios para calcular probabilidades de transición. Rompe autocorrelación → mejores estimaciones de la matriz.
- **Resultado esperado**: Markov más robusto, menos sesgado por los últimos N días consecutivos.

---

## SEMANA 2 — News Filter + Portfolio Stop (14/04 - 18/04)
**Nadie nada en el mar cuando hay tormenta anunciada**

### Entregable 1: `news_calendar.py`
- Fuente: Forex Factory API (gratuita) o scraper simple
- Eventos HIGH impact: FOMC, NFP, CPI, PPI, GDP, Jobless Claims, ISM, PCE
- Publicar: `{"news_window": true, "event": "CPI", "minutes_to_event": 25}`
- NT8 debe consultar este flag ANTES de ejecutar cualquier entrada
- Bonus: marcar semanas FOMC, semanas OpEx (3er viernes) como "elevated caution"

### Entregable 2: Portfolio Stop Global en NT8
```csharp
// En CADA estrategia — un shared state coordinator
// Si pérdida combinada del día > $LimiteDiario → signal "STOP_ALL"
// Todas las estrategias consultan este flag antes de entrar
```
Alternativa más simple: proceso Python que monitorea P&L de cuentas sim
y publica `{"portfolio_stop": true}` cuando el límite se alcanza.

### Entregable 3: Calendario de patrones estacionales
- Mapear históricamente: FOMC weeks, OpEx, fin de mes, inicio de mes
- Añadir como features al brain: `fomc_week`, `opex_week`, `month_end`, `month_start`

---

## SEMANA 3 — Monte Carlo Risk Engine (21/04 - 25/04)
**Conocer los límites del sistema antes de que el mercado te los enseñe**

### Entregable: `monte_carlo_sizer.py`

```python
def calculate_safe_sizing(trades_history, apex_limit=7500, confidence=0.95):
    """
    trades_history: lista de P&L de trades reales/backtest
    Retorna: contratos máximos seguros para no reventar Apex
    """
    n_sims = 10_000
    results = []
    for _ in range(n_sims):
        shuffled = np.random.choice(trades_history, size=len(trades_history), replace=True)
        max_dd = calcular_max_drawdown(shuffled)
        results.append(max_dd)

    dd_p95 = np.percentile(results, 100 - confidence*100)
    safe_contracts = int(apex_limit / abs(dd_p95))
    ruin_prob = np.mean(np.array(results) < -apex_limit)

    return {
        "safe_contracts": safe_contracts,
        "dd_p95": dd_p95,
        "ruin_probability": ruin_prob,
        "kelly_fraction": calcular_kelly(trades_history)
    }
```

### Correr para cada estrategia con datos de marzo:
- StatMeanCross, PivotTrendBreak, ULTRA, EMATrendRenko, OrderFlowReversal
- Comparar sizing MC vs sizing actual → ajustar si necesario

### Dynamic sizing basado en drawdown actual:
```
drawdown_actual < 20% del MaxDD → sizing 100%
drawdown_actual 20-50% del MaxDD → sizing 75%
drawdown_actual 50-75% del MaxDD → sizing 50%
drawdown_actual > 75% del MaxDD → sizing 25% (modo supervivencia)
```

---

## SEMANA 4 — Upgrade del Brain (28/04 - 02/05)
**De portero binario a asesor con probabilidades**

### Entregable 1: Brain recibe contexto del market_monitor
```python
# Antes (brain ciego):
{"rsi": 45, "adx": 28, "vol_ratio": 1.3, ...}

# Después (brain con contexto de marea):
{"rsi": 45, "adx": 28, "vol_ratio": 1.3, ...
 "tide_score": -2, "sea_state": "rough", "swim_ok": False,
 "news_window": False, "choppiness_15M": 68.4,
 "fomc_week": False, "session_phase": "open",
 "portfolio_drawdown_pct": 0.35}
```

### Entregable 2: Brain retorna probabilidad, no binario
```python
# Antes: {"allow": 1}
# Después: {"allow": 1, "confidence": 0.73, "contracts_multiplier": 0.73,
#            "reason": "tide_score neutral, sea_state moderate, RF_prob=0.73"}
```

### Entregable 3: NT8 usa el confidence_multiplier
```csharp
int contracts = (int)(BaseQuantity * confidence_multiplier);
// confidence 0.9 → full size | 0.5 → half size | 0.3 → no entra
if (contracts < 1) return; // umbral mínimo
```

### [RL] Imitation Learning — bootstrapping del brain_v2 (Semana 4):
- **Concepto AlphaGo aplicado**: AlphaGo usó 30M de partidas humanas para bootstrapping. Los logs de `market_monitor_logger.py` desde el 09/03/2026 + los PnL por estrategia son **exactamente ese dataset** — demonstrations del comportamiento heurístico validado.
- **Pipeline concreto**:
  1. Etiquetar cada trade del período 09/03-presente con outcome: `(estado_mercado, acción_tomada, resultado)`
  2. Entrenar el RF en supervisado imitando este comportamiento (Behavioral Cloning) — fase rápida de bootstrap
  3. Luego RF + reglas ajustadas para superar la heurística base
- **Resultado**: Brain_v2 no arranca desde random — arranca desde el comportamiento heurístico ya validado. Convergencia 3-4x más rápida.

### [RL] Reward Shaping multi-componente — target del RF (Semana 4):
- **Concepto DQN aplicado**: Si el RF clasifica solo `ganó/perdió` (binario), aprende a maximizar micro-ganancias frecuentes → destruye Sortino.
- **Target compuesto para el RF**:
  ```python
  trade_score = pnl_neto_normalizado
              - 0.001 * bars_en_trade        # penaliza holds eternos
              - 0.05 * (1 if trades_hoy > 15 else 0)  # penaliza overtrading
              + 0.10 * (1 if pnl/mae_ratio > 2.0 else 0)  # bonus R:R > 2:1
  ```
- **El RF predice este score**, no solo ganó/perdió. Aprende calidad del trade, no solo dirección.

### [RL] Curriculum Learning — pipeline de entrenamiento RF (Semana 4):
- **Concepto AlphaZero aplicado**: Entrenar de mercados fáciles a difíciles evita que el RF se confunda desde el día 1 con patrones contradictorios.
- **3 etapas con los datos de marzo**:
  1. Días con tendencia clara (tide_score ≥ +2 o ≤ -2): 500 trades → RF aprende el caso base
  2. Días mixtos (tide_score -1 a +1): 150 trades → RF aprende transiciones
  3. Días volátiles/noticias (sea_state = "rough"): 60 trades → RF aprende a decir "no operar"
- **No entrenar con todo mezclado desde el principio** — el RF se confunde y generaliza peor.

---

## MAYO-JUNIO — Brain Proactivo (Fase 3)
**El brain deja de ser reactivo y empieza a liderar**

### Conceptos a implementar:
1. **Online learning layer**: actualiza pesos del RF diariamente con últimos 5 trades
2. **Correlation-aware sizing**: si correlación entre estrategias > 0.7, reduce sizing global 50%
3. **Cross-strategy confirmation**: si 3+ estrategias señalan la misma dirección → sizing 1.5x
4. **Stress testing**: correr todas las estrategias contra datos COVID 2020 y Bear 2022
5. **Benchmark alpha**: comparar retornos vs buy-and-hold QQQ ajustado por volatilidad
6. **Multi-strategy brain central**: un solo proceso coordina todas las estrategias
7. **RL brain_v3 con ε-greedy**: exploración/explotación — ε=0.30 inicio, decae a 0.05 en producción
8. **GA optimizer**: auto-evolucionar params de cada estrategia (fitness = Sortino×0.40 + DD×0.30 + R²×0.20 + ruin×0.10)
9. **HMM (Hidden Markov Model)**: upgrade del Markov simple — estados de régimen OCULTOS inferidos desde precio/volumen/volatilidad sin que los definamos manualmente. Inspirado en Renaissance Technologies (Mercer/Brown venían de reconocimiento de voz donde HMM es fundamental). `pip install hmmlearn` — reemplaza/complementa markov_regime.py. 4 estados ocultos: el modelo los descubre solo.

### PENDIENTE EVALUACIÓN (Mayo):
- **Hurst Exponent como selector de estrategias**: H > 0.6 = mercado persistente → activar tendenciales (ULTRA, EMA, SuperTrend). H < 0.4 = mean-reverting → activar reversales (StatMean, ABCD, PivotReverse). H ≈ 0.5 = ruido → swim_ok=False. Implementar en `market_monitor_logger.py`. CI ya es una aproximación pero Hurst es más preciso matemáticamente. Capa 11 del stack.
- ~~**EVOLA-style Volatility Compression Detector**~~: **ABSORBIDO 17/03/2026** → BC Zone (compresión) = Choppiness Index (Capa 1). LD Pulse (expansión con volumen) = KDL Gate 3 Volume Participation (Capa 4). No es capa separada.
- **Supply & Demand Zone — DOBLE ROL (17/03/2026)**:
  - **Como capa Midas**: Midas mapea zonas D&S activas (último impulso fuerte = zona de demanda/oferta) y las usa como S/R dinámico para filtrar entradas. Si el precio está en zona de oferta → no longs. Si está en zona de demanda → no shorts. Capa de contexto estructural, complementa KDL Gate 1.
  - **Como estrategia #18**: estrategia pura D&S en Renko — entrada en pullback a zona, SL debajo de zona, TP = siguiente zona. Baja correlación con portafolio actual. VWAPOrderBlock la toca parcialmente pero no es D&S puro. Evaluar en Mayo.
- **Market Structure Renko — HH/HL/LL/LH (17/03/2026)**:
  - En Renko los swings son limpios (sin ruido de timeframe). Trackear los últimos 7 swings: si secuencia = HH+HL → estructura alcista confirmada. Si LH+LL → estructura bajista confirmada. Transición HH→LH = primera señal de reversal (alerta). Transición HL→LL = reversal confirmado.
  - **Como capa Midas**: gate de estructura — solo permite longs en estructura HH/HL. Solo permite shorts en LH/LL. En transición (primer LH en uptrend) → reduce sizing 50%.
  - **Como estrategia**: entrada en el breakout del HH/HL anterior con SL en el LL más reciente. Complementa PivotTrendBreak pero basado en estructura pura de market, no en pivots calculados. Evaluar en Mayo.
- **KDL Gate 2.5 — Trend Phase Detector (Flex Trend Engine$ concept, 20/03/2026)**:
  - **El concepto**: Flex Trend Engine$ ($306, ninza.co) detecta que dentro de un trend hay 2 fases distintas: "Trend Continue" (slope del MA empinado = precio corriendo) y "Trend Flat" (slope del MA plano = precio en pausa/pullback). El momento óptimo de entrada es cuando Trend Flat termina y Trend Continue reanuda.
  - **Por qué es nuevo**: nuestras capas detectan Bull/Bear/Neutral (TIPO de mercado) pero ninguna detecta la FASE INTRA-TENDENCIA. La diferencia: puedes estar en mercado Bull pero en fase "Continue" bajista intraday — exactamente lo que ocurrió el 17/03 cuando StatMean/EMATrend/BreadButter entraron long a las 10:05 AM.
  - **Implementación propia (gratis)**: `slope = (ema_actual - ema_hace_N_barras) / N` → si `abs(slope) > threshold` → fase "CONTINUE" (no entrar en contra). Si `abs(slope) <= threshold` → fase "FLAT" (pullback activo, buscar entry de continuación). En Renko el slope es especialmente estable por brick size fijo.
  - **Integración en KDL**: nueva Gate 2.5 entre Trend Strength (Gate 2) y Volume Participation (Gate 3):
    ```
    Gate 2.5: Phase Gate
    → CONTINUE + dirección = solo permite trades EN esa dirección
    → FLAT = habilita pullback entries (nuestro edge principal)
    → CONTINUE opuesto = BLOQUEA totalmente → habría evitado -$1,100 el 17/03
    ```
  - **2 modos adaptativos** (concepto Sensitive/Confirmed de Flex):
    - ConvictionScore 60-80 → modo Sensitive: acepta fase FLAT incipiente
    - ConvictionScore 80+ → modo Confirmed: espera confirmación de reanudación
  - **Implementar en**: `market_monitor_logger.py` → nuevo campo `trend_phase: "CONTINUE"/"FLAT"` por timeframe (1H, 30M)
  - **Semana de implementación**: Semana 2 Abril (junto con KDL completa)

- **Polymarket Macro Filter**: integrar API de Polymarket como capa de sentiment fundamental. Las probabilidades de Polymarket = "dinero real apostado" (Taleb: skin in the game) → señal más honesta que Twitter/noticias. Casos de uso: P(oil>$90), P(Fed cut), P(geopolitical event) → `macro_score` que pondera el tide: `tide_ajustado = tide × (1 + macro_score × 0.3)`. Implementar en `market_monitor_logger.py` como módulo `polymarket_sentiment.py`. Polymarket tiene API REST pública. Esta capa responde la pregunta que el análisis técnico no puede: *¿qué cree el mercado que va a pasar?*

- **OmniSpectrum → Brick Speed + Momentum Quality Score (20/03/2026)**:
  - **El concepto**: OmniSpectrum Scan (ninza.co) estudia la anatomía de cada vela en 8 dimensiones. La más novedosa para Renko: **velocidad de formación del brick** (segundos que tardó en completarse). En Renko el precio del brick es fijo (35 ticks), por eso la velocidad es una señal pura de momentum.
  - **Por qué es nuevo para nosotros**: Ninguna de nuestras estrategias ni capas mide cuánto tiempo tarda en formarse el brick. Solo miramos dirección y volumen. La velocidad añade la tercera dimensión.
  - **Interpretación**:
    - Brick rápido (< percentil 25 de tiempo) = orden flow concentrado → mercado corriendo → fase CONTINUE
    - Brick lento (> percentil 75 de tiempo) + delta balanceado = absorción → mercado pausando → fase FLAT
    - Brick rápido + delta extremo + volumen alto = "Momentum Bar" (señal de máxima calidad)
    - Brick lento + delta casi cero + volumen alto = "Absorption Bar" (liquidez siendo absorbida → posible reversal)
  - **Mejora a Gate 2.5 (Trend Phase Detector)**: Reemplazar `slope` simple por `phase_score`:
    ```python
    phase_score = ema_slope × volume_delta × (1 / brick_formation_seconds)
    # Alto phase_score = CONTINUE fuerte | Bajo = FLAT
    ```
  - **Implementación gratuita en NinjaScript**: `barDuration` en NT8 mide el tiempo de cada barra en segundos. Rolling percentile de los últimos N bricks para calibrar "rápido" vs "lento".
  - **Integración**: KDL Gate 2.5 upgrade — `trend_phase` pasa de binario (CONTINUE/FLAT) a escalar [0-100]: `brick_momentum_score`. Feeding directo al ConvictionScore.
  - **Semana de implementación**: Semana 2 Abril (junto con KDL completa, como upgrade del Gate 2.5)

- **Sky Fibomoku → FiboCloud_v1: Nueva Estrategia Candidata (20/03/2026)**:
  - **El concepto**: Sky Fibomoku (ninza.co) usa el **Ichimoku Leading Span B** (promedio del high más alto y low más bajo de los últimos 52 períodos, desplazado 26 barras hacia adelante) como nivel del 50% Fibonacci. Desde ahí proyecta los niveles 23.6%, 38.2%, 61.8%, 76.4% **delante del precio actual**. El precio "encuentra" esos niveles antes de llegar — zonas predictivas, no reactivas.
  - **Por qué es diferente**: Todos nuestros S/R son reactivos (el precio tocó algo y rebotó). El Leading Span B es el único indicador que traza soporte/resistencia ANTES de que el precio llegue. La zona golden ratio (38.2-61.8%) = zona de alta probabilidad de reacción.
  - **Señal de entrada**: Precio entra en golden ratio zone (38.2-61.8%) + Span B cambia a verde (uptrend) → BUY. Span B rojo (downtrend) → SELL. Exit cuando precio sale del otro extremo de la zona.
  - **Para Midas como capa**: El Span B como filtro de tendencia de largo plazo (complementa tide_score). Si Span B es verde → Midas solo permite longs o reduce sizing en shorts. Más robusto que EMA simple porque integra 52 períodos de estructura.
  - **Para estrategia FiboCloud_v1 (evaluar en Mayo)**:
    - Chart: Renko 35 (consistente con portafolio top)
    - Entry: precio entra en golden ratio zone + Span B confirma dirección
    - SL: debajo/encima del extremo opuesto de la zona (23.6% o 76.4%)
    - TP: siguiente zona Fibonacci (ratio dinámico)
    - Filtros: volumen mínimo, prime hours, AllowShort=ON
    - Descorrelación esperada: alta — entrada basada en tiempo futuro, no en precio pasado
  - **Semana de evaluación**: Mayo (junto con S&D puro y HH/HL como estrategia)

- **RQA Features — Recurrence Quantification Analysis (26/03/2026)**:
  - **El concepto**: Analiza el espacio de fases de la serie de precios y extrae 3 métricas dinámicas que Choppiness Index no puede capturar: `recurrence_rate` (¿el mercado vuelve a estados similares?), `determinism` (¿hay estructura o ruido puro?) y `laminarity` (¿ranging o trending?). Librería: `pyrqa`.
  - **Mapa directo a Midas**: `laminarity` alto → StatMean/DarvasBox ON | `laminarity` bajo → EMATrend/MomentumZ ON. `determinism` bajo → ConvictionScore=0, no operar. `recurrence_rate` bajo → régimen nuevo → sizing 50%.
  - **Por qué es mejor que Choppiness Index**: CI mira solo ATR vs rango (1D). RQA mira el espacio de fases multidimensional — captura estructura de patrones que CI pierde. Son complementarios, no sustitutos.
  - **Implementación**: `get_recurrence_features(price_window)` → 3 floats como features adicionales en `market_monitor_logger.py` + inputs directos para brain_v2 RF.
  - **Nota técnica**: Usar `log(P_t/P_{t-1})` (log-returns) como input del RF en lugar de cambios absolutos — mejora estabilidad del modelo.
  - **Semana de implementación**: Semana 4 Abril (junto con brain_v2 RF).

- **MAE/MFE Analyzer — Stop/Target Empírico por Estrategia (26/03/2026)**:
  - **El concepto** (inspirado en QuantZone, $346 — NO comprar): Maximum Adverse Excursion y Maximum Favorable Excursion por estrategia, calculados desde los CSV de NT8. El modelo: `Pwin = P(F ≥ MFE_target ∩ A ≤ MAE_stop)` — dado el stop X, ¿cuál es la probabilidad empírica de llegar al target Y?
  - **Por qué es nuevo para Midas**: Hoy los stops son parámetros fijos del backtest. Con MAE/MFE real de paper trading, los stops se calibran con comportamiento VIVO, no histórico. Si StatMean tiene MAE mediano de 12 ticks → stop en 14 ticks = captura 85% de ganadores sin ser cortado prematuramente.
  - **Caso de uso inmediato**: Días de GAP (26/03) la distribución MAE se infla 3x en momentum strategies → ajuste automático de stops o bloqueo de entry.
  - **Implementación**: `mae_mfe_analyzer.py` — lee los CSV de NT8 (ya disponibles), calcula distribuciones por estrategia, genera `mae_mfe_profile_ESTRATEGIA.json`. NT8 ya exporta MAE/MFE en performance reports — costo = $0.
  - **Output para brain_v2**: Pwin(stop, target) por estrategia = input directo para Kelly criterion mejorado (replace fixed f).
  - **Semana de implementación**: Post-período de prueba (después de Semana 4 Abril). Necesita mínimo 30 días de trades reales para distribuciones estables.

- **VoluTank Army → Zone Quality Score para S&D (20/03/2026)**:
  - **El concepto**: VoluTank Army (ninza.co) añade el ratio Buy/Sell DENTRO de cada zona de Supply/Demand. Una zona de demanda donde Buy volume > Sell volume = zona fuerte (alta probabilidad de rebote). Una zona de demanda donde Sell > Buy = zona débil (probable breakout a través de ella).
  - **Por qué mejora nuestro S&D existente**: El roadmap ya contempla S&D como Capa Midas y como estrategia futura. VoluTank agrega el criterio de CALIDAD de la zona, no solo su existencia.
  - **Zone Quality Score**:
    - `zone_quality = buy_volume / (buy_volume + sell_volume)` dentro de la zona
    - Demand zone con quality > 0.60 → "Strong Zone" → ConvictionScore +10
    - Demand zone con quality < 0.45 → "Weak Zone" → ConvictionScore -10 o ignorar
    - Supply zone: lógica inversa (sell_volume dominante = fuerte)
  - **Power Shift**: El momento donde el control cambia de compradores a vendedores (o viceversa) = borde de la zona. Más preciso que el clásico "último impulso fuerte" que usamos en VWAPOrderBlock.
  - **Integración en Midas**: KDL Gate 1 (Trend Structure) + S&D layer: antes de marcar una zona como activa, verificar el volume quality score. Zonas débiles no bloquean entradas, zonas fuertes sí.
  - **Implementación gratuita**: NT8 tiene acceso a Buy/Sell volume via `VOL[0]` y delta por tick. Calculable sin comprar el indicador.
  - **Semana de implementación**: Mayo (cuando se implemente S&D como capa de Midas)

---

## JULIO-SEPTIEMBRE — Capital Real (Fase 4)
**Del simulador al mundo real**

### Prerequisitos para pasar a Apex real:
- [ ] WFO validado: top estrategias sobreviven out-of-sample
- [ ] 6 meses de paper con Sharpe > 1.5 y MaxDD < $7,000 simulado
- [ ] Monte Carlo confirma P(ruin) < 5%
- [ ] Brain con 100+ trades reales, RF activo y calibrado
- [ ] Portfolio stop global funcionando
- [ ] News filter activo y probado
- [ ] Correlación entre estrategias < 0.6 promedio

### Darwin/X prerequisitos adicionales:
- [ ] Track record verificable de 6-12 meses
- [ ] Drawdown máximo documentado y dentro de límites
- [ ] Ratio de retorno/drawdown > 2.0
- [ ] Consistencia mensual (no solo un mes bueno)

---

## MÉTRICAS DE ÉXITO DEL PROYECTO

| Métrica | Target mínimo | Target ideal | Darwin/X |
|---------|--------------|--------------|----------|
| Sharpe anual | > 1.0 | > 1.5 | > 2.0 |
| Sortino anual | > 2.0 | > 3.0 | > 4.0 |
| MaxDD | < $7,000 | < $5,000 | < $4,000 |
| Profit/mes (Apex) | > $2,000 | > $5,000 | > $8,000 |
| Win rate (portafolio) | > 30% | > 40% | — |
| Correlación entre estrategias | < 0.7 | < 0.5 | < 0.4 |
| P(ruin anual) | < 10% | < 5% | < 2% |

---

## FILOSOFÍA DEL PROYECTO
> "La marea (1D/4H) define el campo de batalla.
>  El mar (1H/30M) define si vale la pena pelear.
>  La ola (señal) define el momento exacto.
>  El brain decide si el surfista entra o espera."
>
> Un sistema que sabe cuándo NO operar vale más que uno que siempre opera.
> La paciencia del sistema = la paciencia del trader × 1000.

**Inicio real: 01/04/2026. Destino: Darwin/X 2027.**
