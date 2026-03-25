# Insights sobre MNQ y NinjaTrader
> Patrones aprendidos a través del desarrollo y backtesting de estrategias

---

## Sobre el instrumento: MNQ

### Características fundamentales
- **Micro E-mini Nasdaq 100** — 1/10 del tamaño del NQ
- TickSize = 0.25 puntos | TickValue = $0.50 | PointValue = $2.00
- Horario principal: 9:30 AM — 4:00 PM ET (Regular Session)
- ETH (Extended Trading Hours): 6:00 PM — 9:30 AM siguiente día

### Comportamiento del instrumento

**1. MNQ es estructuralmente alcista**
El Nasdaq 100 ha tenido un sesgo alcista secular durante décadas. En el corto plazo intradía, esto se manifiesta como:
- Movimientos alcistas más graduales y sostenidos (difíciles de contrarrestar)
- Movimientos bajistas más rápidos y violentos (buenas para scalp short pero difíciles de mantener)
- Estrategias de short puro consistentemente underperforman vs estrategias de long o mixtas

**2. MNQ retrocede ~1.0x ATR comúnmente**
Este es el dato más importante para el sizing de stops. Cualquier stop menor a 1.0× ATR en MNQ resulta en stop-outs frecuentes por ruido normal:
- Stop < 0.5× ATR → muerte por stop-outs
- Stop 0.75× ATR → todavía muy ajustado
- Stop 1.0× ATR → mínimo viable
- Stop 2-3× ATR → más cómodo pero reduce R:R

**3. La apertura de NY (9:30-10:00) es la ventana de mayor volatilidad**
- El mayor volumen, los moves más rápidos y las tendencias más claras
- Alta probabilidad de establecer el mínimo o máximo del día en esta ventana
- Oportunidad: NYOpenBlast, OpeningRange — ambos explotan esta ventana
- Riesgo: slippage y spreads más amplios en los primeros segundos

**4. Prime hours tienen estadísticamente mejor edge**
- 9:00-9:30 AM: Pre-apertura, menor liquidez
- **9:30 AM-12:00 PM**: Prime AM — mejor edge para todo tipo de estrategias
- 12:00-1:30 PM: Almuerzo NY — menor actividad, más ruido
- **1:30-3:30 PM**: Prime PM — segundo bloque de actividad
- 3:30-4:00 PM: Cierre — actividad de reequilibrio, spreads más amplios

**5. Shorts outperforman longs en scalp/momentum, pero no en trend-following**
- En scalp (1-min, 5-min rápido): Shorts PF=1.45 vs Longs PF=1.21 (ULTRA)
- En trend-following (SuperTrend, Apex): Longs dominan claramente
- Explicación: los movimientos bajistas intradía son más rápidos y "limpios" para scalp. Los movimientos alcistas son más sostenidos para trend-following.

**6. El slippage importa más de lo que parece**
- Slippage=1 tick con 15 contratos = ~$15/round trip adicional
- En estrategias de alta frecuencia (>5 trades/día), el slippage puede erosionar un PF de 1.20 a 1.05
- Siempre backtest con slippage realista, especialmente en apertura de NY

---

## Sobre el desarrollo de estrategias

### Regla del PF con comisiones
**Nunca evaluar un sistema sin comisiones incluidas.** La diferencia puede ser enorme:
- VWAPPulse: PF=1.23 sin comm → 1.05 con comm (diferencia de 0.18)
- NYOpenBlast: PF=1.72 en condiciones ideales → 1.55 real → ~1.42 con comm

**Regla práctica**: Si el PF sin comisiones es < 1.30, el sistema probablemente no sobrevivirá comisiones reales en producción.

### El "filtro accidental" como principio de diseño
El descubrimiento en ULTRA y SCALPER reveló un principio importante: **limitar la frecuencia de trades puede ser un edge en sí mismo**. El primer trade del día tiende a ser el de mayor calidad — los subsecuentes son a menudo "perseguir el mercado".

Aplicación consciente: MaxTradesPerDay=1 en BreadButter_v5_Apex, MaxTradesPerDay limitado en casi todas las estrategias.

### La paradoja del trailing stop
Múltiples iteraciones de BreadButter mostraron que **el trailing stop puede destruir el edge de un sistema de alta R:R**:
- Con trailing: El precio llega cerca del target, el trailing sube, el precio retrocede ligeramente → sale con ganancia pequeña
- Sin trailing: El precio llega al target y sale → ganancia completa
- El trailing solo beneficia a sistemas donde el trade puede correr indefinidamente (SuperTrendWave, donde no hay target fijo)

### VWAP: la lección de "filtro vs trigger"
Una de las lecciones más caras del proyecto:
- VWAP como **filtro de sesgo** (¿está el precio del lado correcto?) → funciona, PF hasta 1.79
- VWAP como **trigger de entrada** (¿es este el momento exacto de entrar?) → no funciona, PF techo ~1.33 con alta varianza

La diferencia es conceptual: el VWAP mide el precio promedio institucional, pero eso no significa que el momento de cruzar el VWAP sea una señal precisa de entrada. Los cruces son ruidosos.

### Timeframes y ruido
| Timeframe | Observación |
|---|---|
| 1-min | Mucho ruido, requiere filtros muy precisos para evitar comisión drag |
| 2-min | Sweet spot para BreadButter_v5_Apex — menos ruido que 1-min, más señales que 5-min |
| 5-min | Mejor relación señal/ruido para la mayoría de setups |
| 15-min | Excelente para contexto de tendencia (filtro), no como timeframe de ejecución |
| 30-min+ | Solo para filtros de macro-régimen |
| Renko | Elimina ruido temporal, excelente para trend-following puro |

---

## Sobre NinjaTrader 8

### Patrones de implementación esenciales

**Cachear indicadores en `State.DataLoaded`, nunca en `OnBarUpdate`**:
```csharp
// CORRECTO:
else if (State == State.DataLoaded)
{
    ema = EMA(21);  // Se crea una vez
}

// INCORRECTO: crea una nueva instancia cada barra → memory leak + resultados incorrectos
protected override void OnBarUpdate()
{
    if (EMA(21)[0] > Close[0]) ...  // Problemático en algunos contextos
}
```

**Series secundarias requieren guardia obligatoria**:
```csharp
if (BarsInProgress != 0) return;  // Sin esto, OnBarUpdate se ejecuta para CADA series
```

**NinjaTrader cachea parámetros después de compilar**:
Después de modificar parámetros en el código, simplemente recompilar no actualiza los valores por defecto en el UI. Solución: quitar la estrategia y re-agregarla.

**`StopTargetHandling.PerEntryExecution`**:
Necesario cuando hay múltiples nombres de señal de entrada. Permite tener stops/targets diferentes por señal.

**`SetStopLoss` con `CalculationMode.Ticks`**:
El valor es en ticks (unidades), no en precio. Para MNQ:
```
1 punto = 4 ticks (TickSize = 0.25)
ATR en puntos / TickSize = ATR en ticks
```

**`Draw.Text` — usar solo el overload simple**:
```csharp
// CORRECTO:
Draw.Text(this, "tag", "texto", barsAgo, y, brush);

// PROBLEMÁTICO — no usar:
Draw.Text(this, "tag", "texto", barsAgo, y, brush, fontFamily, fontWeight);
```

---

## Sobre el proceso de investigación

### Lo que NO funciona para encontrar edge

1. **Copiar estrategias de YouTube** — invariablemente están curve-fitted o usan datos cherry-picked
2. **Hidden Markov Models (HMM)** — el concepto de régimen es válido, pero la implementación en Python para crypto no se traduce directamente a NinjaTrader/MNQ. El concepto de régimen sí es útil (→ ver Roadmap)
3. **Backtesting engine externo en Python** — útil para iteración rápida, pero el valor real está en replicar exactamente el modelo de ejecución de NinjaTrader (comisiones, slippage, gestión de órdenes)
4. **Estrategias que "se ven bien" en TradingView** — TradingView usa PineScript con backtesting simplificado. Los resultados rara vez coinciden con NinjaTrader real

### Lo que SÍ funciona

1. **Concepto institucional primero** — si puedes explicar por qué funciona desde la lógica del flujo de dinero grande, tiende a tener edge real
2. **PF con comisiones, siempre**
3. **R² como indicador de calidad** — una curva de equity con R²>0.90 tiene edge más consistente que una con PF alto pero R² bajo
4. **Muestra estadística suficiente** — <100 trades en 3 años (VWAPOrderBlock) tiene más incertidumbre que 692 trades (v5_Apex) aunque el PF de OB sea mayor
5. **Separar longs y shorts** para entender dónde está realmente el edge
6. **Backtest en 3+ años** — incluye al menos un bear market y un bull market para validez

### El indicador más valioso: Sortino Ratio

El Sortino ratio (retorno / desviación estándar downside) es superior al Sharpe para trading porque solo penaliza la volatilidad negativa:
- Sortino > 2.0 → excelente (BreadButter_v5_Apex: 2.14)
- Sortino 1.0-2.0 → bueno (ULTRA: 1.43)
- Sortino 0.5-1.0 → aceptable (NYOpenBlast: 0.89, SCALPER: 0.53)
- Sortino < 0.5 → preocupante
