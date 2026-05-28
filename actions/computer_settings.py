"""computer_settings.py — Refactored Windows 11 deep settings controls."""
import os
import sys
import subprocess

def set_app_volume(app_name: str, volume_percent: int) -> bool:
    """Adjust volume for a specific running application session (e.g. 'spotify', 'chrome')."""
    try:
        from pycaw.pycaw import AudioUtilities
        from comtypes import CoInitialize, CoUninitialize
        CoInitialize()
        sessions = AudioUtilities.GetAllSessions()
        success = False
        target_name = app_name.lower().replace(".exe", "").strip()
        for session in sessions:
            if session.Process:
                pname = session.Process.name().lower()
                if target_name in pname:
                    volume = session.SimpleAudioVolume
                    volume.SetMasterVolume(max(0.0, min(1.0, volume_percent / 100.0)), None)
                    success = True
        CoUninitialize()
        return success
    except Exception as e:
        print(f"[Settings] Error setting app volume: {e}")
        return False


def set_dark_mode(enabled: bool) -> bool:
    """Enables or disables system and app-wide dark mode via the Windows Registry."""
    try:
        import winreg
        key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
        key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path, 0, winreg.KEY_SET_VALUE)
        val = 0 if enabled else 1
        winreg.SetValueEx(key, "AppsUseLightTheme", 0, winreg.REG_DWORD, val)
        winreg.SetValueEx(key, "SystemUsesLightTheme", 0, winreg.REG_DWORD, val)
        winreg.CloseKey(key)
        return True
    except Exception:
        return False


def toggle_wifi(enabled: bool) -> bool:
    """Toggles the Wi-Fi network interface state on or off."""
    state = "enabled" if enabled else "disabled"
    cmd = f"netsh interface set interface name=\"Wi-Fi\" admin={state}"
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", cmd],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        return True
    except Exception:
        return False


def computer_settings(parameters: dict, response=None, player=None) -> str:
    """Adjust system settings like volume, brightness, dark mode, Wi-Fi, or power states."""
    action = parameters.get("action", "").lower().strip()
    value = parameters.get("value", "")
    app_name = parameters.get("app_name", "").strip()

    if action == "volume":
        target_val = str(value).lower().strip()
        
        # Check if setting app-specific volume
        if app_name:
            if target_val.isdigit():
                vol = int(target_val)
                if set_app_volume(app_name, vol):
                    msg = f"Volume for application '{app_name}' set to {vol}%."
                else:
                    msg = f"Could not find running session for application '{app_name}' to set volume."
            else:
                msg = f"Application volume level must be numeric: {value}"
            if player:
                player.write_log(f"🔊 {msg}")
            return msg

        # Otherwise adjust master volume
        if target_val.isdigit():
            target = int(target_val)
            try:
                from ctypes import cast, POINTER
                from comtypes import CoInitialize, CoUninitialize, CLSCTX_ALL
                from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
                CoInitialize()
                devices = AudioUtilities.GetSpeakers()
                interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
                volume_ctrl = cast(interface, POINTER(IAudioEndpointVolume))
                scalar_vol = max(0.0, min(1.0, target / 100.0))
                volume_ctrl.SetMasterVolumeLevelScalar(scalar_vol, None)
                CoUninitialize()
                msg = f"Master volume adjusted to {target}%."
            except Exception as e:
                msg = f"Failed to set master volume using COM endpoint: {e}"
        else:
            try:
                import pyautogui
                if "up" in target_val or "subir" in target_val:
                    pyautogui.press("volumeup", presses=5)
                    msg = "Volume increased."
                elif "down" in target_val or "bajar" in target_val:
                    pyautogui.press("volumedown", presses=5)
                    msg = "Volume decreased."
                elif "mute" in target_val or "silenciar" in target_val:
                    pyautogui.press("volumemute")
                    msg = "Volume mute toggled."
                else:
                    msg = f"Unrecognized volume value: {value}"
            except Exception as e:
                msg = f"Failed to emulate key volume change: {e}"
        
        if player:
            player.write_log(f"🔊 {msg}")
        return msg

    elif action in ("brightness", "set_brightness"):
        try:
            level = int(float(value))
        except Exception:
            return "Brightness value must be a number (0-100)."
        try:
            from actions.contextual_control import set_brightness
            if set_brightness(level):
                return f"Brightness set to {level}%."
            return "Brightness control is not supported on this hardware."
        except Exception as e:
            return f"Failed to adjust brightness: {e}"

    elif action == "dark_mode":
        val_lower = str(value).lower().strip()
        enabled = val_lower in ("true", "1", "on", "enable", "activar", "si")
        if set_dark_mode(enabled):
            state_str = "enabled" if enabled else "disabled"
            return f"Dark theme {state_str} successfully."
        return "Failed to modify registry for dark mode."

    elif action == "wifi":
        val_lower = str(value).lower().strip()
        enabled = val_lower in ("true", "1", "on", "enable", "activar", "si", "conectar")
        if toggle_wifi(enabled):
            state_str = "enabled" if enabled else "disabled"
            return f"Wi-Fi interface {state_str} successfully."
        return "Failed to toggle Wi-Fi status."

    elif action == "lock_screen":
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return "Screen locked successfully."
        except Exception as e:
            return f"Failed to lock screen: {e}"

    elif action == "shutdown":
        try:
            os.system("shutdown /s /t 15")
            return "Shutdown command triggered. System will shutdown in 15 seconds."
        except Exception as e:
            return f"Failed to trigger shutdown: {e}"

    elif action == "restart":
        try:
            os.system("shutdown /r /t 15")
            return "Restart command triggered. System will restart in 15 seconds."
        except Exception as e:
            return f"Failed to trigger restart: {e}"

    elif action in ("minimize", "window_minimize"):
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                window.minimize()
                return "Active window minimized."
            return "No active window found."
        except Exception as e:
            return f"Failed to minimize window: {e}"

    elif action in ("maximize", "window_maximize"):
        try:
            import pygetwindow as gw
            window = gw.getActiveWindow()
            if window:
                window.maximize()
                return "Active window maximized."
            return "No active window found."
        except Exception as e:
            return f"Failed to maximize window: {e}"

    return f"Settings action '{action}' is not supported yet, sir."
