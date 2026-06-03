import json
import os
import threading
from typing import Optional


class WakeWordDetector:
    def __init__(self, model_path: str = "config/vosk_model",
                 keywords: Optional[list[str]] = None,
                 sample_rate: int = 16000):
        self.sample_rate = sample_rate
        self.keywords = keywords or ["min"]
        self._recognizer = None
        self._model = None
        self._lock = threading.Lock()
        self._load_model(model_path)

    def _load_model(self, model_path: str):
        if not os.path.exists(model_path):
            return
        try:
            from core.config_manager import get_config
            if get_config().active_provider == "gemini":
                return
        except Exception:
            pass
        try:
            import vosk
            self._model = vosk.Model(model_path)
            self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
        except Exception:
            self._recognizer = None

    @property
    def available(self) -> bool:
        return self._recognizer is not None

    def detect(self, audio_data: bytes) -> Optional[str]:
        if not self._recognizer:
            return None
        with self._lock:
            try:
                if self._recognizer.AcceptWaveform(audio_data):
                    res = json.loads(self._recognizer.Result())
                    text = res.get("text", "").strip().lower()
                    for kw in self.keywords:
                        if kw in text:
                            return kw
            except Exception:
                pass
        return None

    def reset(self):
        if self._model:
            import vosk
            self._recognizer = vosk.KaldiRecognizer(self._model, self.sample_rate)
