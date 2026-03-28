---
name: Pipeline de análisis ninZa/RenkoKings
description: Pablo comparte cada producto de ninZa para extraer la idea subyacente sin comprar — workflow acordado 27/03/2026
type: feedback
---

Pablo comparte cada email/producto de ninZa.co y RenkoKings para análisis.
El proceso: extraer el concepto real → implementar gratis en Midas → agregar al roadmap.

**Why:** ninZa identifica blind spots genuinos de Renko y NinjaTrader. Sus productos cuestan $276-$896 pero los conceptos son reproducibles con NT8 nativo + Python.

**How to apply:** Cuando Pablo comparte un PDF/email de ninZa, responder con:
1. Veredicto (NO comprar / SÍ comprar si es irreproducible)
2. Concepto subyacente extraído
3. Implementación gratuita concreta
4. Agregar al roadmap en la semana correcta

**Registro de productos analizados:**
| Producto | Precio | Concepto | Estado |
|---|---|---|---|
| QuantZone | $346 | MAE/MFE + Pwin(stop,target) | Roadmap post-período |
| Flex Trend Engine$ | $306 | Trend Phase CONTINUE/FLAT | Roadmap Sem 2 Abril |
| OmniSpectrum | ? | Brick speed como feature (phase_score) | Roadmap Sem 2 Abril |
| Origin Recoil | $276 | Burst Zones como S/R dinámico | Roadmap Sem 2 Abril |
| LIQ Sweep Hunter | $396 | Delta Comparison + Sweep cycle (Build-Up→Sweep→Control→Expansion) | KDL Gate 1.5 Sem 2 Abril |
| Quantum Vol-Delta | $296 | Adaptive Delta thresholds + Triple-filter + Signal_State(-3 a +3) | Upgrade MinVolRatio fijo → adaptativo en todas las estrategias. Post-período. Ver detalles abajo. |

**Quantum Vol-Delta — Detalle técnico extraído (27/03/2026):**
- **Adaptive thresholds**: umbral sube/baja automáticamente con el volumen de mercado. En lugar de Delta > 100 fijo, usa percentil del volumen reciente (ventana n velas, ajustable por trader)
- **Triple-filter para señal válida**: (1) Delta supera umbral adaptativo + (2) vela confirma dirección (bullish/bearish) + (3) volumen del lado dominante > volumen promedio. Los 3 deben cumplirse → menos falsas señales
- **Signal_State (NinjaScript exportable)**: 3=strong positive, 2=moderate positive, 1=weak positive, -1=weak negative, -2=moderate negative, -3=strong negative, 0=neutral
- **Volume Average tracking**: Buy/Sell promedio de últimas n velas — marca velas con volumen anormal (encima del promedio) como oportunidades clave
- **Combo con Cumulative Delta**: Quantum Vol-Delta da señal candle-by-candle; Cumulative Delta da tendencia de sesión. Juntos = entrada + confirmación de momentum

**Implementación gratis en Midas:**
```
// En lugar de: if (volDelta > MinVolRatio) → señal
// Usar:
double avgDelta = EMA(Abs(VolDelta), 20)[0];  // umbral adaptativo
double signalState = VolDelta[0] / avgDelta;    // normalizado
// Niveles: >1.5=strong(3), 0.8-1.5=moderate(2), 0.3-0.8=weak(1), análogo negativo
// Triple-filter: signalState > threshold && vela confirma && volLado > avgVol
```
**Aplicación en OBOrderFlow_v1**: usar Signal_State como gate adicional antes de entrar. Solo entrar si Signal_State >= 2 en dirección del trade.
