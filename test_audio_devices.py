import sounddevice as sd
print(sd.query_devices())
print("\nDefault output:", sd.default.device)
