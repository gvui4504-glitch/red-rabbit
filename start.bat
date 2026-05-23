@echo off
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
title 红兔 - 启动器

REM 找 Python
python --version >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    goto :go
)

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
) do (
    if exist %%P (
        set "PYEXE=%%~P"
        goto :go
    )
)

echo.
echo [失败] 没找到 Python，请先双击 setup.bat 安装
echo.
pause
exit /b 1

:go
echo.
echo ============================================================
echo    红兔 - 启动器
echo ============================================================
echo.
echo    地址: http://localhost:8502  (固定端口，避开原项目的 8501)
echo.
echo    停止：在此窗口按 Ctrl+C，或直接关掉这个窗口
echo.

REM 阻止 Streamlit 首次启动的 email 询问
if not exist "%USERPROFILE%\.streamlit" mkdir "%USERPROFILE%\.streamlit" >nul 2>&1
if not exist "%USERPROFILE%\.streamlit\credentials.toml" (
    echo [general] > "%USERPROFILE%\.streamlit\credentials.toml"
    echo email = "" >> "%USERPROFILE%\.streamlit\credentials.toml"
)

REM 后台 5 秒后强制开浏览器到 8502（双保险，免得 streamlit 没自动开）
start /b "" powershell -NoProfile -WindowStyle Hidden -Command "Start-Sleep -Seconds 5; Start-Process 'http://localhost:8502/'"

"%PYEXE%" -m streamlit run "%~dp0app.py" --server.port 8502 --browser.gatherUsageStats false

echo.
echo    服务器已停止
pause
