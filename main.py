"""
CIPHER — Cold Intelligence, Precise High-level Execution & Reasoning
Entry point: PyQt6 overlay, wake word, gesture detector, all agents.

Voice flow:
  Say "Cipher" / "Activate" → CIPHER wakes up and listens continuously
  Say "sleep"               → CIPHER goes idle, returns to wake word mode
"""
import asyncio
import logging
import sys
import threading
from typing import Optional

from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QScreen

import config
from ui.overlay import overlay
from voice.wake_word import WakeWordDetector
from voice.stt import stt
from voice.tts import tts
from gesture.detector import GestureDetector, Gesture
from agents.orchestrator import orchestrator
from agents.chat_agent import chat_agent
from agents.code_agent import code_agent
from agents.file_agent import file_agent
from agents.web_agent import web_agent
from agents.whatsapp_agent import whatsapp_agent
from agents.openclaw_agent import openclaw_agent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("cipher.main")

_loop: Optional[asyncio.AbstractEventLoop] = None
_active = False
_listen_thread = None


def run_coro(coro):
    if _loop and _loop.is_running():
        asyncio.run_coroutine_threadsafe(coro, _loop)


# ── Gesture handler ───────────────────────────────────────────────────────────

def on_gesture(gesture: Gesture):
    global _active
    logger.info(f"Gesture: {gesture.value}")
    overlay.log(f"Gesture: {gesture.value}")

    if gesture == Gesture.OPEN_PALM:
        _go_idle()
    elif gesture == Gesture.FIST:
        run_coro(orchestrator.cancel())
        overlay.log("Cancelled.")
        _go_idle()
    elif gesture == Gesture.THUMBS_UP:
        overlay.log("Confirmed.")
    elif gesture == Gesture.SWIPE_LEFT:
        _go_idle()
    elif gesture == Gesture.SWIPE_RIGHT:
        _go_active()


# ── Active / idle ─────────────────────────────────────────────────────────────

def _go_active():
    global _active, _listen_thread
    if _active:
        return
    _active = True
    overlay.activate("Listening…")
    overlay.log("CIPHER online — awaiting command")
    _listen_thread = threading.Thread(target=_continuous_listen, daemon=True)
    _listen_thread.start()


def _go_idle():
    global _active
    _active = False
    overlay.idle()
    overlay.log("CIPHER idle — say 'Cipher' to wake")
    overlay.agent_idle()


def _continuous_listen():
    global _active
    while _active:
        text = stt.listen_and_transcribe()
        if not text:
            continue

        logger.info(f"Heard: {text}")
        overlay.log(f"You: {text}")

        if any(w in text.lower() for w in ["sleep", "go to sleep", "goodbye", "stop listening"]):
            tts.speak("Going dark. Say Cipher to wake me.")
            _go_idle()
            return

        run_coro(_handle_command(text))

        import time
        time.sleep(0.5)


# ── Wake word callback ────────────────────────────────────────────────────────

def on_wake_word():
    if _active:
        return
    logger.info("Wake word detected.")
    tts.speak("CIPHER online.")
    _go_active()


# ── Command handler ───────────────────────────────────────────────────────────

async def _handle_command(text: str):
    import time as _time
    try:
        overlay.agent("Orchestrator", "Routing…")
        t0 = _time.monotonic()
        response = await orchestrator.handle(text)
        elapsed_ms = int((_time.monotonic() - t0) * 1000)
        overlay.set_response_time(elapsed_ms)
        logger.info(f"CIPHER: {response[:120]}")
        if response:
            overlay.response(response)
            overlay.log(f"CIPHER: {response[:120]}")
            tts.speak(response)
        overlay.agent_idle()
        overlay.activate()
    except Exception as e:
        logger.error(f"Command error: {e}")
        overlay.log(f"Error: {e}")
        overlay.agent_idle()


# ── Background event loop ─────────────────────────────────────────────────────

def _start_event_loop():
    global _loop
    _loop = asyncio.new_event_loop()
    asyncio.set_event_loop(_loop)
    _loop.run_forever()


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    threading.Thread(target=_start_event_loop, daemon=True).start()

    app = QApplication(sys.argv)
    app.setApplicationName("CIPHER")
    app.setQuitOnLastWindowClosed(False)
    screen: QScreen = app.primaryScreen()
    geom = screen.availableGeometry()
    sw, sh = geom.width(), geom.height()

    agents = [chat_agent, code_agent, file_agent, web_agent, whatsapp_agent, openclaw_agent]
    try:
        from agents.system_agent import system_agent
        agents.append(system_agent)
    except ImportError as e:
        logger.warning(f"system_agent not loaded: {e}")
    for agent in agents:
        orchestrator.register(agent)

    overlay.start(app, sw, sh)
    overlay.log("CIPHER initializing…")

    # Noise calibration before wake word starts
    threading.Thread(target=_calibrate, daemon=True).start()

    wake = WakeWordDetector(callback=on_wake_word)
    wake.start()

    gesture_det = GestureDetector(callback=on_gesture)
    gesture_det.start()

    if config.OPENROUTER_API_KEY:
        overlay.log("OpenRouter primary brain ready")

    overlay.idle()
    overlay.log("Say 'Cipher' to wake")
    logger.info("CIPHER fully started.")
    sys.exit(app.exec())


def _calibrate():
    import time
    time.sleep(2)  # let overlay settle first
    try:
        overlay.log("Calibrating microphone noise floor…")
        stt.calibrate_noise(3.0)
        overlay.log("Microphone calibrated.")
    except Exception as e:
        logger.warning(f"Calibration failed: {e}")


if __name__ == "__main__":
    main()
