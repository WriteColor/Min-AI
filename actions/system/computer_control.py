"""computer_control.py — Refactored active keyboard, mouse, and window focus control."""
import time
import pyautogui
import pygetwindow as gw

def focus_window_uia(title: str) -> bool:
    """Uses pywinauto UIA backend to restore and force focus onto a window on Windows 11."""
    try:
        from pywinauto import Desktop
        windows = Desktop(backend="uia").windows(title_re=f".*{title}.*", visible_only=True)
        if windows:
            win = windows[0]
            if win.is_minimized():
                win.restore()
            win.set_focus()
            return True
    except Exception:
        pass
    
    # Fallback to pygetwindow + win32gui to force foreground focus
    try:
        wins = gw.getWindowsWithTitle(title)
        if wins:
            win = wins[0]
            if win.isMinimized:
                win.restore()
            win.activate()
            return True
    except Exception:
        pass
    return False

def computer_control(parameters: dict, player=None) -> str:
    action = str(parameters.get("action", "")).lower().strip()

    if action == "type":
        text = parameters.get("text", "")
        if not text:
            return "Error: text is required."
        pyautogui.write(text, interval=0.01)
        return "Text typed successfully."

    elif action == "press":
        key = parameters.get("key", "")
        if not key:
            return "Error: key is required."
        pyautogui.press(key)
        return f"Key '{key}' pressed."

    elif action == "hotkey":
        keys = parameters.get("keys", "")
        if not keys:
            return "Error: keys is required."
        seq = [k.strip() for k in keys.split("+") if k.strip()]
        if not seq:
            return "Error: keys is invalid."
        pyautogui.hotkey(*seq)
        return f"Shortcut executed: {keys}."

    elif action in ("click", "double_click", "right_click"):
        x = parameters.get("x")
        y = parameters.get("y")
        if x is None or y is None:
            return "Error: x and y coordinates are required."
        
        # Focus screen coordinates
        px, py = int(x), int(y)
        if action == "click":
            pyautogui.click(px, py)
        elif action == "double_click":
            pyautogui.doubleClick(px, py)
        else:
            pyautogui.rightClick(px, py)
        return f"Click executed at coordinates: ({px}, {py})."

    elif action == "scroll":
        amount = int(parameters.get("amount", 3))
        direction = str(parameters.get("direction", "down")).lower().strip()
        sign = -1 if direction in ("down", "abajo") else 1
        pyautogui.scroll(sign * abs(amount) * 120)
        return "Scroll executed."

    elif action == "move":
        x = parameters.get("x")
        y = parameters.get("y")
        if x is None or y is None:
            return "Error: x and y coordinates are required."
        pyautogui.moveTo(int(x), int(y))
        return "Cursor moved."

    elif action == "wait":
        seconds = float(parameters.get("seconds", 0.5))
        time.sleep(max(0.0, seconds))
        return "Wait completed."

    elif action == "copy":
        pyautogui.hotkey("ctrl", "c")
        return "Copied to clipboard."

    elif action == "paste":
        pyautogui.hotkey("ctrl", "v")
        return "Pasted from clipboard."

    elif action == "clear_field":
        pyautogui.hotkey("ctrl", "a")
        pyautogui.press("backspace")
        return "Field cleared."

    elif action == "focus_window":
        title = parameters.get("title", "")
        if not title:
            return "Error: title is required."
        if focus_window_uia(title):
            return f"Window matching '{title}' focused."
        return f"Could not find or focus window matching title: '{title}'."

    elif action == "minimize_window":
        title = parameters.get("title", "")
        try:
            if title:
                wins = gw.getWindowsWithTitle(title)
                if wins:
                    wins[0].minimize()
                    return f"Window '{wins[0].title}' minimized."
                return f"No window matching '{title}' was found."
            else:
                win = gw.getActiveWindow()
                if win:
                    win.minimize()
                    return f"Active window '{win.title}' minimized."
                return "No active window found."
        except Exception as e:
            return f"Failed to minimize window: {e}"

    elif action == "maximize_window":
        title = parameters.get("title", "")
        try:
            if title:
                wins = gw.getWindowsWithTitle(title)
                if wins:
                    wins[0].maximize()
                    return f"Window '{wins[0].title}' maximized."
                return f"No window matching '{title}' was found."
            else:
                win = gw.getActiveWindow()
                if win:
                    win.maximize()
                    return f"Active window '{win.title}' maximized."
                return "No active window found."
        except Exception as e:
            return f"Failed to maximize window: {e}"

    elif action == "restore_window":
        title = parameters.get("title", "")
        try:
            if title:
                wins = gw.getWindowsWithTitle(title)
                if wins:
                    wins[0].restore()
                    return f"Window '{wins[0].title}' restored."
                return f"No window matching '{title}' was found."
            else:
                win = gw.getActiveWindow()
                if win:
                    win.restore()
                    return f"Active window '{win.title}' restored."
                return "No active window found."
        except Exception as e:
            return f"Failed to restore window: {e}"

    elif action == "close_window":
        title = parameters.get("title", "")
        try:
            if title:
                wins = gw.getWindowsWithTitle(title)
                if wins:
                    wins[0].close()
                    return f"Window '{wins[0].title}' closed."
                return f"No window matching '{title}' was found."
            else:
                win = gw.getActiveWindow()
                if win:
                    win.close()
                    return f"Active window '{win.title}' closed."
                return "No active window found."
        except Exception as e:
            return f"Failed to close window: {e}"

    elif action == "list_windows":
        try:
            titles = [w.title for w in gw.getAllWindows() if w.title and w.visible]
            if not titles:
                return "No visible open windows found."
            return "Active visible windows:\n" + "\n".join(f"- {t}" for t in set(titles))
        except Exception as e:
            return f"Failed to list windows: {e}"

    elif action == "screenshot":
        try:
            from pathlib import Path
            import datetime
            import ctypes
            import io
            
            # 1. Resolve save path
            custom_path = parameters.get("path", "").strip()
            if custom_path:
                filepath = Path(custom_path)
            else:
                pictures_dir = Path.home() / "Pictures" / "MIN Screenshots"
                pictures_dir.mkdir(parents=True, exist_ok=True)
                timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                filepath = pictures_dir / f"screenshot_{timestamp}.png"
            
            # Ensure parent directories exist
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # 2. Take screenshot
            screenshot = pyautogui.screenshot()
            screenshot.save(str(filepath))
            
            # 3. Copy to Windows clipboard via ctypes (CF_DIB)
            try:
                output = io.BytesIO()
                screenshot.convert("RGB").save(output, "BMP")
                data = output.getvalue()[14:]  # Offset 14 is the BMP file header
                output.close()
                
                ctypes.windll.user32.OpenClipboard(None)
                ctypes.windll.user32.EmptyClipboard()
                ctypes.windll.user32.SetClipboardData(8, ctypes.windll.kernel32.GlobalAlloc(0x0002, len(data)))
                h_clip_mem = ctypes.windll.user32.GetClipboardData(8)
                p_clip_mem = ctypes.windll.kernel32.GlobalLock(h_clip_mem)
                ctypes.cdll.msvcrt.memcpy(p_clip_mem, data, len(data))
                ctypes.windll.kernel32.GlobalUnlock(h_clip_mem)
                ctypes.windll.user32.CloseClipboard()
                copied_info = " y guardada en el portapapeles"
            except Exception as clip_err:
                copied_info = f" (error al guardar en portapapeles: {clip_err})"
                
            msg = f"Captura de pantalla guardada en: {filepath}{copied_info}."
            if player:
                player.write_log(f"📸 {msg}")
            return msg
        except Exception as e:
            return f"Error al tomar captura de pantalla: {e}"

    return f"Action '{action}' is not supported by computer_control."
