@echo off

@REM 激活虚拟环境
call .venv\Scripts\activate.bat

@REM 运行服务器
fastapi run src/server.py
