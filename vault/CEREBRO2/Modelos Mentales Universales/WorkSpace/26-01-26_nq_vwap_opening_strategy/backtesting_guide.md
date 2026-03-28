# GUÍA DE BACKTESTING PROFESIONAL EN NINJATRADER 8

## Objetivo
Validar científicamente si tu estrategia `NQ_VWAP_Reversion_Bot` habría ganado dinero en el pasado y, más importante, si habría respetado tu límite de Drawdown de $7,500.

---

## PASO 1: PREPARACIÓN DE DATOS (CRÍTICO PARA VWAP)
El VWAP se calcula volumen por precio. Si usas datos de "fin de día" o datos de minuto simples, el cálculo será erróneo. Necesitas **Tick Replay**.

1.  Abre NinjaTrader 8.
2.  Ve a **Tools** -> **Options** -> **Market Data**.
3.  Asegúrate de que "Show Tick Replay" esté activado.
4.  Ve a **Tools** -> **Instrument Manager**. Busca `NQ` y asegúrate de que tienes el contrato actual mapeado.

---

## PASO 2: CONFIGURACIÓN DEL STRATEGY ANALYZER

1.  Ve a **New** -> **Strategy Analyzer**.
2.  En la derecha, bajo **Settings**:
    *   **Strategy:** Selecciona `NQ_VWAP_Reversion_Bot`.
    *   **Type:** `Backtest`.

### Parámetros de la Estrategia (Inputs):
    *   **Contracts:** 10 (Tu tamaño deseado).
    *   **StopLossTicks:** 100.
    *   **TargetTicks:** 100.
    *   **VwapSD:** 2.0.

### Data Series (CONFIGURACIÓN VITAL):
    *   **Instrument:** `NQ 03-26` (O el contrato futuro vigente).
    *   **Price based on:** `Last`.
    *   **Type:** `Minute`.
    *   **Value:** `5` (Tu timeframe).
    *   **Tick Replay:** **[X] CHECK (MARCAR OBLIGATORIAMENTE)**. *Sin esto, el backtest del VWAP es basura.*

### Timeframe (Período de Prueba):
    *   **Start Date:** Selecciona hace 3 meses (ej. `2025-10-26`).
    *   **End Date:** Hoy.
    *   **Trading Hours:** `Default 24/7` (o `US Equities RTH` si solo quieres sesión americana, pero el código ya filtra por hora).

3.  Haz clic en el botón **Run** (Abajo a la derecha).
    *   *Nota:* Con Tick Replay tardará un poco más en procesar.

---

## PASO 3: INTERPRETACIÓN DE RESULTADOS (LA PRUEBA DE FUEGO)

Una vez termine, verás una tabla. Ignora el dinero ganado por un momento. Ve a la pestaña **Summary** y busca estos 3 números asesinos:

### 1. Max Drawdown (Currency)
*   **Qué es:** La caída máxima desde el pico de tu cuenta.
*   **Tu Límite:** $7,500.
*   **Prueba:**
    *   Si dice `-$8,000` o más: **ESTRATEGIA REPROBADA**. Perderías la cuenta financiada.
    *   Si dice `-$4,000`: APROBADA (Estás dentro del límite).

### 2. Profit Factor
*   **Qué es:** (Ganancia Bruta / Pérdida Bruta).
*   **Meta:** Debe ser mayor a **1.3**.
    *   Si es < 1.0: La estrategia pierde dinero.
    *   Si es 1.0 - 1.2: Es "ruido", apenas cubres comisiones en la vida real.

### 3. Total Trades
*   **Qué es:** Número de operaciones.
*   **Meta:** Necesitas al menos 30 operaciones para que la estadística sea válida. Si solo hizo 3 trades en 3 meses y ganó dinero, es suerte, no sistema.

---

## PASO 4: OPTIMIZACIÓN (SI FALLA)

Si el backtest muestra pérdidas o un Drawdown gigante, no te desanimes. Usa el modo **Optimization** en lugar de Backtest.

1.  Cambia **Type** de `Backtest` a `Optimization`.
2.  En **StartMinute** (Parametros), en lugar de poner `30`, pon un rango:
    *   Min: `30`
    *   Max: `45`
    *   Increment: `5`
    *   *(Esto probará entrar a las 9:30, 9:35, 9:40, 9:45).*
3.  En **TargetTicks**:
    *   Min: `50`
    *   Max: `150`
    *   Increment: `25`
4.  Ejecuta. NinjaTrader probará miles de combinaciones y te dirá cuál funciona mejor matemáticamente.

---

## ADVERTENCIA FINAL: OVERFITTING
Si encuentras una configuración que gana millones en el pasado, **desconfía**.
A menudo, optimizamos tanto que creamos una estrategia que solo funciona "ayer" y fallará "mañana".
Busca parámetros que sean **estables** (ej. si funciona con 100 ticks, debería funcionar también con 90 y 110. Si solo funciona con 100 exactos, es suerte).
