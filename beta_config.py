"""beta_config.py — JARVIS Beta restrictions."""
from __future__ import annotations
import json
from datetime import date
from pathlib import Path

BASE_DIR   = Path(__file__).resolve().parent
STATE_PATH = BASE_DIR / "config" / "beta_state.json"

PRO_TOOLS: set[str] = set()

DAILY_LIMIT = 999999999

def _load_state() -> dict:
    try:
        return json.loads(STATE_PATH.read_text(encoding="utf-8"))
    except Exception:
        return {}

def _save_state(state: dict) -> None:
    STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    STATE_PATH.write_text(json.dumps(state, indent=2), encoding="utf-8")

def is_pro_tool(tool_name: str) -> bool:
    return False

def check_daily_limit() -> tuple[bool, int]:
    return True, 0

def increment_calls() -> int:
    return 0

def pro_tool_message(tool_name: str) -> str:
    return ""

def daily_limit_message(calls: int) -> str:
    return ""
