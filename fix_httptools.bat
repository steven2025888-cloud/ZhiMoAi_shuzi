@echo off
echo Fixing httptools module...
echo.

set HTTP_PROXY=
set HTTPS_PROXY=
set NO_PROXY=
set http_proxy=
set https_proxy=
set no_proxy=

echo [1/2] Reinstalling httptools...
_internal_app\installer_files\env\Scripts\python.exe -m pip install --force-reinstall httptools -i https://pypi.tuna.tsinghua.edu.cn/simple
if errorlevel 1 (
    echo.
    echo [ERROR] Failed to install httptools
    echo Trying official PyPI...
    _internal_app\installer_files\env\Scripts\python.exe -m pip install --force-reinstall httptools
    if errorlevel 1 (
        echo [ERROR] Still failed. You may need to rebuild the environment.
        pause
        exit /b 1
    )
)

echo.
echo [2/2] Verifying httptools...
_internal_app\installer_files\env\Scripts\python.exe -c "import httptools; print('httptools version:', httptools.__version__)"
if errorlevel 1 (
    echo [ERROR] httptools still broken
    pause
    exit /b 1
)

echo.
echo [OK] httptools fixed successfully!
echo.
pause
