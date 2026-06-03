import os
import sys
import asyncio
import tempfile
import requests
from pathlib import Path
import numpy as np
import sounddevice as sd
import soundfile as sf

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

KOKORO_VOICE_MAP = {
    "Aoede": ("ef_dora", "es"),
    "Kore": ("ef_dora", "es"),
    "Leda": ("ef_dora", "es"),
    "Zephyr": ("em_alex", "es"),
    "Charon": ("em_santa", "es"),
    "Puck": ("em_alex", "es"),
    "Fenrir": ("em_santa", "es"),
    "Orus": ("em_alex", "es"),
}


def _strip_markdown(text: str) -> str:
    import re
    text = re.sub(r"\*+", "", text)
    text = re.sub(r"#+", "", text)
    text = re.sub(r"`", "", text)
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    text = re.sub(r"_+", "", text)
    return text.strip()


class KokoroEngine:
    _instance = None

    def __new__(cls, *args, **kwargs):
        if not cls._instance:
            cls._instance = super(KokoroEngine, cls).__new__(cls, *args, **kwargs)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._kokoro = None
        self._initialized = True

    def is_loaded(self) -> bool:
        return self._kokoro is not None

    def unload(self):
        if self._kokoro is not None:
            print("[TTS] Unloading Kokoro model from memory...")
            self._kokoro = None
            import gc
            gc.collect()

    def load_if_needed(self):
        from core.config_manager import get_config
        cfg = get_config()
        if cfg.active_provider == "gemini":
            if self._kokoro is not None:
                self.unload()
            return

        if self._kokoro is not None:
            return

        base_dir = Path(__file__).parent.parent.parent
        kokoro_dir = base_dir / "config" / "kokoro"
        model_path = kokoro_dir / "kokoro-v1.0.onnx"
        voices_path = kokoro_dir / "voices-v1.0.bin"

        model_url_v1 = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/v1.0.0/kokoro-v1.0.onnx"
        voices_url_v1 = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/v1.0.0/voices-v1.0.bin"
        model_url_fallback = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.onnx"
        voices_url_fallback = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin"

        if not model_path.exists() or not voices_path.exists():
            print("[TTS] Kokoro files not found. Starting download...")
            kokoro_dir.mkdir(parents=True, exist_ok=True)

            def download_with_fallback(url_primary, url_fallback, dest_path):
                print(f"[TTS] Attempting download from primary URL: {url_primary}")
                try:
                    r = requests.get(url_primary, stream=True)
                    r.raise_for_status()
                except Exception as e:
                    print(f"[TTS] Primary URL failed ({e}). Falling back to: {url_fallback}")
                    r = requests.get(url_fallback, stream=True)
                    r.raise_for_status()

                with open(dest_path, "wb") as f:
                    for chunk in r.iter_content(chunk_size=8192):
                        f.write(chunk)

            if not model_path.exists():
                download_with_fallback(model_url_v1, model_url_fallback, model_path)
            if not voices_path.exists():
                download_with_fallback(voices_url_v1, voices_url_fallback, voices_path)
            print("[TTS] Kokoro files downloaded successfully.")

        print("[TTS] Initializing Kokoro-82M ONNX model...")
        from kokoro_onnx import Kokoro
        self._kokoro = Kokoro(str(model_path), str(voices_path))

    def generate(self, text: str, voice_name: str, speed: float = 1.0) -> tuple[np.ndarray, int]:
        self.load_if_needed()
        if self._kokoro is None:
            raise RuntimeError("Kokoro engine is not loaded (active provider is Gemini).")

        kokoro_voice, lang = "ef_dora", "es"
        if voice_name in KOKORO_VOICE_MAP:
            kokoro_voice, lang = KOKORO_VOICE_MAP[voice_name]
        elif voice_name.startswith(("af_", "am_", "pm_", "bm_", "bf_")):
            kokoro_voice = voice_name
            lang = "en-us"

        samples, sample_rate = self._kokoro.create(
            text,
            voice=kokoro_voice,
            speed=speed,
            lang=lang
        )
        return samples, sample_rate


class TTSEngine:
    def __init__(self, voice_name: str = "PalomaNeural",
                 speech_rate: float = 1.0,
                 use_local: bool = True):
        self.voice_name = voice_name
        self.speech_rate = speech_rate
        self.use_local = use_local
        self.kokoro_engine = KokoroEngine()

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

        from core.config_manager import get_config
        cfg = get_config()
        if cfg.active_provider == "gemini":
            print("[TTS] Active provider is Gemini. Playing using edge-tts fallback...")
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
                data, fs = sf.read(temp_path)
                data = data.astype(np.float32)
                channels = data.shape[1] if data.ndim > 1 else 1
                idx = 0
                with sd.OutputStream(
                    samplerate=fs, channels=channels,
                    dtype="float32", blocksize=4096
                ) as stream:
                    while idx < len(data):
                        if stop_requested and stop_requested.is_set():
                            break
                        if is_speaking_func and not is_speaking_func():
                            break
                        chunk = data[idx: idx + 4096]
                        stream.write(chunk)
                        if on_audio_level:
                            try:
                                rms = float(np.sqrt(np.mean(chunk ** 2)))
                                on_audio_level(min(1.0, rms * 25.0))
                            except:
                                pass
                        idx += 4096
                return True
            except Exception as e:
                print(f"[TTS] edge-tts error: {e}")
                return False
            finally:
                try:
                    os.remove(temp_path)
                except:
                    pass
        else:
            try:
                clean = _strip_markdown(text)
                if not clean.strip():
                    return True

                samples, sample_rate = self.kokoro_engine.generate(clean, self.voice_name, self.speech_rate)
                idx = 0
                n = len(samples)
                block_size = 512

                with sd.OutputStream(
                    samplerate=sample_rate, channels=1,
                    dtype="float32", blocksize=block_size
                ) as stream:
                    while idx < n:
                        if stop_requested and stop_requested.is_set():
                            break
                        if is_speaking_func and not is_speaking_func():
                            break
                        chunk = samples[idx: idx + block_size]
                        if len(chunk) < block_size:
                            pad = np.zeros(block_size - len(chunk), dtype=np.float32)
                            chunk = np.concatenate([chunk, pad])
                        stream.write(chunk.astype(np.float32))
                        if on_audio_level:
                            try:
                                rms = float(np.sqrt(np.mean(chunk ** 2)))
                                on_audio_level(min(1.0, rms * 25.0))
                            except:
                                pass
                        idx += block_size
                return True
            except Exception as e:
                print(f"[TTS] Kokoro speak error: {e}")
                return False
