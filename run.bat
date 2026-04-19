@echo off
title NEXUS — Neural EXecution & Understanding System
color 0B
echo.
echo  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
echo  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
echo  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
echo  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
echo  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
echo  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo  Starting NEXUS...
echo.

:: Check Ollama is running
curl -s http://localhost:11434/api/tags >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [INFO] Starting Ollama in background...
    start /B ollama serve
    timeout /t 3 /nobreak >nul
)

:: Launch NEXUS
python main.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [ERROR] NEXUS exited with an error.
    echo Run setup.bat if this is your first time.
    pause
)
