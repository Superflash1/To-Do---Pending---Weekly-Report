@echo off

setlocal enabledelayedexpansion

chcp 65001 >nul



cd /d "%~dp0"



echo ==================================================

echo  第二大脑系统 - 本地启动脚本（无 Docker，Python 由 uv 管理）

echo ==================================================



echo [1/10] 检查 Node.js...

where node >nul 2>nul

if errorlevel 1 (

  echo [ERROR] 未检测到 Node.js，请先安装 Node.js 20+

  pause

  exit /b 1

)

for /f "tokens=1" %%v in ('node --version') do set NODE_VER=%%v

echo [OK] Node 版本: %NODE_VER%



echo [2/10] 检查 uv...

where uv >nul 2>nul

if errorlevel 1 (

  echo [WARN] 未检测到 uv，尝试自动安装...

  powershell -NoProfile -ExecutionPolicy Bypass -Command "irm https://astral.sh/uv/install.ps1 | iex"

  if errorlevel 1 (

    echo [ERROR] uv 自动安装失败，请先手动安装 uv 后重试

    echo         安装文档: https://docs.astral.sh/uv/getting-started/installation/

    pause

    exit /b 1

  )

)

for /f "tokens=*" %%v in ('uv --version 2^>^&1') do set UV_VER=%%v

echo [OK] %UV_VER%



echo [3/10] 安装 Python 3.11（通过 uv）...

uv python install 3.11

if errorlevel 1 (

  echo [ERROR] Python 3.11 安装失败

  pause

  exit /b 1

)

echo [OK] Python 3.11 已就绪



echo [4/10] 检查 .env 文件...

if not exist ".env" (

  if exist ".env.example" (

    copy /y ".env.example" ".env" >nul

    echo [OK] 已从 .env.example 创建 .env

  ) else (

    echo [ERROR] 未找到 .env.example，请先创建环境变量模板

    pause

    exit /b 1

  )

) else (

  echo [OK] .env 已存在

)



echo [5/10] 创建必要目录...

if not exist "data" mkdir "data"

if not exist "data\uploads" mkdir "data\uploads"

if not exist "backend\uploads" mkdir "backend\uploads"

if not exist "backend\data" mkdir "backend\data"

echo [OK] 目录准备完成



echo [6/10] 清理旧虚拟环境并重建（uv + Python 3.11）...

if exist "backend\.venv" (

  rmdir /s /q "backend\.venv"

  if errorlevel 1 (

    echo [ERROR] 删除旧虚拟环境失败，请关闭占用 .venv 的进程后重试

    pause

    exit /b 1

  )

  echo [OK] 已删除旧虚拟环境

)

uv venv --python 3.11 "backend\.venv"

if errorlevel 1 (

  echo [ERROR] 后端虚拟环境创建失败

  pause

  exit /b 1

)

echo [OK] 新虚拟环境创建完成



echo [7/10] 安装后端依赖（uv）...

if exist "backend\requirements.txt" (

  uv pip install --python "backend\.venv\Scripts\python.exe" -r "backend\requirements.txt"

  if errorlevel 1 (

    echo [ERROR] 后端依赖安装失败

    pause

    exit /b 1

  )

  echo [OK] 后端依赖安装完成

) else (

  echo [WARN] 未找到 backend\requirements.txt，跳过依赖安装

)



echo [8/10] 安装前端依赖...

cd /d "%~dp0frontend"

if not exist "node_modules" (

  call npm install

  if errorlevel 1 (

    echo [ERROR] 前端依赖安装失败

    pause

    exit /b 1

  )

  echo [OK] 前端依赖安装完成

) else (

  echo [OK] 前端依赖已存在，跳过 npm install

)

cd /d "%~dp0"



echo [9/10] 端口占用检查（5174）...

for %%p in (5174) do (

  netstat -ano | findstr ":%%p" | findstr "LISTENING" >nul

  if not errorlevel 1 (

    echo [WARN] 端口 %%p 已被占用，请确认是否冲突

  )

)



echo [10/10] 关闭旧窗口并启动服务...

echo ==================================================

echo [INFO] 尝试关闭旧的后端/前端命令行窗口...

taskkill /F /FI "WINDOWTITLE eq Backend - FastAPI*" /T >nul 2>nul

taskkill /F /FI "WINDOWTITLE eq Frontend - Vue*" /T >nul 2>nul

timeout /t 1 /nobreak >nul

start "Backend - FastAPI" cmd /k "cd /d ""%~dp0backend"" && .venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app --reload-exclude "".venv"" --reload-exclude ""data"" --reload-exclude ""*.db"""



REM 等待后端就绪（最多 30 秒）

set "HEALTH_OK=0"

for /l %%i in (1,1,15) do (

  powershell -NoProfile -Command "try { $r=Invoke-WebRequest -Uri 'http://127.0.0.1:8000/health' -UseBasicParsing -TimeoutSec 2; if ($r.StatusCode -eq 200) { exit 0 } else { exit 1 } } catch { exit 1 }"

  if not errorlevel 1 (

    set "HEALTH_OK=1"

    goto :backend_ready

  )

  timeout /t 2 /nobreak >nul

)

:backend_ready

if "%HEALTH_OK%"=="0" (

  echo [WARN] 后端启动超时，前端仍会启动，可能出现代理报错

)



start "Frontend - Vue" cmd /k "cd /d "%~dp0frontend" && npm run dev"



REM 等待前端就绪后自动打开界面

timeout /t 4 /nobreak >nul

start "" "http://127.0.0.1:5174"

start "" "http://127.0.0.1:5174/docs"

echo ==================================================



echo [OK] 本地服务已启动：

echo      统一入口: http://127.0.0.1:5174

echo      Swagger: http://127.0.0.1:5174/docs

echo      健康检查: http://127.0.0.1:5174/health

echo.

echo 若要停止：请关闭两个新开的命令行窗口。



pause

endlocal

