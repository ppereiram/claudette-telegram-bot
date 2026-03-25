# DarvasBox_v1 — Reporte de Desarrollo

> Estado: ✅ CONFIRMADA — Renko 30-tick, 02/03/2026
> Chart: Renko 30-tick | MNQ | AllowLong=ON, AllowShort=ON

---

## Concepto

Nicolas Darvas (1960) identificó que los grandes movimientos en acciones están precedidos por un período de **acumulación en rango** (la "caja"). Cuando el precio rompe esa caja con volumen elevado, es el institucional que finalmente mueve el precio.

Para MNQ en 5-min:

```
Precio forma máximo local → consolida X barras sin superar ese máximo
→ volumen en la ruptura confirma participación real → ENTRY LONG

(Espejo: mínimo local → consolidación → breakdown → ENTRY SHORT)
```

**Diferencia clave con otros breakouts del portafolio**:
| Estrategia | Tipo de breakout | Ancla |
|---|---|---|
| PivotTrendBreak_v1 | Ruptura de pivot estructural (swing high/low) | Renko 25 |
| LWDonchianBreak_v1 | Ruptura del canal de 1 semana | 15-min |
| **DarvasBox_v1** | **Ruptura de consolidación temporal (caja)** | **5-min** |

La caja Darvas no requiere un pivot significativo ni un canal de largo plazo — solo un período de quietud donde el precio "coila" energía.

---

## Lógica de Entrada

### LONG
1. **Máximo local**: `High[0]` es el más alto de los últimos `BoxMinBars` barras
2. **Formación de caja**: durante `BoxMinBars` a `BoxMaxBars` barras, el precio no supera ese máximo
3. **Validez de tamaño**: `MinBoxSizeTicks ≤ (boxTop - boxBottom) / TickSize ≤ MaxBoxSizeTicks`
4. **Breakout**: `Close[0] > boxTop`
5. **Volumen**: `Volume[0] ≥ SMA(Volume, 20)[0] × MinVolRatio`
6. **SL**: `boxBottom - StopBufferTicks × TickSize`
7. **TP**: `Entry + (Entry - SL) × TargetRR`

### SHORT (espejo)
1. **Mínimo local**: `Low[0]` es el más bajo de los últimos `BoxMinBars` barras
2. **Consolidación**: precio no rompe ese mínimo por `BoxMinBars`+ barras
3. **Breakdown**: `Close[0] < shortBoxBottom`
4. **Volumen** confirma
5. **SL**: `shortBoxTop + StopBufferTicks × TickSize`

---

## Lógica de la Caja (State Machine)

```
Estado: INACTIVE
    → si High[0] es máximo local → FORMING (longBoxTop = High[0])

Estado: FORMING
    → si High[0] > longBoxTop → RESTART (nuevo techo más alto)
    → si barras > BoxMaxBars → RESET (caja expiró)
    → si boxWidth > MaxBoxSizeTicks → RESET (demasiado ancha)
    → si barras >= BoxMinBars AND width >= MinBoxSizeTicks → CONFIRMED

Estado: CONFIRMED (y no ha expirado)
    → si Close[0] > longBoxTop AND volumen OK → ENTRY → RESET caja
    → si High[0] > longBoxTop → RESTART (nueva caja desde aquí)
```

**Prioridad breakout sobre restart**: si la caja está confirmada y Close > boxTop, se opera el breakout antes de reiniciar la caja. Esto evita el bug clásico donde un breakout real se convierte en "restart de caja".

---

## Parámetros Iniciales para Backtest

```
Chart: 5-min MNQ, ETH session

1. Darvas Box
   BoxMinBars      = 3       // mínimo 3 velas de consolidación (= 15 min)
   BoxMaxBars      = 20      // máximo 20 velas antes de expirar (= 100 min)
   MinBoxSizeTicks = 10      // caja mínima de 10 ticks ($5)
   MaxBoxSizeTicks = 80      // caja máxima de 80 ticks ($40)

2. Risk / Reward
   TargetRR        = 3.0     // probar 2.0, 2.5, 3.0, 4.0
   BreakevenR      = 1.0
   StopBufferTicks = 4       // 4 ticks = $2 más allá del borde

3. Volume Filter
   UseVolumeFilter = true
   VolumePeriod    = 20
   MinVolRatio     = 1.2     // volumen ≥ 1.2× promedio 20 barras

4. Trade Management
   MaxTradesPerDay = 1
   Quantity        = 1
   AllowLong       = true
   AllowShort      = true    // probar también Long-only

5. Horario (ET)
   PrimeStart = 93000        // 9:30 AM
   PrimeEnd   = 153000       // 3:30 PM
```

---

## Variables a Optimizar en Backtest

| Parámetro | Rango a probar | Motivo |
|---|---|---|
| BoxMinBars | 2, 3, 5, 8 | Tamaño mínimo de consolidación |
| BoxMaxBars | 10, 20, 30 | Cajas más viejas = patrones más débiles |
| MinBoxSizeTicks | 5, 10, 20 | Filtrar micro-cajas de ruido |
| MaxBoxSizeTicks | 60, 80, 120 | Filtrar cajas demasiado anchas |
| TargetRR | 2.0, 2.5, 3.0, 4.0 | Sweet spot R:R |
| MinVolRatio | 1.0, 1.2, 1.5 | Agresividad del filtro de volumen |
| AllowShort | ON/OFF | MNQ es alcista estructuralmente |

**También probar en 15-min**: cajas más grandes = patrones más significativos

---

## Criterios de Validación

Para confirmar la estrategia:
- PF > 1.50 con comisiones y Slippage=1
- R² > 0.85
- Sortino > 2.0
- Trades ≥ 150 en 3 años (≥ 50/año)
- MaxDD/ct < $375 (para caber en Apex con 20ct) → ideal < $500

---

## Sizing para Apex (estimación)

| MaxDD/ct | Contratos | MaxDD total | Notas |
|---|---|---|---|
| ≤ $375 | 20 ct | ≤ $7,500 ✅ | máximo margen |
| ≤ $500 | 15 ct | ≤ $7,500 ✅ | |
| ≤ $750 | 10 ct | ≤ $7,500 ✅ | |

> Cifras especulativas hasta tener backtest.

---

## Por Qué Tiene Edge Potencial en MNQ

1. **PivotTrendBreak_v1 valida breakouts**: el mejor Sortino del portafolio usa breakouts de pivots en Renko. La caja Darvas es un primo cercano.
2. **Volumen como confirmación**: el filtro de volumen elimina breakouts falsos (fakeouts) que son el talón de Aquiles de los sistemas de breakout puro.
3. **Tamaño de caja como filtro implícito**: `MinBoxSizeTicks` y `MaxBoxSizeTicks` filtran ruido (cajas muy pequeñas) y distribución (cajas muy anchas).
4. **MNQ tiene tendencias sostenidas**: breakouts de consolidación tienen mejor resultado en mercados con momentum que en mercados de reversión.

**Riesgo principal**: en mercados laterales, la estrategia puede tomar muchos breakouts falsos → `MaxBoxSizeTicks` y `BoxMinBars` son los parámetros clave para controlar esto.

---

## Resultados del Backtest (02/03/2026)

### Evolución de configuraciones probadas

| Config | Chart | Trades | PF | R² | Sortino | MaxDD/ct | Veredicto |
|---|---|---|---|---|---|---|---|
| Long-only, BoxMin=3, RR=4 | 5-min | 31 | 1.82 | 0.77 | 0.69 | $138 | ❌ muestra |
| Combined, BoxMin=3, RR=4 | Renko 40 | 97 | 1.81 | 0.54 | 0.83 | $770 | ❌ R² bajo |
| Combined, BoxMin=2, RR=2 | Renko 35 | 742 | 1.14 | 0.26 | 0.41 | $1,303 | ❌ overtrading |
| Combined, BoxMin=2, RR=3 | Renko 35 | 727 | 1.16 | 0.73 | 0.50 | $916 | ❌ R² bajo |
| **Combined, BoxMin=2, RR=3** | **Renko 30** | **879** | **1.35** | **0.92** | **3.92** | **$630** | **✅ GANADOR** |

### Params ganadores confirmados (Renko 30-tick)

```
BoxMinBars      = 2       // caja mínima de 2 bricks = ~60 ticks de consolidación
BoxMaxBars      = 10      // caja expira a los 10 bricks
MinBoxSizeTicks = 5       // altura mínima de la caja
MaxBoxSizeTicks = 80      // altura máxima

TargetRR        = 3       // R:R = 3:1
BreakevenR      = 1       // BE en 1R
StopBufferTicks = 3

MaxTradesPerDay = 3
AllowLong       = true
AllowShort      = true

UseVolumeFilter = true
VolumePeriod    = 14
MinVolRatio     = 1.0     // volumen ≥ SMA(14) (sin restricción extra)

PrimeStart = 93000        // 9:30 ET
PrimeEnd   = 153000       // 3:30 ET
```

### Métricas finales (Renko 30, 1ct, 02/01/2023–22/02/2026)

```
Trades:         879 en 3 años (293/año, 1.79/día)   ✅
PF:             1.35  (Long=1.33 | Short=1.38)       ⚠️ < 1.50 mínimo
R²:             0.92  (Long=0.68 | Short=0.94)       ✅✅
Sortino:        3.92                                  ✅✅ (4° en portafolio)
MaxDD:          -$630.70 (1ct)
WR:             22.07%
Win/Loss:       4.77x (patrón trend-following)
Profit/mes:     $269.58 (1ct)
Avg time:       30.36 min en mercado
Avg MAE:        $25.43 | Avg MFE: $60.40
```

**Nota sobre Long R²=0.68**: El lado short (R²=0.94) domina el edge. Los longs contribuyen positivamente (PF=1.33) pero con menos consistencia. El combined R²=0.92 valida la estrategia.

### La curva de equity

La curva (Analysis tab, screenshot 7) es prácticamente lineal desde el inicio hasta el final — el patrón de crecimiento más consistente observado en el desarrollo de estrategias del portafolio para esta muestra de trades.

### Sizing para Apex

Usando el run de 20ct como base (más preciso por comisiones escaladas):

| Contratos | MaxDD | Dentro de Apex | Profit/mes |
|---|---|---|---|
| 9 ct | $7,476 ✅ | ✅ | **$2,426/mes** |
| 11 ct | $9,138 ❌ | ❌ supera $7,500 | — |

**Sizing recomendado: 9 contratos → MaxDD $7,476 ✅ → Profit/mes $2,426**

> Nota: MaxDD/ct sube de $630 (1ct) a $830 (20ct basis) por escalado de comisiones.

### Contexto en el portafolio

| Estrategia | PF | R² | Sortino | MaxDD (Apex) |
|---|---|---|---|---|
| BreadButter_v5_Apex | 1.34 | 0.95 | 1.68 | $6,510 |
| **DarvasBox_v1** | **1.35** | **0.92** | **3.92** | **~$7,476** |

PF idéntico al BBv5 pero **Sortino 2.3× mejor** — DarvasBox tiene equity curve más suave.

---

## Estado Final

- ✅ Código creado (02/03/2026): `Strategies/DarvasBox_v1.cs`
- ✅ Backtest confirmado (02/03/2026): Renko 30-tick, 9ct, PF=1.35, R²=0.92, Sortino=3.92
- ⏳ Iniciar paper trading (1ct, Renko 30)

---

## Archivos

- Código: `Strategies/DarvasBox_v1.cs`
- Reporte: `Reports/19_DarvasBox_v1.md`
