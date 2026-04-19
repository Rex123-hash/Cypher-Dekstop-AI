"""
Wake word detector — listens for "Cipher" / "Activate".
Primary: pvporcupine (if PICOVOICE_KEY + .ppn file available).
Fallback: faster-whisper with fuzzy matching + webrtcvad pre-filter.
"""
import difflib
import io
import logging
import threading
import wave
from pathlib import Path
from typing import Callable

import numpy as np
import sounddevice as sd

import config

logger = logging.getLogger("cipher.wake_word")

SAMPLE_RATE    = 16000
CHANNELS       = 1
LISTEN_SEC     = 2.5
SILENCE_THRESH = 0.005   # sensitive — catches quiet speech
_WAKE_VARIANTS = {"cipher", "activate", "active", "activation", "nexus", "hey cipher"}
_FUZZY_THRESH  = 0.72    # similarity ratio for fuzzy match


def _is_wake(text: str) -> bool:
    lower = text.lower().strip()
    for v in _WAKE_VARIANTS:
        if v in lower:
            return True
    for word in lower.split():
        if (difflib.SequenceMatcher(None, word, "cipher").ratio() >= _FUZZY_THRESH or
                difflib.SequenceMatcher(None, word, "activate").ratio() >= _FUZZY_THRESH):
            return True
    return False


# ── Porcupine engine (optional) ───────────────────────────────────────────────

def _try_porcupine(callback: Callable) -> bool:
    """
    Attempt to start pvporcupine wake word engine.
    Requires: pip install pvporcupine, PICOVOICE_KEY in .env,
              and a cipher.ppn model file in the assets folder.
    Returns True if successfully started.
    """
    key     = config.PICOVOICE_KEY
    ppn     = Path(config.BASE_DIR) / "assets" / "cipher_en_windows_v3_0_0.ppn"
    if not key or not ppn.exists():
        return False
    try:
        import pvporcupine
        import struct
        porcupine = pvporcupine.create(
            access_key=key,
            keyword_paths=[str(ppn)],
            sensitivities=[0.7],
        )
        logger.info("pvporcupine engine started — listening for 'Cipher'.")

        def _loop():
            chunk = porcupine.frame_length
            with sd.InputStream(samplerate=porcupine.sample_rate, channels=1,
                                 dtype="int16", blocksize=chunk) as stream:
                while True:
                    pcm, _ = stream.read(chunk)
                    pcm_list = pcm.flatten().tolist()
                    idx = porcupine.process(pcm_list)
                    if idx >= 0:
                        logger.info("Wake word detected (porcupine)!")
                        callback()

        threading.Thread(target=_loop, daemon=True).start()
        return True
    except Exception as e:
        logger.warning(f"pvporcupine unavailable: {e}")
        return False


# ── Whisper fallback detector ─────────────────────────────────────────────────

class WakeWordDetector:
    def __init__(self, callback: Callable[[], None]):
        self.callback  = callback
        self._running  = False
        self._thread   = None
        self._model    = None

    def _load_model(self):
        if self._model is None:
            from faster_whisper import WhisperModel
            logger.info("Loading wake word Whisper model…")
            self._model = WhisperModel(
                config.WHISPER_MODEL,
                device=config.WHISPER_DEVICE,
                compute_type=config.WHISPER_COMPUTE_TYPE,
            )
            logger.info("Wake word model ready.")

    def start(self):
        if _try_porcupine(self.callback):
            return   # porcupine is handling it
        self._running = True
        self._thread  = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
        logger.info("Wake word detector started (whisper) — say 'Cipher' or 'Activate'.")

    def stop(self):
        self._running = False

    def _listen_loop(self):
        self._load_model()
        chunk_samples = int(SAMPLE_RATE * LISTEN_SEC)
        while self._running:
            try:
                audio = sd.rec(chunk_samples, samplerate=SAMPLE_RATE,
                               channels=CHANNELS, dtype="float32")
                sd.wait()
                rms = float(np.sqrt(np.mean(audio ** 2)))
                if rms < SILENCE_THRESH:
                    continue
                text = self._transcribe(audio.flatten())
                logger.debug(f"Wake check: {text!r}")
                if _is_wake(text):
                    logger.info("Wake word detected!")
                    self.callback()
            except Exception as e:
                logger.error(f"Wake word loop error: {e}")

    def _transcribe(self, audio: np.ndarray) -> str:
        pcm = (audio * 32767).astype(np.int16).tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm)
        buf.seek(0)
        segments, _ = self._model.transcribe(
            buf, language="en", beam_size=1, vad_filter=False
        )
        return " ".join(s.text for s in segments)
