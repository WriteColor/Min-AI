import time
import os
import re
from pathlib import Path
import pygetwindow as gw
import pyautogui
from pywinauto import Application
from pywinauto.findwindows import ElementNotFoundError, ElementAmbiguousError

def native_ui(parameters: dict, player=None) -> str:
    """
    Automatización nativa con esteroides usando pywinauto (UIA backend) y fallbacks.
    Permite emular la manipulación del DOM en Windows para aplicaciones nativas y modernas.
    """
    action = parameters.get("action", "")
    window_title = parameters.get("window_title", "")
    control_name = parameters.get("control_name", "") # Nombre del control (Button, Tab, etc)
    control_type = parameters.get("control_type", "") # Tipo de control (Button, Edit, List, etc)
    text_to_type = parameters.get("text", "")
    auto_id = parameters.get("auto_id", "")
    
    def get_app_and_dialog(title_re):
        try:
            # Conectarse a una ventana existente
            app = Application(backend="uia").connect(title_re=title_re, timeout=3)
            dlg = app.window(title_re=title_re)
            return app, dlg
        except Exception as e:
            if player:
                player.write_log(f"⚠️ pywinauto connection failed: {e}. Trying fallback.")
            return None, None

    if action == "list_windows":
        titles = [t for t in gw.getAllTitles() if t.strip()]
        return "Ventanas abiertas:\n" + "\n".join(titles)
        
    elif action == "focus_window":
        if not window_title:
            return "Error: Se requiere el nombre de la ventana (window_title)."
        app, dlg = get_app_and_dialog(f".*{window_title}.*")
        if dlg:
            try:
                dlg.set_focus()
                return f"Ventana '{window_title}' enfocada exitosamente con pywinauto."
            except Exception:
                pass
        
        # Fallback a pygetwindow
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            return f"No se encontró ninguna ventana con el título: '{window_title}'"
        
        win = windows[0]
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            return f"Ventana '{win.title}' enfocada exitosamente (fallback)."
        except Exception as e:
            return f"Error al intentar enfocar la ventana: {str(e)}"
            
    elif action == "type_in_window":
        if not window_title or not text_to_type:
            return "Error: Se requiere window_title y text."
        
        app, dlg = get_app_and_dialog(f".*{window_title}.*")
        if dlg:
            try:
                dlg.set_focus()
                kwargs = {}
                if control_name:
                    kwargs["title"] = control_name
                if control_type:
                    kwargs["control_type"] = control_type
                if auto_id:
                    kwargs["auto_id"] = auto_id
                
                if kwargs:
                    edit = dlg.child_window(**kwargs)
                    edit.type_keys(text_to_type, with_spaces=True)
                else:
                    dlg.type_keys(text_to_type, with_spaces=True)
                return f"Texto escrito en la ventana '{window_title}' usando pywinauto."
            except Exception as e:
                if player:
                    player.write_log(f"⚠️ pywinauto type keys failed: {e}. Trying fallback.")
            
        # Fallback a pygetwindow + pyautogui
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            return f"No se encontró la ventana: '{window_title}'"
            
        win = windows[0]
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.5) # Breve pausa para asegurar foco
            
            pyautogui.write(text_to_type, interval=0.01)
            return f"Texto escrito en la ventana '{win.title}' (fallback)."
        except Exception as e:
            return f"Error al escribir en la ventana: {str(e)}"

    elif action == "click_control":
        if not window_title or not (control_name or auto_id):
            return "Error: Se requiere window_title y control_name o auto_id."
        app, dlg = get_app_and_dialog(f".*{window_title}.*")
        if not dlg:
            return f"No se pudo conectar a la ventana '{window_title}'."
        try:
            dlg.set_focus()
            kwargs = {}
            if control_name:
                kwargs["title"] = control_name
            if control_type:
                kwargs["control_type"] = control_type
            if auto_id:
                kwargs["auto_id"] = auto_id
                
            ctrl = dlg.child_window(**kwargs)
            ctrl.click_input()
            return f"Clic realizado en el control '{control_name or auto_id}' de la ventana '{window_title}'."
        except Exception as e:
            return f"Error al hacer clic en el control: {e}"
            
    elif action == "click_center":
        if not window_title:
            return "Error: Se requiere window_title."
            
        app, dlg = get_app_and_dialog(f".*{window_title}.*")
        if dlg:
            try:
                dlg.set_focus()
                rect = dlg.rectangle()
                cx = rect.left + (rect.width() // 2)
                cy = rect.top + (rect.height() // 2)
                pyautogui.click(cx, cy)
                return f"Clic realizado en el centro de la ventana '{window_title}' usando rect de pywinauto."
            except Exception:
                pass
            
        # Fallback a pygetwindow
        windows = gw.getWindowsWithTitle(window_title)
        if not windows:
            return f"No se encontró la ventana: '{window_title}'"
            
        win = windows[0]
        try:
            if win.isMinimized:
                win.restore()
            win.activate()
            time.sleep(0.5)
            
            cx = win.left + (win.width // 2)
            cy = win.top + (win.height // 2)
            pyautogui.click(cx, cy)
            
            return f"Clic realizado en el centro de la ventana '{win.title}' (fallback)."
        except Exception as e:
            return f"Error al hacer clic: {str(e)}"
            
    elif action == "print_control_identifiers":
        if not window_title:
            return "Error: Se requiere window_title."
        app, dlg = get_app_and_dialog(f".*{window_title}.*")
        if not dlg:
            return f"No se pudo conectar a la ventana '{window_title}'."
        try:
            import io
            import sys as sys_module
            old_stdout = sys_module.stdout
            new_stdout = io.StringIO()
            sys_module.stdout = new_stdout
            dlg.print_control_identifiers()
            sys_module.stdout = old_stdout
            return new_stdout.getvalue()
        except Exception as e:
            return f"Error al listar identificadores: {e}"

    else:
        return f"Acción '{action}' no soportada por native_ui."
