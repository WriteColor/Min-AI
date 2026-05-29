import pyautogui

def media_control(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "")).lower().strip()
    key_map = {
        "play": "playpause",
        "pause": "playpause",
        "play_pause": "playpause",
        "toggle": "playpause",
        "next": "nexttrack",
        "previous": "prevtrack",
        "prev": "prevtrack",
        "stop": "stop",
        "volume_up": "volumeup",
        "volume_down": "volumedown",
        "mute": "volumemute",
    }

    if action not in key_map:
        return f"Accion '{action}' no soportada por media_control."

    # Direct master volume control via pycaw (WASAPI) on Windows
    if action in ["volume_up", "volume_down", "mute"]:
        try:
            from pycaw.pycaw import AudioUtilities
            devices = AudioUtilities.GetSpeakers()
            if devices:
                volume = devices.EndpointVolume
                if action == "volume_up":
                    current_val = volume.GetMasterVolumeLevelScalar()
                    new_val = min(1.0, current_val + 0.05)
                    volume.SetMasterVolumeLevelScalar(new_val, None)
                    return f"Volumen de Windows incrementado a {new_val * 100:.0f}%"
                elif action == "volume_down":
                    current_val = volume.GetMasterVolumeLevelScalar()
                    new_val = max(0.0, current_val - 0.05)
                    volume.SetMasterVolumeLevelScalar(new_val, None)
                    return f"Volumen de Windows decrementado a {new_val * 100:.0f}%"
                elif action == "mute":
                    is_muted = volume.GetMute()
                    new_mute = 0 if is_muted else 1
                    volume.SetMute(new_mute, None)
                    return f"Volumen de Windows {'activado' if is_muted else 'silenciado'}."
        except Exception as e:
            print(f"[Volume API] pycaw failed, falling back to pyautogui: {e}")

    try:
        pyautogui.press(key_map[action])
        return f"Media: {action} ejecutado."
    except Exception as exc:
        return f"Error ejecutando media_control ({action}): {exc}"
