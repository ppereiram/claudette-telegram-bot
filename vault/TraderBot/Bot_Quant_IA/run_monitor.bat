@echo off
echo ================================
echo  Market Monitor Logger
echo  Corriendo despues del cierre...
echo ================================
cd /d "%~dp0"
pip install yfinance pandas numpy -q
python market_monitor_logger.py
echo.
echo Presiona cualquier tecla para cerrar...
pause > nul
