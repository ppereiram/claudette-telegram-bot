# PivotReverse_v1
> Complemento de PivotTrendBreak — Doble Techo / Doble Piso estructural | `Strategies/PivotReverse_v1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Estado | ⚠️ En optimización — params pendientes de confirmar |
| Primer backtest (MinRR=1, 20ct) | PF=1.36, R²=0.86, Sortino=0.62, MaxDD=$11,980 |
| Problema detectado | Long R²=0.61 — doble pisos en Renko generan señales débiles |
| Chart | Renko 25-tick MNQ |
| Relación con PivotTrendBreak | **Estrategia complementaria** — reversal vs momentum |

---

## Concepto y edge

### Doble Techo / Doble Piso Estructural

Mientras PivotTrendBreak opera **breakouts** (precio rompiendo un pivot), PivotReverse opera **reversiones** (precio fallando en superar un pivot anterior).

**Doble Techo → SHORT**:
1. Se forma Pivot High 1 (ph1)
2. Precio retrocede hasta un Intermediate Low (IL)
3. Precio sube de nuevo pero **no supera ph1** → se forma ph2 < ph1
4. Precio rompe por debajo del IL → confirmación del doble techo
5. SHORT en el break del IL, SL en ph2, TP = TargetRR × riesgo

**Doble Piso → LONG**:
1. Se forma Pivot Low 1 (pl1)
2. Precio sube hasta un Intermediate High (IH)
3. Precio baja de nuevo pero **no perfora pl1** → se forma pl2 > pl1
4. Precio rompe por encima del IH → confirmación del doble piso
5. LONG en el break del IH, SL en pl2, TP = TargetRR × riesgo

### Relación con PivotTrendBreak

| | PivotTrendBreak | PivotReverse |
|---|---|---|
| Señal | Precio rompe pivot | Precio falla en superar pivot anterior |
| Dirección | Con la tendencia | Contra la tendencia reciente (reversal) |
| Setup | Breakout | Double top/bottom |
| Mercado ideal | Trending | Rangos y reversiones |

---

## Primer backtest — Análisis (24/02/2026)

**Parámetros usados**: MinRR=1, 20ct, Renko 25-tick

| Métrica | All | Longs | Shorts |
|---|---|---|---|
| PF | 1.36 | débil | mejor |
| R² | 0.86 | 0.61 ❌ | 0.75 |
| Sortino | 0.62 | bajo | mejor |
| MaxDD (20ct) | $11,980 ❌ | — | — |

**Problemas identificados**:
1. **MinRR=1 fue un error** — el valor correcto del código es 1.5. Con MinRR=1 se aceptan trades de baja calidad
2. **Long R²=0.61** — los Doble Pisos en Renko MNQ generan señales inconsistentes (mercado alcista prefiere reversal bajista, no alcista)
3. **MaxDD demasiado alto** — consecuencia directa del MinRR bajo + longs débiles

---

## Optimizaciones pendientes

### Prueba 1 — Params correctos
```
MinRR = 1.5 (restaurar default)
AllowLong = ON
AllowShort = ON
```
Esperado: reducir trades de baja calidad, mejorar R²

### Prueba 2 — Shorts only
```
AllowLong = OFF
AllowShort = ON
```
Motivación: R²=0.75 para shorts vs 0.61 para longs. Los Doble Techos tienen más edge en MNQ (mercado alcista = reversiones bajistas más violentas)

### Prueba 3 — Brick size diferente
```
Renko 35 o Renko 40
```
Motivación: Bricks más grandes = pivots más significativos = menos falsos doble techos

---

## Estado actual

- **Código**: creado y compilado ✅
- **Params**: Quantity=1 (pendiente ver MaxDD final para sizing)
- **Backtest ganador**: pendiente — necesita pruebas con MinRR=1.5 y AllowLong=OFF
- **Sizing Apex**: a determinar después de confirmar MaxDD/ct

---

## Por qué tiene potencial

PivotTrendBreak demostró que los pivots estructurales en Renko 25-tick tienen edge genuino en MNQ. PivotReverse usa el mismo framework pero explota el patrón complementario: cuando el precio **falla** en un pivot en lugar de romperlo.

En mercados con tendencia alcista fuerte (como MNQ 2023-2026), los Doble Techos tienden a ser más confiables que los Doble Pisos porque el mercado "lucha" más para revertir la tendencia principal.

---

## Próximos pasos

1. Backtest con MinRR=1.5, AllowLong=OFF (shorts only)
2. Si PF>1.4 y R²>0.75 → confirmar sizing
3. Si no mejora → considerar mayor brick size (Renko 35-40)
4. Publicar resultados aquí una vez confirmados
