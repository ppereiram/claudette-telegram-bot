# MNQ Momentum Scalper v1.1

## Resumen
Bot de scalping automatizado para **MNQ (Micro E-mini Nasdaq 100)** en NinjaTrader 8.
Estrategia de pullback en tendencia usando confluencia de VWAP + EMAs con gestion de riesgo dinamica basada en ATR y la **Regla 3-5-7** para position sizing.

---

## Filosofia (inspirada en Martin Luke & Kalamagi)
- **Perdidas pequenas, ganadores grandes** - TP1 asegura profit rapido, TP2 corre con trailing
- **Risk-first** - Daily loss limit, consecutive loss breaker, ATR-based stops
- **Sin emociones** - El bot respeta TODOS los stops, sin revenge trading, sin FOMO
- **Numeros y probabilidad** - Win rate del 40-50% es rentable con R:R de 2:1+
- **Regla 3-5-7** - 3% riesgo por trade, 5% exposicion maxima, 2.33:1 R:R minimo

---

## Regla 3-5-7 (v1.1)

El bot implementa la regla 3-5-7 para position sizing dinamico:

| Regla | Que hace | Implementacion |
|---|---|---|
| **3%** | Max riesgo por trade | `AccountRiskPercent = 3.0` - Calcula contratos automaticamente |
| **5%** | Max exposicion total | `MaxExposurePercent = 5.0` - Cap de seguridad |
| **7%** | Min profit target (R:R 2.0:1) | `MinRewardRiskRatio = 2.0` - TP2 se auto-ajusta |

### Ejemplo con cuenta de $5,000
```
Account:     $5,000
3% risk:     $150 max por trade
Stop:        12 ticks (3 pts) = $6/contrato
Contratos:   $150 / $6 = 25 → split 12+13 (TP1+TP2)
Exposicion:  $150 / $5,000 = 3% < 5% ✓
R:R check:   TP2 49t / Stop 12t = 4.08:1 > 2.33:1 ✓
```

### Position sizing dinamico
- El bot recalcula contratos en cada trade basado en equity actual
- Si ganas: equity sube → mas contratos (compounding)
- Si pierdes: equity baja → menos contratos (proteccion)
- Toggle `UseDynamicSizing = false` para usar contratos fijos

---

## Como funciona

### Entrada (Long)
```
1. TENDENCIA:    EMA 9 > EMA 21 > EMA 50
2. PULLBACK:     Low toca zona de VWAP o EMA 9
3. VELA FUERTE:  Close en top 30% del rango, arriba de EMA 9 y VWAP
4. RSI:          Entre 30-70 (no agotado)
5. VOLATILIDAD:  ATR > 4 ticks (hay movimiento)
```

### Entrada (Short)
Condiciones espejo: EMA 9 < 21 < 50, pullback arriba, vela bearish, etc.

### Salida
| Componente | Detalle |
|---|---|
| **TP1** | 1.5x ATR - Cierra 50% posicion |
| **Despues de TP1** | Stop se mueve a breakeven + 2 ticks |
| **TP2** | 2.5x ATR - Cierra el resto (R:R 2.0:1 minimo) |
| **Trailing Stop** | 0.8x ATR - Se activa despues de TP1 |
| **Stop Loss** | 1.2x ATR (minimo 8 ticks) |

### Proteccion diaria
- Max 8 trades por dia
- Stop despues de perder $150 en el dia
- Stop despues de 3 perdidas consecutivas
- Auto-flatten al final de sesion

---

## Instalacion en NinjaTrader 8

### Paso 1: Copiar el archivo
```
Copiar:  Strategies\MNQMomentumScalper.cs
Hacia:   C:\Users\[TU_USUARIO]\Documents\NinjaTrader 8\bin\Custom\Strategies\
```

### Paso 2: Compilar
1. Abrir NinjaTrader 8
2. `Tools` > `NinjaScript Editor`
3. Click derecho en la carpeta `Strategies` > `Compile`
4. Verificar que no haya errores en la ventana de output

### Paso 3: Aplicar a chart
1. Abrir chart de **MNQ** en timeframe de **2 minutos**
2. Click derecho en el chart > `Strategies` > `MNQMomentumScalper`
3. Configurar parametros si es necesario
4. **IMPORTANTE**: Primero probar en modo Sim o Replay

---

## Backtest

### Configuracion recomendada
- **Instrumento**: MNQ 03-26 (o el contrato activo)
- **Timeframe**: 2 minutos
- **Periodo**: Minimo 3 meses de datos
- **Slippage**: 1 tick
- **Commission**: Configurar segun tu broker (tipico $0.62/lado/contrato)

### Metricas clave a evaluar
- **Profit Factor** > 1.3 (idealmente > 1.5)
- **Max Drawdown** < 20% del capital
- **Win Rate** > 40% (con el R:R de la estrategia)
- **Avg Winner / Avg Loser** > 1.5
- **Sharpe Ratio** > 1.0

---

## Optimizacion

### Parametros mas importantes para optimizar
1. `StopLossATRMult` (rango: 1.0 - 2.5)
2. `TakeProfit1ATRMult` (rango: 0.5 - 2.0)
3. `TrailingStopATRMult` (rango: 0.5 - 2.0)
4. `PullbackToleranceTicks` (rango: 4 - 12)
5. `MinATRTicks` (rango: 4 - 10)

### Tips
- Optimizar de a 1-2 parametros a la vez, no todos juntos
- Usar Walk-Forward Analysis si es posible
- Cuidado con el overfitting: si funciona perfecto en backtest pero usa valores extremos, probablemente no funcione en vivo
- Los defaults estan pensados para ser robustos, no perfectos

---

## Ejemplo de trade tipico

### Long trade en tendencia alcista
```
09:42 AM | MNQ @ 21,450.50
  EMA9: 21,448  |  EMA21: 21,440  |  EMA50: 21,420
  VWAP: 21,445  |  RSI: 52  |  ATR: 3.50 pts (14 ticks)

ACCOUNT: $5,000 | 3% = $150 max risk
STOP:    21 ticks (1.5x ATR) = $10.50/contrato
SIZE:    $150 / $10.50 = 14 contratos → 7+7 (TP1+TP2)

ENTRY:  21,450.50 (14 contratos total)
STOP:   21,445.25 (21 ticks) → Riesgo: $147 (2.9% de cuenta)
TP1:    21,454.00 (14 ticks = 1.0x ATR) → +$49.00 (7 contratos)
TP2:    21,462.75 (49 ticks = 3.5x ATR) → +$171.50 (7 contratos)
R:R:    49/21 = 2.33:1 ✓

09:48 AM | TP1 HIT → +$49.00
  Stop movido a 21,451.00 (breakeven + 2 ticks)
  Trailing activado: 1.0x ATR = 3.50 pts

10:05 AM | Trailing stop hit @ 21,458.25
  TP2 parcial: +$54.25 (7 contratos x 7.75 pts x $2)

RESULTADO: +$103.25 total | Riesgo original: $147 | R:R efectivo = 0.70:1
(Nota: trailing salio antes de TP2, pero profit asegurado por breakeven)
```

---

## Riesgos y limitaciones
- **No predice noticias**: Eventos macro pueden causar gaps violentos
- **Mercado lateral**: En dias sin tendencia clara, la estrategia no entrara (esto es bueno)
- **Slippage en vivo**: Puede ser mayor que en backtest, especialmente en alta volatilidad
- **Datos historicos**: La calidad del backtest depende de la calidad de los datos

---

## Changelog
- **v1.3** - Balance: entrada vela fuerte (close top/bottom 30% del rango), stop 1.2x ATR (punto medio), TP2 2.5x ATR, MinRR 2.0. Busca equilibrio entre win rate (~50%) y ratio W/L (~1.2+)
- **v1.2** - Fix estructural: entrada con confirmacion 2 barras, stop 1.0x ATR, TP1 1.5x ATR, trailing 0.8x ATR. Resultado: ratio W/L 1.42 pero win rate cayo a 39% → -$1,958
- **v1.1** - Regla 3-5-7: Position sizing dinamico, exposure cap, R:R minimo 2.33:1, TP2 ajustado a 3.5x ATR. Resultado: 57% WR pero ratio 0.69 → -$1,100
- **v1.0** - Version inicial: VWAP + EMA pullback, ATR stops, partial exits, daily limits

## Roadmap futuro
- [ ] v1.2: Filtro de volumen (solo entrar con volumen por encima del promedio)
- [ ] v1.3: Multi-timeframe (confirmar tendencia en 15min)
- [ ] v1.4: Deteccion de rango vs tendencia (evitar chop automaticamente)
- [ ] v1.5: Dashboard en pantalla con metricas en tiempo real
- [ ] v2.0: Machine learning para ajustar parametros dinamicamente
