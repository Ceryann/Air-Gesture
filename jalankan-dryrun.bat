@echo off
cd /d "%~dp0"
call "%~dp0_env.bat"
echo MODE UJI: mouse asli TIDAK disentuh. Tekan q atau ESC di jendela preview untuk keluar.
".venv\Scripts\python.exe" -m gesture_core --dry-run
echo.
pause
