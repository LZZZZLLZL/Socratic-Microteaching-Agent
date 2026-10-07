@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

rem ==========================================================================
rem  学思践悟 AI 多模态实训系统 · 新样式版
rem  Windows 一键启动脚本
rem
rem  用法：双击本文件即可。
rem        自动定位同目录下「微课系统」文件夹，
rem        因此整个文件夹解压到任何位置都能正常使用。
rem
rem  可用命令行参数（可选）：
rem    start.bat preview   快速预览模式
rem    start.bat full      完整模式（前端 + 后端）
rem ==========================================================================

title 学思践悟 · AI 多模态实训系统（新样式版）

set "SCRIPT_DIR=%~dp0"
set "PROJECT_DIR=%SCRIPT_DIR%微课系统"
set "FRONTEND_DIR=%PROJECT_DIR%\frontend"
set "BACKEND_DIR=%PROJECT_DIR%\backend"

set "FRONTEND_PORT=3000"
set "BACKEND_PORT=8000"

echo.
echo   ======================================================
echo     学思践悟 · AI 多模态实训系统（新样式版）
echo   ======================================================
echo.

rem ---------- 检查项目目录 ----------
if not exist "%PROJECT_DIR%" (
    echo   [错误] 找不到「微课系统」文件夹：
    echo          %PROJECT_DIR%
    echo.
    echo   请确认本脚本与「微课系统」文件夹位于同一目录下。
    echo.
    pause
    exit /b 1
)

rem ---------- 检查 Node.js ----------
where node >nul 2>&1
if errorlevel 1 (
    echo   [错误] 未找到 Node.js
    echo.
    echo   请先安装 Node.js 18 或更高版本：https://nodejs.org
    echo.
    pause
    exit /b 1
)
for /f "delims=" %%v in ('node --version') do set "NODE_VER=%%v"
echo   [√] Node.js %NODE_VER%

rem ---------- 安装前端依赖 ----------
if not exist "%FRONTEND_DIR%\node_modules" (
    echo.
    echo   [!] 首次运行，正在安装前端依赖，约需 1-3 分钟...
    cd /d "%FRONTEND_DIR%"
    call npm install --silent
    if errorlevel 1 (
        echo.
        echo   [错误] 前端依赖安装失败。
        echo         请手动执行： cd 微课系统\frontend ^&^& npm install
        echo.
        pause
        exit /b 1
    )
    echo   [√] 前端依赖安装完成
) else (
    echo   [√] 前端依赖已就绪
)

rem ---------- 选择启动模式 ----------
set "MODE=%~1"
if "%MODE%"=="" (
    echo.
    echo   请选择启动模式：
    echo.
    echo     [1] 快速预览模式   零依赖，不需要模型和 API Key
    echo                        -- 推荐给评委演示，打开即可用
    echo.
    echo     [2] 完整模式       前端 + 后端，真实视频分析
    echo                        -- 需要 Python 依赖与 ffmpeg
    echo.
    set /p "CHOICE=  输入选项 [1]: "
    if "!CHOICE!"=="" set "CHOICE=1"
    if "!CHOICE!"=="1" set "MODE=preview"
    if "!CHOICE!"=="2" set "MODE=full"
)

rem ---------- 完整模式：额外检查后端环境 ----------
if /i "%MODE%"=="full" (
    echo.
    where python >nul 2>&1
    if errorlevel 1 (
        where python3 >nul 2>&1
        if errorlevel 1 (
            echo   [错误] 未找到 Python，完整模式需要 Python 3.9+
            echo         下载：https://www.python.org/downloads/
            echo.
            pause
            exit /b 1
        )
        set "PY=python3"
    ) else (
        set "PY=python"
    )

    echo   [√] Python 已就绪

    where ffmpeg >nul 2>&1
    if errorlevel 1 (
        echo   [!] 未找到 ffmpeg -- 视频转写与姿态分析将不可用
        echo       安装：https://www.gyan.dev/ffmpeg/builds/
    ) else (
        echo   [√] ffmpeg 已就绪
    )

    rem DEEPSEEK_API_KEY：启动阶段不再提示，也不在此处配置。
    rem 改为进入系统后在「分析工作台 - API 设置」面板里填写（保存即生效，无需重启）。

    echo.
    echo   [!] 首次启动后端会加载模型，可能需要 1-2 分钟...
    start "学思践悟-后端" cmd /k "cd /d "%BACKEND_DIR%" && %PY% -m uvicorn main:app --host 127.0.0.1 --port %BACKEND_PORT%"
)

rem ---------- 启动前端 ----------
echo.
echo   正在启动前端服务...
start "学思践悟-前端" cmd /k "cd /d "%FRONTEND_DIR%" && npm run dev -- --port %FRONTEND_PORT%"

rem ---------- 等待并打开浏览器 ----------
echo   等待服务就绪...
timeout /t 12 /nobreak >nul

echo.
echo   ======================================================
echo     系统已启动！
echo.
echo     浏览器访问： http://localhost:%FRONTEND_PORT%
echo   ======================================================
echo.
if /i "%MODE%"=="full" (
    echo    请把右上角开关切到「FULL / 完整版」
    echo    首次分析会自动监测模型并让你选择 Whisper 精度
    echo.
)

start "" "http://localhost:%FRONTEND_PORT%"

echo    关闭本窗口不会停止服务。
echo    如需停止，请关闭「学思践悟-前端」「学思践悟-后端」窗口。
echo.
pause
