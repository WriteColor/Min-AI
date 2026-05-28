import time
import urllib.parse
import pyautogui
import pygetwindow as gw
from actions.browser_registry import launch_url, resolve_browser_path

def _preferred_keywords() -> list[str]:
    keyword_map = {
        "chrome": ["chrome"],
        "brave": ["brave"],
        "edge": ["edge"],
        "firefox": ["firefox"],
        "opera": ["opera"],
        "opera_gx": ["opera gx", "opera"],
        "vivaldi": ["vivaldi"],
        "tor": ["tor"],
    }

    preferred, _ = resolve_browser_path()
    ordered: list[str] = []
    if preferred in keyword_map:
        ordered.extend(keyword_map[preferred])
    for values in keyword_map.values():
        for item in values:
            if item not in ordered:
                ordered.append(item)
    return ordered


def _find_browser_window() -> tuple[object | None, str | None]:
    keywords = _preferred_keywords()
    for win in gw.getAllWindows():
        title = win.title.strip()
        if not title:
            continue
        lower = title.lower()
        for kw in keywords:
            if kw in lower:
                return win, kw
    return None, None


def _normalize_action(action: str) -> str:
    mapping = {
        "open_url": "go_to",
        "navigate": "go_to",
        "open": "go_to",
        "search_web": "search",
        "newtab": "new_tab",
        "nexttab": "next_tab",
        "prevtab": "prev_tab",
        "previous_tab": "prev_tab",
        "close": "close_tab",
        "reload": "refresh",
        "hard_reload": "refresh_hard",
        "refresh_hard": "refresh_hard",
        "page_up": "page_up",
        "page_down": "page_down",
        "scroll_up": "scroll",
        "scroll_down": "scroll",
        "incognito": "private_window",
        "private": "private_window",
        "fullscreen": "toggle_fullscreen",
        "devtools": "open_devtools",
        "history": "open_history",
        "downloads": "open_downloads",
        "bookmarks": "open_bookmarks",
    }
    return mapping.get(action, action)


def _coerce_int(value, default: int) -> int:
    try:
        return int(value)
    except Exception:
        return default


def browser_control(parameters: dict, player=None) -> str:
    """
    Controla el navegador activo del usuario (Chrome, Edge, Firefox, etc.) mediante simulación de teclado.
    """
    action = _normalize_action(str(parameters.get("action", "")).lower().strip())

    target_window, browser_kw = _find_browser_window()
    if not target_window:
        if action in ("go_to", "search", "new_tab", "new_window", "private_window"):
            url = parameters.get("url", "").strip()
            query = parameters.get("query", "").strip()
            if action == "search":
                if not query:
                    return "Error: Falta la búsqueda (query)."
                url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            if url:
                launch_url(url)
                return "No se encontró un navegador abierto. Abrí la URL en el navegador configurado."
        return "No se encontró ningún navegador (Chrome, Edge, Firefox, etc.) abierto en la pantalla."
        
    try:
        # 2. Restaurar y Enfocar la ventana del navegador
        if target_window.isMinimized:
            target_window.restore()
        target_window.activate()
        time.sleep(0.15) # Tiempo para que la ventana tome foco
        
        # 3. Ejecutar la acción mediante atajos de teclado universales
        if action == "go_to":
            url = parameters.get("url", "")
            if not url:
                return "Error: Falta la URL."
            # Foco en barra de direcciones
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.05)
            pyautogui.write(url, interval=0.005)
            pyautogui.press('enter')
            return f"Navegando a {url} en la ventana '{target_window.title}'."
            
        elif action == "search":
            query = parameters.get("query", "")
            if not query:
                return "Error: Falta la búsqueda (query)."
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            # Foco en barra de direcciones
            pyautogui.hotkey('ctrl', 'l')
            time.sleep(0.05)
            pyautogui.write(url, interval=0.005)
            pyautogui.press('enter')
            return f"Buscando '{query}' en la ventana '{target_window.title}'."
            
        elif action == "new_tab":
            url = parameters.get("url", "")
            pyautogui.hotkey('ctrl', 't')
            time.sleep(0.3)
            if url:
                pyautogui.write(url, interval=0.01)
                pyautogui.press('enter')
                return f"Nueva pestaña abierta y navegando a {url}."
            return "Nueva pestaña abierta."

        elif action == "new_window":
            pyautogui.hotkey('ctrl', 'n')
            return "Nueva ventana abierta."

        elif action == "private_window":
            if browser_kw == "firefox":
                pyautogui.hotkey('ctrl', 'shift', 'p')
            else:
                pyautogui.hotkey('ctrl', 'shift', 'n')
            return "Nueva ventana privada abierta."
            
        elif action == "close_tab":
            pyautogui.hotkey('ctrl', 'w')
            return "Pestaña actual cerrada."

        elif action == "next_tab":
            pyautogui.hotkey('ctrl', 'tab')
            return "Cambiando a la siguiente pestana."

        elif action == "prev_tab":
            pyautogui.hotkey('ctrl', 'shift', 'tab')
            return "Cambiando a la pestana anterior."

        elif action == "back":
            pyautogui.hotkey('alt', 'left')
            return "Retrocediendo en el historial."

        elif action == "forward":
            pyautogui.hotkey('alt', 'right')
            return "Avanzando en el historial."

        elif action == "refresh":
            pyautogui.hotkey('ctrl', 'r')
            return "Recargando pagina."

        elif action == "refresh_hard":
            pyautogui.hotkey('ctrl', 'shift', 'r')
            return "Recarga completa ejecutada."

        elif action == "stop_loading":
            pyautogui.press('esc')
            return "Carga detenida."
            
        elif action == "scroll":
            direction = str(parameters.get("direction", "down")).lower().strip()
            amount = _coerce_int(parameters.get("amount"), 600)
            sign = -1 if direction in ("down", "abajo", "d") else 1
            pyautogui.scroll(sign * abs(amount))
            return f"Scroll {direction} completado."

        elif action == "page_down":
            pyautogui.press('pgdn')
            return "Page down ejecutado."

        elif action == "page_up":
            pyautogui.press('pgup')
            return "Page up ejecutado."

        elif action == "zoom_in":
            pyautogui.hotkey('ctrl', '+')
            return "Zoom aumentado."

        elif action == "zoom_out":
            pyautogui.hotkey('ctrl', '-')
            return "Zoom reducido."

        elif action == "zoom_reset":
            pyautogui.hotkey('ctrl', '0')
            return "Zoom restablecido."

        elif action == "find":
            pyautogui.hotkey('ctrl', 'f')
            text = parameters.get("text", "").strip()
            if text:
                pyautogui.write(text, interval=0.005)
            return "Buscador abierto."

        elif action == "type":
            text = parameters.get("text", "")
            if not text:
                return "Error: Falta el texto para escribir."
            pyautogui.write(text, interval=0.005)
            if parameters.get("enter"):
                pyautogui.press('enter')
            return "Texto escrito."

        elif action == "open_downloads":
            pyautogui.hotkey('ctrl', 'j')
            return "Descargas abiertas."

        elif action == "open_history":
            pyautogui.hotkey('ctrl', 'h')
            return "Historial abierto."

        elif action == "open_bookmarks":
            pyautogui.hotkey('ctrl', 'shift', 'o')
            return "Marcadores abiertos."

        elif action == "open_devtools":
            pyautogui.hotkey('ctrl', 'shift', 'i')
            return "DevTools abierto."

        elif action == "toggle_fullscreen":
            pyautogui.press('f11')
            return "Pantalla completa alternada."

        elif action == "close_window":
            pyautogui.hotkey('alt', 'f4')
            return "Ventana cerrada."
            
        else:
            return f"Accion '{action}' no es compatible con el control de navegador activo. Usa atajos de teclado estandar."
            
    except Exception as e:
        return f"Error al intentar controlar el navegador: {str(e)}"
