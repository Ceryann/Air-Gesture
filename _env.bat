@echo off
rem Mengarahkan SEMUA cache ke dalam folder proyek (.cache) supaya mudah dihapus.
set "PIP_CACHE_DIR=%~dp0.cache\pip"
set "MPLCONFIGDIR=%~dp0.cache\matplotlib"
set "PYTHONPYCACHEPREFIX=%~dp0.cache\pycache"
set "PIP_DISABLE_PIP_VERSION_CHECK=1"
if not exist "%~dp0.cache" mkdir "%~dp0.cache"
