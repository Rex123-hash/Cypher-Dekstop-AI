<div align="center">

# CIPHER / NEXUS Desktop AI

### A voice-first Windows AI assistant with a sci-fi HUD, local models, OpenRouter intelligence, gesture control, system automation, and agent routing.

![Python](https://img.shields.io/badge/Python-3.11%2B-0B84FF?style=for-the-badge&logo=python&logoColor=white)
![Windows](https://img.shields.io/badge/Windows-11-00A4EF?style=for-the-badge&logo=windows&logoColor=white)
![PyQt6](https://img.shields.io/badge/PyQt6-HUD-00D4FF?style=for-the-badge)
![Ollama](https://img.shields.io/badge/Ollama-Local_AI-111111?style=for-the-badge)
![OpenRouter](https://img.shields.io/badge/OpenRouter-Cloud_Brain-7C3AED?style=for-the-badge)

**Say `Activate`. Watch the HUD wake up. Speak a command. Let the agents move.**

</div>

---

## What Is This?

**CIPHER / NEXUS** is an experimental desktop AI assistant for Windows. It combines speech recognition, text-to-speech, local LLMs, OpenRouter cloud models, a PyQt6 animated overlay, webcam gestures, browser automation, and specialized agents into one assistant-style system.

It is built like a small command center:

- **Voice layer** listens for wake words and transcribes commands.
- **Orchestrator** decides which specialist agent should handle your request.
- **AI brain router** chooses the best model path for chat, code, reasoning, or web-style answers.
- **Agents** handle chat, code, files, Windows system actions, WhatsApp, web questions, security checks, and OpenClaw delegation.
- **Overlay HUD** renders a glowing always-on-top interface over the desktop.
- **TTS** speaks the final answer back to you.

This is not just a chatbot. It is a desktop control system built around AI agents.

---

## Feature Highlights

| Area | What It Does |
|---|---|
| Voice activation | Wake NEXUS with words like `Activate` or `Cipher` |
| Speech-to-text | Uses Faster-Whisper to turn microphone input into commands |
| Spoken replies | Uses Edge TTS for voice responses |
| Animated HUD | PyQt6 + QPainter overlay with neon sci-fi visuals |
| Agent routing | Routes commands to specialized agents |
| Local AI | Uses Ollama models for private/local reasoning and code |
| Cloud AI | Uses OpenRouter models as the main high-level brain path |
| File control | Search, read, list, write, copy, move, rename, and delete files |
| System control | Open apps, screenshots, volume, brightness, shutdown, process stats |
| Security tools | Windows Defender, firewall, ports, startup items, suspicious processes |
| WhatsApp automation | Playwright-based WhatsApp Web messaging |
| Gesture input | MediaPipe/OpenCV hand gesture control |
| OpenClaw bridge | Delegates tasks to OpenClaw as an external agent process |

---

## How It Works

The normal command flow looks like this:

```text
You say "Activate"
        |
Wake-word detector wakes NEXUS
        |
Overlay switches into active listening mode
        |
STT records your command and transcribes it
        |
Orchestrator classifies the intent
        |
Specialist agent handles the request
        |
Brain router picks local Ollama or OpenRouter if AI is needed
        |
Response returns to main.py
        |
Overlay logs the answer
        |
TTS speaks the response
```

In short:

```text
wake -> listen -> transcribe -> route -> think/act -> display -> speak
```

---

## Project Structure

```text
NEXUS/
├── main.py                    # App entry point and runtime coordinator
├── config.py                  # Model names, API keys, paths, voice, display config
├── requirements.txt           # Python dependency list
├── setup.bat                  # Windows setup helper
├── run.bat                    # Windows launcher
├── agents/
│   ├── orchestrator.py        # Routes commands to the right agent
│   ├── chat_agent.py          # General conversation
│   ├── code_agent.py          # Code generation/debug/refactor
│   ├── file_agent.py          # Filesystem operations
│   ├── web_agent.py           # Web-style knowledge and weather
│   ├── system_agent.py        # Windows control and monitoring
│   ├── security_agent.py      # Defender/security checks
│   ├── whatsapp_agent.py      # WhatsApp Web automation
│   └── openclaw_agent.py      # OpenClaw subprocess bridge
├── core/
│   ├── brain.py               # Model routing layer
│   ├── memory.py              # Rolling conversation memory
│   └── openrouter.py          # OpenRouter API client
├── voice/
│   ├── wake_word.py           # Wake-word detection
│   ├── stt.py                 # Faster-Whisper speech-to-text
│   └── tts.py                 # Edge TTS speech output
├── gesture/
│   └── detector.py            # Webcam gesture recognition
├── ui/
│   └── overlay.py             # PyQt6 animated overlay HUD
├── assets/
│   └── hand_landmarker.task   # MediaPipe hand model
├── data/                      # Runtime data, ignored where private
├── tmp/                       # Temporary runtime output
└── info/
    ├── NEXUS_System_Story.md
    └── NEXUS_System_Story.pdf
```

---

## Requirements

Recommended environment:

- Windows 11
- Python 3.11+
- Working microphone
- Webcam for gestures
- Ollama installed
- Optional NVIDIA GPU for faster Whisper inference
- Optional OpenRouter API key
- Optional Picovoice key for dedicated wake-word detection
- Optional OpenClaw installed on PATH

Install Ollama from:

```text
https://ollama.com
```

---

## Quick Start

### 1. Clone the repository

```powershell
git clone https://github.com/Rex123-hash/Cypher-Dekstop-AI.git
cd Cypher-Dekstop-AI
```

### 2. Run setup

```powershell
.\setup.bat
```

The setup script installs Python dependencies, installs Playwright Chromium, checks Ollama, checks OpenClaw, and pulls the expected local models.

### 3. Configure environment variables

Copy the template:

```powershell
copy .env.example .env
```

Then edit `.env` and add your own keys.

Important: never commit `.env`.

### 4. Start NEXUS

```powershell
.\run.bat
```

Then say:

```text
Activate
```

---

## Model Routing

NEXUS uses a hybrid model strategy.

### Local Ollama models

Local models are used when privacy or task type matters:

| Config Key | Default | Purpose |
|---|---|---|
| `FAST_MODEL` | `qwen3:8b` | Fast replies |
| `CHAT_MODEL` | `qwen3:8b` | General local chat |
| `REASONING_MODEL` | `deepseek-r1:8b` | File and private reasoning |
| `CODER_MODEL` | `qwen2.5-coder:7b` | Code/system-style generation |

### OpenRouter cloud models

OpenRouter is used as the stronger cloud brain path for general conversation, reasoning, and web-style answers.

The chain is configured in `config.py`, and the brain attempts fallback models if one fails.

---

## Agents

NEXUS is built around specialist agents:

- **Chat Agent**: normal conversation.
- **Code Agent**: code generation, explanation, debugging, refactoring.
- **File Agent**: read/search/list/write/delete/move/copy/rename files.
- **Web Agent**: explanations, news-style answers, weather.
- **System Agent**: open apps, screenshots, volume, brightness, lock, sleep, restart, shutdown, process stats.
- **Security Agent**: Defender scans, threat checks, firewall state, open ports, startup items, suspicious processes.
- **WhatsApp Agent**: sends messages through WhatsApp Web using Playwright.
- **OpenClaw Agent**: delegates larger tasks to OpenClaw as an external subprocess.

The orchestrator decides which agent receives each command.

---

## Example Commands

```text
Activate
```

```text
Open Chrome
```

```text
Take a screenshot
```

```text
What is the weather in Delhi?
```

```text
Write Python code for a file organizer
```

```text
Search files for resume in C:\Users
```

```text
Show system stats
```

```text
Run a quick security scan
```

```text
Send hello to John on WhatsApp
```

```text
Sleep
```

---

## Security Vision

The current security agent is the foundation for a bigger system security assistant.

Planned or natural next upgrades:

- digital signature checks
- file hash reputation
- suspicious PowerShell analysis
- startup persistence inspection
- scheduled task inspection
- browser extension audit
- risk scoring
- quarantine workflow
- structured security reports

Important design note: the LLM should not be treated as the antivirus engine. Windows Defender, system telemetry, process inspection, signatures, and hashes should provide ground truth. AI should explain, correlate, prioritize, and guide.

---

## Current Prototype Notes

This project is powerful, but it is still experimental.

Known areas to harden:

- security agent registration should be verified in startup
- cancellation needs real task cancellation, not just UI feedback
- command parsing should handle quoted paths and spaces more reliably
- WhatsApp selectors may break when WhatsApp Web changes
- destructive actions should ask for confirmation
- automated tests are still limited
- some source comments/log text may contain encoding artifacts from earlier edits

Treat this as an ambitious prototype, not a finished production security tool.

---

## Safety Warning

NEXUS can control parts of your Windows machine.

Be careful with commands involving:

- deleting files
- killing processes
- running PowerShell
- shutdown/restart
- sending messages
- scanning private folders

Do not expose your `.env` file. Do not commit real API keys. Rotate any key that was accidentally stored in a file meant for GitHub.

---

## Documentation

A longer narrative architecture guide is included in:

```text
info/NEXUS_System_Story.md
info/NEXUS_System_Story.pdf
```

It explains the system like a story, from voice input all the way to spoken response.

---

## Roadmap

- Real cancellation support across agents
- Better security scanner and risk reports
- Safer command confirmation layer
- More robust natural-language parsing
- Better README screenshots/GIFs
- Plugin-style agent loading
- Test suite for routing and agent behavior
- Improved overlay customization
- Stronger local/cloud model failover

---

## Credits

Built as a Windows desktop AI assistant experiment using:

- Python
- PyQt6
- Faster-Whisper
- Edge TTS
- Ollama
- OpenRouter
- MediaPipe
- OpenCV
- Playwright
- psutil

---

<div align="center">

**CIPHER / NEXUS**

Cold Intelligence. Precise High-level Execution. Reasoning.

</div>
