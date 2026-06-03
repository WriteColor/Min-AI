import json
import os
import re
import unicodedata
from typing import Optional
import numpy as np

# Global model cache to prevent loading the Vosk model multiple times
_MODEL_CACHE = {}

def sanitize_vosk_text(text: str) -> str:
    """
    Sanitizes Vosk output text:
    - Validates UTF-8 encoding
    - Normalizes to Unicode NFC
    - Repairs Mojibake (e.g. Latin-1 decodings of UTF-8)
    - Fixes/sanitizes Spanish special characters (á, é, í, ó, ú, ü, ñ) and inverted punctuation (¿, ¡)
    """
    if not text:
        return ""
        
    # 1. UTF-8 Validation and Mojibake Repair
    try:
        if any(c in text for c in ("Ã", "Â", "â", "æ", "ô")):
            repaired = text.encode("latin-1", errors="ignore").decode("utf-8", errors="ignore")
            if repaired:
                text = repaired
    except (UnicodeEncodeError, UnicodeDecodeError):
        pass

    # Backup manual replacements for common Mojibake sequences in Spanish
    replacements = {
        "Ã¡": "á", "Ã©": "é", "Ã­": "í", "Ã³": "ó", "Ãº": "ú",
        "Ã±": "ñ", "Ã¼": "ü", "Ã ": "Á", "Ã‰": "É", "Ã ": "Í",
        "Ã“": "Ó", "Ãš": "Ú", "Ã‘": "Ñ", "Ãœ": "Ü",
        "Â¿": "¿", "Â¡": "¡"
    }
    for bad, good in replacements.items():
        text = text.replace(bad, good)

    # 2. Unicode Normalization (NFC)
    text = unicodedata.normalize("NFC", text)

    # 3. Clean up spacing around punctuation
    text = re.sub(r'\s+\?', '?', text)
    text = re.sub(r'\s+\!', '!', text)
    text = re.sub(r'\s+,', ',', text)

    # 4. Repair/sanitize Spanish special characters if written with apostrophes/accents
    text = re.sub(r"\ba'\b", "á", text)
    text = re.sub(r"\be'\b", "é", text)
    text = re.sub(r"\bi'\b", "í", text)
    text = re.sub(r"\bo'\b", "ó", text)
    text = re.sub(r"\bu'\b", "ú", text)

    # 5. Inverted Punctuation (¿ and ¡)
    if '?' in text:
        parts = re.split(r'([.!?])', text)
        new_parts = []
        for part in parts:
            if part.endswith('?') and '¿' not in part:
                m = re.search(r'\b(qu[eé]|c[oó]mo|d[oó]nde|cu[aá]ndo|qui[eé]n|cu[aá]l|por\s+qu[eé])\b', part, re.IGNORECASE)
                if m:
                    idx = m.start()
                    prefix = part[:idx]
                    suffix = part[idx:]
                    new_parts.append(prefix + "¿" + suffix)
                else:
                    stripped = part.lstrip()
                    leading_spaces = part[:len(part) - len(stripped)]
                    new_parts.append(leading_spaces + "¿" + stripped)
            else:
                new_parts.append(part)
        text = "".join(new_parts)

    if '!' in text:
        parts = re.split(r'([.!?])', text)
        new_parts = []
        for part in parts:
            if part.endswith('!') and '¡' not in part:
                stripped = part.lstrip()
                leading_spaces = part[:len(part) - len(stripped)]
                new_parts.append(leading_spaces + "¡" + stripped)
            else:
                new_parts.append(part)
        text = "".join(new_parts)

    # Strip control characters
    text = re.sub(r'[\x00-\x08\x0b-\x0c\x0e-\x1f\x7f]', '', text)

    return text.strip()


class STTEngine:
    def __init__(self, model_path: str = "config/vosk_model",
                 sample_rate: int = 16000,
                 language: str = "es",
                 force_load: bool = False):
        self.sample_rate = sample_rate
        self.language = language
        self._vosk_recognizer = None
        self._init_vosk(model_path, force_load=force_load)

    def _init_vosk(self, model_path: str, force_load: bool = False):
        self._model_path = model_path
        if not os.path.exists(model_path):
            return
        if not force_load:
            try:
                from core.config_manager import get_config
                if get_config().active_provider == "gemini":
                    return
            except Exception:
                pass
        try:
            import vosk
            global _MODEL_CACHE
            abs_path = os.path.abspath(model_path)
            if abs_path not in _MODEL_CACHE:
                _MODEL_CACHE[abs_path] = vosk.Model(model_path)
            self._vosk_model = _MODEL_CACHE[abs_path]
            self._vosk_recognizer = vosk.KaldiRecognizer(self._vosk_model, self.sample_rate)
        except Exception:
            self._vosk_model = None
            self._vosk_recognizer = None

    @property
    def available(self) -> bool:
        return self._vosk_recognizer is not None

    def transcribe(self, audio_data: np.ndarray) -> str:
        if self._vosk_recognizer is not None:
            return self._transcribe_vosk(audio_data)
        return ""

    def transcribe_bytes(self, audio_bytes: bytes) -> str:
        if self._vosk_recognizer is not None:
            try:
                self._vosk_recognizer.AcceptWaveform(audio_bytes)
                res = json.loads(self._vosk_recognizer.Result())
                text = res.get("text", "").strip()
                if not text:
                    res = json.loads(self._vosk_recognizer.FinalResult())
                    text = res.get("text", "").strip()
                return sanitize_vosk_text(text)
            except Exception:
                pass
        return ""

    def _transcribe_vosk(self, audio_data: np.ndarray) -> str:
        return self.transcribe_bytes(audio_data.astype(np.int16).tobytes())

    def reset(self):
        if self._vosk_model:
            import vosk
            self._vosk_recognizer = vosk.KaldiRecognizer(self._vosk_model, self.sample_rate)