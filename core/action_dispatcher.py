"""
core/action_dispatcher.py — Dynamic tool loader and executor.
Decouples main.py from individual action files and dispatches them safely.
"""

import asyncio
import importlib
import inspect
import traceback
from pathlib import Path
from typing import Any, Dict, Callable

# Load Windows service or fallback helpers
try:
    from services.system.windows_api import WindowsService, HAS_WIN32
    _win_service = WindowsService()
except ImportError:
    _win_service = None
    HAS_WIN32 = False

try:
    import pyautogui
except ImportError:
    pyautogui = None

try:
    import pygetwindow as gw
except ImportError:
    gw = None

CATEGORIES = ["automation", "files", "media", "music", "system", "utils", "vision", "web"]

# Special function name or module mappings
SPECIAL_MAPPINGS = {
    # weather_report function was renamed from weather_action to match schema name
    "weather_report": ("automation.weather_report", "weather_report"),
    "desktop_control": ("system.desktop", "desktop_control"),
    "screen_process": ("vision.screen_vision", "screen_vision"),
    "screen_vision": ("vision.screen_vision", "screen_vision"),
}

class ActionDispatcher:
    def __init__(self, ui, speak_fn, executor):
        self.ui = ui
        self.speak_fn = speak_fn
        self.executor = executor

    async def dispatch(self, name: str, args: Dict[str, Any]) -> str:
        """
        Dynamically imports and executes the requested tool.
        Handles overrides and fallback methods.
        """
        loop = asyncio.get_running_loop()

        # Intercept Special System Actions
        if name == "computer_settings":
            action = args.get("action", "")
            if action == "volume":
                val = args.get("value", "")
                return await loop.run_in_executor(self.executor, lambda: self._handle_volume(val))
            elif action in ["window_minimize", "minimize"]:
                return await loop.run_in_executor(self.executor, self._handle_minimize)
            elif action in ["window_maximize", "maximize"]:
                return await loop.run_in_executor(self.executor, self._handle_maximize)

        # Resolve Module Path and Function Name
        module_path, func_name = "", ""
        if name in SPECIAL_MAPPINGS:
            module_path, func_name = SPECIAL_MAPPINGS[name]
        else:
            # Check categories
            for cat in CATEGORIES:
                potential_file = Path(__file__).parent.parent / "actions" / cat / f"{name}.py"
                if potential_file.exists():
                    module_path = f"{cat}.{name}"
                    func_name = name
                    break
            else:
                # Direct file fallback
                potential_file = Path(__file__).parent.parent / "actions" / f"{name}.py"
                if potential_file.exists():
                    module_path = name
                    func_name = name

        if not module_path:
            return f"Error: Tool '{name}' not found."

        try:
            # Dynamic Import
            module = importlib.import_module(f"actions.{module_path}")
            func = getattr(module, func_name)
            
            # Inspect signature to align arguments
            sig = inspect.signature(func)
            kwargs = {}
            if "parameters" in sig.parameters:
                kwargs["parameters"] = args
            else:
                for p in sig.parameters:
                    if p in args:
                        kwargs[p] = args[p]

            if "player" in sig.parameters:
                kwargs["player"] = self.ui
            if "response" in sig.parameters:
                kwargs["response"] = None
            if "session_memory" in sig.parameters:
                kwargs["session_memory"] = None
            if "speak" in sig.parameters:
                kwargs["speak"] = self.speak_fn

            # Execute in the dedicated thread pool
            result = await loop.run_in_executor(self.executor, lambda: func(**kwargs))
            return result or "Done."

        except Exception as e:
            traceback.print_exc()
            if self.speak_fn:
                try:
                    # Check TTS guard to avoid overlapping error speech
                    if hasattr(self.speak_fn, '__self__') and hasattr(self.speak_fn.__self__, '_is_speaking'):
                        if self.speak_fn.__self__._is_speaking:
                            pass  # Skip error speak if TTS is already playing
                        else:
                            self.speak_fn(f"Error al ejecutar {name}: {str(e)}")
                    else:
                        self.speak_fn(f"Error al ejecutar {name}: {str(e)}")
                except:
                    pass
            return f"Tool '{name}' failed: {e}"

    def _handle_volume(self, val: str) -> str:
        """Handle volume adjustments using WindowsService if available, falling back to pyautogui."""
        if not val:
            return "Volume value is missing."
        
        # Absolute volume (e.g. '50')
        if str(val).isdigit():
            target = int(val)
            if _win_service:
                success = _win_service.set_volume(target)
                if success:
                    return f"Volumen ajustado al {target}%."
            # Fallback to comtypes/pycaw direct method if service fails or isn't loaded
            try:
                from ctypes import cast, POINTER
                from comtypes import CoInitialize, CoUninitialize
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                CoInitialize()
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, 1, None)
                volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
                scalar_vol = max(0.0, min(1.0, target / 100.0))
                volume_ctrl.SetMasterVolumeLevelScalar(scalar_vol, None)
                CoUninitialize()
                return f"Volumen ajustado al {target}%."
            except Exception as e:
                return f"Error ajustando volumen absoluto: {e}"
        else:
            # Relative command: up, down, mute
            val_lower = val.lower()
            if "up" in val_lower or "subir" in val_lower:
                if pyautogui:
                    pyautogui.press("volumeup", presses=5)
                    return "Volumen subido."
            elif "down" in val_lower or "bajar" in val_lower:
                if pyautogui:
                    pyautogui.press("volumedown", presses=5)
                    return "Volumen bajado."
            elif "mute" in val_lower or "silenciar" in val_lower:
                if pyautogui:
                    pyautogui.press("volumemute")
                    return "Volumen silenciado."
            return f"Acción de volumen no reconocida: {val}"

    def _handle_minimize(self) -> str:
        if _win_service and HAS_WIN32:
            windows = _win_service.get_all_windows()
            active_hwnd = None
            try:
                import win32gui
                active_hwnd = win32gui.GetForegroundWindow()
            except ImportError:
                pass
            if active_hwnd:
                success = _win_service.minimize_window(active_hwnd)
                if success:
                    return "Ventana minimizada."
        if gw:
            try:
                window = gw.getActiveWindow()
                if window:
                    window.minimize()
                    return "Ventana minimizada."
            except Exception as e:
                return f"Error al minimizar: {e}"
        return "Librería pygetwindow/win32 no disponible o no hay ventana activa."

    def _handle_maximize(self) -> str:
        if _win_service and HAS_WIN32:
            active_hwnd = None
            try:
                import win32gui
                active_hwnd = win32gui.GetForegroundWindow()
            except ImportError:
                pass
            if active_hwnd:
                success = _win_service.maximize_window(active_hwnd)
                if success:
                    return "Ventana maximizada."
        if gw:
            try:
                window = gw.getActiveWindow()
                if window:
                    window.maximize()
                    return "Ventana maximizada."
            except Exception as e:
                return f"Error al maximizar: {e}"
        return "Librería pygetwindow/win32 no disponible o no hay ventana activa."
