@echo off
setlocal
cd /d "%~dp0"
call "%~dp0_env.bat"
echo === GestureInput: setup (sekali saja) ===
echo Semua file dipasang DI DALAM folder ini. Hapus folder = bersih total.
echo.

set "PY="
for %%V in (3.12 3.11 3.10) do (
  if not defined PY (
    py -%%V --version >nul 2>&1 && set "PY=py -%%V"
  )
)
if not defined PY (
  python --version >nul 2>&1 && set "PY=python"
)
if not defined PY (
  echo [GAGAL] Python tidak ditemukan. Pasang Python 3.10-3.12 lalu ulangi.
  goto :err
)
echo Memakai: %PY%
%PY% --version

if not exist ".venv\Scripts\python.exe" (
  echo.
  echo [1/4] Membuat lingkungan Python di folder .venv ...
  %PY% -m venv .venv || goto :err
) else (
  echo [1/4] .venv sudah ada, dilewati.
)

echo.
echo [2/4] Memasang library (bisa beberapa menit, perlu internet) ...
".venv\Scripts\python.exe" -m pip install -r requirements.txt || goto :err

echo.
echo [3/4] Mengunduh model tangan ke folder models ...
".venv\Scripts\python.exe" scripts\download_model.py || goto :err

echo.
echo [4/4] Cek instalasi ...
".venv\Scripts\python.exe" -m gesture_core --selfcheck || goto :selfcheck_err

echo.
echo === SETUP SELESAI. Jalankan: jalankan-dryrun.bat ===
pause
exit /b 0

:selfcheck_err
echo.
echo [GAGAL] Cek instalasi tidak lolos.
echo Jika ada "WinError 4551 / Application Control policy": Smart App Control memblokir
echo DLL MediaPipe. Lihat README (bagian Smart App Control).
pause
exit /b 1

:err
echo.
echo [GAGAL] Setup berhenti karena error di atas.
pause
exit /b 1
