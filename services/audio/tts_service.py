"""services/tts_service.py — Text-to-Speech using edge-tts"""

import os
import asyncio
import threading
import tempfile

import numpy as np
import sounddevice as sd
import edge_tts


class TTSService:
    def __init__(self, ui):
        self.ui = ui
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        self._stop_requested = asyncio.Event()
        self._loop = None
        self._last_speak_time = 0.0

    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
            if not value:
                self._stop_requested.clear()

    async def speak_local(self, text: str):
        """TTS local robusto utilizando edge-tts. Previene hoarseness o cortes."""
        import tempfile
        from services._core.helpers import strip_markdown
        from core.config_manager import get_config

        self.set_speaking(True)
        try:
            temp_path = os.path.join(tempfile.gettempdir(), f"min_local_tts_{os.getpid()}.mp3")

            clean_text = strip_markdown(text)

            cfg = get_config()
            rate = f"+{int((cfg.speech_rate or 1.0) * 15)}%" if cfg.speech_rate >= 1.0 else f"-{int((1.0 - cfg.speech_rate) * 15)}%"

            voices = {
                "Aoede": "es-US-PalomaNeural",
                "Kore": "es-MX-DaliaNeural",
                "Leda": "es-ES-ElviraNeural",
                "Zephyr": "es-US-AlonsoNeural",
                "Charon": "es-MX-JorgeNeural",
                "Puck": "es-ES-AlvaroNeural",
                "Fenrir": "es-AR-TomasNeural",
                "Orus": "es-CL-LorenzoNeural"
            }
            voice_code = voices.get(cfg.min_voice, "es-US-PalomaNeural")

            communicate = edge_tts.Communicate(clean_text, voice_code, rate=rate)
            await communicate.save(temp_path)

            def _play_and_wait():
                try:
                    import soundfile as sf
                    data, fs = sf.read(temp_path)

                    rms_multiplier = 25
                    block_size = 480

                    with sd.OutputStream(
                        samplerate=fs,
                        channels=len(data.shape) if len(data.shape) > 1 else 1,
                        dtype="float32",
                        blocksize=block_size
                    ) as stream:

                        idx = 0
                        while idx < len(data) and self._is_speaking and not self._stop_requested.is_set():
                            chunk = data[idx: idx + block_size]

                            try:
                                rms = float(np.sqrt(np.mean(chunk ** 2)))
                                self.ui.set_audio_level(min(1.0, rms * rms_multiplier))
                            except Exception:
                                pass

                            stream.write(chunk.astype(np.float32))
                            idx += block_size
                except Exception as pe:
                    print(f"[MIN] local play error: {pe}")
                finally:
                    try:
                        os.remove(temp_path)
                    except:
                        pass

            await asyncio.to_thread(_play_and_wait)
        except Exception as e:
            print(f"[MIN] TTS local error: {e}")

        self.set_speaking(False)

    def speak(self, text: str):
        """Dynamic text speaking function exposed to tools."""
        if not text:
            return
        print(f"[MIN] speak command: {text}")
        if self._loop:
            asyncio.run_coroutine_threadsafe(self.speak_local(text), self._loop)

    def speak_error(self, tool_name: str, error: str):
        msg = f"Señor, ocurrió un error en la herramienta {tool_name}."
        self.speak(msg)
