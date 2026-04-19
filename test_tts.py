import asyncio, tempfile, subprocess
from pathlib import Path
from voice.tts import tts

async def test():
    print("Generating speech...")
    await tts.speak_async("NEXUS online. I am fully operational.")
    import time; time.sleep(5)
    print("Done.")

asyncio.run(test())
