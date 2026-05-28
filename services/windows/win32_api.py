"""
services/windows/win32_api.py — Windows 11 Native Control Layer
================================================================
Win32 API integration for reliable Windows 11 control.
Provides unified interface for window management, process control,
and system operations.

Author: MIN AI Team
Version: 1.0
"""

import ctypes
import win32gui
import win32con
import win32process
import win32api
import win32security
from ctypes import wintypes
from typing import Optional, List, Dict, Tuple, Callable
from dataclasses import dataclass
from enum import Enum
import time


class WindowState(Enum):
    UNKNOWN = "unknown"
    MINIMIZED = "minimized"
    RESTORED = "restored"
    MAXIMIZED = "maximized"
    FULLSCREEN = "fullscreen"
    FOCUSED = "focused"


@dataclass
class WindowInfo:
    hwnd: int
    title: str
    process_name: str
    process_id: int
    state: WindowState
    bounds: Tuple[int, int, int, int]  # (x, y, width, height)
    is_elevated: bool = False


@dataclass
class ProcessInfo:
    pid: int
    name: str
    path: str
    memory_mb: float
    cpu_percent: float


class Win32API:
    """
    Windows 11 Win32 API wrapper for native control operations.
    Provides reliable, verified control of Windows system components.
    """
    
    def __init__(self):
        self._window_cache: Dict[int, WindowInfo] = {}
        self._last_cache_update = 0
        self._cache_timeout = 5.0  # seconds
        
    def _is_cache_valid(self) -> bool:
        return (time.time() - self._last_cache_update) < self._cache_timeout
    
    def _invalidate_cache(self):
        self._window_cache.clear()
        self._last_cache_update = 0
    
    def get_window_by_title(self, title: str, partial: bool = True) -> Optional[WindowInfo]:
        """
        Find window by title.
        
        Args:
            title: Window title to search for
            partial: If True, match partial titles
            
        Returns:
            WindowInfo or None
        """
        windows = self.enumerate_windows()
        for win in windows:
            if partial:
                if title.lower() in win.title.lower():
                    return win
            else:
                if win.title.lower() == title.lower():
                    return win
        return None
    
    def get_window_by_pid(self, pid: int) -> List[WindowInfo]:
        """Get all windows for a process ID."""
        windows = self.enumerate_windows()
        return [w for w in windows if w.process_id == pid]
    
    def get_foreground_window(self) -> Optional[WindowInfo]:
        """Get currently focused window."""
        try:
            hwnd = win32gui.GetForegroundWindow()
            return self._get_window_info(hwnd)
        except Exception:
            return None
    
    def set_foreground_window(self, hwnd: int) -> bool:
        """Bring window to foreground."""
        try:
            win32gui.SetForegroundWindow(hwnd)
            return True
        except Exception:
            return False
    
    def restore_window(self, hwnd: int) -> bool:
        """Restore minimized window."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            return True
        except Exception:
            return False
    
    def minimize_window(self, hwnd: int) -> bool:
        """Minimize window."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
            return True
        except Exception:
            return False
    
    def maximize_window(self, hwnd: int) -> bool:
        """Maximize window."""
        try:
            win32gui.ShowWindow(hwnd, win32con.SW_MAXIMIZE)
            return True
        except Exception:
            return False
    
    def close_window(self, hwnd: int) -> bool:
        """Close window gracefully."""
        try:
            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
            return True
        except Exception:
            return False
    
    def get_window_state(self, hwnd: int) -> WindowState:
        """Get window state (minimized, maximized, etc)."""
        try:
            if not win32gui.IsWindowVisible(hwnd):
                return WindowState.MINIMIZED
            if win32gui.IsZoomed(hwnd):
                return WindowState.MAXIMIZED
            if win32gui.IsIconic(hwnd):
                return WindowState.MINIMIZED
            return WindowState.RESTORED
        except Exception:
            return WindowState.UNKNOWN
    
    def enumerate_windows(self) -> List[WindowInfo]:
        """
        Enumerate all visible windows with their info.
        Uses caching for performance.
        """
        if self._is_cache_valid() and self._window_cache:
            return list(self._window_cache.values())
        
        windows = []
        
        def callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                title = win32gui.GetWindowText(hwnd)
                if not title:
                    return
                    
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                process_name = self._get_process_name(pid)
                state = self.get_window_state(hwnd)
                rect = win32gui.GetWindowRect(hwnd)
                bounds = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
                is_elevated = self._is_process_elevated(pid)
                
                info = WindowInfo(
                    hwnd=hwnd,
                    title=title,
                    process_name=process_name,
                    process_id=pid,
                    state=state,
                    bounds=bounds,
                    is_elevated=is_elevated
                )
                windows.append(info)
                self._window_cache[hwnd] = info
            except Exception:
                pass
        
        try:
            win32gui.EnumWindows(callback, None)
            self._last_cache_update = time.time()
        except Exception:
            pass
        
        return windows
    
    def _get_window_info(self, hwnd: int) -> Optional[WindowInfo]:
        """Get window info for specific hwnd."""
        try:
            title = win32gui.GetWindowText(hwnd)
            if not title:
                return None
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            process_name = self._get_process_name(pid)
            state = self.get_window_state(hwnd)
            rect = win32gui.GetWindowRect(hwnd)
            bounds = (rect[0], rect[1], rect[2] - rect[0], rect[3] - rect[1])
            is_elevated = self._is_process_elevated(pid)
            
            return WindowInfo(
                hwnd=hwnd,
                title=title,
                process_name=process_name,
                process_id=pid,
                state=state,
                bounds=bounds,
                is_elevated=is_elevated
            )
        except Exception:
            return None
    
    def _get_process_name(self, pid: int) -> str:
        """Get process name from PID."""
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION | win32con.PROCESS_VM_READ, False, pid)
            name = win32process.GetModuleFileNameEx(handle, 0)
            win32api.CloseHandle(handle)
            return name.split('\\')[-1] if name else "Unknown"
        except Exception:
            return "Unknown"
    
    def _is_process_elevated(self, pid: int) -> bool:
        """Check if process runs with elevated privileges."""
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
            token = win32security.OpenProcessToken(handle, win32con.TOKEN_QUERY)
            elevation = win32security.GetTokenInformation(token, win32security.TokenElevation)
            win32api.CloseHandle(handle)
            return bool(elevation)
        except Exception:
            return False
    
    def find_window_by_class(self, class_name: str) -> Optional[int]:
        """Find window by class name."""
        try:
            return win32gui.FindWindow(class_name, None)
        except Exception:
            return None
    
    def get_children_windows(self, hwnd: int) -> List[int]:
        """Get child windows of a parent window."""
        children = []
        
        def callback(child, _):
            children.append(child)
        
        try:
            win32gui.EnumChildWindows(hwnd, callback, None)
        except Exception:
            pass
        
        return children
    
    def get_window_text(self, hwnd: int) -> str:
        """Get window title text."""
        try:
            return win32gui.GetWindowText(hwnd)
        except Exception:
            return ""
    
    def set_window_text(self, hwnd: int, text: str) -> bool:
        """Set window title text."""
        try:
            win32gui.SetWindowText(hwnd, text)
            return True
        except Exception:
            return False
    
    def move_window(self, hwnd: int, x: int, y: int, width: int, height: int) -> bool:
        """Move and resize window."""
        try:
            win32gui.MoveWindow(hwnd, x, y, width, height, True)
            return True
        except Exception:
            return False


class ProcessManager:
    """
    Windows process management with verification.
    Handles process creation, termination, and monitoring.
    """
    
    @staticmethod
    def get_process_list() -> List[ProcessInfo]:
        """Get list of running processes with resource usage."""
        processes = []
        
        def callback(hwnd, _):
            try:
                if not win32gui.IsWindowVisible(hwnd):
                    return
                _, pid = win32process.GetWindowThreadProcessId(hwnd)
                if pid == 0:
                    return
                    
                try:
                    handle = win32api.OpenProcess(win32con.PROCESS_QUERY_INFORMATION, False, pid)
                    name = win32process.GetModuleFileNameEx(handle, 0)
                    win32api.CloseHandle(handle)
                    name = name.split('\\')[-1] if name else "Unknown"
                except Exception:
                    name = "Unknown"
                
                processes.append(ProcessInfo(
                    pid=pid,
                    name=name,
                    path="",
                    memory_mb=0,
                    cpu_percent=0
                ))
            except Exception:
                pass
        
        try:
            win32gui.EnumWindows(callback, None)
        except Exception:
            pass
        
        return processes
    
    @staticmethod
    def is_process_running(process_name: str) -> bool:
        """Check if a process is running."""
        processes = ProcessManager.get_process_list()
        for p in processes:
            if process_name.lower() in p.name.lower():
                return True
        return False
    
    @staticmethod
    def terminate_process(pid: int, force: bool = False) -> bool:
        """Terminate a process by PID."""
        try:
            handle = win32api.OpenProcess(win32con.PROCESS_TERMINATE | win32con.PROCESS_QUERY_INFORMATION, False, pid)
            if force:
                win32api.TerminateProcess(handle, 1)
            else:
                win32api.PostMessage(handle, win32con.WM_CLOSE, 0, 0)
            win32api.CloseHandle(handle)
            return True
        except Exception:
            return False


class SystemInfo:
    """Windows system information gathering."""
    
    @staticmethod
    def get_cpu_count() -> int:
        """Get number of CPU cores."""
        system_info = win32api.GetSystemInfo()
        return system_info['dwNumberOfProcessors']
    
    @staticmethod
    def get_memory_info() -> Dict[str, float]:
        """Get memory usage info in MB."""
        try:
            kernel32 = ctypes.windll.kernel32
            
            class MEMORYSTATUSEX(ctypes.Structure):
                _fields_ = [
                    ("dwLength", wintypes.DWORD),
                    ("dwMemoryLoad", wintypes.DWORD),
                    ("ullTotalPhys", ctypes.c_uint64),
                    ("ullAvailPhys", ctypes.c_uint64),
                    ("ullTotalPageFile", ctypes.c_uint64),
                    ("ullAvailPageFile", ctypes.c_uint64),
                    ("ullTotalVirtual", ctypes.c_uint64),
                    ("ullAvailVirtual", ctypes.c_uint64),
                    ("sullAvailExtendedVirtual", ctypes.c_uint64),
                ]
            
            memstatus = MEMORYSTATUSEX()
            memstatus.dwLength = ctypes.sizeof(MEMORYSTATUSEX)
            kernel32.GlobalMemoryStatusEx(ctypes.byref(memstatus))
            
            return {
                'total_mb': memstatus.ullTotalPhys / (1024 * 1024),
                'available_mb': memstatus.ullAvailPhys / (1024 * 1024),
                'used_mb': (memstatus.ullTotalPhys - memstatus.ullAvailPhys) / (1024 * 1024),
                'percent_used': memstatus.dwMemoryLoad
            }
        except Exception:
            return {'total_mb': 0, 'available_mb': 0, 'used_mb': 0, 'percent_used': 0}
    
    @staticmethod
    def get_screen_size() -> Tuple[int, int]:
        """Get primary screen resolution."""
        try:
            width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            return (width, height)
        except Exception:
            return (1920, 1080)


# Singleton instances
_win32_api = None
_process_manager = None
_system_info = None


def get_win32_api() -> Win32API:
    """Get global Win32API instance."""
    global _win32_api
    if _win32_api is None:
        _win32_api = Win32API()
    return _win32_api


def get_process_manager() -> ProcessManager:
    """Get global ProcessManager instance."""
    global _process_manager
    if _process_manager is None:
        _process_manager = ProcessManager()
    return _process_manager


def get_system_info() -> SystemInfo:
    """Get global SystemInfo instance."""
    global _system_info
    if _system_info is None:
        _system_info = SystemInfo()
    return _system_info