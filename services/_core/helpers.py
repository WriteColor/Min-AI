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
    _BA_TZ = _tz(_td(hours=-5))


def _load_tz():
    """Load timezone from config.json config."""
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
            _BA_TZ = _ZoneInfo(tz_name)
            print(f"[TZ] Timezone loaded: {tz_name}")
        except Exception as e:
            print(f"[TZ] Failed to load '{tz_name}': {e}")
            import zoneinfo as _zi
            available = _zi.available_timezones()
            tz_lower = tz_name.lower()
            for known in available:
                if known.lower() == tz_lower:
                    _BA_TZ = _ZoneInfo(known)
                    print(f"[TZ] Matched '{tz_name}' -> '{known}'")
                    break
            else:
                parts = tz_name.replace("\\", "/").split("/")
                short = parts[-1].lower() if parts else ""
                for known in available:
                    if known.lower().endswith("/" + short):
                        _BA_TZ = _ZoneInfo(known)
                        print(f"[TZ] Partial match '{tz_name}' -> '{known}'")
                        break
                else:
                    from datetime import datetime as _dt
                    _BA_TZ = _dt.now().astimezone().tzinfo
                    print(f"[TZ] Falling back to system timezone: {_BA_TZ}")
    except Exception as e:
        print(f"[TZ] Error reading config: {e}")


def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent


BASE_DIR        = get_base_dir()
API_CONFIG_PATH = BASE_DIR / "config" / "config.json"
PROMPT_PATH     = BASE_DIR / "core" / "prompt.txt"
LOG_PATH        = BASE_DIR / "Min.log"


def _load_system_prompt() -> str:
    try:
        return PROMPT_PATH.read_text(encoding="utf-8")
    except Exception:
        return (
            "You are MIN, Tony Stark's AI assistant. "
            "Be concise, direct, and always use the provided tools to complete tasks. "
            "Never simulate or guess results -- always call the appropriate tool."
        )


_CTRL_RE = re.compile(r"<ctrl\d+>", re.IGNORECASE)


def _clean_transcript(text: str) -> str:
    text = _CTRL_RE.sub("", text)
    text = re.sub(r"[\x00-\x08\x0b-\x1f]", "", text)
    return text.strip()


def strip_markdown(text: str) -> str:
    """Removes standard markdown characters so that TTS doesn't read them aloud."""
    text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
    text = re.sub(r"\*([^*]+)\*", r"\1", text)
    text = re.sub(r"__([^_]+)__", r"\1", text)
    text = re.sub(r"_([^_]+)_", r"\1", text)
    text = re.sub(r"```[\s\S]*?```", "", text)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r"#+\s+", "", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    return text.strip()
