@echo off
cd /d "%~dp0"
call "%~dp0_env.bat"
echo MENGONTROL MOUSE SUNGGUHAN. Freeze: Ctrl+Alt+F ^| Keluar: Ctrl+Alt+Q
".venv\Scripts\python.exe" -m gesture_core
echo.
pause
