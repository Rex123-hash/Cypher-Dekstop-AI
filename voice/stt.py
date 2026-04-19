"""
STT — faster-whisper base model on RTX 4060 (CUDA float16).
Audio capture via sounddevice. Includes webrtcvad VAD and startup noise calibration.
"""
import io
import logging
import threading
import wave
from typing import Optional

import numpy as np
import sounddevice as sd
from faster_whisper import WhisperModel

import config

logger = logging.getLogger("cipher.stt")

SAMPLE_RATE    = 16000
CHANNELS       = 1
SILENCE_LIMIT  = 1.0     # seconds of silence to stop (was 1.5)
MAX_RECORD_SEC = 20
SILENCE_THRESH = 0.018   # base RMS threshold
MIN_AUDIO_SEC  = 0.8     # ignore anything shorter (eliminates air sounds)

try:
    import webrtcvad as _webrtcvad
    _VAD_OK = True
except ImportError:
    _VAD_OK = False
    logger.info("webrtcvad not installed — using RMS-only VAD")


def _rms(data: np.ndarray) -> float:
    return float(np.sqrt(np.mean(data ** 2)))


def _vad_check(audio: np.ndarray, vad) -> bool:
    """Return True if webrtcvad detects speech in at least 30% of frames."""
    frame_ms   = 20
    frame_samp = int(SAMPLE_RATE * frame_ms / 1000)
    pcm        = (audio * 32767).astype(np.int16).tobytes()
    speech = total = 0
    for i in range(0, len(pcm) - frame_samp * 2, frame_samp * 2):
        frame = pcm[i : i + frame_samp * 2]
        if len(frame) < frame_samp * 2:
            break
        try:
            if vad.is_speech(frame, SAMPLE_RATE):
                speech += 1
            total += 1
        except Exception:
            pass
    return (speech / max(total, 1)) >= 0.30


class STT:
    def __init__(self):
        self._model: Optional[WhisperModel] = None
        self._load_lock    = threading.Lock()
        self._noise_floor  = SILENCE_THRESH
        self._vad          = _webrtcvad.Vad(2) if _VAD_OK else None

    def calibrate_noise(self, seconds: float = 3.0):
        """Listen to background noise and set adaptive silence threshold."""
        logger.info(f"Calibrating background noise for {seconds:.0f}s — stay quiet…")
        chunk  = int(SAMPLE_RATE * 0.1)
        n      = int(seconds / 0.1)
        rms_vals = []
        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype="float32", blocksize=chunk) as stream:
            for _ in range(n):
                data, _ = stream.read(chunk)
                rms_vals.append(_rms(data))
        baseline = float(np.mean(rms_vals))
        self._noise_floor = max(SILENCE_THRESH, baseline * 1.25)
        logger.info(f"Noise floor set to {self._noise_floor:.4f}")

    def _ensure_model(self):
        if self._model is None:
            with self._load_lock:
                if self._model is None:
                    logger.info(f"Loading Whisper {config.WHISPER_MODEL} on {config.WHISPER_DEVICE}…")
                    self._model = WhisperModel(
                        config.WHISPER_MODEL,
                        device=config.WHISPER_DEVICE,
                        compute_type=config.WHISPER_COMPUTE_TYPE,
                    )
                    logger.info("Whisper model loaded.")

    def record(self) -> Optional[bytes]:
        """Record until silence, return WAV bytes or None if no valid speech."""
        chunk_size  = int(SAMPLE_RATE * 0.1)
        max_silent  = int(SILENCE_LIMIT / 0.1)
        max_chunks  = int(MAX_RECORD_SEC / 0.1)
        threshold   = max(self._noise_floor, SILENCE_THRESH)

        frames      = []
        silent_cks  = 0
        has_speech  = False

        with sd.InputStream(samplerate=SAMPLE_RATE, channels=CHANNELS,
                            dtype="float32", blocksize=chunk_size) as stream:
            for _ in range(max_chunks):
                data, _ = stream.read(chunk_size)
                rms      = _rms(data)
                frames.append(data.copy())
                if rms < threshold:
                    silent_cks += 1
                    if has_speech and silent_cks >= max_silent:
                        break
                else:
                    has_speech  = True
                    silent_cks  = 0

        if not has_speech:
            return None

        audio = np.concatenate(frames).flatten()

        # Minimum length check — rejects air sounds / mouth noises
        if len(audio) / SAMPLE_RATE < MIN_AUDIO_SEC:
            logger.debug("Audio too short — ignoring")
            return None

        # VAD confidence check
        if self._vad is not None and not _vad_check(audio, self._vad):
            logger.debug("VAD rejected — not enough speech patterns")
            return None

        pcm = (audio * 32767).astype(np.int16).tobytes()
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(CHANNELS)
            wf.setsampwidth(2)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm)
        return buf.getvalue()

    def transcribe(self, audio_bytes: bytes) -> str:
        self._ensure_model()
        buf = io.BytesIO(audio_bytes)
        segments, _ = self._model.transcribe(
            buf,
            language="en",
            beam_size=5,
            vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 300},
        )
        text = " ".join(seg.text.strip() for seg in segments).strip()
        logger.debug(f"Transcribed: {text}")
        return text

    def listen_and_transcribe(self) -> str:
        audio = self.record()
        if not audio:
            return ""
        try:
            return self.transcribe(audio)
        except Exception as e:
            logger.error(f"Transcription error: {e}")
            return ""


stt = STT()
