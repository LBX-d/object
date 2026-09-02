@echo off
title 智能车间缺陷检测系统 - 一键启动
echo ================================================
echo    智能车间产品外观缺陷检测与报告系统
echo ================================================
echo.

rem 定位到本脚本所在目录（无论从哪里双击都正确）
cd /d "%~dp0"

rem ---- 环境检查 ----
if not exist "backend\.venv\Scripts\python.exe" (
    echo [错误] 未找到后端虚拟环境 backend\.venv
    echo        请先安装后端依赖，详见 README.md
    pause
    exit /b 1
)
if not exist "defect-detection-frontend\node_modules" (
    echo [错误] 未找到前端依赖 node_modules
    echo        请先运行: cd defect-detection-frontend ^&^& npm install
    pause
    exit /b 1
)

rem ---- 检查服务是否已在运行（已运行则跳过，避免端口冲突） ----
set "BACKEND_RUNNING="
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul && set "BACKEND_RUNNING=1"
set "FRONTEND_RUNNING="
netstat -ano | findstr ":5173" | findstr "LISTENING" >nul && set "FRONTEND_RUNNING=1"

if defined BACKEND_RUNNING (
    echo [提示] 后端已在运行（端口 8000），跳过启动
) else (
    echo [1/2] 启动后端服务（端口 8000）...
    start "缺陷检测-后端服务" /d "%~dp0backend" cmd /k ".venv\Scripts\python.exe run.py --port 8000"
)

if defined FRONTEND_RUNNING (
    echo [提示] 前端已在运行（端口 5173），跳过启动
) else (
    echo [2/2] 启动前端服务（端口 5173）...
    start "缺陷检测-前端服务" /d "%~dp0defect-detection-frontend" cmd /k "npm run dev"
)

rem ---- 等待后端就绪（最多约 40 秒），避免浏览器打开太早报网络错误 ----
echo.
echo 正在等待后端服务就绪...
set /a TRIES=0
:waitloop
ping -n 2 127.0.0.1 >nul
netstat -ano | findstr ":8000" | findstr "LISTENING" >nul
if not errorlevel 1 goto ready
set /a TRIES+=1
if %TRIES% GEQ 20 goto ready
goto waitloop
:ready

echo 服务就绪，正在打开浏览器...
start "" http://localhost:5173

echo.
echo ================================================
echo  完成！
echo    前端界面: http://localhost:5173
echo    后端接口: http://localhost:8000
echo.
echo  提示: 关闭弹出的黑色窗口即可停止系统
echo ================================================
echo.
pause
