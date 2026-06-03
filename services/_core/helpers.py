"""services/helpers.py — Shared helper functions extracted from main.py"""

import os
import re
import sys
from pathlib import Path

try:
    from zoneinfo import ZoneInfo as _ZoneInfo
    _BA_TZ = _ZoneInfo("America/Tegucigalpa")
except Exception:
    from datetime import timezone as _tz, timedelta as _td
    _BA_TZ = _tz(hours=-5)


def _load_tz():
    global _BA_TZ
    from core.config_manager import get_config
    try:
        tz_name = get_config().timezone
        if not tz_name:
            from datetime import datetime as _dt
            _BA_TZ = _dt.now().astimezone().tzinfo
            print(f"[TZ] Using system timezone: {_BA_TZ}")
            return
        try:
            from zoneinfo import ZoneInfo
            _BA_TZ = ZoneInfo(tz_name)
            print(f"[TZ] Timezone loaded: {tz_name}")
        except Exception:
            from datetime import timezone as _tz2, timedelta as _td2
            parts = tz_name.replace("\\", "/").split("/")
            short = parts[-1].lower() if parts else ""
            available = set()
            for z in str(_tz2.utcfromtimestamp(0).tzname):
                pass
            import zoneinfo
            for z in zoneinfo.available_timezones():
                if z.lower().endswith(short):
                    available.add(z)
            if available:
                _BA_TZ = zoneinfo.ZoneInfo(sorted(available)[0])
                print(f"[TZ] Matched '{tz_name}' -> '{_BA_TZ}'")
            else:
                from datetime import datetime as _dt
                _BA_TZ = _dt.now().astimezone().tzinfo
                print(f"[TZ] Could not match '{tz_name}', using system timezone")
    except Exception as e:
        from datetime import datetime as _dt
        _BA_TZ = _dt.now().astimezone()
        print(f"[TZ] Error loading: {e}, using system timezone")


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "config.json"
PROMPT_PATH = BASE_DIR / "core" / "prompt.txt"
LOG_PATH = BASE_DIR / "Min.log"


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are MIN. Be concise, direct, and always use the provided tools. "
            "Never simulate or guess results."
        )


_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


def _clean_transcript(text: str) -> str:
    """
    Remove control chars and garbage unicode that causes TTS to read nonsense.
    Strips Kannada, Tamil, Bengali, CJK blocks and 3+ runs of non-Latin chars.
    PRESERVES: ellipses, Spanish inverted punctuation (¿¡), emphasis content,
    questions, exclamations, and all conversational elements that form MIN's personality.
    """
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    text = re.sub(r"[ಀ-೿]+", " ", text)
    text = re.sub(r"[一-鿿]+", " ", text)
    text = re.sub(r"([^\w\s¿¡\.!\?\,:;\-\(\)···])\1{2,}", " ", text)
    return text.strip()


def strip_markdown(text: str) -> str:
    """Remove markdown so TTS doesn't read it aloud."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"#+\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^\)]+\)", r"\1", text)
    return text.strip()


def clean_think_blocks(text: str) -> str:
    """Strip <think>...</think> blocks case-insensitively and handle newlines/multi-lines."""
    if not text:
        return ""
    # Remove any content inside <think>...</think> including the tags.
    # Handles multi-line (?s) and case-insensitivity (?i) and unclosed tags at the end of the text.
    cleaned = re.sub(r'(?is)<think>.*?(?:</think>|$)', '', text)
    return cleaned.strip()


class StreamingThinkFilter:
    def __init__(self):
        self.buffer = ""
        self.in_think = False

    def process(self, chunk: str) -> str:
        self.buffer += chunk
        output = ""
        
        while self.buffer:
            if not self.in_think:
                lower_buffer = self.buffer.lower()
                idx = lower_buffer.find("<think>")
                if idx != -1:
                    output += self.buffer[:idx]
                    self.buffer = self.buffer[idx + len("<think>"):]
                    self.in_think = True
                else:
                    partial_match = False
                    for i in range(1, len("<think>")):
                        sub = "<think>"[:i]
                        if lower_buffer.endswith(sub):
                            output += self.buffer[:-i]
                            self.buffer = self.buffer[-i:]
                            partial_match = True
                            break
                    if not partial_match:
                        output += self.buffer
                        self.buffer = ""
            else:
                lower_buffer = self.buffer.lower()
                idx = lower_buffer.find("</think>")
                if idx != -1:
                    self.buffer = self.buffer[idx + len("</think>"):]
                    self.in_think = False
                else:
                    partial_match = False
                    for i in range(1, len("</think>")):
                        sub = "</think>"[:i]
                        if lower_buffer.endswith(sub):
                            self.buffer = self.buffer[-i:]
                            partial_match = True
                            break
                    if not partial_match:
                        self.buffer = ""
        return output

    def flush(self) -> str:
        res = ""
        if not self.in_think and self.buffer:
            res = self.buffer
        self.buffer = ""
        return res

    def reset(self):
        self.buffer = ""
        self.in_think = False
