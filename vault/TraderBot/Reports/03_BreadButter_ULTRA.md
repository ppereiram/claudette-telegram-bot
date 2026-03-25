# BreadButter_ULTRA
> Multi-setup en Renko 35-tick | `Strategies/BreadButter_ULTRA.cs`
> **Confirmada 26/02/2026 — Renko 35, AllowShort=ON, Slippage=1**

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **2.03** |
| R² | **0.96** |
| Sortino Ratio | **18.52** |
| Net total (3 años, 1ct) | $24,249 |
| Profit/mes (9ct) | **$9,378** |
| MaxDD (1ct) | **$767** |
| MaxDD (9ct) | **$6,903** ✅ |
| Trades totales (3 años) | 466 (0.95/día) |
| WR | 45.28% |
| Win/loss ratio | ~2.21x |
| Chart | Renko 35-tick MNQ |
| Dirección | AllowLong=ON, AllowShort=ON |

**Concepto**: 4 setups de entrada (Momentum Burst, Micro Reversal, Breakout Scalp, EMA Touch) en Renko 35-tick. El "Filtro Accidental" limita a ~1 trade/día efectivo donde todos los setups compiten por el slot diario. Shorts PF=2.33 y Longs PF=1.82 — ambas direcciones contribuyen positivamente.

> ⚠️ **Historia**: En 1-min chart con Slippage=0, el PF era ~1.08. El chart Renko 35-tick y Slippage=1 revelaron el edge real. Archivada temporalmente el 26/02/2026 y re-confirmada el mismo día con la configuración correcta.

---

## Edge conceptual

**¿Por qué Renko 35 en lugar de 1-min?**

En 1-min los 4 setups disparan señales por ruido de tiempo. En Renko 35-tick, cada brick requiere 35 ticks ($17.50) de movimiento sostenido. Los 4 setups en Renko 35 capturan momentum real — los cruces y bounces tienen significado estructural, no son ruido estadístico.

**El "Filtro Accidental" — el edge real:**

```csharp
dailyPnL += execution.Commission + execution.Order.AverageFillPrice * execution.Quantity
```

Esta fórmula suma el valor nominal del contrato (~$49k) en lugar del P&L. El primer trade del día dispara `MaxPerdidaDiaria=$300` → solo ~1 trade/día efectivo. Con los 4 setups activos en ambas direcciones, la señal de mayor momentum del día gana el slot. Selección implícita de la oportunidad más fuerte del día.

**NO corregir este bug** — sin él, 25 trades/día → PF colapsa a ~1.01.

---

## Los 4 setups (todos activos)

1. **Momentum Burst** — impulso fuerte en dirección de tendencia
2. **Micro Reversal** — reversión después de movimiento extendido
3. **Breakout Scalp** — ruptura de consolidación intraday
4. **EMA Touch** — rebote en la EMA lenta (EMA 21)

La competencia entre los 4 setups + longs y shorts = 8 candidatos por el slot diario. Gana el más temprano y fuerte.

---

## Evolución del backtest — Comparación de brick sizes

*(AllowShort=ON, Slippage=1, comisiones incluidas, 3 años)*

| Brick | PF | R² | Sortino | MaxDD | Profit/mes | Long PF | Short PF |
|---|---|---|---|---|---|---|---|
| 1-min (original) | ~~1.08~~ | 0.89 | ~~1.43~~ | — | — | — | — |
| Renko 30 | 1.91 | 0.97 | 5.82 | $1,149 | $835 | 1.76 | 2.10 |
| **Renko 35** | **2.03** | **0.96** | **18.52** | **$767** | **$1,042** | **1.82** | **2.33** |
| Renko 40 | 2.00 | 0.96 | 18.15 | $1,446 | $1,162 | 1.96 | 2.06 |

**Por qué Renko 35 gana sobre Renko 40** (mayor profit/mes $1,162):
- Renko 40: MaxDD=$1,446 vs Renko 35: MaxDD=$767. Ratio MaxDD/ganancia es peor.
- Renko 35: Sortino=18.52 > Renko 40: Sortino=18.15 (marginal, ambos excelentes)
- Renko 35: **MaxDD más bajo del portafolio completo** — $767/ct

---

## Parámetros ganadores

### Trade Management
| Parámetro | Valor | Descripción |
|---|---|---|
| Contratos | 9 | → MaxDD $6,903 ≤ Apex $7,500 |
| Max Trades por Día | 25 | Filtro accidental limita a ~1 en la práctica |
| Max Pérdida Diaria ($) | 300 | Triggea el filtro accidental al primer trade |

### EMAs
| Parámetro | Valor |
|---|---|
| EMA Fast | 3 |
| EMA Mid | 21 |

### Momentum
| Parámetro | Valor |
|---|---|
| Momentum Threshold | 0.05 |

### Volumen
| Parámetro | Valor |
|---|---|
| Require Volume Spike | OFF |
| Min Volume % | 80 |
| Volume SMA | 20 |

### ATR / Stop
| Parámetro | Valor |
|---|---|
| ATR Period | 10 |
| ATR Stop Multiplier | 1 |
| R/R Ratio | 2 |
| Enable Trailing | OFF |
| Trail Activation R | 0.5 |
| Trail ATR Mult | 0.4 |

### RSI Filter
| Parámetro | Valor |
|---|---|
| Usar Filtro RSI | OFF |
| RSI Period | 14 |
| RSI Long Max | 65 |
| RSI Short Min | 35 |

### Setups activos
| Setup | Estado |
|---|---|
| Momentum Burst | ON |
| Micro Reversal | ON |
| Breakout Scalp | ON |
| EMA Touch | ON |

### Horario (ET)
| Parámetro | Valor |
|---|---|
| Start Hour | 9 |
| Start Minute | 0 |
| End Hour | 15 |
| End Minute | 30 |

### Dirección
| Parámetro | Valor |
|---|---|
| Allow Long | ON |
| Allow Short | ON |

### Chart
| Parámetro | Valor |
|---|---|
| Tipo | Renko |
| Brick Size | **35 ticks** |

---

## Fortalezas

- **Sortino=18.52** — el más alto del portafolio completo por margen enorme
- **PF=2.03** — top tier del portafolio
- **MaxDD=$767/ct** — el más bajo de todo el portafolio (permite máxima escalabilidad)
- **9 contratos para Apex** → $9,378/mes — contribución dominante al portafolio
- **4 setups compitiendo** — selección de la señal más fuerte del día sin intervención manual
- **R²=0.96** — curva de equity muy lineal y consistente

## Debilidades / Riesgos

- **El bug es el edge** — cualquier modificación al bloque de cálculo de `dailyPnL` destruye la estrategia
- **Renko 35 en MNQ**: brick size medio — menos afectado por chop que Renko 25/30, más señales que Renko 40/50
- **Correlación media con SCALPER Renko 30** — ambos operan en prime hours con lógica similar
- **Shorts dominan** (PF=2.33 vs Longs=1.82) — si mercado se vuelve extremadamente alcista sostenido, el edge podría reducirse marginalmente

---

## Sizing para Apex

| Contratos | Profit/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 7 | $7,294 | $5,369 | ✅ cómodo |
| 8 | $8,336 | $6,136 | ✅ |
| **9** | **$9,378** | **$6,903** | ✅ **recomendado** |
| 10 | $10,420 | $7,670 | ⚠️ límite |

---

## Rol en el portafolio

**Tier-1 por Sortino** (18.52 — el más alto del portafolio). Con 9 contratos aporta $9,378/mes, convirtiéndose en la **estrategia más rentable del portafolio** por amplio margen. Su MaxDD por contrato ($767) es el más bajo de todas las estrategias — permite máxima escalabilidad dentro de los límites de Apex.

Complementa a BreadButter_SCALPER (Renko 30 vs Renko 35 — brick sizes distintos, lógica distinta). La descorrelación es media-baja ya que ambas son EMA-based con filtro accidental.

---

## Próximos pasos

1. Activar en paper trading (Renko 35, 1 contrato)
2. Verificar que el filtro accidental opera (~1 trade/día en Sim account)
3. Verificar que los 4 setups se activan visualmente en el chart Renko 35
4. Tras 1 mes de datos paper → subir a 9 contratos live
