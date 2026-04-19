import numpy as np
import sounddevice as sd
import winsound

print("Test 1: Windows beep (winsound)...")
winsound.Beep(1000, 1000)
print("Did you hear a beep? If yes, winsound works.")

print("\nTest 2: sounddevice sine wave...")
sr = 48000
t = np.linspace(0, 1.0, sr, dtype=np.float32)
tone = (np.sin(2 * np.pi * 440 * t) * 0.5).astype(np.float32)
sd.play(tone, samplerate=sr)
sd.wait()
print("Did you hear a 440Hz tone?")
