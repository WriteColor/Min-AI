import json
import os
from typing import Optional

import numpy as np


class STTEngine:
    def __init__(self, model_path: str = "config/vosk_model",
                 sample_rate: int = 16000,
                 language: str = "es"):
        self.sample_rate = sample_rate
        self.language = language
        self._vosk_recognizer = None
        self._whisper_available = False
        self._init_vosk(model_path)
        self._init_whisper()

    def _init_vosk(self, model_path: str):
        self._model_path = model_path
        if not os.path.exists(model_path):
            return
        try:
            import vosk
            self._vosk_model = vosk.Model(model_path)
            self._vosk_recognizer = vosk.KaldiRecognizer(self._vosk_model, self.sample_rate)
        except Exception:
            self._vosk_model = None
            self._vosk_recognizer = None

    def _init_whisper(self):
        try:
            import whisper
            self._whisper_model = whisper.load_model("tiny")
            self._whisper_available = True
        except Exception:
            self._whisper_model = None
            self._whisper_available = False

    @property
    def available(self) -> bool:
        return self._vosk_recognizer is not None or self._whisper_available

    def transcribe(self, audio_data: np.ndarray) -> str:
        if self._whisper_available and self._whisper_model is not None:
            return self._transcribe_whisper(audio_data)
        if self._vosk_recognizer is not None:
            return self._transcribe_vosk(audio_data)
        return ""

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        if self._vosk_recognizer is not None:
            try:
                if self._vosk_recognizer.AcceptWaveform(audio_bytes):
                    res = json.loads(self._vosk_recognizer.Result())
                    return res.get("text", "").strip()
            except Exception:
                pass
        return ""

    def _transcribe_vosk(self, audio_data: np.ndarray) -> str:
        return self.transcribe_bytes(audio_data.astype(np.int16).tobytes())

    def _transcribe_whisper(self, audio_data: np.ndarray) -> str:
        try:
            audio_float = audio_data.astype(np.float32) / 32768.0
            result = self._whisper_model.transcribe(audio_float, language=self.language)
            return result.get("text", "").strip()
        except Exception:
            return ""

    def reset(self):
        if self._vosk_model:
            import vosk
            self._vosk_recognizer = vosk.KaldiRecognizer(self._vosk_model, self.sample_rate)
