# LOGICA DE AUTOMATIZACIÓN (NINJATRADER 8 / C#)

## Objetivo
Crear una estrategia totalmente automatizada (NinjaScript) que elimine la intervención emocional del usuario.

## Parámetros de Entrada (Optimizables)
- `StartTime`: 09:30 AM (Hora NY - Ajustable según zona horaria local).
- `EndTime`: 10:00 AM (Ventana operativa limitada para evitar sobre-operar).
- `Contracts`: 10 (Cantidad fija, aunque se recomienda lógica de gestión de riesgo).
- `TargetTicks`: 100.
- `StopTicks`: 100.
- `VWAP_SD`: 2.0 (Desviaciones estándar para considerar "lejos").

## Lógica de Ejecución (Máquina de Estados)

### Estado 1: Espera (Pre-Market)
- Si `Time < StartTime`: No hacer nada. Calcular VWAP y Bandas en segundo plano.

### Estado 2: Monitoreo (Ventana Operativa)
- Si `Time >= StartTime` AND `Time <= EndTime` AND `No Trades Taken Today`:
  - Calcular `UpperBand = VWAP + (SD * StDev)`.
  - Calcular `LowerBand = VWAP - (SD * StDev)`.
  
  **Condición de VENTA (Reversión Bajista):**
  - Si `Close[0] > UpperBand` (Precio cierra por encima de la banda superior).
  - O Si `High[0] >= UpperBand` (Toque).
  - Acción: `EnterShort(Contracts)`.
  
  **Condición de COMPRA (Reversión Alcista):**
  - Si `Close[0] < LowerBand` (Precio cierra por debajo de la banda inferior).
  - O Si `Low[0] <= LowerBand` (Toque).
  - Acción: `EnterLong(Contracts)`.

  **Condición de CRUCE (Continuación - Opcional/Complejo):**
  - *Nota:* Para la primera versión, nos centraremos en la reversión desde bandas extremas, ya que es más objetiva que "cruzar con fuerza".

### Estado 3: Gestión del Trade (ATM Strategy)
- Una vez dentro, el código NO toma decisiones. Deja que el ATM (SL/TP) maneje el resultado.
- `SetStopLoss(CalculationMode.Ticks, StopTicks)`.
- `SetProfitTarget(CalculationMode.Ticks, TargetTicks)`.
- **Regla de Oro:** `EntriesPerDirection = 1`. Solo 1 trade al día. Ganar o perder y apagar.

### Estado 4: Cierre (Post-Trade)
- Si `Position.MarketPosition != MarketPosition.Flat`: Esperar cierre.
- Si ya se operó hoy: No hacer nada hasta mañana.

## Prevención de Errores (Safety)
- **Daily Loss Limit:** Si PnL < -$600, detener estrategia (Safety switch adicional al Stop Loss).
- **Time Filter:** No abrir posiciones después de las 10:00 AM.
