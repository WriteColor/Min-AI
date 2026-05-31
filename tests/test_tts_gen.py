"""
TTS Generation Test - Generate MP3 without playing
"""
import asyncio
import sys
import os
import tempfile
sys.path.insert(0, ".")

TEXT = "Hola, esto es una prueba del sistema TTS. Si puedes escucharme, entonces funciona correctamente."

async def test():
    print("Testing TTS MP3 generation...")
    try:
        import edge_tts
        temp_path = os.path.join(tempfile.gettempdir(), "min_tts_test.mp3")

        voice = "es-US-PalomaNeural"
        rate = "+15%"
        volume = "+0%"

        communicate = edge_tts.Communicate(TEXT, voice, rate=rate, volume=volume)
        await communicate.save(temp_path)

        size = os.path.getsize(temp_path)
        print(f"MP3 generated: {temp_path}")
        print(f"File size: {size} bytes")
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)
