"""
Windows Integration Service
============================
Capa de integración nativa con Windows 11 utilizando:
- pywinauto para UI Automation
- win32gui/win32con para control de ventanas
- psutil para gestión de procesos
- win32com para automatización COM

Este servicio permite control verificable y auditable del sistema operativo.
"""

from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass
from enum import Enum
import subprocess
import os
import sys
import time
import re
import threading
from functools import lru_cache

# Windows APIs
try:
    import win32gui
    import win32con
    import win32api
    import win32process
    import win32com.client
    HAS_WIN32 = True
except ImportError:
    HAS_WIN32 = False

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False

try:
    from pywinauto import Application, Desktop, timings
    from pywinauto.win32_element_info import HwndElementInfo
    HAS_PYWINAUTO = True
except ImportError:
    HAS_PYWINAUTO = False


class WindowState(Enum):
    UNKNOWN = "unknown"
    MINIMIZED = "minimized"
    NORMAL = "normal"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"


@dataclass
class WindowInfo:
    """Información sobre una ventana del sistema."""
    hwnd: int
    title: str
    process_name: str
    process_id: int
    state: WindowState
    rect: Tuple[int, int, int, int]  # left, top, right, bottom
    is_visible: bool
    is_active: bool
    
    @property
    def position(self) -> Tuple[int, int]:
        return (self.rect[0], self.rect[1])
    
    @property
    def size(self) -> Tuple[int, int]:
        return (self.rect[2] - self.rect[0], self.rect[3] - self.rect[1])


@dataclass
class ProcessInfo:
    """Información sobre un proceso."""
    pid: int
    name: str
    exe_path: str
    cpu_percent: float
    memory_mb: float
    is_running: bool
    window_hwnds: List[int]


class WindowsService:
    """
    Servicio de integración con Windows.
    Provee control verificable del sistema operativo.
    """
    
    def __init__(self):
        self._shell = None
        self._cached_processes: Dict[int, ProcessInfo] = {}
        self._process_cache_time = 0
        self._process_cache_ttl = 5  # seconds
        
    def _get_shell(self):
        """Obtiene referencia al Shell de Windows."""
        if self._shell is None and HAS_WIN32:
            try:
                self._shell = win32com.client.Dispatch("Shell.Application")
            except Exception as e:
                print(f"[WinService] Shell error: {e}")
        return self._shell
    
    # ── Window Management ──────────────────────────────────────────────────
    
    def find_window_by_title(self, title_pattern: str, exact: bool = False) -> Optional[WindowInfo]:
        """Busca una ventana por título (parcial o exacto)."""
        if not HAS_WIN32:
            return None
        
        result = [None]
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if title:
                    if exact:
                        if title == title_pattern:
                            result[0] = hwnd
                            return False
                    else:
                        if title_pattern.lower() in title.lower():
                            result[0] = hwnd
                            return False
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            print(f"[WinService] EnumWindows error: {e}")
        
        if result[0]:
            return self.get_window_info(result[0])
        return None
    
    def get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """Obtiene información completa de una ventana."""
        if not HAS_WIN32:
            return None
        
        try:
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return None
            
            rect = win32gui.GetWindowRect(hwnd)
            process_id = win32process.GetWindowThreadProcessId(hwnd)[0]
            
            # Get process info
            process_name = ""
            try:
                if HAS_PSUTIL:
                    proc = psutil.Process(process_id)
                    process_name = proc.name()
            except:
                pass
            
            # Determine state
            if win32gui.IsIconic(hwnd):
                state = WindowState.MINIMIZED
            elif win32gui.IsZoomed(hwnd):
                state = WindowState.MAXIMIZED
            else:
                state = WindowState.NORMAL
            
            is_visible = win32gui.IsWindowVisible(hwnd)
            is_active = win32gui.GetForegroundWindow() == hwnd
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                process_id=process_id,
                state=state,
                rect=rect,
                is_visible=is_visible,
                is_active=is_active
            )
        except Exception as e:
            print(f"[WinService] get_window_info error: {e}")
            return None
    
    def get_all_windows(self) -> List[WindowInfo]:
        """Obtiene todas las ventanas visibles del sistema."""
        if not HAS_WIN32:
            return []
        
        windows = []
        
        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                info = self.get_window_info(hwnd)
                if info and info.title:
                    windows.append(info)
            return True
        
        try:
            win32gui.EnumWindows(enum_callback, None)
        except Exception as e:
            print(f"[WinService] EnumWindows error: {e}")
        
        return windows
    
    def restore_window(self, hwnd: int) -> bool:
        """Restaura una ventana minimizada."""
        if not HAS_WIN32:
            return False
        
        try:
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception as e:
            print(f"[WinService] restore_window error: {e}")
            return False
    
    def minimize_window(self, hwnd: int) -> bool:
        """Minimiza una ventana."""
        if not HAS_WIN32:
            return False
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception as e:
            print(f"[WinService] minimize_window error: {e}")
            return False
    
    def maximize_window(self, hwnd: int) -> bool:
        """Maximiza una ventana."""
        if not HAS_WIN32:
            return False
        
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception as e:
            print(f"[WinService] maximize_window error: {e}")
            return False
    
    def close_window(self, hwnd: int) -> bool:
        """Cierra una ventana."""
        if not HAS_WIN32:
            return False
        
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception as e:
            print(f"[WinService] close_window error: {e}")
            return False
    
    # ── App Lifecycle ────────────────────────────────────────────────────────
    
    def find_running_app(self, app_name: str) -> Optional[WindowInfo]:
        """
        Busca una aplicación ya abierta que coincida con el nombre.
        Retorna la ventana si existe, None si no está corriendo.
        """
        app_lower = app_name.lower()
        
        # Common process names mapping
        process_map = {
            "chrome": "chrome.exe",
            "edge": "msedge.exe", 
            "firefox": "firefox.exe",
            "spotify": "spotify.exe",
            "whatsapp": "whatsapp.exe",
            "discord": "discord.exe",
            "vscode": "code.exe",
            "notepad": "notepad.exe",
            "explorer": "explorer.exe",
            "file explorer": "explorer.exe",
            "word": "WINWORD.EXE",
            "excel": "EXCEL.EXE",
            "powershell": "powershell.exe",
            "terminal": "WindowsTerminal.exe",
        }
        
        process_name = process_map.get(app_lower, f"{app_name}.exe")
        
        # Check if process is running
        if HAS_PSUTIL:
            for proc in psutil.process_iter(['pid', 'name', 'exe']):
                try:
                    if proc.info['name'].lower() == process_name.lower():
                        pid = proc.info['pid']
                        # Find window for this process
                        windows = self.get_all_windows()
                        for win in windows:
                            if win.process_id == pid:
                                return win
                        # Process running but no window? Still return info
                        return WindowInfo(
                            hwnd=0, title=app_name, process_name=process_name,
                            process_id=pid, state=WindowState.NORMAL,
                            rect=(0,0,0,0), is_visible=False, is_active=False
                        )
                except:
                    continue
        
        return None
    
    def launch_app(self, app_name: str, check_running: bool = True) -> Tuple[bool, str]:
        """
        Lanza una aplicación. Si ya está corriendo, la restaura en vez de abrir nueva instancia.
        
        Returns: (success, message)
        """
        app_lower = app_name.lower()
        
        # Check if already running
        if check_running:
            existing = self.find_running_app(app_name)
            if existing and existing.hwnd != 0:
                # App is already open - restore window instead of launching new
                self.restore_window(existing.hwnd)
                return True, f"Restored existing {app_name} window"
        
        # URL/website shortcuts
        if app_lower.startswith("http://") or app_lower.startswith("https://"):
            import webbrowser
            webbrowser.open(app_name)
            return True, f"Opened {app_name} in browser"
        
        # Try to launch via Shell
        try:
            shell = self._get_shell()
            if shell:
                # Try to use ShellExecute for better app launching
                import win32api
                result = win32api.ShellExecute(0, "open", app_name, None, None, 1)
                if result > 32:  # >32 means success
                    return True, f"Launched {app_name}"
        except Exception as e:
            print(f"[WinService] ShellExecute error: {e}")
        
        # Fallback to subprocess
        try:
            subprocess.Popen(app_name, creationflags=0x00000008)  # DETACHED_PROCESS
            return True, f"Launched {app_name}"
        except Exception as e:
            return False, f"Failed to launch {app_name}: {e}"
    
    # ── UI Automation ───────────────────────────────────────────────────────
    
    def find_element(self, window_title: str, element_description: str) -> Optional[Dict]:
        """
        Encuentra un elemento UI usando UI Automation.
        element_description puede ser: button_text, class_name, control_type
        
        Returns: dict con 'hwnd', 'rect', 'enabled', 'type'
        """
        if not HAS_PYWINAUTO:
            return None
        
        try:
            # Try to connect to the app
            app = Application(backend="win32")
            
            # Find window by title
            try:
                app.connect(title_re=f".*{window_title}.*", timeout=5)
            except:
                return None
            
            dlg = app.window(title_re=f".*{window_title}.*")
            
            # Try to find button with text
            try:
                btn = dlg.child_window(title_re=f".*{element_description}.*", control_type="Button")
                if btn.exists(timeout=2):
                    return {
                        "hwnd": btn.handle,
                        "rect": btn.rectangle(),
                        "enabled": btn.is_enabled(),
                        "type": "button",
                        "text": btn.window_text()
                    }
            except:
                pass
            
            # Try any control with matching text
            try:
                ctrl = dlg.child_window(title_re=f".*{element_description}.*")
                if ctrl.exists(timeout=2):
                    return {
                        "hwnd": ctrl.handle,
                        "rect": ctrl.rectangle(),
                        "enabled": ctrl.is_enabled(),
                        "type": ctrl.control_type(),
                        "text": ctrl.window_text()
                    }
            except:
                pass
                
        except Exception as e:
            print(f"[WinService] find_element error: {e}")
        
        return None
    
    def click_element(self, window_title: str, element_text: str) -> bool:
        """Hace clic en un elemento UI."""
        if not HAS_PYWINAUTO:
            return False
        
        try:
            app = Application(backend="win32")
            app.connect(title_re=f".*{window_title}.*", timeout=5)
            dlg = app.window(title_re=f".*{window_title}.*")
            
            btn = dlg.child_window(title_re=f".*{element_text}.*", control_type="Button")
            if btn.exists(timeout=2):
                btn.click()
                return True
        except Exception as e:
            print(f"[WinService] click_element error: {e}")
        
        return False
    
    def type_text(self, window_title: str, control_description: str, text: str) -> bool:
        """Escribe texto en un control de entrada."""
        if not HAS_PYWINAUTO:
            return False
        
        try:
            app = Application(backend="win32")
            app.connect(title_re=f".*{window_title}.*", timeout=5)
            dlg = app.window(title_re=f".*{window_title}.*")
            
            ctrl = dlg.child_window(title_re=f".*{control_description}.*", control_type="Edit")
            if ctrl.exists(timeout=2):
                ctrl.set_edit_text(text)
                return True
        except Exception as e:
            print(f"[WinService] type_text error: {e}")
        
        return False
    
    # ── Process Management ──────────────────────────────────────────────────
    
    def get_processes(self, refresh: bool = False) -> List[ProcessInfo]:
        """Obtiene lista de procesos activos."""
        if not HAS_PSUTIL:
            return []
        
        now = time.time()
        if not refresh and (now - self._process_cache_time) < self._process_cache_ttl:
            return list(self._cached_processes.values())
        
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cpu_percent', 'memory_info']):
                try:
                    info = proc.info
                    cpu = info.get('cpu_percent', 0) or 0
                    mem = info.get('memory_info')
                    mem_mb = mem.rss / 1024 / 1024 if mem else 0
                    
                    # Get window handles for this process
                    hwnds = []
                    for hwnd in self.get_all_windows():
                        if hwnd.process_id == info['pid']:
                            hwnds.append(hwnd.hwnd)
                    
                    p = ProcessInfo(
                        pid=info['pid'],
                        name=info['name'],
                        exe_path=info.get('exe', ''),
                        cpu_percent=cpu,
                        memory_mb=mem_mb,
                        is_running=True,
                        window_hwnds=hwnds
                    )
                    processes.append(p)
                except:
                    continue
            
            self._cached_processes = {p.pid: p for p in processes}
            self._process_cache_time = now
        except Exception as e:
            print(f"[WinService] get_processes error: {e}")
        
        return processes
    
    def kill_process(self, pid: int) -> bool:
        """Termina un proceso por PID."""
        if not HAS_PSUTIL:
            return False
        
        try:
            proc = psutil.Process(pid)
            proc.terminate()
            proc.wait(timeout=3)
            return True
        except psutil.NoSuchProcess:
            return True  # Already dead
        except Exception as e:
            print(f"[WinService] kill_process error: {e}")
            return False
    
    # ── System Control ────────────────────────────────────────────────────────
    
    def set_volume(self, level: int) -> bool:
        """Establece el volumen del sistema (0-100)."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevelScalar(level / 100.0, None)
            return True
        except Exception as e:
            print(f"[WinService] set_volume error: {e}")
            return False
    
    def get_volume(self) -> int:
        """Obtiene el volumen actual del sistema (0-100)."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            return int(volume.GetMasterVolumeLevelScalar() * 100)
        except Exception:
            return 50
    
    def mute_system(self) -> bool:
        """Silencia el sistema."""
        try:
            from ctypes import cast, POINTER
            from comtypes import CLSCTX_ALL
            from pycaw.pycaw import AudioUtilities, IAudioEndpointVolume
            
            devices = AudioUtilities.GetSpeakers()
            interface = devices.Activate(IAudioEndpointVolume._iid_, CLSCTX_ALL, None)
            volume = cast(interface, POINTER(IAudioEndpointVolume))
            volume.SetMasterVolumeLevel(0, None)
            return True
        except Exception as e:
            print(f"[WinService] mute_system error: {e}")
            return False
    
    # ── Screenshot ──────────────────────────────────────────────────────────
    
    def capture_screen(self, monitor: int = 0, path: Optional[str] = None) -> Optional[bytes]:
        """Captura screenshot de la pantalla."""
        try:
            from PIL import ImageGrab
            import os
            
            if monitor == 0:
                # All monitors combined
                bbox = None
            else:
                # Specific monitor - use virtual screen for multi-monitor
                monitors = self.get_monitor_geometry()
                if monitor <= len(monitors):
                    bbox = monitors[monitor - 1]
                else:
                    bbox = None
            
            img = ImageGrab.grab(bbox=bbox)
            
            if path:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                img.save(path)
            
            import io
            buf = io.BytesIO()
            img.save(buf, format='PNG')
            return buf.getvalue()
        except Exception as e:
            print(f"[WinService] capture_screen error: {e}")
            return None
    
    def get_monitor_geometry(self) -> List[Tuple[int, int, int, int]]:
        """Obtiene geometría de todos los monitores."""
        if not HAS_WIN32:
            return []
        
        monitors = []
        
        def callback(hwnd, mon):
            rect = win32gui.GetWindowRect(hwnd)
            if rect[2] - rect[0] > 0 and rect[3] - rect[1] > 0:
                # Filter out invisible/minimal windows
                pass
            return True
        
        try:
            # Get virtual screen bounds for all monitors
            virtual_left = win32api.GetSystemMetrics(win32con.SM_XVIRTUALSCREEN)
            virtual_top = win32api.GetSystemMetrics(win32con.SM_YVIRTUALSCREEN)
            virtual_width = win32api.GetSystemMetrics(win32con.SM_CXVIRTUALSCREEN)
            virtual_height = win32api.GetSystemMetrics(win32con.SM_CYVIRTUALSCREEN)
            
            # Get monitor info
            for i in range(win32api.GetSystemMetrics(win32con.SM_CMONITORS)):
                pass
        except:
            pass
        
        return [(0, 0, 1920, 1080)]  # Fallback single monitor


# Singleton instance
_windows_service: Optional[WindowsService] = None


def get_windows_service() -> WindowsService:
    """Obtiene la instancia singleton del servicio de Windows."""
    global _windows_service
    if _windows_service is None:
        _windows_service = WindowsService()
    return _windows_service