# NEXUS System Story

This is the story of how NEXUS works, from the moment you say a wake word to the moment it answers back.

## The Big Idea

NEXUS is not one giant AI blob. It is more like a team living inside your PC.

One teammate listens for a wake word.
One teammate records your voice.
One teammate turns sound into text.
One teammate decides which specialist should handle the request.
One teammate speaks the answer back.
And floating above everything is the HUD, the glowing overlay that makes the whole thing feel alive.

At the center of this crew is a traffic-control room called the orchestrator, and behind that sits the brain router. The orchestrator decides *who* should do the job. The brain router decides *which AI model* should think about the job.

So when you talk to NEXUS, you are not talking to one file. You are triggering a chain of listeners, agents, models, UI layers, and system tools.

## The Story of a Command

Imagine this moment:

You say, "Activate."

The wake-word detector is already listening in the background. Its first job is to decide whether the sound coming from your microphone is the magic phrase that should wake the system.

If Picovoice Porcupine is available, NEXUS uses that as a dedicated wake-word engine. If not, it falls back to Faster-Whisper and fuzzy matching. Either way, once the detector believes you said "Cipher" or "Activate," it calls back into `main.py`.

`main.py` is the mission-control file of the whole project. It starts the app, launches the overlay, spins up the async event loop, registers the agents, starts wake-word listening, starts gesture detection, and kicks off microphone calibration.

When the wake callback fires, `main.py` switches NEXUS from idle mode into active mode.

The overlay changes state.
The HUD glows brighter.
The system logs that NEXUS is now online.
And a dedicated listening thread begins capturing your real command.

Now you say:

"Open Chrome and tell me the latest news about AI."

The speech-to-text system in `voice/stt.py` takes over. It records audio from the microphone, watches the sound level, waits for speech, and stops when silence lasts long enough. If `webrtcvad` is installed, it uses that too, to make sure the audio sounds like actual speech instead of random noise.

Once it has a valid chunk of audio, Faster-Whisper transcribes it into text.

Now the computer is no longer dealing with sound. It is dealing with language.

That text is passed to `_handle_command()` in `main.py`, which forwards the request to the orchestrator.

The orchestrator lives in `agents/orchestrator.py`. Think of it as the dispatcher at a futuristic control desk. It looks at your command and asks:

- Is this a chat question?
- Is it about files?
- Is it about the web?
- Is it a system control request?
- Is it code-related?
- Is it a WhatsApp message?

First it tries regex-based keyword routing because that is fast and cheap. If the keywords are unclear, it asks the AI brain to classify the request into one of the supported categories.

Once the orchestrator chooses an agent, it hands the text to that specialist.

If the command sounds like a web question, the `web_agent` handles it.
If it sounds like a code request, the `code_agent` handles it.
If it sounds like a file operation, the `file_agent` handles it.
If it sounds like a system command, the `system_agent` takes over.

That agent either performs an action directly or asks the brain for help.

The result comes back to `main.py`.
The overlay logs the answer.
The HUD animates like the system is thinking.
And the text-to-speech layer turns that answer into spoken audio.

You hear the reply.

That is the full loop:

**wake -> listen -> transcribe -> route -> think or act -> display -> speak**

## The Core Files

### `main.py`

This is the launch pad. It does the following:

- starts the background asyncio loop
- creates the Qt application
- registers all the loaded agents
- starts the overlay
- starts mic calibration
- starts the wake-word detector
- starts the gesture detector
- handles the final command-response cycle

If you had to point to the "boss" file of the project, this is it.

### `config.py`

This is the control panel for settings:

- API keys
- model names
- OpenRouter URLs
- Ollama base URL
- wake word
- TTS voice
- Whisper device and precision
- gesture settings
- display size
- neon UI colors
- project data paths

This file exists so you can swap models, keys, voices, and hardware settings without digging through all the code.

### `.env` and `.env.example`

These exist so secrets and machine-specific settings do not have to be hardcoded. They are where you put:

- API keys
- custom model names
- host URLs
- optional device settings

`.env.example` is the template. `.env` is the real local config.

### `requirements.txt`

This is the ingredient list for the whole machine. Every package in it supports a major feature, which we will break down later.

## The `core/` Layer

### `core/brain.py`

This file is the model-routing brain. It decides *which model should think about what*.

It does not assume one model is best at every task. Instead, it uses different models for different types of work.

General chat and reasoning can go through OpenRouter first.
Code and system-style work prefer the local coder model.
Privacy-sensitive file reasoning prefers the local reasoning model.

So `brain.py` is not just "call AI." It is a strategy file for choosing the right AI.

### `core/openrouter.py`

This is the OpenRouter client. It wraps the HTTP calls to the OpenRouter API and sends OpenAI-style chat requests.

It handles:

- authorization headers
- model selection
- message payload creation
- basic failure handling

Without this file, the brain would have no clean way to talk to OpenRouter.

### `core/memory.py`

This is short-term memory. It stores recent conversation turns in a rolling deque and saves them to `data/conversation_history.json`.

Its job is to let NEXUS remember recent context instead of treating every command as if it happened in a vacuum.

## The `voice/` Layer

### `voice/wake_word.py`

This file is the sleeping ear.

It listens in the background for:

- `Cipher`
- `Activate`
- close fuzzy matches

Primary mode:

- Picovoice Porcupine if a key and model file are available

Fallback mode:

- Faster-Whisper on short audio snippets
- fuzzy string matching against wake phrases

This file exists so NEXUS can stay mostly asleep until you intentionally wake it.

### `voice/stt.py`

This is the speech-to-text engine.

It:

- records microphone input
- calculates RMS loudness
- detects silence
- optionally uses WebRTC VAD
- loads the Faster-Whisper model
- transcribes audio into English text

This is the bridge between sound and language.

### `voice/tts.py`

This is the speaking mouth of NEXUS. It takes response text and turns it into spoken audio using `edge-tts`.

Without this layer, NEXUS would feel like a silent dashboard instead of a voice assistant.

## The `ui/` Layer

### `ui/overlay.py`

This is the cinematic shell of the whole project.

It creates a transparent, always-on-top, frameless PyQt6 window and manually paints the HUD with `QPainter`.

It is responsible for:

- the center orb
- animated rings
- side panels
- waveform display
- activity logs
- system stats
- corner brackets
- scan lines
- neon glow effects

Instead of building a normal business-app interface with standard widgets, this file paints the entire experience like a sci-fi control system. That is why the project feels like a JARVIS-style assistant instead of a regular Python desktop program.

## The `gesture/` Layer

### `gesture/detector.py`

This file uses computer vision to detect hand gestures through the webcam.

Those gestures are then mapped to actions such as:

- going idle
- cancelling
- confirming
- waking

It gives NEXUS a second input channel beyond voice.

## The `agents/` Layer

The agents are specialists. Each one has a `handle(command)` method. The orchestrator picks one and sends the command there.

### `agents/orchestrator.py`

This is the traffic officer.

It:

- registers the agents
- uses regex keyword routing
- falls back to AI classification if needed
- calls the chosen agent
- stores the command and response in memory

It decides *who* should act, but not *how* they act internally.

### `agents/chat_agent.py`

This is the conversational specialist. It pulls recent context from memory and asks the brain for a natural reply.

Use it for normal back-and-forth interaction.

### `agents/code_agent.py`

This one handles:

- generating code
- explaining code
- debugging code
- refactoring code
- optionally invoking Codex CLI
- writing temporary code files and running them

It exists for programming and automation tasks.

### `agents/file_agent.py`

This is the file-system worker.

It can:

- list folders
- search for files
- read files
- write files
- delete files
- move files
- copy files
- rename files
- report disk usage
- ask the reasoning model to analyze file contents

This file exists so NEXUS can interact with the drive as more than just a chatbot.

### `agents/web_agent.py`

This one handles:

- general knowledge questions
- topic explanations
- latest-news style prompts
- weather checks via `wttr.in`

It mostly relies on the cloud brain because web-style knowledge is one of the places where stronger remote models help most.

### `agents/system_agent.py`

This is the Windows control specialist.

It can:

- open apps
- close apps
- kill processes
- take screenshots
- change volume
- mute audio
- change brightness
- lock the PC
- sleep, restart, or shut down the PC
- show system stats
- list top processes
- run raw PowerShell or CMD commands
- type text into the active window

This is one of the most powerful agents because it directly touches the operating system.

### `agents/security_agent.py`

This is the beginning of a future security layer.

It can:

- trigger Windows Defender scans
- check current threats
- inspect firewall profiles
- list open ports
- inspect startup items
- look for suspicious processes
- generate a security report

It is not yet a full cybersecurity engine, but it is the seed of one.

### `agents/whatsapp_agent.py`

This file uses Playwright to automate WhatsApp Web.

It:

- opens a persistent browser session
- waits for login
- searches for a contact
- fills in a message
- presses Enter to send

This is how NEXUS jumps from "assistant" into actual browser automation.

### `agents/openclaw_agent.py`

This is the bridge to OpenClaw.

Instead of re-implementing OpenClaw internally, NEXUS launches it as an external subprocess. It streams OpenClaw's stdout line by line into the NEXUS activity log and returns the combined result at the end.

That means OpenClaw acts like a heavy-duty external operative that NEXUS can delegate to.

## How the Brain Chooses Models

Inside `core/brain.py`, there are multiple pathways:

- `fast()`
- `chat()`
- `web_search()`
- `code()`
- `reason()`
- `heavy_reason()`
- `complex_task()`
- `multi_agent()`
- `smart()`

### OpenRouter as the Main Brain

For general chat and reasoning, the project tries OpenRouter first.

The configured chain is:

- heavy reasoning model
- complex-task model
- multi-agent fallback model

If those fail, chat can fall back to local Ollama.

That makes OpenRouter the main cloud brain for rich answers, while Ollama acts as the local safety net.

### Local Models

Local models are used for tasks where privacy or determinism matters more:

- code generation
- system-style instructions
- file analysis

That means the system is trying to combine the best of both worlds:

- cloud strength for broad intelligence
- local privacy and control for sensitive work

## How OpenRouter Free Models Fit In

OpenRouter gives NEXUS access to stronger cloud models without locking the project to one provider.

The project uses OpenRouter as:

- the main general-purpose chat layer
- the main reasoning layer
- a fallback chain when one remote model fails

Why this matters:

- better general answers
- better world knowledge
- resilience through fallback
- easy swapping of models in `config.py`

So OpenRouter is not a side feature. It is the main external intelligence backbone.

## How OpenClaw Fits In

OpenClaw is integrated as a subprocess tool rather than a normal in-process Python module.

That means NEXUS can:

- build an OpenClaw task string
- launch OpenClaw
- stream its output live
- stop it if needed

That design keeps the systems loosely coupled. NEXUS remains the coordinator. OpenClaw remains its own powerful subsystem.

## How to Add a New Agent

Adding a new agent is straightforward.

### Step 1: create the file

Make a new file inside `agents/`, for example:

`music_agent.py`

### Step 2: create the class

Give it a `name` and a `handle()` method:

```python
class MusicAgent:
    name = "music"

    async def handle(self, command: str) -> str:
        return "Playing music."


music_agent = MusicAgent()
```

### Step 3: import it in `main.py`

Register it with the orchestrator.

### Step 4: teach the orchestrator how to route to it

Either:

- add a regex rule to `ROUTE_MAP`
- or expand the AI classifier categories

That is the pattern for scaling NEXUS into a larger assistant.

## How to Swap Models in the Future

This project is already set up well for model-swapping because model names are centralized in `config.py` and can be overridden from `.env`.

If you want to change:

- coder model -> change `CODER_MODEL`
- chat model -> change `CHAT_MODEL`
- reasoning model -> change `REASONING_MODEL`
- fast model -> change `FAST_MODEL`
- OpenRouter model choices -> change the OpenRouter constants

Because `brain.py` is the abstraction layer, most model changes can happen without rewriting every agent.

That is one of the most future-proof parts of the design.

## Common Problems and Fixes

### Wake word not triggering

Possible causes:

- wrong microphone selected
- no Picovoice key
- fallback Whisper too slow
- background noise too high

Fixes:

- confirm mic works with the test scripts
- lower noise in the room
- verify Whisper device config
- verify Picovoice files and key

### Speech-to-text feels slow

Possible causes:

- CPU fallback instead of CUDA
- Whisper model loading delay
- duplicate model usage across STT and wake-word paths

Fixes:

- confirm CUDA is working
- preload models carefully
- consider using a lighter wake-word path

### No spoken response

Possible causes:

- `edge-tts` issue
- bad voice name
- audio output device mismatch

Fixes:

- test TTS separately
- verify the configured voice in `.env`

### Overlay not rendering

Possible causes:

- PyQt6 not installed correctly
- transparency issues
- graphics-driver oddities

Fixes:

- reinstall UI dependencies
- test with a simpler PyQt window

### WhatsApp automation failing

Possible causes:

- not logged in
- QR session expired
- frontend selectors changed

Fixes:

- re-authenticate
- inspect current WhatsApp Web selectors

### Security commands not doing anything

At the moment, one real architectural issue is that the security agent exists but is not currently registered in startup registration in `main.py`. That means some routed security requests will not actually reach a loaded agent until that is fixed.

### Cancel gesture says "Cancelled" but task keeps going

The UI suggests cancellation, but the orchestrator cancel method is still a stub. That means visual cancellation and real cancellation are not yet the same thing.

## Every Line in `requirements.txt`

### UI

- `PyQt6>=6.7.0`
  The desktop UI toolkit that powers the overlay window and event system.

- `PyQt6-Qt6>=6.7.0`
  The Qt runtime layer used by PyQt6.

### Voice

- `faster-whisper>=1.0.3`
  Speech-to-text engine and fallback wake-word recognition path.

- `edge-tts>=6.1.12`
  Text-to-speech voice output.

### Gesture

- `opencv-python>=4.9.0.80`
  Camera/image processing.

- `mediapipe>=0.10.14`
  Hand tracking and gesture recognition.

### Browser automation

- `playwright>=1.44.0`
  Browser control for WhatsApp Web and future web automations.

### System monitoring

- `psutil>=5.9.8`
  CPU, RAM, process, and system inspection.

- `gputil>=1.4.0`
  GPU usage and VRAM stats for the HUD.

### AI

- `google-generativeai>=0.7.0`
  Support for Gemini-style integration, even if not currently central to the main routing path.

- `openai>=1.30.0`
  OpenAI-compatible client support, useful because OpenRouter follows an OpenAI-like API style.

- `httpx>=0.27.0`
  Async HTTP client used for OpenRouter and web requests.

### Utilities

- `python-dotenv>=1.0.1`
  Loads `.env` values into Python at startup.

- `numpy>=1.26.4`
  Audio math, signal handling, RMS calculations, and array operations.

## Final Picture

NEXUS is a layered desktop AI system built around one dramatic illusion:

that you are speaking to a single futuristic intelligence.

But under the surface, that illusion is created by many moving parts:

- a wake-word listener
- a speech recognizer
- a routing orchestrator
- specialist agents
- a model-selection brain
- a transparent PyQt HUD
- a text-to-speech voice
- optional browser automation
- optional OpenClaw delegation

When it all works together, the experience feels simple:

You speak.
NEXUS wakes.
NEXUS understands.
NEXUS decides.
NEXUS acts.
NEXUS answers.

That simplicity is the magic trick.

Under the hood, it is a chain of carefully timed systems working together like the bridge crew of a starship.
