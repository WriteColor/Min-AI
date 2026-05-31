"""memory_manager.py — Long-term memory manager with extended context support."""
import sys
import json
import threading
from pathlib import Path
from datetime import datetime
from typing import Optional

def get_base_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    return Path(__file__).resolve().parent.parent

BASE_DIR = get_base_dir()
MEMORY_PATH = BASE_DIR / "memory" / "long_term.json"
SESSIONS_PATH = BASE_DIR / "memory" / "sessions"

MAX_VALUE_LENGTH = 10000
MEMORY_MAX_CHARS = 150000
SESSION_MAX_CHARS = 50000
_lock = threading.Lock()

def _empty_memory() -> dict:
    return {
        "notes": {},
        "habits": {},
        "preferences": {},
        "context": {},
        "conversations": {}
    }

def load_memory() -> dict:
    """Load long term memory file safely."""
    with _lock:
        if not MEMORY_PATH.exists():
            return _empty_memory()
        try:
            return json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
        except Exception:
            return _empty_memory()

def save_memory(memory: dict) -> None:
    """Save the memory state to disk."""
    with _lock:
        try:
            MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
            MEMORY_PATH.write_text(json.dumps(memory, indent=2), encoding="utf-8")
        except Exception as e:
            print(f"[Memory] Error saving: {e}")

def _recursive_update(d: dict, u: dict) -> dict:
    for k, v in u.items():
        if isinstance(v, dict) and k in d and isinstance(d[k], dict):
            _recursive_update(d[k], v)
        else:
            d[k] = v
    return d

def _truncate_value(val: str) -> str:
    if len(val) > MAX_VALUE_LENGTH:
        return val[:MAX_VALUE_LENGTH] + "... [truncated]"
    return val

def _all_entries(mem: dict) -> list[tuple[str, str, str, Optional[str]]]:
    """Returns (category, key, value, timestamp) tuples."""
    entries = []
    for cat, keys in mem.items():
        if not isinstance(keys, dict):
            continue
        for k, v in keys.items():
            ts = None
            if isinstance(v, dict):
                ts = v.get("timestamp")
                v = v.get("value", v)
            entries.append((cat, k, str(v), ts))
    return entries

def _trim_to_limit(mem: dict, limit: int = MEMORY_MAX_CHARS) -> dict:
    entries = _all_entries(mem)
    total_len = sum(len(c) + len(k) + len(v) for c, k, v, _ in entries)
    if total_len <= limit:
        return mem

    while total_len > limit and entries:
        cat, k, _, _ = entries.pop(0)
        if cat in mem and k in mem[cat]:
            del mem[cat][k]
        entries = _all_entries(mem)
        total_len = sum(len(c) + len(k) + len(v) for c, k, v, _ in entries)
    return mem

def update_memory(updates: dict, category: str = None) -> None:
    """Recursively update the memory with updates, truncating and trimming size limits."""
    mem = load_memory()
    timestamp = datetime.now().isoformat()

    truncated_updates = {}
    for cat, items in updates.items():
        if category and cat != category:
            truncated_updates[cat] = items
            continue
        truncated_updates[cat] = {}
        if isinstance(items, dict):
            for k, val_info in items.items():
                if isinstance(val_info, dict) and "value" in val_info:
                    val_str = _truncate_value(str(val_info["value"]))
                    truncated_updates[cat][k] = {"value": val_str, "timestamp": timestamp}
                else:
                    truncated_updates[cat][k] = {"value": _truncate_value(str(val_info)), "timestamp": timestamp}
        else:
            truncated_updates[cat] = {"value": _truncate_value(str(items)), "timestamp": timestamp}

    mem = _recursive_update(mem, truncated_updates)
    mem = _trim_to_limit(mem)
    save_memory(mem)

def remember(category: str, key: str, value: str) -> None:
    """Store a single memory value with timestamp."""
    update_memory({category: {key: {"value": value}}})

def forget(category: str, key: str) -> None:
    """Remove a single memory value."""
    mem = load_memory()
    if category in mem and key in mem[category]:
        del mem[category][key]
        save_memory(mem)

def forget_memory() -> None:
    """Clear all memory."""
    save_memory(_empty_memory())

def search_memory(query: str, max_results: int = 10) -> list[tuple[str, str, str]]:
    """Search memory entries containing the query string."""
    mem = load_memory()
    results = []
    query_lower = query.lower()
    for cat, keys in mem.items():
        if not isinstance(keys, dict):
            continue
        for k, v in keys.items():
            val = v.get("value", v) if isinstance(v, dict) else str(v)
            if query_lower in val.lower() or query_lower in k.lower():
                results.append((cat, k, str(val)))
                if len(results) >= max_results:
                    return results
    return results

def get_recent_memories(count: int = 20) -> list[tuple[str, str, str, str]]:
    """Get most recently modified memory entries."""
    mem = load_memory()
    entries = _all_entries(mem)
    entries_with_ts = [(c, k, v, ts) for c, k, v, ts in entries if ts]
    entries_with_ts.sort(key=lambda x: x[3] or "", reverse=True)
    return entries_with_ts[:count]

def format_memory_for_prompt(memory: dict, include_context: bool = True) -> str:
    """Format memory dict into a system prompt segment with extended context."""
    entries = _all_entries(memory)
    if not entries:
        return ""

    if include_context:
        lines = ["\n[LONG-TERM MEMORY & USER CONTEXT]"]
        current_cat = None
        for cat, k, v, ts in sorted(entries, key=lambda x: (x[0], x[1])):
            if cat != current_cat:
                lines.append(f"\n* {cat.upper()}:")
                current_cat = cat
            ts_str = f" [{ts[:10]}]" if ts else ""
            v_preview = v[:200] + "..." if len(v) > 200 else v
            lines.append(f"  - {k}: {v_preview}{ts_str}")
        return "\n".join(lines) + "\n"
    else:
        summary_lines = ["[MEMORY SUMMARY]"]
        for cat, keys in sorted(memory.items()):
            if not isinstance(keys, dict):
                continue
            keys_list = list(keys.keys())
            if keys_list:
                summary_lines.append(f"  {cat}: {len(keys_list)} entries")
        return "\n".join(summary_lines) + "\n"

class SessionMemory:
    """Temporary session memory with larger limits for active conversations."""

    def __init__(self, session_id: str = "default"):
        self.session_id = session_id
        self.session_path = SESSIONS_PATH / f"{session_id}.json"
        self._mem = self._load()

    def _load(self) -> dict:
        if not self.session_path.exists():
            return _empty_memory()
        try:
            return json.loads(self.session_path.read_text(encoding="utf-8"))
        except Exception:
            return _empty_memory()

    def _save(self) -> None:
        self.session_path.parent.mkdir(parents=True, exist_ok=True)
        self.session_path.write_text(json.dumps(self._mem, indent=2), encoding="utf-8")

    def remember(self, category: str, key: str, value: str) -> None:
        """Store session memory."""
        timestamp = datetime.now().isoformat()
        if category not in self._mem:
            self._mem[category] = {}
        self._mem[category][key] = {"value": value, "timestamp": timestamp}
        self._mem = _trim_to_limit(self._mem, SESSION_MAX_CHARS)
        self._save()

    def recall(self, category: str = None, key: str = None) -> Optional[dict]:
        """Recall session memory."""
        if category and key:
            return self._mem.get(category, {}).get(key)
        if category:
            return self._mem.get(category, {})
        return self._mem

    def clear(self) -> None:
        """Clear session memory."""
        self._mem = _empty_memory()
        if self.session_path.exists():
            self.session_path.unlink()

    def format_for_prompt(self) -> str:
        """Format session memory for prompt inclusion."""
        return format_memory_for_prompt(self._mem)

def get_context_summary() -> str:
    """Get a brief summary of memory for quick context."""
    mem = load_memory()
    return format_memory_for_prompt(mem, include_context=False)
