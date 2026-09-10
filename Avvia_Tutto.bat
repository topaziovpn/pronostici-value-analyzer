@echo off
title Bet1X2 - PRO SYSTEM
color 0B

echo ========================================================
echo        BET1X2 - AVVIO SISTEMA PRO
echo ========================================================
echo.

echo [1/4] Aggiornamento Dashboard Performance e CLV...
python backend\src\stats_generator.py
echo Fatto.
echo.

echo [2/4] Avvio Scheduler Pronostici (main.py)...
start "Pronostici Scheduler Bet1X2" cmd /k "python backend\src\main.py --schedule"
echo.

echo [3/4] Avvio Live Tracker in una finestra separata...
start "Live Tracker Bet1X2" cmd /k "color 0A & python backend\src\live_tracker.py"

echo [4/4] Avvio Server Web e Apertura Pronostici...
start "Web Server Bet1X2" cmd /k "python -m http.server 8080"

timeout /t 2 /nobreak >nul

start http://localhost:8080/Visualizza_Pronostici.html

echo.
echo ========================================================
echo SISTEMA AVVIATO CON SUCCESSO!
echo ========================================================
pause
