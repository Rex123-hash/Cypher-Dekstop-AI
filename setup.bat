@echo off
title NEXUS Setup
color 0B
echo.
echo  ███╗   ██╗███████╗██╗  ██╗██╗   ██╗███████╗
echo  ████╗  ██║██╔════╝╚██╗██╔╝██║   ██║██╔════╝
echo  ██╔██╗ ██║█████╗   ╚███╔╝ ██║   ██║███████╗
echo  ██║╚██╗██║██╔══╝   ██╔██╗ ██║   ██║╚════██║
echo  ██║ ╚████║███████╗██╔╝ ██╗╚██████╔╝███████║
echo  ╚═╝  ╚═══╝╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚══════╝
echo  Neural EXecution ^& Understanding System
echo  Setup Script
echo.

:: ── Step 1: Python deps ───────────────────────────────────────────────────────
echo [1/5] Installing Python dependencies...
pip install -r requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] pip install failed. Make sure Python 3.11+ is installed.
    pause
    exit /b 1
)
echo [OK] Python deps installed.
echo.

:: ── Step 2: Playwright browsers ───────────────────────────────────────────────
echo [2/5] Installing Playwright browsers (Chromium)...
python -m playwright install chromium
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] Playwright browser install failed. WhatsApp automation may not work.
) else (
    echo [OK] Playwright Chromium installed.
)
echo.

:: ── Step 3: Check Ollama ──────────────────────────────────────────────────────
echo [3/5] Checking Ollama...
ollama --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Ollama not found. Install from https://ollama.com and re-run setup.
    pause
    exit /b 1
)
echo [OK] Ollama found.
echo.

:: ── Step 4: Check OpenClaw ────────────────────────────────────────────────────
echo [4/5] Checking OpenClaw...
openclaw --version >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [WARN] OpenClaw not found on PATH. Ensure OpenClaw v2026.4.14 is installed.
    echo        OpenClaw features will be unavailable until it is on PATH.
) else (
    echo [OK] OpenClaw found.
)
echo.

:: ── Step 5: Pull Ollama models ────────────────────────────────────────────────
echo [5/5] Pulling Ollama models (this may take a while)...
echo.

echo Checking qwen3:8b...
ollama list | findstr /C:"qwen3:8b" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Pulling qwen3:8b (fast chat model)...
    ollama pull qwen3:8b
) else (
    echo [OK] qwen3:8b already present.
)

echo Checking deepseek-r1:8b...
ollama list | findstr /C:"deepseek-r1:8b" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Pulling deepseek-r1:8b (reasoning model)...
    ollama pull deepseek-r1:8b
) else (
    echo [OK] deepseek-r1:8b already present.
)

echo Checking qwen2.5-coder:7b...
ollama list | findstr /C:"qwen2.5-coder:7b" >nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo Pulling qwen2.5-coder:7b (code model)...
    ollama pull qwen2.5-coder:7b
) else (
    echo [OK] qwen2.5-coder:7b already present.
)

echo.

:: ── Copy .env if not present ─────────────────────────────────────────────────
if not exist .env (
    echo Creating .env from .env.example...
    copy .env.example .env
    echo [ACTION REQUIRED] Edit .env and fill in your API keys.
)

echo.
echo ══════════════════════════════════════════
echo  NEXUS setup complete!
echo  Next steps:
echo    1. Edit .env with your API keys
echo    2. Run: run.bat
echo ══════════════════════════════════════════
echo.
pause
