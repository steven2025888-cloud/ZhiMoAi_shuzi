@echo off
chcp 65001 >nul
cd /D "%~dp0IndexTTS2-SonicVale"
"%cd%\installer_files\env\python.exe" webui.py --port 7860
pause
