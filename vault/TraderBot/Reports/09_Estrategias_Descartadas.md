# Estrategias Descartadas — Experimentos y Lecciones

> Registro completo de todo lo que se intentó y por qué no funcionó.
> Mantener este registro evita repetir errores y acelera el aprendizaje.

---

## BBShorts_v1 y v2
**Concepto**: Shorts puros en dirección de tendencia bajista usando EMA

**Por qué falló**:
- PF techo ~1.12 — nunca superó el umbral mínimo de rentabilidad real
- Curva de equity en rojo durante 2 años de los 3 backtestados
- MNQ tiene **sesgo estructural alcista** — los shorts puros van en contra del instrumento

**Lección**: En MNQ, las estrategias pure-short son estructuralmente desventajosas. Los shorts tienen edge solo como complemento de un sistema mixto o en ventanas muy específicas (ej: scalp intradía como en ULTRA donde shorts PF=1.45 pero con filtros específicos).

---

## ABCDScalper_v1
**Concepto**: Patrón ABCD (pullback clásico de análisis técnico)

**Por qué falló**: Abandonado. La detección automática del patrón ABCD requiere definir subjetivamente qué constituye cada punto del patrón. En automatización, esto genera demasiados falsos positivos.

**Lección**: Los patrones que un trader experimentado identifica "visualmente" a menudo dependen de contexto implícito que el algoritmo no puede replicar fácilmente.

---

## Mean Reversion Shorts
**Concepto**: Vender cuando el precio está sobreextendido al alza, esperando retroceso

**Por qué falló**: PF=0.68 — pérdida neta. En MNQ, los movimientos alcistas extendidos tienden a continuar (momentum) más que a revertir en el corto plazo intradía.

**Lección**: Mean reversion en la dirección contraria al sesgo estructural del instrumento es una apuesta de baja probabilidad. Si se implementa mean reversion, debe ser en la dirección alcista (comprar dips).

---

## EMAIntention_v1
**Concepto**: Basado en metodología de un profesor de trading — EMA21 + "intention candle" (vela de intención que muestra dónde quiere ir el precio)

**Por qué falló**:
- PF techo ~1.06 — insuficiente para trading real
- El concepto de "intention candle" es **discrecional y visual** — el trader humano usa contexto subconsciente al identificarla que el algoritmo no puede replicar
- La definición matemática de "intention candle" se convirtió en una regla arbitraria que capturaba falsos positivos

**Lección**: Las estrategias que enseñan traders discrecionales tienen un PF techo bajo al automatizarse (~1.06). El edge del trader humano viene de factores no cuantificables (noticias en tiempo real, intuición de flujo, experience pattern matching). No perseguir este tipo de conceptos para automatización.

---

## NQ_VWAP_MeanReversion
**Concepto**: Mean reversion al VWAP — cuando el precio se aleja mucho del VWAP, vuelve

**Por qué falló**:
- 6 bugs encontrados durante el desarrollo
- El concepto estaba **invertido** — el código entraba en la dirección opuesta a la intención
- Después de corregir bugs, PF < 1.0

**Lección**: VWAP como soporte/resistencia funciona (VWAPOrderBlock usa esto). VWAP como trigger de mean reversion puro en MNQ no funciona — el instrumento tiene demasiado momentum para que los retrocesos al VWAP sean confiables como señal de reversión.

---

## TheStrat_v1
**Concepto**: "The Strat" es una metodología de trading basada en patrones de velas de 3 tipos (1-inside, 2-directional, 3-outside) con confluencia de timeframes múltiples

**Por qué falló**:
- Nunca rentable en backtest
- Tiempos de backtest **extremadamente lentos** — el procesamiento de múltiples timeframes simultáneos era computacionalmente costoso
- La combinación de tipos de velas no generó señales con edge estadístico suficiente en MNQ

**Lección**: Los sistemas multi-timeframe complejos de patrones de velas tienen alta complejidad de implementación con bajo retorno de edge. El tiempo de backtest extremadamente lento fue una señal adicional de que el diseño tenía problemas de eficiencia.

---

## VWAPPulse_v1
**Concepto**: VWAP cross en 1-min como trigger primario, filtrado por tendencia 15-min, EMA 5/13, y delta de volumen proxy

**Desarrollo**: Concepto original sólido (el VWAP como trigger institucional), con 5 confirmaciones independientes. Se testó en 1-min y luego en 5-min.

**Resultados**:

| Configuración | PF | WR | Pérd. consec. | R² |
|---|---|---|---|---|
| 1-min con filtros | ~1.23 | 40.99% | 7 | 0.77 |
| 1-min con comisión | ~1.05 | 19.50% | — | 0.35 |
| 5-min sin filtros | 1.33 | 12.90% | **24** | 0.71 |

**Por qué falló**:
- **VWAP cross en MNQ es demasiado ruidoso** — el instrumento cruza el VWAP múltiples veces al día sin dirección clara
- Con comisiones, el edge prácticamente desaparece (181 trades "even" se vuelven pérdidas)
- La mejor configuración encontrada (5-min, filtros desactivados, PF=1.33) tiene 24 pérdidas consecutivas y WR=12.9% — psicológicamente difícil de mantener aunque sea automatizado
- La variante de 5-min tiene techo natural de PF~1.33

**Lección clave**: **VWAP como filtro/bias funciona (VWAPOrderBlock PF=1.79). VWAP como trigger de entrada directa no funciona en MNQ.** La diferencia es fundamental: como filtro pregunta "¿estamos del lado correcto del mercado?", como trigger pregunta "¿es ahora el momento exacto?" — y el cruce del VWAP no responde bien esa segunda pregunta.

---

## MNQMomentumScalper
**Concepto**: VWAP + EMA pullback en 2-min, múltiples señales de momentum

**Por qué falló**: PF techo ~1.03 — insuficiente. Confirmó el principio de que **VWAP+EMA pullback en timeframes cortos tiene ceiling de ~1.03 en MNQ**.

**Lección**: El pullback al VWAP+EMA es un concepto visual convincente pero matemáticamente débil en 2-min. El ruido del instrumento supera el edge de la señal en este timeframe.

---

## Resumen de patrones de fracaso

| Patrón | Ejemplos | Señal de alerta |
|---|---|---|
| Short puro | BBShorts | PF nunca >1.12 |
| Discrecional automatizado | EMAIntention | PF techo ~1.06 |
| Mean reversion vs tendencia | MR Shorts, NQ_VWAP | PF < 1.0 |
| VWAP como trigger (no filtro) | VWAPPulse, MNQMomentum | PF techo ~1.03-1.33 |
| Detección de patrones visuales complejos | ABCD, TheStrat | Backtest lento + bajo PF |
| R:R bajo con alta frecuencia | VWAPPulse 1-min | Comisiones eliminan el edge |
