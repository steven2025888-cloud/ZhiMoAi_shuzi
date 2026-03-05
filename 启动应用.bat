@echo off
REM 织梦AI启动脚本
REM 优先使用.py文件，如果不存在则使用.pyc文件

set PYTHON_EXE=FunCosyVoice3\python310\pythonw.exe
set APP_PY=app_backend.py
set APP_PYC=app_backend.pyc

if exist "%APP_PY%" (
    start "" "%PYTHON_EXE%" "%APP_PY%"
) else if exist "%APP_PYC%" (
    start "" "%PYTHON_EXE%" "%APP_PYC%"
) else (
    echo 错误：找不到app_backend.py或app_backend.pyc
    pause
)

