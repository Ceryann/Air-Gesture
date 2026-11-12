@echo off
cd /d "%~dp0"
echo MODE UJI: mouse asli TIDAK disentuh. Tekan q atau ESC di jendela preview untuk keluar.
GestureInput.exe --dry-run
echo.
pause
