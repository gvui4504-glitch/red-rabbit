@echo off
cd /d "%~dp0"
title 红兔 - 首次安装

echo.
echo ============================================================
echo    红兔 - 首次安装器
echo    预计 1-2 分钟（含装 Python 依赖）
echo ============================================================
echo.

REM ============================================================
REM 第 1 步：找 Python
REM ============================================================
echo [1/2] 检测 Python ...

python --version >nul 2>&1
if not errorlevel 1 (
    set "PYEXE=python"
    for /f "delims=" %%V in ('python --version 2^>^&1') do echo       已找到: %%V
    goto :check_version
)

echo       系统 PATH 里没有 Python，扫描常见安装位置 ...
for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
    "%ProgramFiles%\Python313\python.exe"
    "%ProgramFiles%\Python312\python.exe"
    "%ProgramFiles%\Python311\python.exe"
    "%ProgramFiles%\Python310\python.exe"
) do (
    if exist %%P (
        set "PYEXE=%%~P"
        echo       已找到: %%~P
        goto :check_version
    )
)

echo.
echo       没装过 Python，准备用 Windows 自带的 winget 自动安装 Python 3.12 ...
echo.
where winget >nul 2>&1
if errorlevel 1 (
    echo [失败] 你的 Windows 太老，没有 winget。
    echo        请手动到 https://www.python.org/downloads/ 装，记得勾 Add Python to PATH
    start https://www.python.org/downloads/
    pause
    exit /b 1
)

echo ============================================================
echo   注意：接下来会弹出 UAC 对话框，请点「是」同意安装 Python
echo ============================================================
echo.
pause

winget install --id Python.Python.3.12 --silent --accept-package-agreements --accept-source-agreements --scope user
if errorlevel 1 (
    echo [失败] winget 装 Python 失败，请手动到 python.org 安装
    pause
    exit /b 1
)

for %%P in (
    "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
    "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
) do (
    if exist %%P (
        set "PYEXE=%%~P"
        echo       接下来使用: %%~P
        goto :check_version
    )
)

echo [失败] winget 装完但找不到 Python，请关掉此窗口重双击 setup.bat
pause
exit /b 1

:check_version
"%PYEXE%" -c "import sys; sys.exit(0 if sys.version_info >= (3,10) else 1)" >nul 2>&1
if errorlevel 1 (
    echo [失败] Python 版本太旧，需要 3.10+
    "%PYEXE%" --version
    pause
    exit /b 1
)
echo.

REM ============================================================
REM 第 2 步：装依赖
REM ============================================================
echo [2/2] 安装 Python 依赖（清华镜像约 30 秒）...
echo       网络卡？关 VPN/Clash 再试
echo.

"%PYEXE%" -m pip install --upgrade pip -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --no-warn-script-location >nul 2>&1

"%PYEXE%" -m pip install -r "%~dp0requirements.txt" -i https://pypi.tuna.tsinghua.edu.cn/simple --timeout 120 --retries 5 --no-warn-script-location
if errorlevel 1 (
    echo.
    echo       清华源失败，自动尝试阿里源 ...
    "%PYEXE%" -m pip install -r "%~dp0requirements.txt" -i https://mirrors.aliyun.com/pypi/simple/ --timeout 120 --no-warn-script-location
    if errorlevel 1 (
        echo.
        echo [失败] 依赖装失败，常见原因：
        echo        1. 关 VPN / Clash 再试
        echo        2. 换个网络（手机热点常常比家里宽带稳）
        pause
        exit /b 2
    )
)

echo.
echo ============================================================
echo    安装完成！下一步：启动
echo ============================================================
echo.
echo    3 秒后自动启动 streamlit
echo    如果没自动启动，请手动双击 start.bat
echo.
timeout /t 3 /nobreak >nul
start "" "%~dp0start.bat"
exit /b 0
