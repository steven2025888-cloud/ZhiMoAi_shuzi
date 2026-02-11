@echo off
chcp 65001 >nul
cd /D "%~dp0"
set PY=%cd%\IndexTTS2-SonicVale\installer_files\env\python.exe
set PYTHONNOUSERSITE=1
set PYTHONPATH=
set PYTHONHOME=
set http_proxy=
set https_proxy=
set HTTP_PROXY=
set HTTPS_PROXY=
set NO_PROXY=*
"%PY%" -u unified_app.py --port 7870
pause
