@echo off
chcp 65001 >nul
echo ========================================
echo   布林带回归策略 · 量化回测系统启动
echo ========================================
echo.

echo [1/2] 启动后端服务 (FastAPI :8000)...
cd /d "%~dp0backend"
start "BB-Backend" cmd /k "python main.py"

echo [2/2] 启动前端服务 (Vite :5173)...
cd /d "%~dp0frontend"
start "BB-Frontend" cmd /k "npm run dev"

echo.
echo ========================================
echo   启动完成！
echo   前端界面: http://localhost:5173
echo   后端API:  http://localhost:8000
echo ========================================
echo.
echo 按任意键关闭此窗口（不影响服务运行）
pause >nul
