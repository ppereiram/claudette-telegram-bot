# BreadButter_v5_Apex
> Mejor estrategia del portafolio | Archivo: `Strategies/BreadButter_v5_Apex.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor | **1.41** |
| R² (linealidad) | **0.96** — excelente |
| Sortino Ratio | **2.14** — excelente |
| Net total (4 años) | $184,537 |
| Profit/mes | **$4,985** |
| Max Drawdown | $38,727 ⚠️ |
| Total trades (4 años) | 692 |
| Win Rate | 36% |
| Win/Loss ratio | 2.35x |
| Trades/día | 0.89 |
| Chart | 2-min MNQ |

---

## Concepto y edge

Sistema de **baja win rate + alta relación riesgo/recompensa**. La estrategia no busca tener razón la mayoría del tiempo — busca perder pequeño muchas veces y ganar grande pocas veces. Con 36% WR y ratio 2.35x, el edge matemático es:

```
Expected Value = (0.36 × 2.35R) - (0.64 × 1R) = 0.846R - 0.64R = +0.206R por trade
```

Esto explica por qué el R² es 0.96 — la curva es casi perfectamente lineal porque el edge es consistente y no depende de condiciones específicas del mercado.

**Indicadores usados:**
- EMA 9 / EMA 15 (señal de corto plazo)
- EMA 100 (filtro de tendencia principal)
- ATR period=7 (medición de volatilidad dinámica)
- RSI period=7 (filtro de sobrecompra/sobreventa)
- ADX period=21 (filtro de tendencia vs rango)

---

## Parámetros ganadores

| Parámetro | Valor | Notas |
|---|---|---|
| Stop | 3× ATR(7) | Amplio para sobrevivir retrocesos normales de MNQ |
| R:R | 4:1 | Clave para el edge — no reducir |
| Breakeven | 1R | Mueve stop a entrada al llegar a 1R de ganancia |
| Trailing | **OFF** | Crítico — trailing ON mataba el ETD/MFE |
| Max Trades/día | 1 | Limita a la mejor señal del día |
| RSI Long | < 65 | Evita entrar en sobrecompra extrema |
| RSI Short | > 35 | Evita entrar en sobreventa extrema |
| VolMin | 0.7× promedio | Requiere algo de participación del mercado |
| Prime Hours | ON | Solo opera durante horas de mayor liquidez |

---

## Historia de desarrollo

### El problema original
La versión anterior tenía un ratio ETD/MFE del 96% — los trades llegaban casi al target y luego revertían para salir por stop o breakeven. Era frustrante ver trades correctos terminar en pérdida.

### La solución
El problema era el **trailing stop** combinado con un **R:R demasiado pequeño** (2:1). El trailing capturaba parciales pero daba espacio al mercado para revertir. La solución:
1. **Apagar trailing completamente** — dejar correr los ganadores sin interferir
2. **Subir R:R a 4:1** — los pocos ganadores deben compensar muchas pérdidas pequeñas
3. **Mantener stop en 3×ATR** — amplio para sobrevivir el ruido normal de MNQ

Resultado: ETD/MFE mejoró dramáticamente, curva pasó de ~0.80 a 0.96 R².

---

## Fortalezas

- **R² = 0.96** — la curva más lineal del portafolio, señal de edge genuino y consistente
- **Sortino 2.14** — excelente relación retorno/riesgo downside
- **692 trades en 4 años** — muestra estadística suficiente para confiar en los números
- **Timeframe 2-min** — único en el portafolio, no compite con otras estrategias

## Debilidades / Riesgos

- **MaxDD $38,727** — demasiado alto para una cuenta Apex de $50k
  - Solución: operar con 1 contrato y aceptar profit mensual menor (~$4,985/mes con 1ct es excelente de todas formas)
  - Si se escala: con 2ct MaxDD sería ~$77k, imposible para Apex
- **36% WR** — en trading en vivo, rachas de 8-12 pérdidas seguidas son normales y psicológicamente difíciles aunque el bot sea automático

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD estimado | Viable Apex $50k |
|---|---|---|---|
| 1 | $4,985 | $38,727 | ⚠️ Al límite |
| 1 (con buffer) | $4,985 | $38,727 | ✅ Si cuenta tiene $50k+ de historial |

**Recomendación**: Operar 1 contrato. El profit/mes de $4,985 por 1 solo contrato ya justifica completamente la estrategia.

---

## Notas operativas

- Requiere **chart de 2-min** — único en el portafolio
- NinjaTrader cachea parámetros — después de recompilar, quitar y re-agregar la estrategia
- No compartir capital con ULTRA o SCALPER en la misma cuenta (mismo instrumento, posible conflicto)
