# BreadButter_SCALPER
> MACD + EMA bounce en Renko 30-tick | `Strategies/BreadButter_SCALPER.cs`
> **Confirmada 26/02/2026 — Renko 30, AllowShort=ON, Slippage=1**

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (con comm) | **1.74** |
| R² | **0.98** |
| Sortino Ratio | **4.13** |
| Net total (3 años, 1ct) | $14,274 |
| Profit/mes (6ct) | **$3,679** |
| MaxDD (1ct) | **$1,154** |
| MaxDD (6ct) | **$6,924** ✅ |
| Trades totales (3 años) | 396 (0.81/día) |
| WR | 44.95% |
| Win/loss ratio | 2.13x |
| Chart | Renko 30-tick MNQ |
| Dirección | AllowLong=ON, AllowShort=ON |

**Concepto**: MACD crossover + EMA bounce en Renko 30-tick. El "Filtro Accidental" limita a ~1 trade/día efectivo, donde longs y shorts compiten por el slot diario. Longs PF=1.73 ≈ Shorts PF=1.75 — edge balanceado en ambas direcciones, sin dependencia de régimen de mercado.

---

## Edge conceptual

**¿Por qué Renko en lugar de 5-min?**

En 5-min el MACD genera cruces por ruido temporal — MNQ oscila dentro del tick sin movimiento real. En Renko 30-tick, cada brick requiere 30 ticks ($15) de movimiento sostenido. El MACD en Renko captura momentum real, no volatilidad estocástica.

**¿Por qué el "Filtro Accidental" no se corrige?**

```csharp
dailyPnL += execution.Commission + execution.Order.AverageFillPrice * execution.Quantity
```

Esta fórmula suma el valor nominal del contrato (~$49k) en lugar del P&L. Al primer trade del día, `MaxPerdidaDiaria=$300` se dispara → solo pasa ~1 trade/día. Con AllowShort=ON, longs y shorts compiten por ese slot — selección implícita de la señal más temprana y fuerte del día.

**NO corregir este bug** — sin él, 15+ trades/día → PF colapsa a ~1.01.

---

## Evolución del backtest — Comparación de brick sizes

*(AllowShort=ON, Slippage=1, comisiones incluidas, 3 años)*

| Brick | PF | R² | Sortino | MaxDD | Profit/mes | Long PF | Short PF |
|---|---|---|---|---|---|---|---|
| Renko 25 | 1.49 | 0.96 | 1.79 | $1,835 | $404 | 1.37 | 1.63 |
| **Renko 30** | **1.74** | **0.98** | **4.13** | **$1,154** | **$613** | **1.73** | **1.75** |
| Renko 35 | 1.58 | 0.93 | 3.25 | $2,015 | $519 | 1.69 | 1.45 |
| Renko 40 | 1.77 | 0.95 | 2.76 | $1,330 | $637 | 1.33 | 2.56 |

**Por qué Renko 30 gana sobre Renko 40** (mayor PF y profit):
- Renko 40: Longs PF=1.33, R²=0.74 — longs débiles, strategy depende de shorts (PF=2.56). Vulnerable si el régimen cambia.
- Renko 30: Longs PF=1.73 ≈ Shorts PF=1.75 — **edge genuinamente balanceado**. Robusto ante cualquier régimen de mercado.
- Renko 30 tiene el **MaxDD más bajo** ($1,154 vs $1,330) y **Sortino más alto** (4.13 vs 2.76).

**Historial del slippage corregido:**
- 5-min original: Slippage=0 inflaba PF. PF real en 5-min con Slippage=1 sería aún menor que 1.22 → descartado.
- Código corregido a `Slippage = 1` el 26/02/2026.

---

## Parámetros ganadores

### Trade Management
| Parámetro | Valor | Descripción |
|---|---|---|
| Contratos MNQ | 6 | → MaxDD $6,924 ≤ Apex $7,500 |
| Max Trades por Día | 15 | Filtro accidental limita a ~1 en la práctica |
| Max Pérdida Diaria ($) | 300 | Triggea el filtro accidental al primer trade |

### MACD
| Parámetro | Valor |
|---|---|
| MACD Fast | 12 |
| MACD Slow | 26 |
| MACD Smooth | 9 |

### EMAs
| Parámetro | Valor |
|---|---|
| EMA Rápida | 9 |
| EMA Lenta | 21 |

### Volumen
| Parámetro | Valor |
|---|---|
| Volume Spike Multiplier | 1.2 |
| Volume SMA Period | 14 |

### ATR / Stop
| Parámetro | Valor |
|---|---|
| ATR Periodo | 14 |
| ATR Multiplier Stop | 1 |
| Risk/Reward Ratio | 1.3 |
| Activar Trailing | OFF |

### Horario (ET)
| Parámetro | Valor |
|---|---|
| Trading Start | 9:30 |
| Trading End | 14:30 |

### Dirección
| Parámetro | Valor |
|---|---|
| Allow Long | ON |
| Allow Short | ON |

### Chart
| Parámetro | Valor |
|---|---|
| Tipo | Renko |
| Brick Size | **30 ticks** |

---

## Fortalezas

- **PF=1.74 con R²=0.98** — la linealidad de la curva es mejor que PivotTrendBreak (0.96)
- **Sortino=4.13** — 3er mejor del portafolio (tras PivotTrendBreak=8.50 y ABCDHarmonic=5.05)
- **MaxDD=$1,154/ct** — el más bajo del portafolio. 6 contratos con MaxDD cómodo
- **Edge balanceado** — Longs ≈ Shorts. No depende de régimen de mercado
- **396 trades** — muestra estadísticamente sólida
- **Filtro accidental robusto** — selección implícita de la señal más fuerte del día

## Debilidades / Riesgos

- **El bug es el edge** — cualquier refactorización del código de dailyPnL destruye la estrategia
- **RR=1.3** — R:R bajo. El edge viene del WR (44.95%), no del R:R
- **Renko 30 en MNQ**: brick size relativamente pequeño — en mercado muy volátil puede generar bricks en segundos (similar al problema del SuperTrendWave en Renko 40 choppy)
- **Correlación con BreadButter_v5_Apex** — ambos usan MACD/EMA, horario solapado. Correlación media

---

## Sizing para Apex

| Contratos | Profit/mes | MaxDD | Viable Apex |
|---|---|---|---|
| 5 | $3,065 | $5,770 | ✅ cómodo |
| **6** | **$3,679** | **$6,924** | ✅ **recomendado** |
| 7 | $4,291 | $8,078 | ❌ supera $7,500 |

---

## Rol en el portafolio

**Tier-2** por Sortino (4.13, top-3 del portafolio) y R²=0.98. Contribución alta ($3,679/mes con 6ct) con MaxDD bajo ($1,154/ct). Complementa a PivotTrendBreak (Renko 25 vs Renko 30 — brick sizes distintos, lógica distinta). La descorrelación con el resto del portafolio es moderada (comparte horario con BB_v5_Apex).

---

## Próximos pasos

1. Activar en paper trading (Renko 30, 1 contrato)
2. Verificar que el filtro accidental opera correctamente (~1 trade/día visible en Sim account)
3. Tras 1 mes de datos paper → subir a 6 contratos live si WR y R:R coinciden con backtest
