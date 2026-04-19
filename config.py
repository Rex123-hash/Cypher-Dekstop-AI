import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).parent

# API Keys
OPENAI_API_KEY    = os.getenv("OPENAI_API_KEY", "")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# OpenRouter — free tier cloud fallback models
OPENROUTER_BASE_URL       = "https://openrouter.ai/api/v1"
OPENROUTER_LONG_CONTEXT   = "minimax/minimax-m2.5"      # long context + translation
OPENROUTER_HEAVY_REASON   = "google/gemma-4-31b"         # heavy reasoning
OPENROUTER_COMPLEX        = "openai/gpt-oss-120b"        # complex tasks
OPENROUTER_MULTI_AGENT    = "nvidia/nemotron-3-super"    # multi-agent tasks

# Ollama
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
FAST_MODEL      = os.getenv("FAST_MODEL",      "qwen3:8b")           # fast replies + general chat
CHAT_MODEL      = os.getenv("CHAT_MODEL",      "qwen3:8b")           # general conversation
REASONING_MODEL = os.getenv("REASONING_MODEL", "deepseek-r1:8b")     # reasoning / file analysis
CODER_MODEL     = os.getenv("CODER_MODEL",     "qwen2.5-coder:7b")   # code / system commands

# OpenClaw
OPENCLAW_MODEL = os.getenv("OPENCLAW_MODEL", "qwen2.5-coder:7b")
OPENCLAW_PATH  = os.getenv("OPENCLAW_PATH",  "openclaw")         # assumed on PATH

# Voice
WAKE_WORD      = os.getenv("WAKE_WORD",      "cipher")
TTS_VOICE      = os.getenv("TTS_VOICE",      "en-US-GuyNeural")
TTS_RATE       = os.getenv("TTS_RATE",       "-10%")
TTS_PITCH      = os.getenv("TTS_PITCH",      "-15Hz")
PICOVOICE_KEY  = os.getenv("PICOVOICE_KEY",  "")

# Whisper — base model, CUDA for RTX 4060
WHISPER_MODEL        = os.getenv("WHISPER_MODEL",        "base")
WHISPER_DEVICE       = os.getenv("WHISPER_DEVICE",       "cuda")
WHISPER_COMPUTE_TYPE = os.getenv("WHISPER_COMPUTE_TYPE", "float16")

# Gesture
GESTURE_ENABLED = os.getenv("GESTURE_ENABLED", "true").lower() == "true"
WEBCAM_INDEX    = int(os.getenv("WEBCAM_INDEX", "0"))

# Display
DISPLAY_WIDTH  = int(os.getenv("DISPLAY_WIDTH",  "1920"))
DISPLAY_HEIGHT = int(os.getenv("DISPLAY_HEIGHT", "1080"))

# Theme — sci-fi neon palette
NEON_CYAN  = "#00FFFF"
NEON_BLUE  = "#0066FF"
NEON_WHITE = "#E0F8FF"
NEON_PINK  = "#FF00AA"
GLASS_BG   = "rgba(4, 12, 28, 185)"
GLOW_COLOR = "#00D4FF"
ACCENT     = "#00AAFF"

# Paths
ASSETS_DIR = BASE_DIR / "ui" / "assets"
FONTS_DIR  = ASSETS_DIR / "fonts"
DATA_DIR   = BASE_DIR / "data"
TMP_DIR    = BASE_DIR / "tmp"

DATA_DIR.mkdir(exist_ok=True)
TMP_DIR.mkdir(exist_ok=True)
