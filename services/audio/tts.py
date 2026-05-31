import asyncio
import os
import tempfile

import numpy as np

import sounddevice as sd
import soundfile as sf

CHUNK_SIZE = 4096
VOICE_MAP = {
    "Aoede": "es-US-PalomaNeural",
    "Kore": "es-MX-DaliaNeural",
    "Leda": "es-ES-ElviraNeural",
    "Zephyr": "es-US-AlonsoNeural",
    "Charon": "es-MX-JorgeNeural",
    "Puck": "es-ES-AlvaroNeural",
    "Fenrir": "es-AR-TomasNeural",
    "Orus": "es-CL-LorenzoNeural",
}


def _strip_markdown(text: str) -> str:
    import re
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"#+", "", text)
    text = re.sub(r"`", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"_+", "", text)
    return text.strip()


class TTSEngine:
    def __init__(self, voice_name: str = "PalomaNeural",
                 speech_rate: float = 1.0,
                 use_local: bool = True):
        self.voice_name = voice_name
        self.speech_rate = speech_rate
        self.use_local = use_local

    def _resolve_voice(self) -> str:
        if self.voice_name in VOICE_MAP:
            return VOICE_MAP[self.voice_name]
        return self.voice_name

    def _rate_str(self) -> str:
        r = self.speech_rate
        if r >= 1.0:
            return f"+{int(r * 15)}%"
        return f"-{int((1.0 - r) * 15)}%"

    async def speak(self, text: str,
                    on_audio_level=None,
                    is_speaking_func=None,
                    stop_requested=None) -> bool:
        if not self.use_local:
            return False
        import edge_tts
        clean = _strip_markdown(text)
        voice = self._resolve_voice()
        rate = self._rate_str()
        temp_path = os.path.join(
            tempfile.gettempdir(),
            f"jarvis_tts_{os.getpid()}.mp3"
        )
        try:
            comm = edge_tts.Communicate(clean, voice, rate=rate)
            await comm.save(temp_path)
        except Exception as e:
            print(f"[TTS] generation error: {e}")
            return False
        try:
            data, fs = sf.read(temp_path)
            data = data.astype(np.float32)
            channels = data.shape[1] if data.ndim > 1 else 1
            idx = 0
            with sd.OutputStream(
                samplerate=fs, channels=channels,
                dtype="float32", blocksize=CHUNK_SIZE
            ) as stream:
                while idx < len(data):
                    if stop_requested and stop_requested.is_set():
                        break
                    if is_speaking_func and not is_speaking_func():
                        break
                    chunk = data[idx: idx + CHUNK_SIZE]
                    stream.write(chunk)
                    if on_audio_level:
                        try:
                            rms = float(np.sqrt(np.mean(chunk ** 2)))
                            on_audio_level(min(1.0, rms * 25.0))
                        except Exception:
                            pass
                    idx += CHUNK_SIZE
        except Exception as e:
            print(f"[TTS] playback error: {e}")
            return False
        finally:
            try:
                os.remove(temp_path)
            except Exception:
                pass
        return True
