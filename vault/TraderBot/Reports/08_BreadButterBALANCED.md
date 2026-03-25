# BreadButterBALANCED
> Edge de competición long/short | `Strategies/BreadButterBALANCED_v2.1.cs`

---

## Resumen ejecutivo

| Métrica | Valor |
|---|---|
| Profit Factor (combinado) | **1.31** |
| PF Longs solo | ~1.06 |
| PF Shorts solo | ~0.97 |
| Estado | ⚠️ Experimental — no en producción |

---

## El Edge Inusual

Esta estrategia tiene un comportamiento estadístico que no existe en ninguna otra del portafolio: **el edge desaparece cuando se separan longs y shorts**.

| Configuración | PF |
|---|---|
| Solo Longs | ~1.06 |
| Solo Shorts | ~0.97 |
| **Combinados (BALANCED)** | **1.31** |

Esto es contraintuitivo: ¿cómo puede la combinación de dos sistemas mediocres producir algo rentable?

### Explicación del fenómeno

El "filtro accidental" de `dailyPnL` limita a **1 trade efectivo por día**. Cuando ambas señales (long y short) están activas, compiten por ese "slot" del día. El sistema entra con la primera señal que aparezca.

La competición implícita actúa como un **filtro de selección**:
- Si aparece primero una señal long → entra long
- Si aparece primero una señal short → entra short
- La señal que aparece primero en una dirección dada tiende a ser la más "fuerte" del día

**El resultado**: el sistema toma el trade de mayor probabilidad del día sin poder predecir explícitamente cuál será. Es un form de **selección por timing natural** del mercado.

---

## Por qué es interesante conceptualmente

La idea de que **dos sistemas mediocres combinados forman algo mayor** tiene implicaciones:
1. La correlación negativa entre señales long y short crea valor
2. La limitación a 1 trade/día concentra el riesgo en la señal más temprana (que tiende a ser la de mayor momentum)
3. Ningún otro sistema del portafolio explota esta dinámica de competición

---

## Por qué no está en producción

1. **PF=1.31** — sin el filtro accidental, el PF colapsa. La estrategia depende completamente de un bug
2. **R² desconocido** — no se ha documentado la linealidad de la curva
3. **Solapamiento** — comparte timeframe y horario con SCALPER y ULTRA
4. **Fragmentación del análisis** — necesita más estudio antes de confiar en ella
5. **Slippage=0 corregido** — el backtest original tenía `Slippage = 0`. Código actualizado a `Slippage = 1` el 26/02/2026. El PF=1.31 podría ser inferior con slippage correcto — requiere re-backtest antes de cualquier consideración.

---

## Estado: Preservada como experimento

El archivo `BreadButterBALANCED_v22.cs` se mantiene en NT8 como referencia. El concepto de "competición de señales por slot diario" podría inspirar mejoras en otras estrategias, pero BALANCED en sí misma no es candidata inmediata para producción.
