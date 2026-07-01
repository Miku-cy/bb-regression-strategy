@echo off
chcp 65001 >nul
echo 正在停止服务...
taskkill /fi "WindowTitle eq BB-Backend*" /f >nul 2>&1
taskkill /fi "WindowTitle eq BB-Frontend*" /f >nul 2>&1
echo 服务已停止
pause
