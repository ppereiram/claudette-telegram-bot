# VWAPOrderBlock_v1
> Sniper institucional VWAP + Order Blocks | `Strategies/VWAPOrderBlock_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **1.79** 🏆 |
| Long PF | **2.79** |
| Short PF | 1.22 |
| Net total (3 años, 10ct) | $51,591 |
| Profit/mes (9ct) | **$1,255** |
| MaxDD (10ct) | $7,566 |
| MaxDD (9ct) | **$6,810** ✅ |
| Win Rate | 38.54% |
| Win/Loss Ratio | 2.86x |
| Trades/día | 0.12 (1 trade cada 8 días) |
| Chart | 5-min MNQ |

**Mejor PF del portafolio.** Señal de muy alta calidad, baja frecuencia.

---

## Concepto y edge

Combina dos conceptos de flujo institucional:

### 1. VWAP diario como sesgo
El VWAP (Volume Weighted Average Price) es el precio al que las instituciones han transaccionado en promedio en el día. Los algoritmos de ejecución institucional (TWAP/VWAP bots) referencian este nivel constantemente.

- Precio > VWAP → las instituciones están comprando en promedio → sesgo alcista
- Precio < VWAP → las instituciones están vendiendo en promedio → sesgo bajista

### 2. Order Blocks como trigger de entrada
Un Order Block (OB) es la **última vela de consolidación antes de un impulso fuerte**. Hipótesis: en esa vela consolidante, una institución grande colocó órdenes que no se completaron. Cuando el precio regresa a ese nivel, la institución completa sus órdenes → el precio se mueve nuevamente en la dirección original.

**Señal combinada**:
- OB bullish + precio > VWAP → LONG cuando precio retrocede al OB
- OB bearish + precio < VWAP → SHORT cuando precio retrocede al OB

### El patrón ganador
WR=38.54% con ratio 2.86x: **muchos trades salen en breakeven** (stop movido a entrada), **pocos llegan al target de 4R**. Esto es correcto — la mayoría de los OBs "fallan" pero cuando uno funciona, es un move de calidad.

---

## Parámetros ganadores

### Order Block Detection
| Parámetro | Valor | Descripción |
|---|---|---|
| OBMinATRMult | 2.0 | Impulso mínimo para crear un OB (2× ATR) |
| ATRPeriod | 7 | Período del ATR de referencia |
| OBLookback | 2 | Barras hacia atrás para buscar el OB |
| OBMaxAge | 40 | Máximo de barras de vida del OB |

### Trade Management
| Parámetro | Valor | Descripción |
|---|---|---|
| TargetRR | 4 | R:R 4:1 |
| BreakevenR | 1 | Mueve stop a entrada al llegar a 1R |
| StopBufferTicks | 5 | Buffer por encima/debajo del OB para el stop |

### Filtros
| Parámetro | Valor |
|---|---|
| UseVWAPFilter | ON |
| MinVolRatio | 1.0 |
| AllowShort | ON |
| AllowLong | ON |
| UsePrimeHours | ON |

---

## Por qué los Longs dominan tan claramente (PF Long=2.79 vs Short=1.22)

MNQ tiene un **sesgo estructural alcista** de largo plazo. Los Order Blocks bullish cerca del VWAP tienden a ser respetados con mayor consistencia que los bearish, porque:
1. El flujo general es comprador (sesgo bull de mercado)
2. Los OBs bullish + precio sobre VWAP = doble confirmación institucional
3. Los OBs bearish tienen más probabilidad de ser "barridos" por el momentum alcista

---

## Fortalezas

- **PF=1.79 con comisiones** — el mejor número absoluto del portafolio
- **MaxDD $6,810 (9ct)** — cabe perfectamente en Apex $7,500
- **0.12 trades/día** — comisión prácticamente despreciable
- **Concepto institucional genuino** — Order Blocks y VWAP son herramientas reales usadas en trading profesional
- **Alta descorrelación** — opera tan raramente que no interfiere con ninguna otra estrategia

## Debilidades / Riesgos

- **96 trades en 3 años** — muestra estadística pequeña para la magnitud del PF. Un PF de 1.79 con 96 trades tiene más incertidumbre estadística que un PF de 1.41 con 692 trades
- **0.12 trades/día** — en períodos de 2-3 semanas puede no tener ningún trade, lo que dificulta el monitoreo
- **Definición de OB** — la calidad de la detección del Order Block es subjetiva. El parámetro OBMinATRMult=2.0 puede perderse algunos OBs válidos o incluir algunos falsos

---

## Análisis estadístico de la muestra pequeña

| Escenario | PF esperado |
|---|---|
| Optimista (los últimos 3 años se repiten) | 1.79 |
| Conservador (95% confidence interval) | ~1.30-1.50 |
| Pesimista (distribución de OBs cambia) | ~1.10-1.20 |

**Recomendación**: Tratar el PF como 1.40-1.50 en expectativa real para sizing conservador.

---

## Sizing para Apex

| Contratos | Net/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 9 | $1,255 | $6,810 | ✅ |
| 10 | $1,394 | $7,566 | ⚠️ exactamente en el límite |

**Recomendación**: 9 contratos para dejar margen de seguridad.
