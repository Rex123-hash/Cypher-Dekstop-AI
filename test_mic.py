import sounddevice as sd
import numpy as np

print("Recording 3 seconds... speak now!")
a = sd.rec(16000 * 3, samplerate=16000, channels=1, dtype='float32')
sd.wait()
rms = float(np.sqrt(np.mean(a**2)))
print(f"RMS: {rms:.4f}")
if rms < 0.005:
    print("PROBLEM: Mic not picking up sound or wrong device.")
    print("Available devices:")
    print(sd.query_devices())
else:
    print("Mic is working!")
