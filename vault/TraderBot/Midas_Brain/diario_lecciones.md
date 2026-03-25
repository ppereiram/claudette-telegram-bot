---
name: diario_lecciones
description: Diario de trading con lecciones documentadas para educación del brain Midas — patrones de pérdida, correlaciones, insights de mercado
type: project
---

# Diario de Lecciones — Educación del Brain Midas
> Período inicial: 02/03/2026 – 20/03/2026 | 15 días hábiles | 710 trades | P&L: +$366
> Fuente de verdad: CSV exportado de NinjaTrader 8 (NO los strategies_pnl.json — fueron borrados por bug en auto_push_pnl.bat el 20/03)

---

## LECCIÓN 01 — 17/03/2026: Correlación Catastrófica ⚠️
**P&L del día: -$8,906** (2do peor día del período)

**Qué pasó exactamente:**
- 10:05 AM: StatMeanCross + EMATrendRenko + BreadButter_v5_Apex entraron **Long simultáneamente**
- El mercado estaba bajista intraday todo el día
- Todos perdieron juntos. PivotReverse Short también falló. Solo BreadButter_SCALPER terminó positivo

**Contexto de mercado:**
- tide_score nocturno = 0.8 (swim_ok=True) → el monitor NO detectó el peligro
- trend_4H=Bull pero intraday era claramente bajista
- El tide_score se calculaba 1x/día al EOD → ventana ciega de 4-7 horas intraday

**Raíz técnica de la correlación:**
- StatMeanCross usa EMA(21) para crossover
- EMATrendRenko usa EMA(21) como soporte/resistencia
- **Misma EMA(21) = misma señal en el mismo brick de Renko 35** → correlación estructural, no accidental

**Correctivos diseñados:**
- KDL Capa 6 (Correlación de Portafolio): si N estrategias están en mismo lado simultáneamente → reducir sizing o bloquear tardías
- KDL Gate 2.5 (Trend Phase Detector): slope del EMA habría detectado "Continue bajista" a las 10:05 AM → bloqueado todos los longs
- Market Monitor intraday (cada 60s): habrían detectado divergencia entre tide_4H y tendencia 1H real
- **market_breadth_score** (ES+YM+RTY): si los 3 también bajistas → bloquear longs en NQ independientemente del tide_score

**Regla Midas derivada:**
> Si 2+ estrategias están en el mismo lado simultáneamente Y trend_phase = CONTINUE en dirección opuesta → bloquear las tardías, reducir sizing 50%

---

## LECCIÓN 02 — 20/03/2026: Correlación Confirmada — Patrón Sistémico 🔄
**P&L del día: +$1,616** (salvado por DarvasBox +$2,168 y BBv5 supervisado +$4,200)

**Qué pasó exactamente (AM):**
- **9:46:32 AM** — StatMeanCross y EMATrendRenko dispararon SHORT simultáneamente
- Misma barra exacta, mismo lado, ambos perdieron (-$820 combinado)
- Mismo patrón del 17/03 pero en dirección opuesta (shorts en vez de longs)

**Confirmación del patrón:**
- 17/03: longs correlacionados → pérdida
- 20/03: shorts correlacionados → pérdida
- **El patrón aparece en AMBAS direcciones → es sistémico, no casualidad**
- Ya son 3 eventos de correlación documentados en el período (11/03, 17/03, 20/03)

**Qué salvó el día (PM):**
- DarvasBox Short: +$2,168 (estrategia descorrelacionada — no usa EMA(21))
- BreadButter_v5_Apex Short supervisado: +$4,200 (ver Lección 03)

**Regla Midas derivada:**
> La correlación StatMean+EMATrend es estructural (misma EMA base). En producción, tratar estas dos como UN SOLO SLOT de trade cuando coincidan en la misma barra

---

## LECCIÓN 03 — 20/03/2026: El Valor de la Supervisión Humana 👤
**Evento: BreadButter_v5_Apex Short 2:01 PM → cierre manual 2:51 PM → +$4,200**

**Qué pasó:**
- BBv5 tomó Short a las 2:01 PM (precio: 24,203)
- Usuario supervisó y cerró manualmente a 2:51 PM (precio: 24,097)
- Exit type = "Close" (manual) vs exit automático habitual
- MFE alcanzado: $3,269 | ETD: $543 | La supervisión capturó casi todo el MFE

**Por qué el humano fue mejor que el algoritmo:**
- Mercado claramente bajista todo el día (24,450 → 24,090 de AM a PM)
- ConvictionScore alto en esa dirección (short alineado con tendencia del día)
- En tendencia diaria clara + alta convicción → dejar correr más del target automático

**Qué aprende Midas de este trade:**
- RL/PPO (Capa 11 — Mayo 2026) aprenderá exactamente esta decisión: cuándo ajustar el trailing vs cuándo salir fijo
- Señal: trend_1D=bajista + trend_4H=bajista + ConvictionScore alto → extender target o usar trailing agresivo
- El exit_type="Close" con P&L positivo + ETD bajo = label de "salida óptima" para el modelo

**Regla Midas derivada:**
> En días con tendencia diaria clara (tide_score < -1.5 o > +1.5) + todos los TFs alineados → activar trailing agresivo en vez de profit target fijo. El algoritmo debería hacer lo que hizo el humano ese día.

---

## LECCIÓN 04 — 06/03/2026: El Día más Duro sin Análisis Forense ⚠️
**P&L del día: -$11,920** (PEOR DÍA DEL PERÍODO — mayor que 17/03)

**Qué pasó:**
- Pérdida catastrófica. B&Bv5 fue identificado como el swing factor principal
- Llegó ANTES de que las lecciones de correlación fueran formalmente registradas
- Sin análisis forense detallado disponible (el 17/03 sí tiene análisis completo)

**Contexto:**
- Probable régimen de alta volatilidad o evento macro sin filtro activo
- El tide_score nocturno no capturó el riesgo intraday (mismo bug que el 17/03)
- Posible día de noticias extremas (06/03 fue un viernes — potencialmente datos económicos)

**Lo que habría ayudado:**
- Portfolio Stop Global ($LimiteDiario) habría cortado las pérdidas
- KDL Gate 2.5 podría haber detectado el momentum adverso
- News Filter: si hubo evento macro → bloquear entradas ±30min
- market_breadth_score: si ES/YM/RTY también en caída libre → max_sizing reducido

**Regla Midas derivada:**
> Portfolio Stop Global es CRÍTICO. Implementar en Semana 2 Abril. Si pérdida combinada del día > $LimiteDiario → publicar STOP_ALL, todas las estrategias consultan antes de entrar

---

## LECCIÓN 06 — 23/03/2026: Inactividad Masiva — Probable Rollover de Contrato 🔄
**P&L del día: -$7 (solo SuperTrendWave operó — errático)**

**Qué pasó:**
- De 17 estrategias activas, solo SimSuperTrendWave disparó (3 trades, -$7 total)
- Todas las demás registraron $0 — sin señales en todo el día
- SuperTrendWave operó de forma atípica: abrió 3 posiciones simultáneas (1+2+2 contratos) en la misma barra de las 1:55 PM y cerró todas juntas por Stop Loss a las 2:07 PM
- El usuario pregunta si algún cambio en el brain del viernes causó la inactividad

**Hipótesis más probable — Rollover MNQ 03-26 → MNQ 06-26:**
- El instrumento en el CSV es "MNQ 06-26" (contrato de Junio 2026)
- El contrato de Marzo 2026 expiró — el rollover típico de MNQ es la 2da semana de Marzo
- Las estrategias con barras Renko pierden su historial al cambiar de contrato: el brick size se recalcula sobre datos nuevos, las EMAs se reinician, el VWAP empieza desde 0
- En Renko especialmente: hasta que se construyen suficientes bricks con el nuevo contrato, muchas estrategias no generan señales válidas
- Ya estaba documentado en MEMORY.md: "Rollover MNQ cambia datos Renko → re-validar estrategias con nuevo contrato"

**Sobre el brain del viernes:**
- No hubo cambios en el código de las estrategias NT8 el viernes
- Los cambios del viernes fueron solo en los archivos de memoria del brain (arquitectura RL) — no afectan la ejecución de NT8
- La inactividad es interna a NinjaTrader, no del brain Python

**Por qué SuperTrendWave sí operó (y mal):**
- SuperTrendWave puede usar timeframe estándar (no Renko) o Renko con brick pequeño
- Al abrir 3 posiciones simultáneas en la misma barra: comportamiento de "restart" tras rollover — la estrategia vio una señal en la primera barra del nuevo contrato y entró en múltiples capas
- Stop Loss en la misma barra = probable stop demasiado ajustado en el primer brick del nuevo contrato

**Acción requerida:**
- Verificar en NT8 que todas las estrategias apuntan al contrato MNQ 06-26
- Re-cargar las estrategias Renko para que reconstruyan el historial de bricks con el nuevo contrato
- Esperar 1-2 días de trading para que las EMAs se estabilicen en el nuevo contrato antes de evaluar señales

**Regla Midas derivada:**
> Rollover de contrato = día de mantenimiento obligatorio. La semana del rollover (~2da semana de Marzo, Junio, Septiembre, Diciembre) NO contar los $0 como "sin señal" — es silencio técnico, no de mercado. Marcar en el calendario y excluir del análisis de frecuencia de Markov.

---

## LECCIÓN 06b — 23/03/2026: Ranking de Estrategias (Semana 3) 📊
**Fuente: Screenshot NT8 Accounts — ordenado de más perdedor a más ganador (desde $100k inicio)**

| Estrategia | Equity actual | P&L neto | Observación |
|---|---|---|---|
| SimPivotTrendBreak | $93,215.50 | **-$6,784.50** | Peor del portafolio — revisar |
| SimEMATrendRenko_v1 | $97,277.50 | **-$2,722.50** | Correlacionada con StatMean |
| SimSuperTrendWave | $97,329.00 | **-$2,671.00** | Lección 06 — rollover |
| SimVAWAPOrderBlock | $97,639.50 | **-$2,360.50** | Por debajo de R²>0.85 threshold |
| SimStatMeanCross_v1 | $97,734.50 | **-$2,265.50** | Correlacionada con EMATrend |
| SimBreadButter_ULTRA | $99,278.00 | **-$722.00** | Filtro Accidental activo — normal |
| SimVWAPFlux_v1 | $99,751.10 | **-$248.90** | Neutral |
| SimOpeningRange_v1 | $99,754.20 | **-$245.80** | Neutral |
| SimOrderFlowReversal | $99,768.50 | **-$231.50** | Neutral |
| SimBreadButter_SCALPER | $99,918.00 | **-$82.00** | Filtro Accidental activo — normal |
| SimABCDHarmonic_v1 | $99,924.70 | **-$75.30** | Neutral |
| Sim101 | $100,000.00 | $0.00 | Sin trades aún |
| SimLWDonchianBreak_v | $100,665.80 | **+$665.80** | Positivo |
| SimNYOpenBlast_v2 | $101,302.00 | **+$1,302.00** | Positivo |
| SimMomentumZ_v1 | $101,603.30 | **+$1,603.30** | Positivo |
| SimBreadButter_v5_Apex | $101,767.70 | **+$1,767.70** | Positivo — Step Lock activo |
| SimPivotReverse_V1 | $103,034.50 | **+$3,034.50** | Sorpresa positiva |
| SimDarvasBox_v1 | $113,412.00 | **+$13,412.00** | OUTLIER — dominando el portafolio |

**Insights clave:**
- **DarvasBox +$13,412**: era el "traidor" en TFT (tft=0.25) pero está dominando. Revisar si el comportamiento es consistente o spike. Actualizar TFT multiplier si el rendimiento reciente es real.
- **PivotTrendBreak -$6,784**: peor del portafolio en vivo. En backtests tenía Sortino=8.50 (top 3). Divergencia significativa backtest vs live → candidato a revisar parámetros o excluir.
- **StatMean -$2,265 + EMATrend -$2,722**: juntas suman -$4,987 — la correlación estructural sigue costando. Confirma la urgencia de tratarlas como un solo slot.
- **BBv5_Apex +$1,767 positivo**: con Step Lock activo, se comporta de forma controlada.

---

## LECCIÓN 05 — 11/03/2026: Primer Evento de Correlación Documentado 📝
**Evento: 9:44 AM — StatMeanCross y EMATrendRenko dispararon misma dirección simultáneamente**

**Importancia:**
- Este es el PRIMERO de 3 eventos correlacionados en el período
- Solo 2 estrategias afectadas (vs 3 el 17/03)
- La pérdida fue contenida pero el patrón ya estaba presente
- Confirma que el patrón es sistémico desde el primer día de operativa

**Secuencia de eventos de correlación:**
1. **11/03**: StatMean + EMATrend (2 estrategias, pérdida contenida) → primer aviso
2. **17/03**: StatMean + EMATrend + BBv5 (3 estrategias) → catástrofe -$8,906
3. **20/03**: StatMean + EMATrend (2 estrategias, shorts) → confirmación sistémica

---

## LECCIÓN 06 — 13/03/2026: Cómo funciona el portafolio cuando funciona ⭐
**P&L del día: +$7,191** (MEJOR DÍA DEL PERÍODO)

**Qué pasó:**
- Múltiples estrategias en condiciones favorables, alineadas con el mercado
- Probablemente tendencia clara intraday + sea_state calm o moderate
- B&Bv5 aportó un trade ganador significativo

**Por qué funcionó:**
- Portafolio alineado con tendencia diaria real
- No hubo correlación adversa — cada estrategia capturó su edge independientemente
- Sea state = condiciones óptimas (CI bajo, trending)

**Regla Midas derivada:**
> El portafolio tiene capacidad de generar +$7,000 en un solo día. La diferencia vs -$8,906 es alineación con el mercado + ausencia de correlación. Objetivo de Midas: maximizar días como este, eliminar días como el 17/03.

---

## PATRONES ESTADÍSTICOS DEL PERÍODO

| Semana | Resultado | Evento Notable |
|--------|-----------|----------------|
| S1 (02-06/03) | Dominado por -$11,920 el 06/03 | EMATrend y StatMean confirmadas en backtest |
| S2 (09-13/03) | Recuperación; +$7,191 el 13/03 | 1er evento correlación 11/03; rollover próximo |
| S3 (16-20/03) | -$8,906 el 17/03; +$1,616 el 20/03 | Rollover MNQ 06-26; 2 eventos correlación |
| S4 (21-24/03) | ~-$3,300 aprox | Short bias sistémico; 3 estrategias short vs tendencia alcista |
| **TOTAL** | **-$1,847** | **5 lecciones documentadas — MaxDD -$29,104** |

**Análisis de varianza:**
- **B&Bv5** = factor de swing dominante (días extremos → B&Bv5 involucrado)
- **StatMean + EMATrend** = par de correlación estructural (misma EMA(21) base)
- **Días buenos**: portafolio alineado con tendencia + no correlación + sea_state calm
- **Días malos**: correlación + contra-tendencia + sin Portfolio Stop
- **Bug infraestructura**: tide_score 1x/día → ventana ciega 4-7h intraday → Fix: medir cada 60s

---

## BUG CRÍTICO DE INFRAESTRUCTURA — 20/03/2026
**strategies_pnl_*.json sobreescritos a CERO por auto_push_pnl.bat**
- El script auto_push_pnl.bat borró los datos de P&L histórico al correr
- **Fuente de verdad SIEMPRE: CSV exportado de NinjaTrader 8**
- Los archivos JSON son solo cache, no fuente primaria
- Fix pendiente: auto_push_pnl.bat debe hacer append, no overwrite

---

## LECCIÓN 05 — 24/03/2026: Short Bias Sistémico en Día Alcista ⚠️
**P&L del día: -$1,847.50** | **Período 02-24/03: -$1,847.50 neto (746 trades)**

**Qué pasó exactamente:**
- Mercado alcista todo el día: 24,146 → 24,263 (+117 puntos intraday)
- **PivotReverse_v1** SHORT: 4 entradas simultáneas 11:10 (qty 3+6+3+8 = 20 contratos) → todas stop loss → **-$1,048**
- **DarvasBox_v1** SHORT: 3 entradas simultáneas 09:50 (qty 1+4+15 = 20 contratos) → todas stop loss → **-$953**
- **SuperTrendWave** SHORT: 3 intentos a lo largo del día, todos contra tendencia → **-$624**
- **PivotTrendBreak_v1** LONG: 6 entradas simultáneas todas en Profit Target → **+$636** (leyó bien el día)
- **OrderFlowReversal_v1** LONG: pequeñas ganancias, bien comportado

**Patrón nuevo identificado — DIFERENTE al 17/03:**
- El 17/03 fue: múltiples estrategias LONG en día bajista → correlación EMA(21)
- El 24/03 es: múltiples estrategias SHORT en día alcista → **short bias sistémico sin filtro de tendencia**
- No es correlación estructural entre sí — son estrategias independientes que comparten el mismo error: operar short sin confirmar dirección diaria

**Violación de Units Cap (Curtis Faith / B6-0c):**
- PivotReverse: 4 entradas short simultáneas = 4 slots en misma dirección → habría sido bloqueado por MaxCorrelatedUnits=6 parcialmente
- DarvasBox: qty 15 en un solo trade short = concentración extrema
- **La regla de Units Cap no está implementada → costo hoy: ~$2,000**

**El veredicto estadístico del período completo (02-24/03):**

| Dirección | Net Profit | PF | Trades |
|-----------|-----------|-----|--------|
| Longs | **+$7,248** | 1.17 | 372 |
| Shorts | **-$9,095** | 0.80 | 374 |
| **Total** | **-$1,847** | 0.98 | 746 |

→ **Si solo hubiéramos operado longs el período habría sido +$7,248.**
→ Las estrategias short destruyeron el portafolio. PF=0.80 = pérdida garantizada a largo plazo.

**Raíz del problema:**
- PivotReverse, DarvasBox, SuperTrendWave no tienen filtro de tendencia diaria antes de ir short
- tide_score calculado 1x/día al EOD → no disponible intraday cuando se ejecutan las entradas
- Sin VWAP SD Bands intraday → no hay confirmación bearish antes del entry short

**Sobre "el brain llegó y todo empeoró":**
- El brain (market_monitor_logger.py) NO controla las estrategias — solo logea
- Lo que llegó con el brain = **más estrategias short desplegadas en papel**
- La semana 02-08/03 (+$4,516) fue: pocas estrategias, mercado alcista, mayoría longs
- La semana 09-24/03: más estrategias short añadidas + mercado volátil/alcista = shorts fallan
- No es el brain el problema. Es que los shorts no tienen filtro de dirección

**Regla Midas derivada:**
> Antes de cualquier entrada SHORT, verificar: tide_score_intraday < 0 AND VWAP_SD_band < -1σ AND market_breadth < -0.3. Si alguno falla → NO SHORT, esperar o pasar al siguiente día.
> Las estrategias short son estructuralmente peligrosas en tendencia alcista sin filtro. MaxDD del portafolio es SHORT-first.

---

## LECCIÓN 06 — DIAGNÓSTICO PERÍODO COMPLETO 02-24/03/2026
**P&L total: -$1,847 | 746 trades | 23 días hábiles**

**La verdad de los números:**

| Período | Net Profit | PF | Sharpe | Observación |
|---------|-----------|-----|--------|-------------|
| 02-08/03 (sin brain) | +$4,516 | 1.14 | **2.72** | Pocas estrategias, mercado alcista |
| 09-24/03 (con brain) | -$6,363 | <1 | bajo | Más estrategias short + mercado cambia |
| **Total 02-24/03** | **-$1,847** | **0.98** | 0.42 | MaxDD = -$29,104 |

**Por qué el Sharpe de 2.72 en las primeras semanas era ilusorio:**
- Solo 263 trades en la primera semana → muestra pequeña
- Mercado en tendencia alcista → longs ganaron por momentum, no por edge real
- Los shorts tenían PF=0.39 desde semana 1 — siempre fueron malos
- La "llegada del brain" coincidió con mercado más difícil + más estrategias short

**El veredicto honesto:**
- Las estrategias LONG tienen edge real (PF=1.17 en período completo, Sortino>1.0)
- Las estrategias SHORT no tienen filtro de tendencia = P(ruin) alta en bull market
- **Prioridad #1 de Midas antes de Apex**: filtro de tendencia obligatorio para entradas short

**Lo que este período le enseña a Midas:**
1. Patrón SHORT+tendencia alcista = pérdida garantizada → filtrar con tide_score intraday
2. Entradas simultáneas multislot misma dirección = Units Cap violation → implementar AHORA
3. Días buenos del portafolio: TODOS los días con PivotTrendBreak Long acertando tendencia
4. El portafolio puede generar +$7K en longs en 23 días — el edge existe, está en los longs
5. Los -$29K de MaxDD son en gran parte short strategies = si se filtran, MaxDD cae a <$12K estimado

---

## REGLAS DE MIDAS DERIVADAS DEL DIARIO (resumen ejecutivo)

1. **Correlación estructural StatMean+EMATrend**: tratar como 1 slot cuando coincidan en misma barra
2. **Portfolio Stop Global**: implementar antes de cualquier trade en Apex real
3. **market_breadth_score**: ES+YM+RTY deben confirmar dirección antes de full sizing en NQ
4. **tide_score intraday**: medir cada 60s (no 1x/día) para detectar divergencias a tiempo
5. **Tendencia diaria clara + alta convicción**: activar trailing agresivo en vez de TP fijo
6. **Días de noticias**: News Filter obligatorio — bloquear ±30min de eventos macro HIGH impact
7. **B&Bv5 como swing factor**: en días con B&Bv5 con posición abierta grande → sizing conservador en el resto
8. **Filtro short obligatorio**: antes de ANY entrada short verificar tide_score_intraday < 0 + VWAP < -1σ + breadth < -0.3. Sin los 3 → NO SHORT
9. **Units Cap en mismo día**: máximo 2 estrategias short simultáneas (MaxCorrelatedUnits=2 para shorts en bull market)
10. **Las estrategias LONG tienen edge real** (PF=1.17, +$7,248 en 23 días) — protegerlas de las shorts que arrastran el portafolio
11. **Short PF < 1.0 = no opera**: PivotReverse, DarvasBox, SuperTrendWave tienen PF<1.0 en período real → suspender hasta que brain implemente filtro de tendencia
