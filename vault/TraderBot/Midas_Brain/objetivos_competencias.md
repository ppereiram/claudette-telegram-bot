---
name: objetivos_competencias
description: Competencias de trading como objetivos de largo plazo para Midas — USIC y Darwin/X con contexto de mercado 2026
type: project
---

# Objetivos — Competencias de Trading

## Roadmap de competencias (orden cronológico)

| Etapa | Objetivo | Requisito previo |
|---|---|---|
| 2026 (ahora) | Paper trading + construcción brain | Datos reales suficientes |
| Mid-2026 | Apex funded account — track record real | Brain v2 operativo |
| 2027 | **Darwin/X** — capital externo gestionado | 6-12 meses track record verificable |
| 2027+ | **USIC** (US Investing Championship) | Track record Darwin/X validado |

---

## USIC 2026 — US Investing Championship
**Contacto:** Norm Zadeh, Ph.D. — norman@financial-competitions.com
**Web:** financial-competitions.com
**Acepta entradas tardías** — tracking desde cierre del día de entrada

**Contexto recibido (25/03/2026):**
- Solo el **20% de participantes** están en positivo tras 2 meses de 2026
- 2026 calificado como "dismal year" por el organizador
- El mercado 2026 es excepcionalmente difícil — no solo para Midas

**Por qué es relevante para el entrenamiento:**
- Midas está siendo entrenado en uno de los entornos más adversos en años
- Si el brain aprende a generar +EV en 2026, será robusto para cualquier mercado
- La data histórica de 2023-2024 (bull market tranquilo) puede no ser representativa del régimen actual
- **Ventaja:** La mayoría entrena con data pasada favorable. Midas entrena con el mercado más difícil.

---

## Darwin/X 2027
**Plataforma:** Darwinex — gestión de capital externo con track record verificable
**Métricas target:**
| Métrica | Mínimo | Ideal | Darwin/X |
|---|---|---|---|
| Sharpe | >1.0 | >1.5 | >2.0 |
| Sortino | >2.0 | >3.0 | >4.0 |
| MaxDD | <$7,000 | <$5,000 | <$4,000 |
| Profit/mes | >$2,000 | >$5,000 | >$8,000 |

---

## Nota crítica sobre la data de entrenamiento

> "Probablemente los 2-3 años de data del pasado no tengan mucho que ver con lo que ocurre hoy."
> — Pablo, 26/03/2026

**Implicación para Midas:**
- Los backtests de 2023-2024 se hicieron en un régimen bull con VIX bajo y tendencias claras
- El mercado de Q1 2026 tiene características distintas: gaps frecuentes, reversals violentos, breadth negativo (-3/3) con bounces intraday fuertes
- El Adversarial Regime Detector (B5-8) existe exactamente para detectar cuándo el régimen cambió
- El Markov de Midas debe ser entrenado principalmente con datos de 2026, no con históricos pre-2024
- **Ventaja competitiva real:** Si el 80% de traders pierde en este entorno y Midas aprende a operar en él, el edge vs. el mercado es mayor cuando el mercado se normalice

**How to apply:** Al entrenar RF y Markov en Abril, dar mayor peso (3x) a los datos de 2026 vs. datos históricos anteriores a 2025.
