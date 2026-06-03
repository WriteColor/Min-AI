"""
TTS Test for non-Gemini providers (Vosk / Edge-TTS / Kokoro hybrid pipeline)
"""
import asyncio
import sys
import os

sys.path.insert(0, ".")

TEXT = (
    "Hola, mi hermano, quería contarte que ya terminé la tarea. "
    "El sistema de audio ahora segmenta correctamente y no se corta entre las comas. "
    "¿Qué opinas de este nuevo flujo continuo de sonido?"
)

class MockUI:
    def set_audio_level(self, level):
        pass

async def test():
    print("Starting Non-Gemini TTS test...")
    try:
        from core.config_manager import get_config_manager
        cfg = get_config_manager()
        
        # Save current provider to restore later
        old_provider = cfg.get("active_provider")
        
        # Set active provider to non-gemini to trigger the local streaming/Edge-TTS/Kokoro pipeline
        cfg.set("active_provider", "openrouter")
        print(f"Set active_provider to: {cfg.get('active_provider')}")
        
        try:
            from services.audio.tts_service import TTSService
            tts = TTSService(MockUI())
            tts._loop = asyncio.get_event_loop()
            
            print(f"Speaking: {TEXT}")
            await tts.speak_local(TEXT)
            print("TTS completed!")
        finally:
            # Restore old provider
            cfg.set("active_provider", old_provider)
            print(f"Restored active_provider to: {cfg.get('active_provider')}")
            
        return True
    except Exception as e:
        print(f"TTS Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test())
    sys.exit(0 if result else 1)
