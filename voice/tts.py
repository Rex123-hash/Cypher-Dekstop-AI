"""
TTS — edge-tts en-US-GuyNeural with Ultron-style voice processing.
Deeper pitch, slower rate, bass boost + reverb via numpy, no UI window.
"""
import asyncio
import logging
import re
import subprocess
import tempfile
import threading
import wave
from pathlib import Path
from typing import Optional

import av
import numpy as np
import edge_tts

import config

logger = logging.getLogger("cipher.tts")

TARGET_SR = 44100

# ── Text cleaning ─────────────────────────────────────────────────────────────

_EMOJI_RE = re.compile(
    "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF"
    "\U0001F1E0-\U0001F1FF\U00002600-\U000027BF\U0001F900-\U0001F9FF"
    "\U0001FA00-\U0001FAFF\U00002702-\U000027B0]+",
    flags=re.UNICODE,
)
_MARKDOWN_RE = re.compile(r"[*_`#~>\[\]]+")
_MULTI_SPACE = re.compile(r"  +")


def _clean_text(text: str, max_sentences: int = 3) -> str:
    """Strip emojis, markdown, asterisks; trim to max_sentences."""
    text = _EMOJI_RE.sub("", text)
    text = _MARKDOWN_RE.sub("", text)
    text = _MULTI_SPACE.sub(" ", text).strip()
    # Trim to N sentences
    parts = re.split(r"(?<=[.!?])\s+", text)
    return " ".join(parts[:max_sentences]).strip()


# ── Audio FX (Ultron voice: bass boost + subtle reverb) ───────────────────────

def _apply_ultron_fx(audio: np.ndarray, sr: int) -> np.ndarray:
    """Bass boost 0-250 Hz and add subtle room reverb via numpy."""
    a = audio.astype(np.float64)

    # Bass boost via FFT
    spec  = np.fft.rfft(a)
    freqs = np.fft.rfftfreq(len(a), 1.0 / sr)
    for i, f in enumerate(freqs):
        if f < 80:
            spec[i] *= 1.9
        elif f < 280:
            t = (f - 80) / 200.0
            spec[i] *= 1.9 - t * 0.9   # 1.9 → 1.0

    boosted = np.fft.irfft(spec, n=len(a))

    # Subtle reverb — 2 short delay echoes
    result = boosted.copy()
    for delay_s, decay in [(0.018, 0.20), (0.034, 0.10)]:
        d    = int(delay_s * sr)
        echo = np.zeros_like(boosted)
        if d < len(boosted):
            echo[d:] = boosted[:-d] * decay
        result += echo

    peak = np.abs(result).max()
    if peak > 0:
        result = result / peak * 0.88
    return result.astype(np.float32)


# ── MP3 → WAV conversion ──────────────────────────────────────────────────────

def _resample(audio: np.ndarray, from_sr: int, to_sr: int) -> np.ndarray:
    if from_sr == to_sr:
        return audio
    new_len = int(len(audio) * to_sr / from_sr)
    return np.interp(
        np.linspace(0, len(audio) - 1, new_len),
        np.arange(len(audio)), audio,
    ).astype(np.float32)


def _mp3_to_wav(mp3_path: str, wav_path: str):
    container = av.open(mp3_path)
    stream    = container.streams.audio[0]
    src_sr    = stream.sample_rate
    frames    = []
    for frame in container.decode(stream):
        arr = frame.to_ndarray()
        if arr.ndim > 1:
            arr = arr.mean(axis=0)
        frames.append(arr.astype(np.float32))
    container.close()

    audio = np.concatenate(frames) if frames else np.zeros(TARGET_SR, dtype=np.float32)
    peak  = np.abs(audio).max()
    if peak > 0:
        audio = audio / peak * 0.9

    audio = _resample(audio, src_sr, TARGET_SR)
    audio = _apply_ultron_fx(audio, TARGET_SR)

    pcm = (audio * 32767).astype(np.int16).tobytes()
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(TARGET_SR)
        wf.writeframes(pcm)


# ── Playback ──────────────────────────────────────────────────────────────────

def _play_wav(wav_path: str):
    abs_path = str(Path(wav_path).resolve())
    subprocess.run(
        ["powershell", "-NoProfile", "-NonInteractive", "-Command",
         f"Add-Type -AssemblyName System.Windows.Forms; "
         f"$p = New-Object System.Media.SoundPlayer; "
         f"$p.SoundLocation = '{abs_path}'; "
         f"$p.PlaySync()"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )


# ── TTS class ─────────────────────────────────────────────────────────────────

class TTS:
    def __init__(self):
        self.voice     = config.TTS_VOICE
        self.rate      = config.TTS_RATE
        self.pitch     = config.TTS_PITCH
        self._speaking = False

    async def speak_async(self, text: str, voice: Optional[str] = None):
        text = _clean_text(text)
        if not text:
            return
        v = voice or self.voice
        try:
            communicate = edge_tts.Communicate(text, voice=v, rate=self.rate, pitch=self.pitch)
            with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                mp3_path = tmp.name
            await communicate.save(mp3_path)
            threading.Thread(target=self._play, args=(mp3_path,), daemon=True).start()
        except Exception as e:
            logger.error(f"TTS error: {e}")

    def speak(self, text: str, voice: Optional[str] = None):
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.ensure_future(self.speak_async(text, voice))
            else:
                loop.run_until_complete(self.speak_async(text, voice))
        except RuntimeError:
            asyncio.run(self.speak_async(text, voice))

    def _play(self, mp3_path: str):
        wav_path = mp3_path.replace(".mp3", ".wav")
        try:
            self._speaking = True
            _mp3_to_wav(mp3_path, wav_path)
            _play_wav(wav_path)
        except Exception as e:
            logger.error(f"Audio playback error: {e}")
        finally:
            self._speaking = False
            Path(mp3_path).unlink(missing_ok=True)
            Path(wav_path).unlink(missing_ok=True)

    def stop(self):
        self._speaking = False

    @property
    def is_speaking(self) -> bool:
        return self._speaking

    async def list_voices(self) -> list[str]:
        voices = await edge_tts.list_voices()
        return [v["ShortName"] for v in voices if "en-" in v["ShortName"]]


tts = TTS()
