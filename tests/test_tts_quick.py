"""
TTS Test Short - Quick verification
"""
import asyncio, sys
sys.path.insert(0, ".")

SHORT_TEXT = "Hola, esto es una prueba del sistema TTS. Si puedes escucharme, entonces funciona correctamente."

class MockUI:
    def set_audio_level(self, level): pass

async def test():
    print("Starting TTS test...")
    try:
        from services.audio.tts_service import TTSService
        tts = TTSService(MockUI())
        tts._loop = asyncio.get_event_loop()
        print(f"Speaking: {SHORT_TEXT[:50]}...")
        await tts.speak_local(SHORT_TEXT)
        print("TTS completed!")
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)
