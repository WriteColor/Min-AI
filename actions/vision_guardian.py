from __future__ import annotations

import json
import threading
import time
from pathlib import Path

from actions.screen_vision import screen_vision

BASE_DIR = Path(__file__).resolve().parent.parent
STATE_FILE = BASE_DIR / "config" / "vision_guardian_state.json"

_lock = threading.Lock()
_stop_event = threading.Event()
_thread: threading.Thread | None = None
_enabled = True
_interval = 120


def _load_state() -> None:
    global _enabled, _interval
    if not STATE_FILE.exists():
        return
    try:
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        _enabled = bool(data.get("enabled", True))
        _interval = int(data.get("interval", 120))
    except Exception:
        pass


def _save_state() -> None:
    STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(
        json.dumps({"enabled": _enabled, "interval": _interval}, indent=2),
        encoding="utf-8",
    )


def _run_loop(inject_fn, speaking_fn):
    while not _stop_event.is_set():
        time.sleep(max(2, _interval))
        if not _enabled:
            continue
        try:
            if speaking_fn and speaking_fn():
                continue
        except Exception:
            pass

        try:
            result = screen_vision(
                {
                    "query": (
                        "Analiza la pantalla. Si no hay nada relevante, responde EXACTAMENTE 'NO_OP'. "
                        "Si hay algo importante o el usuario parece necesitar ayuda, responde en 1-2 frases."
                    )
                },
                player=None,
            )
            if result and result.strip() and result.strip() != "NO_OP":
                inject_fn(f"[VISION] {result}")
        except Exception:
            continue


def start(**kwargs) -> None:
    global _thread
    _load_state()
    if _thread and _thread.is_alive():
        return
    inject_fn = kwargs.get("inject_fn")
    speaking_fn = kwargs.get("speaking_fn")
    if not inject_fn:
        return
    _stop_event.clear()
    _thread = threading.Thread(
        target=_run_loop,
        args=(inject_fn, speaking_fn),
        daemon=True,
        name="vision-guardian",
    )
    _thread.start()


def vision_guardian(parameters: dict, player=None) -> str:
    global _enabled, _interval
    action = str(parameters.get("action", "status")).lower().strip()

    if action == "status":
        return f"Vision guardian: {'enabled' if _enabled else 'disabled'}, interval={_interval}s."

    if action == "enable":
        _enabled = True
        _save_state()
        return "Vision guardian enabled."

    if action == "disable":
        _enabled = False
        _save_state()
        return "Vision guardian disabled."

    if action == "set_interval":
        seconds = int(parameters.get("seconds", _interval))
        _interval = max(30, min(600, seconds))
        _save_state()
        return f"Vision guardian interval set to {_interval}s."

    if action == "check_now":
        result = screen_vision({"query": "Describe lo mas importante en pantalla ahora."}, player=player)
        return result or "No pude analizar la pantalla."

    return f"Accion '{action}' no soportada por vision_guardian."


def reload_state() -> None:
    """Reloads the enabled and interval settings from the state file in real-time."""
    _load_state()

