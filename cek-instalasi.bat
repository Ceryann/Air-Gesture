@echo off
cd /d "%~dp0"
call "%~dp0_env.bat"
".venv\Scripts\python.exe" -m gesture_core --selfcheck
echo.
pause
