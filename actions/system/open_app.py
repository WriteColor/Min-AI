"""open_app.py — Clean application launcher with Start Menu shortcut resolution and path caching."""
import json
import os
import subprocess
import time
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent.parent
REGISTRY_FILE = BASE_DIR / "config" / "app_registry.json"


def _load_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {"apps": {}}
    try:
        return json.loads(REGISTRY_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {"apps": {}}


def _save_registry(data: dict) -> None:
    REGISTRY_FILE.parent.mkdir(parents=True, exist_ok=True)
    REGISTRY_FILE.write_text(json.dumps(data, indent=2), encoding="utf-8")


def _store_app(app_key: str, entry: dict) -> None:
    data = _load_registry()
    apps = data.get("apps", {})
    apps[app_key] = entry
    data["apps"] = apps
    _save_registry(data)


def _sanitize_ps_string(s: str) -> str:
    """Escapa caracteres especiales para strings de PowerShell."""
    dangerous = [';', '`', '$', '|', '&', '(', ')', '{', '}', '@', '#']
    safe = s
    for ch in dangerous:
        safe = safe.replace(ch, '')
    safe = safe.replace("'", "''")
    return safe.strip()


def _resolve_start_menu_shortcut(app_name: str) -> str | None:
    """Search for Windows Start Menu shortcuts matching the app name and resolve their target exe."""
    safe = _sanitize_ps_string(app_name)
    if not safe:
        return None

    # PowerShell script to find and resolve .lnk files from local and global Start Menu paths
    cmd = (
        f"$paths = @("
        f"  \"$env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\","
        f"  \"$env:AppData\\Microsoft\\Windows\\Start Menu\\Programs\""
        f");"
        f"$shortcut = Get-ChildItem -Path $paths -Recurse -Filter \"*{safe}*.lnk\" -ErrorAction SilentlyContinue | "
        f"Select-Object -First 1;"
        f"if ($shortcut) {{"
        f"  $shell = New-Object -ComObject WScript.Shell;"
        f"  $target = $shell.CreateShortcut($shortcut.FullName).TargetPath;"
        f"  if ($target -and (Test-Path $target)) {{ $target }}"
        f"}}"
    )
    try:
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True,
            text=True,
            timeout=5,
        )
        if result.returncode == 0:
            resolved_path = result.stdout.strip()
            if resolved_path and os.path.exists(resolved_path):
                return resolved_path
    except Exception:
        pass
    return None


ALIASES = {
    "calculator": ["calculadora", "calculator", "calc"],
    "calculadora": ["calculadora", "calculator", "calc"],
    "clock": ["reloj", "clock", "alarma", "alarm", "alarmas"],
    "reloj": ["reloj", "clock", "alarma", "alarm", "alarmas"],
    "settings": ["configuración", "configuracion", "settings", "ajustes"],
    "configuracion": ["configuración", "configuracion", "settings", "ajustes"],
    "ajustes": ["configuración", "configuracion", "settings", "ajustes"],
    "calendar": ["calendario", "calendar"],
    "calendario": ["calendario", "calendar"],
    "mail": ["correo", "mail", "outlook"],
    "correo": ["correo", "mail", "outlook"],
    "photos": ["fotos", "photos", "galería", "galeria"],
    "fotos": ["fotos", "photos", "galería", "galeria"],
    "weather": ["clima", "weather", "tiempo"],
    "clima": ["clima", "weather", "tiempo"],
    "paint": ["paint", "dibujo", "mspaint"],
    "music": ["música", "musica", "music", "reproductor"],
    "musica": ["música", "musica", "music", "reproductor"],
    "whatsapp": ["whatsapp"],
    "spotify": ["spotify"],
    "discord": ["discord"],
    "notepad": ["notepad", "bloc de notas", "notas"],
    "bloc de notas": ["notepad", "bloc de notas", "notas"],
}

def _find_start_app_with_aliases(app_name: str) -> dict | None:
    app_key = app_name.lower().strip()
    aliases = ALIASES.get(app_key, [app_name])
    
    filter_conditions = []
    for alias in aliases:
        safe_alias = _sanitize_ps_string(alias)
        if safe_alias:
            filter_conditions.append(f"$_.Name -like '*{safe_alias}*'")
            
    if not filter_conditions:
        return None
        
    filter_str = " -or ".join(filter_conditions)
    cmd = (
        f"$app = Get-StartApps | Where-Object {{ {filter_str} }} | Select-Object -First 1; "
        f"if ($app) {{ $app | ConvertTo-Json -Compress }}"
    )
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0 or not result.stdout.strip():
        return None
    try:
        return json.loads(result.stdout.strip())
    except Exception:
        return None


def _launch_start_app(app_id: str) -> bool:
    if not app_id:
        return False
    cmd = f"Start-Process 'shell:AppsFolder\\{app_id}'"
    result = subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
        capture_output=True,
        text=True,
    )
    return result.returncode == 0


def _launch_via_search(app_name: str) -> bool:
    try:
        import pyautogui
        pyautogui.press("win")
        time.sleep(0.5)
        pyautogui.write(app_name, interval=0.02)
        time.sleep(0.5)
        pyautogui.press("enter")
        return True
    except Exception:
        return False


def _resolve_exe_path(executable: str) -> str:
    try:
        cmd = (
            "$cmd = Get-Command '" + executable + "' -ErrorAction SilentlyContinue | "
            "Select-Object -First 1 -ExpandProperty Source; if ($cmd) { $cmd }"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True,
            text=True,
        )
        path = result.stdout.strip()
        return path
    except Exception:
        return ""


def open_app(parameters: dict, response=None, player=None) -> str:
    """Launch local desktop applications based on user request."""
    app_name = parameters.get("app_name", "").strip()
    if not app_name:
        return "App name is required, sir."

    app_key = app_name.lower().strip()

    # 1. Hardcoded UWP protocol associations (Always prioritize modern Windows 11 apps)
    uwp_mappings = {
        "calculator": "calculator:",
        "calculadora": "calculator:",
        "clock": "ms-clock:",
        "reloj": "ms-clock:",
        "alarm": "ms-clock:",
        "alarma": "ms-clock:",
        "alarmas": "ms-clock:",
        "calendar": "outlookcalendar:",
        "calendario": "outlookcalendar:",
        "mail": "outlookmail:",
        "correo": "outlookmail:",
        "settings": "ms-settings:",
        "configuracion": "ms-settings:",
        "ajustes": "ms-settings:",
        "camera": "microsoft.windows.camera:",
        "camara": "microsoft.windows.camera:",
        "photos": "ms-photos:",
        "fotos": "ms-photos:",
        "weather": "bingweather:",
        "clima": "bingweather:",
        "maps": "bingmaps:",
        "mapas": "bingmaps:",
        "edge": "microsoft-edge:",
        "microsoft edge": "microsoft-edge:",
        "store": "ms-windows-store:",
        "tienda": "ms-windows-store:",
        "microsoft store": "ms-windows-store:",
        "paint": "ms-paint:",
        "music": "ms-media-player:",
        "musica": "ms-media-player:",
        "video": "ms-media-player:",
        "whatsapp": "whatsapp:",
        "spotify": "spotify:",
        "discord": "discord:",
        "sticky notes": "ms-stickynotes:",
        "notas": "ms-stickynotes:",
        "recortes": "ms-screenclip:",
        "snipping tool": "ms-screenclip:",
    }

    if app_key in uwp_mappings:
        uri = uwp_mappings[app_key]
        try:
            os.startfile(uri)
            _store_app(app_key, {"type": "uwp", "uri": uri})
            if player:
                player.write_log(f"🚀 Opening Windows UWP {app_name} ({uri})...")
            return f"Successfully launched {app_name} via Windows protocol."
        except Exception as e:
            print(f"[UWP Launch] Failed to start {uri}: {e}")

    registry = _load_registry().get("apps", {})
    cached = registry.get(app_key)

    # 2. Check App Registry cache next for fast launch
    if cached:
        if cached.get("type") == "uwp":
            uri = cached.get("uri", "")
            if uri:
                try:
                    os.startfile(uri)
                    if player:
                        player.write_log(f"🚀 Opening {app_name} (Cached UWP)...")
                    return f"Successfully launched {app_name} via Windows protocol."
                except Exception:
                    pass
        elif cached.get("type") == "appid":
            app_id = cached.get("id", "")
            if _launch_start_app(app_id):
                if player:
                    player.write_log(f"🚀 Opening {app_name} (Cached AppID)...")
                return f"Successfully launched {app_name}."
        elif cached.get("type") == "exe":
            path = cached.get("path", "")
            if path and os.path.exists(path):
                try:
                    subprocess.Popen(path, shell=True)
                    if player:
                        player.write_log(f"🚀 Opening {app_name} (Cached path)...")
                    return f"Successfully launched {app_name} from cached path."
                except Exception:
                    pass

    # 3. Resolve via Get-StartApps with language aliases (Finds UWP AppIDs natively)
    start_app = _find_start_app_with_aliases(app_name)
    if start_app:
        app_id = start_app.get("AppID", "")
        if app_id and _launch_start_app(app_id):
            _store_app(app_key, {"type": "appid", "id": app_id})
            if player:
                player.write_log(f"🚀 Opening {app_name} (Resolved AppID)...")
            return f"Successfully launched {app_name}."

    # 4. Resolve via Start Menu Shortcut (.lnk)
    resolved_lnk = _resolve_start_menu_shortcut(app_name)
    if resolved_lnk:
        try:
            subprocess.Popen(resolved_lnk, shell=True)
            _store_app(app_key, {"type": "exe", "path": resolved_lnk})
            if player:
                player.write_log(f"🚀 Opening {app_name} (Resolved Shortcut)...")
            return f"Successfully launched {app_name}."
        except Exception:
            pass

    # 5. Resolve standard cmd executables
    mappings = {
        "notepad": "notepad.exe",
        "bloc de notas": "notepad.exe",
        "calculator": "calc.exe",
        "calculadora": "calc.exe",
        "brave": "brave.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "explorer": "explorer.exe",
        "explorador de archivos": "explorer.exe",
        "cmd": "cmd.exe",
        "terminal": "powershell.exe",
        "paint": "mspaint.exe",
    }
    executable = mappings.get(app_key, app_name)
    try:
        resolved = _resolve_exe_path(executable)
        if resolved:
            subprocess.Popen(resolved, shell=True)
            _store_app(app_key, {"type": "exe", "path": resolved})
            if player:
                player.write_log(f"🚀 Opening {app_name} (Resolved Command)...")
            return f"Successfully launched {app_name}."
    except Exception:
        pass

    # 6. Fallback to Windows Search simulation
    if _launch_via_search(app_name):
        # Trigger background search to cache it for the next run
        def cache_in_background():
            time.sleep(2)
            res = _resolve_start_menu_shortcut(app_name)
            if res:
                _store_app(app_key, {"type": "exe", "path": res})
            else:
                sa = _find_start_app_with_aliases(app_name)
                if sa and sa.get("AppID"):
                    _store_app(app_key, {"type": "appid", "id": sa.get("AppID")})

        import threading
        threading.Thread(target=cache_in_background, daemon=True).start()

        if player:
            player.write_log(f"🚀 Opening {app_name} via Windows Search (caching path)...")
        return f"Attempted to open {app_name} via Windows search."

    return f"Failed to open '{app_name}'."
