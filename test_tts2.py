import asyncio, tempfile, wave, subprocess, av, numpy as np, edge_tts, os

async def test():
    print("Generating speech...")
    communicate = edge_tts.Communicate("NEXUS online. I am fully operational.", voice="en-US-GuyNeural")
    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
        mp3_path = tmp.name
    await communicate.save(mp3_path)

    container = av.open(mp3_path)
    stream = container.streams.audio[0]
    src_sr = stream.sample_rate
    frames = []
    for frame in container.decode(stream):
        arr = frame.to_ndarray()
        if arr.ndim > 1: arr = arr.mean(axis=0)
        frames.append(arr.astype(np.float32))
    container.close()
    audio = np.concatenate(frames)
    audio = audio / np.abs(audio).max() * 0.9
    new_len = int(len(audio) * 44100 / src_sr)
    audio = np.interp(np.linspace(0, len(audio)-1, new_len), np.arange(len(audio)), audio).astype(np.float32)
    pcm = (audio * 32767).astype(np.int16).tobytes()

    wav_path = r"E:\NEXUS\test_output.wav"
    with wave.open(wav_path, "wb") as wf:
        wf.setnchannels(1); wf.setsampwidth(2); wf.setframerate(44100)
        wf.writeframes(pcm)

    print(f"WAV saved to {wav_path}")
    print("Opening in Windows Media Player...")
    os.startfile(wav_path)
    print("Does it play in Media Player?")

asyncio.run(test())
