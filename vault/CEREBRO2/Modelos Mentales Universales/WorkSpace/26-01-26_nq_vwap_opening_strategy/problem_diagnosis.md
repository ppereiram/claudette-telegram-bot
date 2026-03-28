# DIAGNÓSTICO DEL PROBLEMA: nq_vwap_opening_strategy

## Fecha y Hora
26 de enero de 2026

## Problema Declarado por Usuario
El usuario quiere pulir y automatizar una estrategia de trading para el NQ (Nasdaq Futures) en la apertura de NY (9:30 AM).
La estrategia se basa en la relación del precio con el VWAP.

## Tesis de la Estrategia (Observación Empírica)
1. **Reversión a la Media:** Si el precio abre/está "lejos" del VWAP -> Trata de volver a tocarlo.
2. **Continuación de Tendencia:** Si el precio está "cruzando" el VWAP -> Continúa en la dirección del cruce (no rebota).
3. **Frecuencia:** 1 trade al día.

## Restricciones Críticas (Risk Management)
- **Tamaño de cuenta:** $300,000
- **Max Drawdown (DD):** $7,500 (2.5% de la cuenta total).
- **Tolerancia:** Muy baja. Un error de racha negativa quema la cuenta.

## Estado Actual
- Nivel de confianza del usuario: "Altísimo" (basado en observación).
- Validación estadística: NULA (No backtesting).
- Definición de reglas: Vaga ("lejos", "cruzando").

## Tipo de Problema
- [x] Probabilístico (Gestión de incertidumbre)
- [x] Sistémico (Reglas de trading)
- [x] Psicológico (Disciplina vs. FOMO)
- [x] Económico (Gestión de capital/Drawdown)

## Mapa de Conocimiento
**Known Knowns:**
- El instrumento (NQ).
- La hora (9:30 AM NY).
- El indicador base (VWAP).

**Known Unknowns (A definir urgentemente):**
- Definición cuantitativa de "lejos" (¿Puntos? ¿Desviación estándar?).
- Definición de "cruce" (¿Cierre de vela? ¿Toque?).
- Timeframe de ejecución (¿1 min, 5 min?).
- Stop Loss y Take Profit definidos.

**Supuestos Críticos:**
- La observación del usuario tiene esperanza matemática positiva.
- La volatilidad de la apertura no generará slippage que destruya el R:R.
