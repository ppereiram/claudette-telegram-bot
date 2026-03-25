(vol-targeting + fixed risk)
---
double riskDollars = 650;                    // 8.6% del DD buffer (mi número favorito)
double stopPoints = 40;                      // ejemplo: 40 puntos stop en NQ
double contractValuePerPoint = 20;
int positionSize = (int)(riskDollars / (stopPoints * contractValuePerPoint));

// Vol-targeting adicional (mejor que fixed)
double dailyVolTarget = 0.75; // % de volatilidad diaria objetivo del portafolio
double atr14Percent = ATR(14)[0] / Close[0] * 100;
int volSize = (int)((dailyVolTarget / atr14Percent) * (7500 * 0.3)); // 30% del DD como capital de riesgo efectivo
positionSize = Math.Min(positionSize, volSize);
positionSize = Math.Max(1, Math.Min(positionSize, 15)); // nunca más de 15 contratos en 300K Apex