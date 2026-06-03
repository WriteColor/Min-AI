from typing import Any, Optional

import numpy as np

from services.audio.vad import VAD
from services.audio.wake_word import WakeWordDetector
from services.audio.stt import STTEngine
from services.audio.tts import TTSEngine

SAMPLE_RATE = 16000
CHANNELS = 1
CHUNK_SIZE = 4096


class AudioPipeline:
    def __init__(self, sample_rate: int = SAMPLE_RATE,
                 channels: int = CHANNELS,
                 chunk_size: int = CHUNK_SIZE,
                 vosk_model_path: str = "config/vosk_model",
                 wake_keywords: Optional[list[str]] = None,
                 rms_threshold: float = 0.0005,
                 voice_name: str = "Zephyr",
                 speech_rate: float = 1.0):
        self.sample_rate = sample_rate
        self.channels = channels
        self.chunk_size = chunk_size

        self.vad = VAD(sample_rate=sample_rate, rms_threshold=rms_threshold)
        self.wake_word = WakeWordDetector(
            model_path=vosk_model_path,
            keywords=wake_keywords,
            sample_rate=sample_rate
        )
        self.stt = STTEngine(
            model_path=vosk_model_path,
            sample_rate=sample_rate
        )
        self.tts = TTSEngine(
            voice_name=voice_name,
            speech_rate=speech_rate
        )

        self._buffer: list[np.ndarray] = []
        self._buffer_len: int = 0
        self._max_buffer_sec: float = 15.0
        self._max_buffer_samples: int = int(sample_rate * self._max_buffer_sec)
        self._is_sleeping: bool = True
        
        # Silence hangover for low-latency auto-flush
        self._silence_samples: int = 0
        self._silence_limit_samples: int = int(sample_rate * 1.0)

    @property
    def is_sleeping(self) -> bool:
        return self._is_sleeping

    def wake(self):
        self._is_sleeping = False
        self._silence_samples = 0

    def sleep(self):
        self._is_sleeping = True
        self._buffer.clear()
        self._buffer_len = 0
        self._silence_samples = 0

    def process_chunk(self, indata: np.ndarray, accumulate: bool = True) -> dict[str, Any]:
        result = {"action": "silence", "rms": 0.0, "wake_word": None}

        voice, rms = self.vad.is_speech(indata)
        result["rms"] = rms

        if self._is_sleeping:
            if not voice:
                return result
            audio_bytes = indata.tobytes()
            if self.wake_word.available:
                ww = self.wake_word.detect(audio_bytes)
                if ww:
                    result["action"] = "wake"
                    result["wake_word"] = ww
                    self.wake()
                    self.wake_word.reset()
            return result

        if voice:
            self._silence_samples = 0
            if accumulate:
                self._accumulate(indata)
                result["action"] = "accumulate"
                if self._buffer_len >= self._max_buffer_samples:
                    result["action"] = "overflow"
            else:
                result["action"] = "speech"
        else:
            if accumulate and self._buffer_len > 0:
                self._accumulate(indata)
                self._silence_samples += len(indata)
                if self._silence_samples >= self._silence_limit_samples:
                    result["action"] = "flush"
                else:
                    result["action"] = "accumulate"
            else:
                result["action"] = "silence"

        return result

    def flush_buffer(self) -> str:
        if not self._buffer:
            return ""
        audio = np.concatenate(self._buffer, axis=0)
        text = self.stt.transcribe(audio)
        self._buffer.clear()
        self._buffer_len = 0
        self._silence_samples = 0
        return text

    def _accumulate(self, indata: np.ndarray):
        self._buffer.append(indata.copy())
        self._buffer_len += len(indata)

    def set_audio_level(self, level: float):
        pass

    def set_volume(self, level: float) -> bool:
        try:
            from services.system.windows_api import VolumeController
            vol = VolumeController()
            vol.set_volume(level)
            return True
        except Exception:
            return False

    def get_audio_devices(self) -> list[dict[str, Any]]:
        try:
            import sounddevice as sd
            devices = sd.query_devices()
            result = []
            for i, d in enumerate(devices):
                result.append({"id": i, "name": d["name"],
                               "channels": d["max_input_channels"],
                               "default": d.get("default_samplerate", 0)})
            return result
        except Exception:
            return []

    def recognize_speech(self, audio: bytes, language: str = "es") -> str:
        return self.stt.transcribe_bytes(audio)

    async def generate_speech_async(self, text: str,
                                     on_audio_level=None,
                                     is_speaking_func=None,
                                     stop_requested=None) -> bool:
        return await self.tts.speak(
            text,
            on_audio_level=on_audio_level,
            is_speaking_func=is_speaking_func,
            stop_requested=stop_requested
        )

    def generate_speech(self, text: str, voice: str = "default") -> bytes:
        return b""

    def reset_vosk(self):
        self.stt.reset()
