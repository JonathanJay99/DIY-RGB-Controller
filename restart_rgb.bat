@echo off
echo.
echo ========================================================
echo DIY RGB Controller - Schneller Neustart
echo ========================================================
echo.

echo Beende kollidierende Razer-Prozesse...
taskkill /F /IM "Razer Synapse 3.exe" /T >nul 2>&1
taskkill /F /IM "Razer Central.exe" /T >nul 2>&1
taskkill /F /IM "Razer Synapse Service.exe" /T >nul 2>&1

echo Beende bestehende OpenRGB-Server...
taskkill /F /IM OpenRGB.exe /T >nul 2>&1

echo Beende haengende Pinsel...
taskkill /F /IM pythonw3.13.exe /T >nul 2>&1
taskkill /F /IM python3.13.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
taskkill /F /IM python.exe /T >nul 2>&1

echo Warte auf sauberes Beenden...
timeout /t 3 /nobreak >nul

echo Starte OpenRGB als Administrator...
powershell -Command "Start-Process 'C:\Program Files\OpenRGB\OpenRGB.exe' -ArgumentList '--server' -Verb RunAs"

echo Warte auf OpenRGB Initialisierung (inkl. RAM)...
timeout /t 15 /nobreak >nul

echo Erzwinge Device-Rescan...
powershell -Command "Start-Process 'C:\Program Files\OpenRGB\OpenRGB.exe' -ArgumentList '--client --noautoconnect' -Verb RunAs" >nul 2>&1
timeout /t 5 /nobreak >nul

echo Starte DIY Pinsel...
start "" "pythonw.exe" "%~dp0main.py"

echo.
echo FERTIG! OpenRGB laeuft als Admin, RAM sollte erkannt sein.
timeout /t 3 >nul
exit
