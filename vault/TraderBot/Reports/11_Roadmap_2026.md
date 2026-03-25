# Roadmap 2026 — Mejoras Pendientes y Próximos Pasos

> Acordado en sesiones de desarrollo. Implementar gradualmente después de tener datos reales.
> **Regla**: No modificar lo que funciona hasta tener ~4-6 semanas de métricas paper trading.

---

## Estado actual (22/02/2026)

### En producción / activas
- ✅ BreadButter_v5_Apex
- ✅ BreadButter_ULTRA
- ✅ BreadButter_SCALPER
- ✅ NYOpenBlast_v2
- ✅ OpeningRange_v1
- ✅ VWAPOrderBlock_v1

### En paper trading
- 📝 SuperTrendWave (desde 19/02/2026)

### Pendiente de escalar a contratos completos
- ⏳ NYOpenBlast_v2 → 7 contratos
- ⏳ VWAPOrderBlock_v1 → 9 contratos
- ⏳ SuperTrendWave → evaluar después de paper trading

---

## Fase 1: Validación de datos reales (~20/03/2026)

Antes de implementar cualquier mejora, esperar 4-6 semanas de datos de paper trading de SuperTrendWave para:
1. Comparar métricas reales vs backtest
2. Identificar si hay discrepancias sistemáticas
3. Detectar condiciones de mercado que el backtest no capturó bien (ej: chop extremo como el 20/02/2026)

**Criterios de éxito para SuperTrendWave:**
- PF real ≥ 1.20 (vs 1.41 de backtest, con 15% de descuento por condiciones reales)
- MaxDD real ≤ $4,000 (vs $3,074 de backtest, con margen)
- No más de 3 días consecutivos de pérdidas

---

## Mejora 1: Market Regime Filter (todas las estrategias)

### Concepto
Indicador `MarketRegime_v1` en timeframe 30-min como secondary data series. Define 3 estados:
- **Bull**: ADX > 25 + DI+ > DI- → operar solo longs (o todas las estrategias en modo normal)
- **Bear**: ADX > 25 + DI- > DI+ → operar solo shorts (o desactivar longs)
- **Neutral**: ADX < 20 → no operar (mercado en rango / acumulación)

### Beneficios esperados
- Evitar shorts en mercado alcista estructural (el mayor problema de BBShorts)
- Evitar longs en mercado bajista (captura de crash)
- Saltar períodos de acumulación/distribución donde ninguna estrategia tiene edge

### Implementación técnica
```csharp
// En Configure:
AddDataSeries(BarsPeriodType.Minute, 30);

// En DataLoaded:
adx30 = ADX(BarsArray[2], 21);  // Si ya hay una serie secundaria
dmPlus30 = DM(BarsArray[2], 21);  // DI+
dmMinus30 = DM(BarsArray[2], 21);  // DI-

// En OnBarUpdate:
if (BarsInProgress != 0) return;

MarketRegime regime;
if (adx30[0] > 25 && diPlus > diMinus)
    regime = MarketRegime.Bull;
else if (adx30[0] > 25 && diMinus > diPlus)
    regime = MarketRegime.Bear;
else
    regime = MarketRegime.Neutral;

if (regime == MarketRegime.Neutral) return;  // No operar en rango
```

### Prioridad: Alta
Aplicar a: Todas las estrategias del portafolio
Timeline: ~20/03/2026 después de validación paper trading

---

## Mejora 2: Choppiness Index Filter (SuperTrendWave específicamente)

### Contexto
El 20/02/2026 (primer día de paper trading), el mercado abrió con chop extremo — Renko formaba bricks en 5-20 segundos. El sistema tomó múltiples entradas y acumuló -$730.

### Concepto
El Choppiness Index (CI) mide si el mercado está en tendencia o en rango:
- CI > 61.8 → mercado choppy (no entrar)
- CI < 38.2 → mercado tendencial (operar con confianza)
- Zona intermedia → evaluación según contexto

### Implementación
```csharp
// Fórmula CI (N períodos):
double high_N = MAX(High, ChoppyPeriod)[0];
double low_N  = MIN(Low,  ChoppyPeriod)[0];
double atr_sum = suma de ATR de cada barra en N períodos;

double ci = 100 * Math.Log10(atr_sum / (high_N - low_N)) / Math.Log10(ChoppyPeriod);
// CI cercano a 100 = máximo chop; CI cercano a 0 = máxima tendencia
```

### Criterio de implementación
Implementar **solo si** SuperTrendWave muestra un patrón consistente de días malos en mañanas volátiles durante el paper trading. No implementar prematuramente.

### Prioridad: Media-Baja (condicional)
Aplicar a: SuperTrendWave específicamente
Timeline: Si el patrón se confirma durante paper trading

---

## Mejora 3: Multi-Asset Validation

### Concepto
Correr las mismas estrategias con los mismos parámetros en NQ (full), RTY (Russell 2000), y ES (S&P 500) para verificar que el edge no es específico de MNQ.

### Por qué importa
Si una estrategia tiene PF=1.41 en MNQ pero PF=0.95 en ES y PF=0.88 en RTY, hay alta probabilidad de que los parámetros estén overfitted a las características específicas de MNQ.

### Nota importante sobre correlación
MNQ, NQ, ES y RTY están **correlacionados** (~0.7-0.9 durante sesiones normales). La validación cruzada tiene valor limitado si todos los índices están en el mismo régimen de mercado. Interpretar con cautela.

### Criterio de implementación
Implementar después de tener 4-6 semanas de datos de paper trading. El objetivo no es optimizar para otros instrumentos, sino detectar overfitting grosero.

### Prioridad: Baja
Timeline: ~Abril-Mayo 2026

---

## Oportunidad 4: Mean Reversion VWAP (estrategia nueva)

### Concepto
Estrategia "contrarian" — cuando el precio se aleja extremadamente del VWAP, apostar por el retorno al VWAP.

**Setup teórico**:
1. Precio se aleja del VWAP más de 2× ATR
2. Hay señal de agotamiento del movimiento (RSI en extremo, volumen decreciente)
3. Entrar en dirección contraria al movimiento con target en el VWAP

### Por qué es "osada"
- Va contra el momentum — en MNQ, los movimientos pueden extenderse mucho más de lo que parece razonable
- Los "extremos" en mercados de alta volatilidad (como apertura de NY) pueden durar más de lo esperado
- El riesgo es potencialmente ilimitado si el precio continúa alejándose

### Condiciones para explorarla
Solo explorar si:
1. Los datos de paper trading muestran días con muchos over-extensions que revierten
2. Se puede definir con precisión matemática qué constituye "extremo"
3. El MaxDD por contrato cabe en Apex

### Prioridad: Baja (exploración futura)
Timeline: No antes de Q2 2026

---

## Oportunidad 5: Optimización de BreadButter_v5_Apex para Apex

### El problema
MaxDD = $38,727 con 1 contrato es demasiado alto para cuenta Apex de $50k.

### Ideas de reducción de drawdown
1. **Horario de riesgo**: Restringir aún más el horario (ej: solo 9:30-12:00) — el backtesting muestra que algunos de los peores drawdowns ocurren en tarde
2. **Filtro de días de alta volatilidad**: No operar en días con VIX extremo o datos económicos importantes
3. **Filtro de tendencia diaria**: Solo operar en días donde la tendencia del día anterior fue clara (filtro de momentum multi-día)

### Riesgo
Cualquier modificación a v5_Apex es de alto riesgo — es el mejor sistema del portafolio. Cambios podrían deteriorar el PF o el R².

### Prioridad: Media (solo con backtest exhaustivo)
Timeline: Después de validación paper trading completa

---

## Oportunidad 6: EMA Touch como setup dominante — aplicar a otras estrategias

### Descubrimiento (26/02/2026)

En BreadButter_ULTRA sobre Renko 35-tick (Slippage=1, comisiones incluidas), al probar cada setup de forma aislada:

| Setup | PF solo |
|---|---|
| Momentum Burst | ~1.5 |
| Micro Reversal | ~1.5 |
| Breakout Scalp | ~1.5 |
| **EMA Touch** | **~2.03** |
| **Todos juntos** | **2.03** |

**Conclusión**: EMA Touch es el setup dominante. El PF de la combinación es idéntico al de EMA Touch solo — los otros tres setups no añaden ni degradan el PF final en Renko 35.

### ¿Por qué EMA Touch funciona en Renko?

En Renko 35-tick, cada brick requiere 35 ticks ($17.50) de movimiento. Cuando el precio retrocede hasta tocar la EMA 21 en ese contexto, es un retroceso estructural real (no ruido de 1-min). El rebote desde EMA 21 en Renko = confirmación de que la tendencia sigue activa con suficiente momentum.

### Oportunidad de mejora

Aplicar la lógica de **rebote desde EMA** en Renko a otras estrategias del portafolio:

1. **BreadButter_SCALPER** (Renko 30): Ya usa EMA 9/21 — analizar si el setup EMA Touch aislado tiene mejor PF que la lógica MACD actual
2. **SuperTrendWave** (Renko 40): Añadir condición de confirmación con EMA antes de entrar en pyramid
3. **PivotTrendBreak** (Renko 25): Analizar si el break de pivot + EMA touch como filtro adicional mejora el PF
4. **Nueva estrategia potencial**: EMA Touch puro en Renko (varios brick sizes) como estrategia independiente

### Prerrequisito

No implementar hasta tener 4-6 semanas de datos paper de ULTRA en Renko 35 para confirmar que EMA Touch mantiene el PF en condiciones reales.

### Prioridad: Media
Timeline: ~Abril 2026 (después de validación paper trading ULTRA)

---

## Oportunidad 7: Anti-Popcorn — gestión de salidas al estilo Brandt

### Contexto (26/02/2026)

BreadButter_v5_Apex alcanzó ~$1,200 de ganancia unrealized en paper trading y devolvió gran parte del beneficio antes de salir. Este patrón — conocido como "popcorn trade" (Peter Brandt) — ocurre cuando el precio sube con fuerza y vuelve exactamente al punto de entrada.

### Reglas de Brandt relevantes para automatización

1. **Jam the Stop**: cuando la ganancia unrealized alcanza el 1% del capital (~$500 en cuenta $50k), mover stop al 70% del máximo unrealized alcanzado
2. **Half and Half**: cerrar 50% de la posición al alcanzar 2R, dejar el 50% restante con stop en BE
3. **Friday Close**: si hay posición abierta con pérdida al cierre del viernes → liquidar (no aplica a estrategias intraday con ForceExit)

### Estrategias más vulnerables a popcorn

| Estrategia | Vulnerabilidad | Motivo |
|---|---|---|
| **SuperTrendWave** | **Alta** | Sin profit target — solo sale cuando ST flipea |
| **BreadButter_v5_Apex** | Media | R:R=4 es largo recorrido; BE en 1R ya protege algo |
| PivotTrendBreak | Baja | Target estructural definido |
| ULTRA / SCALPER | Baja | R:R=2/1.3, trade rápido por naturaleza |

### Experimento propuesto (backtest comparativo)

Para **SuperTrendWave** en Renko 40, comparar en backtest:
- Versión A (actual): salida solo por SuperTrend flip
- Versión B: SuperTrend flip + jam stop al 70% del máximo unrealized

Si Sortino y R² mejoran en B → implementar. Si no → el sistema actual ya es óptimo.

### Prerrequisito

**No modificar nada basado en un solo trade.** Esperar 4-6 semanas de datos paper para identificar si el patrón popcorn es sistemático o fue un evento aislado.

### Prioridad: Baja (condicional — solo si datos paper muestran patrón)
Timeline: ~Abril 2026

---

## Oportunidad 8: Estrategia de Divergencias MACD/RSI en Renko

### Contexto (26/02/2026)

El portafolio no tiene ninguna estrategia basada en divergencias. Las divergencias RSI/MACD detectan agotamiento de momentum — cuando el precio hace nuevo extremo pero el indicador no lo confirma.

### Por qué puede funcionar en Renko

En 1-min los indicadores generan divergencias falsas por ruido temporal. En Renko 35-tick, cada oscilación requiere movimiento real → las divergencias tienen significado estructural genuino.

### Condiciones de diseño

1. **Solo divergencias alcistas inicialmente** — consistente con sesgo alcista de MNQ
2. **Renko 30-40 tick** — tamaño estructural, no ruido
3. **Confirmación de brick** — el brick siguiente debe ir en dirección de la señal
4. **Horario prime** — divergencias más confiables en 9:30-11:30 ET
5. **Muestra objetivo**: >150 trades en 3 años para validez estadística

### Prerequisito

Esperar resultados de paper trading del portafolio actual. Si EMA Touch en Renko confirma su edge, una estrategia "divergencia + EMA bounce" sería la evolución natural.

### Prioridad: Exploración
Timeline: Q2-Q3 2026

---

## Oportunidad 9: OrderFlow Reversal — Absorption → Exhaustion → Push (nueva estrategia)

### Contexto (26/02/2026)

El portafolio no tiene ninguna estrategia basada en order flow. Esta es la brecha más relevante — los operadores institucionales usan precisamente esta lógica. El concepto proviene de ApexFlow Zignal pero se implementa de forma independiente en NinjaScript sin Tick Replay.

### Lógica central: Causa → Efecto → Confirmación

```
Absorption (causa) → Exhaustion (efecto) → Push (confirmación) → ENTRY
```

**Sin Tick Replay** se aproxima con volumen por brick (disponible nativamente en NT8):

| Fase | Señal en Renko | Lógica |
|---|---|---|
| **Absorption** | N bricks en misma dirección con volumen CRECIENTE | Más esfuerzo por brick = alguien absorbe la presión |
| **Exhaustion** | M bricks seguidos con volumen DECRECIENTE | El lado dominante pierde combustible |
| **Push** | Primer brick en dirección CONTRARIA con volumen > SMA(20) | El otro lado toma control con presión real |

La señal solo se genera si Push aparece dentro de N barras tras Exhaustion — si no aparece en ese tiempo, la setup expira.

### Por qué es diferente al resto del portafolio

| Característica | OrderFlow Reversal | Resto del portafolio |
|---|---|---|
| Tipo | Reversal (contra momentum) | Momentum / Breakout / Pullback |
| Edge | Microestructura de volumen | Precio / indicadores |
| Frecuencia | Baja (~1 trade/2 días estimado) | Variable |
| Correlación | Baja — entra donde otros salen | Alta entre momentum strategies |

### Parámetros a definir en backtest

```csharp
int AbsorptionBricks = 3;       // Bricks con volumen creciente para detectar absorción
int ExhaustionBricks = 2;       // Bricks con volumen decreciente tras absorción
int PushWindow = 5;             // Máximo de barras para que aparezca el push
double MinVolRatioPush = 1.3;   // Push debe tener volumen 1.3x la SMA(20)
double TargetRR = 2.0;          // R:R conservador para reversal
int StopBufferTicks = 6;        // Buffer sobre el extremo del push
```

### Brick size recomendado

Renko 35-40 tick — igual que ULTRA. En brick más pequeño (25-30), la microestructura de volumen tiene más ruido.

### AllowShort

ON desde el inicio — los reversals son simétricos (techo = short, suelo = long) y la lógica de absorción/exhaustion funciona igual en ambas direcciones.

### Prioridad: Media-Alta (llenar brecha de order flow)
Timeline: Construir y backtest en paralelo al paper trading (~Marzo-Abril 2026). No esperar a completar validación paper si el concepto es sólido.

---

## Oportunidad 10: KeltnerFlow_v1 — Canal + Pullback + Volume Delta

### Contexto (01/03/2026)

Basado en el concepto de ninZa: canal ATR/Keltner define estructura de mercado, entradas en pullback a banda inferior (tendencia alcista) o banda superior (tendencia bajista), confirmadas por Volume Delta sintético. Incluye filtro "skip noise" para evitar mercado sin estructura.

### Diferencia con VWAPFlux_v1

| Característica | VWAPFlux_v1 | KeltnerFlow_v1 |
|---|---|---|
| Ancla | VWAP (promedio precio-volumen) | Canal Keltner (volatilidad estructural) |
| Dirección | Long only | Long + Short según tendencia del canal |
| Señales | Solo pullback a VWAP | Pullback a banda + breakout de consolidación |
| Filtro estructura | No | "Skip noise" activo (mercado sin estructura = no operar) |

### Parámetros base

```csharp
int KeltnerPeriod = 20;         // Período EMA central del canal
double KeltnerMultiplier = 2.0; // ATR multiplier para las bandas
int ATRPeriod = 14;             // ATR para las bandas
int DeltaSMAPeriod = 20;        // SMA del volume delta sintético
double MinDeltaRatio = 1.3;     // Delta debe ser 1.3x la SMA para confirmar
double TargetRR = 3.0;          // R:R inicial
int StopBufferTicks = 5;
```

### Prioridad: Alta (nueva estrategia — Semana 2 de Marzo 2026)
Timeline: ~Semana 2 Marzo 2026

---

## Oportunidad 11: DarvasBox_v1 — Acumulación en Box Renko → Breakout

### Contexto (01/03/2026)

Nicolas Darvas: precio acumula en rango horizontal (box), luego rompe. En Renko es naturalmente elegante — los bricks que oscilan dentro de un high/low fijo definen el box sin ruido temporal. El brick que rompe el box ES la señal.

### Diferencia con PivotTrendBreak_v1

- PivotTrendBreak: break de estructura de pivots (máximos/mínimos de oscilación)
- DarvasBox: break de rango horizontal de acumulación/distribución

Son conceptos distintos — PTB detecta momentum, Darvas detecta fin de consolidación.

### Lógica central (implementada en 5-min time chart)

1. Máximo local detectado → caja empieza a formarse
2. Precio consolida sin superar ese máximo por `BoxMinBars` a `BoxMaxBars` barras
3. Box confirmado si tamaño entre `MinBoxSizeTicks` y `MaxBoxSizeTicks`
4. Breakout: `Close[0] > boxTop` con volumen ≥ `MinVolRatio × SMA(Volume)`
5. SL: fondo de caja - `StopBufferTicks`; TP: entry + stopDist × `TargetRR`

### Estado: ✅ Código creado 02/03/2026 — pendiente backtest

- Archivo: `Strategies/DarvasBox_v1.cs`
- Reporte: `Reports/19_DarvasBox_v1.md`
- Chart inicial: **5-min MNQ** (probar también 15-min)
- Params base: BoxMinBars=3, BoxMaxBars=20, MinBoxTicks=10, MaxBoxTicks=80, RR=3.0, BE=1R, VolRatio=1.2

### Prioridad: Alta (nueva estrategia — en backtest Marzo 2026)
Timeline: Semana 1-2 Marzo 2026.

---

## Oportunidad 12: VolumeProfile_POC_v1 — POC Intradiario como Soporte/Resistencia

### Contexto (01/03/2026)

El POC (Point of Control) es el precio con mayor volumen negociado en la sesión. Los institucionales lo usan como ancla — el precio tiende a regresar al POC y luego rechazarlo como soporte/resistencia. Diferente al VWAP (precio promedio ponderado) — el POC es el nivel de máxima aceptación de precio.

NT8 puede calcular el POC intradiario en barras de tiempo (5-min) sin Tick Replay.

### Señales potenciales

1. **Rechazo en POC**: precio toca POC desde arriba + vela bajista + volumen → short
2. **Soporte en POC**: precio toca POC desde abajo + vela alcista + volumen → long
3. **Break del POC**: precio rompe POC con volumen → continuación en dirección del break

### Prioridad: Media (nueva estrategia — Abril 2026)
Timeline: ~Abril 2026, en paralelo con paper trading del resto

---

## Oportunidad 13: BlackSwanCatcher_v1 — La Mancuerna de Taleb

### Contexto (01/03/2026)

Nassim Taleb: **barbell strategy** — un extremo conservador (estrategias regulares que trabajan todos los días) y un extremo especulativo convexo (estrategia que duerme 95% del tiempo y explota cuando ocurre el evento de cola).

> *"No busques predecir el cisne negro. Construye un sistema que se fortalezca cuando llegue."*

El portafolio actual tiene el lado conservador cubierto (12 estrategias diarias). Esta estrategia completa la mancuerna con el lado convexo.

### Concepto: Solo activa durante volatilidad extrema

```
Condición de activación: ATR(14) > ATR_SMA(50) × VolatilityMultiplier
                         O: rango diario acumulado > X ticks desde apertura

En mercado normal: NO opera (pierde 0, gana 0)
En Black Swan:     Se activa, sigue el impulso, sin profit target
```

**Payoff asimétrico** (convexo):
- Días normales: sin trades → sin pérdidas
- Corrección moderada: 1-3 trades → pequeñas pérdidas o ganancias marginales
- Black Swan (crash/spike): 1 trade perfecto → ganancia de 10-50× el riesgo habitual

### Diseño técnico

```csharp
// Detector de Black Swan
double atrCurrent  = ATR(14)[0];
double atrBaseline = SMA(ATR(14), 50)[0];   // ATR promedio de 50 días
bool isBlackSwan   = atrCurrent > atrBaseline * VolatilityMultiplier;  // 2.0-3.0x

// Si no es Black Swan → return (no operar)
if (!isBlackSwan) return;

// En Black Swan → seguir el impulso dominante
// Brick size grande (80-120 tick) = solo se activa en movimientos verdaderamente extremos
// Sin profit target — trailing stop puro (como SuperTrendWave)
// AllowShort=ON — los crashes bajan más rápido de lo que suben
```

### Brick size especial

Renko 80-120 tick — cada brick = $40-60 de movimiento. En mercado normal no se forma ningún brick. En un crash de COVID (MNQ cayó ~3,000 puntos en semanas) formaría decenas de bricks SHORT consecutivos.

### Por qué funciona en Renko durante crashes

En un Black Swan, MNQ puede moverse 500-1,500 ticks en horas. Con Renko 100-tick:
- Mercado normal: 0-2 bricks/día (no hay señal)
- Black Swan: 50+ bricks en cascada → la estrategia cabalga todo el movimiento

### Relación con el portafolio existente

| Estrategia | Trabaja cuando | Payoff |
|---|---|---|
| 12 estrategias regulares | Todos los días | Lineal, consistente |
| **BlackSwanCatcher_v1** | Solo en eventos extremos | Convexo, explosivo |

Esto es la **mancuerna de Taleb** aplicada a futuros: conservador + convexo, nada en el medio.

### Desafío con Apex

El MaxDD diario de $2,500 limita el tamaño de posición durante el Black Swan — precisamente cuando más contratos querías. Solución: esta estrategia puede requerir una cuenta separada no-Apex (cuenta propia o prop firm con límites más amplios) para aprovechar la convexidad completa.

En Apex: puede correr con 1-2 contratos como "señal de alarma" que valida el evento.

### Backtesting

Requiere datos 2018-2026 (incluir COVID crash de marzo 2020 y corrección de 2022) — el período 2023-2026 no tiene ningún Black Swan real. Sin datos de eventos extremos el backtest no tiene validez.

### Prioridad: Media (requiere datos históricos más amplios)
Timeline: Q2-Q3 2026. Prerequisito: tener resultados paper de estrategias actuales + datos históricos 2018-2023.

---

## Oportunidad 14: Salidas Parciales por Niveles — BreadButter_v5_Apex

### Contexto (02/03/2026)

v5_Apex usa R:R=4 con un solo exit point. El problema: muchos trades alcanzan 2R-3R y revierten antes de llegar al target. El "popcorn" devuelve ganancias en trades que ya eran ganadores. La solución es escalar las salidas en 5 niveles para capturar profits reales sin esperar los 4R completos.

### Estructura de 5 niveles propuesta

```
Nivel 1: cerrar 20% de la posición en 1R   → asegura algo siempre
Nivel 2: cerrar 20% de la posición en 2R   → núcleo del edge
Nivel 3: cerrar 20% de la posición en 3R   → bonus
Nivel 4: cerrar 20% de la posición en 4R   → target original
Nivel 5: cerrar 20% restante con trailing  → captura extensiones inesperadas

SL management: mover a BE cuando se ejecuta Nivel 1 (1R alcanzado)
```

### Hipótesis

Si la mayoría de trades llegan a 2R pero no a 4R, los niveles 1-2 capturen el edge real y el PF general mejore (menos trades con ganancia completa devuelta).

### Riesgo del experimento

El "filtro accidental" (1 trade/día) puede interactuar con el partial exit de formas no anticipadas. **Backtest obligatorio** antes de implementar en live. Comparar:
- Versión A (actual): salida única en 4R
- Versión B: 5 niveles como arriba

Si el PF de B ≥ PF de A con R² similar → implementar.

### Implementación técnica

```csharp
// En OnExecutionUpdate — track niveles alcanzados
double entryPrice = Position.AveragePrice;
double stopDistance = Math.Abs(entryPrice - initialStop);

// Targets por nivel
double lvl1 = entryPrice + 1.0 * stopDistance;  // 1R
double lvl2 = entryPrice + 2.0 * stopDistance;  // 2R
double lvl3 = entryPrice + 3.0 * stopDistance;  // 3R
double lvl4 = entryPrice + 4.0 * stopDistance;  // 4R (target original)

// Cantidad por nivel: 20% del total (ej: 3ct → 0-1ct por nivel)
// Nivel 5: trailing con SuperTrend o ATR trailing
```

### Nota sobre sizing

Con 3 contratos (el sizing Apex actual), cada 20% = 0.6 contratos → redondear a 1ct por nivel con ajuste. En práctica: `[1ct, 1ct, 1ct]` en lvl1/2/3 y nada en lvl4/5 si solo tienes 3ct. Para aprovechar bien los 5 niveles necesitas mínimo **10 contratos** (2ct × 5 niveles).

### Prioridad: Media
Timeline: ~Abril 2026. Prerequisito: 4-6 semanas de datos paper v5_Apex para ver cuántos trades llegan a cada nivel de R.

---

## Oportunidad 15: Cascade / Pyramid Controlado (cuenta propia — futuro)

### Contexto (02/03/2026)

Evaluación de grid trading / DCA / cascade ordering tras revisar tres fuentes. **Veredicto final**:

| Concepto | Apex | Cuenta propia | Veredicto |
|---|---|---|---|
| Grid clásico (promediar perdedores) | ❌ Incompatible | ⚠️ Solo en rangos perfectos | Descartar para MNQ |
| **Cascade (pyramid en ganadores)** | ✅ Compatible | ✅ Compatible | Expandir — ya existe en STW |
| Grid personal (futuro lejano) | ❌ | 🟡 Con capital + DD 15%+ | No antes de 2027 |

**Grid Trading en Apex es incompatible**: $7,500 de DD global. Con 4 niveles de grid en MNQ contra la tendencia ($343-500/nivel), el DD acumulado supera el límite en 1-2 días de tendencia fuerte. MNQ es estructuralmente tendencial — el riesgo del grid es ilimitado.

**Cascade Ordering ≠ Grid**: Escalar INTO winners (no losers). Es el concepto del Texto 2 de Echo Engineering. Ya está implementado en SuperTrendWave (pyramidación en impulsos). La diferencia clave:

```
Grid clásico: precio baja → compramos más (promedia en contra)
Cascade:       precio sube → compramos más (sigue el momentum)
```

### Expansión del concepto Cascade para cuenta propia

Para una cuenta personal futura (~$50k+, DD tolerance 15%):

```
Concepto: "Escala Solo Si Ganas"
1. Primera entrada: 1 contrato cuando se detecta señal base
2. Primera escala: +1ct cuando el trade llega a 1R (ya estamos en positivo)
3. Segunda escala: +1ct cuando llega a 2R (nunca añadimos si estamos perdiendo)
4. SL de toda la posición: trailing — nunca vuelve a pérdida neta

Resultado: si el trade llega a 4R con 3ct escalados = PnL mayor
Si el trade sale en BE = $0 (sin pérdida, sin comisiones significativas)
```

### Diferencias con SuperTrendWave pyramid

- STW: pyramid basado en pullbacks detectados (estructural)
- Cascade propuesto: pyramid basado en niveles de R fijos (mecánico)
- Para Apex: usar solo en cuenta propia, no en cuentas prop con DD estricto

### Prioridad: Baja (exploración futura)
Timeline: No antes de Q3-Q4 2026. Prerequisito: cuenta propia capitalizada + experiencia de 6+ meses con portafolio actual.

---

## Lección 01: Correlación Catastrófica — 17/03/2026 ⚠️

### Lo que pasó
A las 10:05 AM ET, **tres estrategias entraron long simultáneamente** en un mercado en caída libre:
- StatMeanCross_v1 LONG x20ct → Stop en 1 barra → **-$491**
- EMATrendRenko_v1 LONG x16ct → Stop en 2 barras → **-$648**
- BreadButter_v5_Apex LONG x20ct → Stop en 6 barras → **-$2,862**

Total del slot: **-$4,001 en ~5 minutos**. Día total: **-$8,906**.

### Diagnóstico
El brain actual evalúa cada señal de forma **aislada** — no tiene visión del estado global del portafolio en ese momento. Tres estrategias con lógicas distintas (EMA cross, stat mean, MACD) fueron engañadas por el mismo ruido de mercado al mismo tiempo.

### La solución: KDL — Kraken Discernment Layer

Inspirado en el **Kraken Protocol** (RenkoKings framework: estructura + momentum + volumen + ejecución), traducido a nuestro contexto como 4 gates pre-trade que actúan **antes** del brain por estrategia:

| Gate | Concepto Kraken | Nuestra implementación | Bloquea si... |
|------|----------------|----------------------|---------------|
| 1 | Trend Structure (RK-Sys Platinum) | EMA slope multi-TF + ADX | Long con EMA bajista o ADX < 18 |
| 2 | Momentum Strength (Solar Wave RK) | RSI + ADX direction | Momentum agotado en la dirección |
| 3 | Volume Participation (VoluCandlez) | vol_ratio relativo | Volumen < 0.6x promedio o vol alto en contra |
| 4 | Portfolio Correlation (**NUESTRO**) | Conteo posiciones activas mismo lado | 3+ estrategias ya en la misma dirección |

**Gate 4 es VETO ABSOLUTO.** Con KDL activo el 17/03, los $4,001 del slot de las 10:05 se habrían bloqueado.

### Diseño técnico completo
El código Python de la KDL está diseñado y listo. Ver conversación 17/03/2026.

### Por qué NO se implementa ahora
Estamos en **Semana 3/6** del período de recolección de datos. El patrón de correlación catastrófica debe repetirse en los datos para que Markov y el RF aprendan a reconocerlo. Si la KDL bloquea el patrón ahora, el brain llegará a producción sin haberlo visto.

> **El -$8,906 de hoy es el costo de un dato de altísimo valor. No una pérdida — una inversión en el brain.**

### Implementación target: **Semana 2 de Abril (14/04-18/04)**

La KDL se integra en `meta_brain.py` como módulo `KrakenDiscernmentLayer`. Se activa en paralelo al **Portfolio Stop Global** que ya está planificado para esa semana.

```python
# Integración en handle_entry_query():
# 1. KDL evalúa → si BLOCK, retorna inmediatamente
# 2. Si ALLOW → brain por estrategia (heurístico o RF)
# 3. KDL conviction modifica la confianza final
# 4. NT8 usa confidence × conviction para sizing
```

### Conceptos Kraken adicionales a evaluar en Q2 2026
- **Volume Participation como feature del RF**: añadir vol_ratio direccional (no solo magnitud) como feature al Random Forest — detecta si el volumen alto va CON o CONTRA la señal
- **Pullback quality filter**: Gate 1 detecta si el pullback tiene volumen decreciente (sano) vs volumen creciente en contra (reversión) — concepto VoluCandlez adaptado a Renko

---

## Resumen del roadmap por prioridad

| Prioridad | Mejora | Timeline | Tipo |
|---|---|---|---|
| 🔴 CRÍTICA | **KDL — Kraken Discernment Layer** (Lección 17/03) | Semana 2 Abril (14/04) | Brain Midas |
| 🔴 Alta | Market Regime Filter | ~20/03/2026 | Mejora portafolio |
| 🔴 Alta | **OrderFlow Reversal** ✅ CONFIRMADA | Completada 01/03/2026 | Nueva estrategia |
| ❌ Descartada | **KeltnerFlow_v1** Short-only PF=1.63 R²=0.87 **Sortino=0.35** ❌ | Descartada 02/03/2026 | Nueva estrategia |
| 🔴 Alta | **DarvasBox_v1** (Consolidación → Breakout + volumen) | En backtest Semana 1-2 Marzo | Nueva estrategia |
| 🟡 Media | **Salidas Parciales 5 niveles — v5_Apex** | ~Abril 2026 | Mejora portafolio |
| 🟡 Media | **VolumeProfile_POC_v1** (POC intradiario) | Abril 2026 | Nueva estrategia |
| 🟡 Media | **BlackSwanCatcher_v1** (Mancuerna de Taleb) | Q2-Q3 2026 | Nueva estrategia |
| 🟡 Media | Escalar NYOpenBlast a 7ct | ~20/03/2026 | Mejora portafolio |
| 🟡 Media | Escalar VWAPOrderBlock a 9ct | ~20/03/2026 | Mejora portafolio |
| 🟡 Media | EMA Touch → otras estrategias Renko | ~Abril 2026 | Mejora portafolio |
| 🟡 Media | Apex sizing para v5_Apex | Q2 2026 | Mejora portafolio |
| 🟢 Baja | Choppiness Index Filter | Condicional | Mejora portafolio |
| 🟢 Baja | Anti-Popcorn (Brandt exits) | Condicional | Mejora portafolio |
| 🟢 Baja | Multi-Asset Validation | Abril-Mayo 2026 | Validación |
| 🟢 Baja | **Cascade Pyramid — cuenta propia** | Q3-Q4 2026 | Mejora futura |
| 🔵 Exploración | Mean Reversion VWAP | Q2-Q3 2026 | Nueva estrategia |
| 🔵 Exploración | EMA Touch Renko — standalone | Q2 2026 | Nueva estrategia |
| 🔵 Exploración | Divergencias MACD/RSI en Renko | Q2-Q3 2026 | Nueva estrategia |
| ❌ Descartada | Elliott Waves + Fibonacci | — | Demasiado subjetivo para automatizar |
| ❌ Descartada | Grid Trading / DCA clásico | — | Incompatible con Apex y MNQ tendencial |

---

## Principios para futuras estrategias

Antes de construir una nueva estrategia, verificar:
1. ¿Tiene un **concepto de flujo institucional** detrás? (no solo indicadores)
2. ¿Es **diferente** a lo que ya tenemos (timeframe, tipo de edge, frecuencia)?
3. ¿El PF sin comisiones es > 1.30? (para sobrevivir comisiones reales)
4. ¿El R² es > 0.80? (curva lineal = edge consistente)
5. ¿El MaxDD cabe en Apex? ($7,500 por estrategia)
6. ¿Tiene > 200 trades en 3 años? (muestra estadística mínima)
7. ¿Funciona separando longs y shorts? (o el edge requiere mezcla)
