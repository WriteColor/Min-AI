from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import webbrowser
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
CONFIG_FILE = BASE_DIR / "config" / "config.json"

_BROWSER_ORDER = [
    "chrome",
    "brave",
    "edge",
    "firefox",
    "opera",
    "opera_gx",
    "vivaldi",
    "tor",
]

_ALIASES = {
    "google chrome": "chrome",
    "chrome": "chrome",
    "brave": "brave",
    "edge": "edge",
    "microsoft edge": "edge",
    "firefox": "firefox",
    "mozilla firefox": "firefox",
    "opera": "opera",
    "opera gx": "opera_gx",
    "gx": "opera_gx",
    "vivaldi": "vivaldi",
    "tor": "tor",
    "tor browser": "tor",
    "default": "default",
    "system": "default",
    "auto": "auto",
}

_WIN_PATHS = {
    "chrome": [
        r"C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
        r"C:\\Program Files (x86)\\Google\\Chrome\\Application\\chrome.exe",
        r"%LOCALAPPDATA%\\Google\\Chrome\\Application\\chrome.exe",
    ],
    "brave": [
        r"C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        r"C:\\Program Files (x86)\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
        r"%LOCALAPPDATA%\\BraveSoftware\\Brave-Browser\\Application\\brave.exe",
    ],
    "edge": [
        r"C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe",
        r"C:\\Program Files\\Microsoft\\Edge\\Application\\msedge.exe",
    ],
    "firefox": [
        r"C:\\Program Files\\Mozilla Firefox\\firefox.exe",
        r"C:\\Program Files (x86)\\Mozilla Firefox\\firefox.exe",
    ],
    "opera": [
        r"C:\\Program Files\\Opera\\launcher.exe",
        r"%LOCALAPPDATA%\\Programs\\Opera\\launcher.exe",
    ],
    "opera_gx": [
        r"C:\\Program Files\\Opera GX\\launcher.exe",
        r"%LOCALAPPDATA%\\Programs\\Opera GX\\launcher.exe",
    ],
    "vivaldi": [
        r"C:\\Program Files\\Vivaldi\\Application\\vivaldi.exe",
        r"%LOCALAPPDATA%\\Vivaldi\\Application\\vivaldi.exe",
    ],
    "tor": [
        r"C:\\Program Files\\Tor Browser\\Browser\\firefox.exe",
        r"%LOCALAPPDATA%\\Tor Browser\\Browser\\firefox.exe",
    ],
}

_MAC_PATHS = {
    "chrome": ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"],
    "brave": ["/Applications/Brave Browser.app/Contents/MacOS/Brave Browser"],
    "edge": ["/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge"],
    "firefox": ["/Applications/Firefox.app/Contents/MacOS/firefox"],
    "opera": ["/Applications/Opera.app/Contents/MacOS/Opera"],
    "opera_gx": ["/Applications/Opera GX.app/Contents/MacOS/Opera GX"],
    "vivaldi": ["/Applications/Vivaldi.app/Contents/MacOS/Vivaldi"],
    "tor": ["/Applications/Tor Browser.app/Contents/MacOS/firefox"],
}

_LINUX_NAMES = {
    "chrome": ["google-chrome", "google-chrome-stable"],
    "brave": ["brave", "brave-browser"],
    "edge": ["microsoft-edge", "microsoft-edge-stable"],
    "firefox": ["firefox"],
    "opera": ["opera"],
    "opera_gx": ["opera-gx"],
    "vivaldi": ["vivaldi", "vivaldi-stable"],
    "tor": ["tor-browser", "tor-browser_en-US"],
}

def _get_windows_default_browser_progid() -> str | None:
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\Shell\Associations\UrlAssociations\http\UserChoice"
        with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
            prog_id, _ = winreg.QueryValueEx(key, "ProgId")
            return prog_id
    except Exception:
        return None

def _get_windows_default_browser_key() -> str | None:
    prog_id = _get_windows_default_browser_progid()
    if not prog_id:
        return None
    prog_id = prog_id.lower()
    if "chrome" in prog_id: return "chrome"
    if "brave" in prog_id: return "brave"
    if "msedge" in prog_id or "edge" in prog_id: return "edge"
    if "firefox" in prog_id: return "firefox"
    if "operagx" in prog_id: return "opera_gx"
    if "opera" in prog_id: return "opera"
    if "vivaldi" in prog_id: return "vivaldi"
    return None



def _load_config() -> dict:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _expand_path(path: str) -> str:
    return os.path.expandvars(path)


def _first_existing(paths: list[str]) -> str | None:
    for p in paths:
        candidate = _expand_path(p)
        if os.path.exists(candidate):
            return candidate
    return None


def _detect_windows() -> dict[str, str]:
    detected: dict[str, str] = {}
    for key, paths in _WIN_PATHS.items():
        found = _first_existing(paths)
        if found:
            detected[key] = found
    return detected


def _detect_macos() -> dict[str, str]:
    detected: dict[str, str] = {}
    for key, paths in _MAC_PATHS.items():
        found = _first_existing(paths)
        if found:
            detected[key] = found
    return detected


def _detect_linux() -> dict[str, str]:
    detected: dict[str, str] = {}
    for key, names in _LINUX_NAMES.items():
        for name in names:
            found = shutil.which(name)
            if found:
                detected[key] = found
                break
    return detected


def detect_installed_browsers() -> dict[str, str]:
    if sys.platform.startswith("win"):
        return _detect_windows()
    if sys.platform == "darwin":
        return _detect_macos()
    return _detect_linux()


def _normalize_pref(value: str | None) -> str:
    if not value:
        return "auto"
    key = value.strip().lower()
    return _ALIASES.get(key, key)


def resolve_browser_path(preferred: str | None = None, cfg: dict | None = None) -> tuple[str, str | None]:
    config = cfg or _load_config()
    pref = _normalize_pref(preferred or config.get("browser_preference"))

    detected = detect_installed_browsers()

    custom_paths = config.get("browser_paths")
    if isinstance(custom_paths, dict):
        for key, path in custom_paths.items():
            if isinstance(path, str) and os.path.exists(_expand_path(path)):
                detected[_normalize_pref(key)] = _expand_path(path)

    chrome_path = config.get("chrome_exe_path") or config.get("chrome_path")
    if isinstance(chrome_path, str) and os.path.exists(_expand_path(chrome_path)):
        detected["chrome"] = _expand_path(chrome_path)

    # Resolve "auto" or "system" to actual default OS browser if possible
    if pref in ("auto", "system", "default"):
        if sys.platform.startswith("win"):
            win_def = _get_windows_default_browser_key()
            if win_def and win_def in detected:
                return win_def, detected[win_def]
        
        # Fallback if no specific OS default is found or on non-Windows
        for key in _BROWSER_ORDER:
            if key in detected:
                return key, detected[key]
        return "default", None

    if pref in detected:
        return pref, detected[pref]

    # Final fallback
    for key in _BROWSER_ORDER:
        if key in detected:
            return key, detected[key]

    return "default", None


def launch_url(url: str, preferred: str | None = None) -> bool:
    key, path = resolve_browser_path(preferred)
    if path:
        try:
            subprocess.Popen([path, url])
            return True
        except Exception:
            pass

    try:
        webbrowser.open(url)
        return True
    except Exception:
        return False
