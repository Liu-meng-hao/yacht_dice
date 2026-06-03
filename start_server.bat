@echo off
echo 正在启动快艇骰子游戏后端服务...
echo.
cd /d d:\桌面\dice\yacht_dice
py -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
pause