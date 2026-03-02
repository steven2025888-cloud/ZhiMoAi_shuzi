@echo off

:: Switch to project root (this script is in build_scripts\)
pushd "%~dp0.."

echo ============================================================
echo   ZhiMoAI - Build Package
echo ============================================================
echo.

set "ENV_DIR=_internal_app\installer_files\env"
echo   Package type: ONLINE
echo   Python env: %ENV_DIR%
echo.

echo [1/9] Verify Python environment exists...
set "PY="
if exist "%ENV_DIR%\Scripts\python.exe" set "PY=%ENV_DIR%\Scripts\python.exe"
if "%PY%"=="" if exist "%ENV_DIR%\python.exe" set "PY=%ENV_DIR%\python.exe"

if "%PY%"=="" (
    echo   [ERROR] Python env not found at %ENV_DIR%
    echo   Run build_scripts\setup_app_env.bat first!
    pause
    exit /b 1
)
echo   [OK] %PY%
echo.

echo [2/9] Verify Python env is standalone (no pyvenv.cfg)...
if exist "%ENV_DIR%\pyvenv.cfg" goto :ENV_NOT_STANDALONE
"%PY%" -c "import sys, os, ssl; print('  Python', sys.version.split()[0], '- stdlib OK')"
if errorlevel 1 goto :ENV_STDLIB_BROKEN
echo   [OK] Standalone env verified
echo.

echo [3/9] Verify Python env native extensions (pip packages)...
"%PY%" build_scripts\verify_env.py
if errorlevel 1 goto :ENV_VERIFY_FAILED
echo.

echo [4/9] Clean temp directories...
if exist "avatars" rmdir /s /q "avatars" 2>nul & mkdir "avatars"
if exist "voices" rmdir /s /q "voices" 2>nul & mkdir "voices"
if exist "unified_outputs" rmdir /s /q "unified_outputs" 2>nul & mkdir "unified_outputs"
echo   [OK]
echo.

echo [5/9] Generate env.dat (obfuscated config)...
if exist ".env" (
    "%PY%" build_scripts\generate_env_dat.py
    if errorlevel 1 (
        echo   [ERROR] env.dat generation failed
        pause
        exit /b 1
    )
    echo   [OK]
) else (
    echo   [SKIP] No .env file found
)
echo.

echo [6/9] Compile Python to .pyc bytecode...
"%PY%" build_scripts\build_pyc_for_package.py
if errorlevel 1 (
    echo   [ERROR] Python compile failed
    pause
    exit /b 1
)
echo   [OK]
echo.

echo [7/9] Check launcher exe...
if not exist "ZhiMoAI_Launcher.exe" (
    echo   Launcher not found, building...
    call build_scripts\build_launcher.bat
    if errorlevel 1 (
        echo   [ERROR] Launcher build failed
        "%PY%" build_scripts\build_pyc_for_package.py --clean
        pause
        exit /b 1
    )
    echo   [OK] Built
) else (
    echo   [OK] Exists
)
echo.

echo [8/9] Verify .pyc files...
set MISSING=0
if not exist "app_backend.pyc" ( echo   [MISSING] app_backend.pyc & set MISSING=1 )
if not exist "unified_app.pyc" ( echo   [MISSING] unified_app.pyc & set MISSING=1 )
if not exist "libs\app_version.pyc" ( echo   [MISSING] libs\app_version.pyc & set MISSING=1 )
if not exist "libs\voice_api.pyc" ( echo   [MISSING] libs\voice_api.pyc & set MISSING=1 )
if not exist "libs\lib_avatar.pyc" ( echo   [MISSING] libs\lib_avatar.pyc & set MISSING=1 )
if not exist "libs\lib_voice.pyc" ( echo   [MISSING] libs\lib_voice.pyc & set MISSING=1 )
if not exist "libs\lib_subtitle.pyc" ( echo   [MISSING] libs\lib_subtitle.pyc & set MISSING=1 )
if not exist "libs\lib_license.pyc" ( echo   [MISSING] libs\lib_license.pyc & set MISSING=1 )
if not exist "libs\lib_meta_store.pyc" ( echo   [MISSING] libs\lib_meta_store.pyc & set MISSING=1 )
if not exist "libs\lib_publish_base.pyc" ( echo   [MISSING] libs\lib_publish_base.pyc & set MISSING=1 )
if not exist "libs\lib_douyin_publish.pyc" ( echo   [MISSING] libs\lib_douyin_publish.pyc & set MISSING=1 )
if not exist "libs\lib_bilibili_publish.pyc" ( echo   [MISSING] libs\lib_bilibili_publish.pyc & set MISSING=1 )
if not exist "libs\lib_shipinhao_publish.pyc" ( echo   [MISSING] libs\lib_shipinhao_publish.pyc & set MISSING=1 )
if not exist "libs\lib_xiaohongshu_publish.pyc" ( echo   [MISSING] libs\lib_xiaohongshu_publish.pyc & set MISSING=1 )
if not exist "libs\lib_kuaishou_publish.pyc" ( echo   [MISSING] libs\lib_kuaishou_publish.pyc & set MISSING=1 )
if not exist "libs\lib_pip.pyc" ( echo   [MISSING] libs\lib_pip.pyc & set MISSING=1 )
if not exist "libs\lib_pip_websocket.pyc" ( echo   [MISSING] libs\lib_pip_websocket.pyc & set MISSING=1 )
if not exist "libs\veo_video.pyc" ( echo   [MISSING] libs\veo_video.pyc & set MISSING=1 )

if %MISSING%==1 (
    echo   [ERROR] Some .pyc files missing
    pause
    exit /b 1
)
echo   [OK]
echo.

echo [9/9] Build installer (Inno Setup)...
set ISCC="C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
if exist %ISCC% (
    echo   Compiling installer...
    %ISCC% build_scripts\setup_zhimengai.iss
    if errorlevel 1 (
        echo   [ERROR] Inno Setup compile failed
        "%PY%" build_scripts\build_pyc_for_package.py --clean
        pause
        exit /b 1
    )
    echo   [OK]
) else (
    echo   [ERROR] Inno Setup not found at default path
    "%PY%" build_scripts\build_pyc_for_package.py --clean
    pause
    exit /b 1
)

echo.
echo Cleaning temp .pyc files...
"%PY%" build_scripts\build_pyc_for_package.py --clean
echo.

echo ============================================================
echo   BUILD SUCCESS!
echo ============================================================
echo.
echo   Check dist\ for output file
echo.
pause

popd

goto :EOF

:ENV_NOT_STANDALONE
echo   [ERROR] pyvenv.cfg found! Env is still a venv, not standalone.
echo   The packaged env must be self-contained (no dependency on build machine Python).
echo   Current: %ENV_DIR%\pyvenv.cfg
pause
popd
exit /b 1

:ENV_STDLIB_BROKEN
echo   [ERROR] Python env stdlib broken! Env may still be a venv.
pause
popd
exit /b 1

:ENV_VERIFY_FAILED
echo.
echo   [ERROR] Python env is broken! Run build_scripts\setup_app_env.bat to fix.
pause
popd
exit /b 1
