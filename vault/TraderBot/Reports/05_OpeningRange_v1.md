# OpeningRange_v1
> Rango de apertura | `Strategies/OpeningRange_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor | **1.30** |
| R² | 0.83 |
| Net/mes (15ct) | **$2,052** |
| MaxDD (1ct) | ~$1,440 |
| MaxDD (5ct) | ~$7,200 |
| Total trades (3 años) | 362 |
| Trades/día | 0.47 |
| Ventana activa | 9:30 — 13:00 |
| Chart | 5-min MNQ |

---

## Concepto y edge

Explota el hecho de que los **primeros 15 minutos de sesión regular** (9:30-9:45 AM) establecen niveles de soporte y resistencia genuinos. Las instituciones usan estos extremos como referencia para posicionarse durante el resto de la mañana.

### Mecánica

1. **Fase de construcción** (9:30-9:45): El sistema registra el máximo y mínimo de los primeros 15 minutos → establece el "Opening Range" (OR)
2. **Determinación de sesgo**: El EMA(9) en barras de 15-min determina la tendencia
   - EMA ascendente → sesgo alcista → esperar precio en el MÍNIMO del OR para comprar
   - EMA descendente → sesgo bajista → esperar precio en el MÁXIMO del OR para vender
3. **Entrada**: Cuando el precio regresa al nivel del OR relevante (pullback al soporte/resistencia)
4. **Salida**: Target fijo (2×stop) o ForceExit a las 13:00

### Por qué funciona

Los niveles del OR son **soporte/resistencia real** — no son líneas arbitrarias. Las instituciones colocan órdenes cerca de estos niveles porque todos los participantes los ven. El regreso al OR después de una ruptura inicial es uno de los patrones más consistentes del mercado de índices.

---

## Parámetros confirmados

| Parámetro | Valor | Descripción |
|---|---|---|
| ORMinutos | 15 | Duración del Opening Range (9:30-9:45) |
| Stop | 200 ticks ($100/ct) | 2 puntos de buffer |
| Target | 400 ticks ($200/ct) | R:R 2:1 |
| Breakeven | 150 ticks | Mueve stop después de 1.5× el stop inicial |
| GapFilter | ON | Evita días con gaps extremos |
| GapMin | 5 puntos | Umbral del filtro de gap |

### Datos de la serie secundaria
```csharp
// En Configure:
AddDataSeries(BarsPeriodType.Minute, 15);  // Para EMA de tendencia

// En OnBarUpdate:
if (BarsInProgress != 0) return;  // Solo barras primarias
ema9_15min = EMA(BarsArray[1], 9)[0];  // EMA 9 en 15-min
```

---

## Fortalezas

- **Concepto con edge genuino** — OR levels son usados por instituciones reales
- **MaxDD baja por contrato** ($1,440) — excelente para escalado
- **Descorrelacionado del resto** — opera solo en la mañana (9:45-13:00) y en 5-min
- **362 trades en 3 años** — muestra estadística suficiente
- **Complemento ideal** para NYOpenBlast (ventana diferente, lógica diferente)

## Debilidades / Riesgos

- **PF=1.30** — el más bajo de las estrategias activas principales. Más sensible a costos de fricción
- **R²=0.83** — aceptable pero no excelente. Hay períodos de 2-3 meses con curva plana
- **Dependencia del gap filter** — días con gaps extremos generan OR distorsionados. Si el filtro falla, el sistema puede entrar en trades de muy bajo edge

---

## Oportunidades de mejora

1. **Confirmar con volumen**: Agregar filtro de volumen en el momento del pullback al OR — si el volumen es muy bajo cuando el precio toca el OR, la reversión puede ser falsa
2. **Filtro de días con noticias**: Datos económicos importantes (NFP, FOMC) distorsionan el OR. Un filtro de calendario económico podría mejorar el PF
3. **OR Breakout mode**: Adicionalmente a OR pullback, capturar breakouts del OR cuando el precio lo rompe con momentum (estrategia complementaria)

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD estimado | Viable Apex |
|---|---|---|---|
| 5 | $685 | ~$7,200 | ✅ (límite) |
| 4 | $548 | ~$5,760 | ✅ con margen |
| 15 | $2,052 | ~$21,600 | ❌ necesita cuenta mayor |

**Recomendación**: 5 contratos en Apex (al límite de $7,500). Para maximizar ingresos necesitas una cuenta de mayor capacidad.
