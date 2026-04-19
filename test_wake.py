import sounddevice as sd
import numpy as np
import io
import wave
from faster_whisper import WhisperModel

print("Loading Whisper (CPU)...")
model = WhisperModel("base", device="cpu", compute_type="int8")
print("Say 'Activate' now — recording 3 seconds...")

audio = sd.rec(16000 * 3, samplerate=16000, channels=1, dtype="float32")
sd.wait()

pcm = (audio.flatten() * 32767).astype(np.int16).tobytes()
buf = io.BytesIO()
with wave.open(buf, "wb") as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    wf.writeframes(pcm)
buf.seek(0)

segments, _ = model.transcribe(buf, language="en", beam_size=1, vad_filter=False)
text = " ".join(s.text for s in segments)
print(f"Heard: '{text}'")
detected = any(w in text.lower() for w in ["activate", "active", "activation", "nexus"])
print(f"Wake word detected: {detected}")
