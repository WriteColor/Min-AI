"""
UI Action Logger Service
=======================
Logs all UI actions with screenshots for verification and auditing.

Each logged action includes:
- Timestamp
- Action type and parameters
- Before/after screenshots (optional)
- Success/failure status
- Error details if failed
"""

import os
import json
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass, asdict
import threading


@dataclass
class UIActionLog:
    """Represents a single UI action log entry."""
    id: str
    timestamp: str
    action_type: str
    parameters: Dict[str, Any]
    success: bool
    verified: bool
    error: Optional[str]
    screenshot_before: Optional[str]  # Path to before screenshot
    screenshot_after: Optional[str]   # Path to after screenshot
    duration_ms: float
    target_window: Optional[str]
    target_element: Optional[str]


class UIActionLogger:
    """
    Logger for UI actions with screenshot capture and verification.
    
    Usage:
        logger = UIActionLogger()
        
        # Before action
        logger.start_action("click", target_element="button_ok")
        
        # Execute action...
        
        # After action
        logger.end_action(success=True, verified=True)
    """
    
    LOG_DIR = Path("logs/ui_actions")
    SCREENSHOT_DIR = Path("logs/ui_actions/screenshots")
    MAX_LOG_SIZE = 1000  # Rotate after this many entries
    
    def __init__(self):
        self.LOG_DIR.mkdir(parents=True, exist_ok=True)
        self.SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)
        
        self._current_action: Optional[UIActionLog] = None
        self._screenshot_counter = 0
        self._lock = threading.Lock()
        
        self._log_file = self.LOG_DIR / f"ui_actions_{datetime.now().strftime('%Y%m%d')}.jsonl"
    
    def _generate_id(self) -> str:
        """Generate unique ID for action."""
        return f"ui_{datetime.now().strftime('%H%M%S')}_{uuid.uuid4().hex[:6]}"
    
    def _capture_screenshot(self, label: str) -> Optional[str]:
        """
        Capture screenshot and save to file.
        Returns the path to the saved screenshot.
        """
        try:
            from services.system.windows_api import WindowsService
            ws = WindowsService()
            
            timestamp = datetime.now().strftime('%H%M%S')
            self._screenshot_counter += 1
            filename = f"{self._current_action.id}_{label}_{timestamp}_{self._screenshot_counter}.png"
            filepath = self.SCREENSHOT_DIR / filename
            
            screenshot_bytes = ws.capture_screen(monitor=0, path=str(filepath))
            
            if screenshot_bytes and filepath.exists():
                return str(filepath)
            return None
        except Exception as e:
            print(f"[UIActionLogger] Screenshot capture failed: {e}")
            return None
    
    def start_action(
        self,
        action_type: str,
        parameters: Optional[Dict[str, Any]] = None,
        target_window: Optional[str] = None,
        target_element: Optional[str] = None,
        capture_before: bool = True
    ) -> str:
        """
        Start logging a UI action.
        
        Args:
            action_type: Type of action (click, type, scroll, etc.)
            parameters: Action parameters
            target_window: Target window name/HWND
            target_element: Target UI element description
            capture_before: Whether to capture before screenshot
            
        Returns:
            Action ID for correlation with end_action
        """
        with self._lock:
            action_id = self._generate_id()
            
            screenshot_before = None
            if capture_before and self._current_action is None:
                # Only capture if no action in progress
                pass
            
            self._current_action = UIActionLog(
                id=action_id,
                timestamp=datetime.now().isoformat(),
                action_type=action_type,
                parameters=parameters or {},
                success=False,  # Will be updated
                verified=False,  # Will be updated
                error=None,
                screenshot_before=None,  # Capture if needed
                screenshot_after=None,
                duration_ms=0,
                target_window=target_window,
                target_element=target_element
            )
            
            return action_id
    
    def capture_before_shot(self, action_id: str) -> Optional[str]:
        """Capture before screenshot for an action."""
        with self._lock:
            if self._current_action and self._current_action.id == action_id:
                self._current_action.screenshot_before = self._capture_screenshot("before")
                return self._current_action.screenshot_before
        return None
    
    def capture_after_shot(self, action_id: str) -> Optional[str]:
        """Capture after screenshot for an action."""
        with self._lock:
            if self._current_action and self._current_action.id == action_id:
                self._current_action.screenshot_after = self._capture_screenshot("after")
                return self._current_action.screenshot_after
        return None
    
    def end_action(
        self,
        action_id: str,
        success: bool,
        verified: bool = False,
        error: Optional[str] = None,
        duration_ms: float = 0,
        capture_after: bool = True
    ) -> Optional[UIActionLog]:
        """
        End logging a UI action.
        
        Args:
            action_id: ID returned by start_action
            success: Whether action executed successfully
            verified: Whether result was verified
            error: Error message if failed
            duration_ms: Action duration in milliseconds
            capture_after: Whether to capture after screenshot
            
        Returns:
            The completed UIActionLog entry, or None if ID mismatch
        """
        with self._lock:
            if not self._current_action or self._current_action.id != action_id:
                print(f"[UIActionLogger] Action ID mismatch: {action_id}")
                return None
            
            action = self._current_action
            action.success = success
            action.verified = verified
            action.error = error
            action.duration_ms = duration_ms
            
            if capture_after:
                action.screenshot_after = self._capture_screenshot("after")
            
            # Write to log file
            self._write_log(action)
            
            # Clear current action
            self._current_action = None
            
            return action
    
    def _write_log(self, action: UIActionLog) -> None:
        """Write action log entry to file."""
        try:
            with open(self._log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(asdict(action), ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"[UIActionLogger] Failed to write log: {e}")
    
    def log_action_direct(
        self,
        action_type: str,
        success: bool,
        verified: bool = False,
        parameters: Optional[Dict[str, Any]] = None,
        target_window: Optional[str] = None,
        target_element: Optional[str] = None,
        error: Optional[str] = None,
        screenshot_before: Optional[str] = None,
        screenshot_after: Optional[str] = None,
        duration_ms: float = 0
    ) -> UIActionLog:
        """
        Log an action directly without start/end pattern.
        
        Useful for simple fire-and-forget logging.
        """
        action = UIActionLog(
            id=self._generate_id(),
            timestamp=datetime.now().isoformat(),
            action_type=action_type,
            parameters=parameters or {},
            success=success,
            verified=verified,
            error=error,
            screenshot_before=screenshot_before,
            screenshot_after=screenshot_after,
            duration_ms=duration_ms,
            target_window=target_window,
            target_element=target_element
        )
        
        self._write_log(action)
        return action
    
    def get_recent_logs(self, count: int = 10) -> list:
        """Get most recent log entries."""
        if not self._log_file.exists():
            return []
        
        try:
            with open(self._log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
            
            entries = []
            for line in lines[-count:]:
                try:
                    entries.append(json.loads(line.strip()))
                except json.JSONDecodeError:
                    continue
            
            return entries
        except Exception as e:
            print(f"[UIActionLogger] Failed to read logs: {e}")
            return []
    
    def verify_action_by_screenshots(
        self,
        screenshot_before: str,
        screenshot_after: str,
        expected_change: str
    ) -> Tuple[bool, str]:
        """
        Verify an action by comparing before/after screenshots.
        
        This is a basic implementation. For more sophisticated verification,
        integrate with vision analysis.
        
        Args:
            screenshot_before: Path to before screenshot
            screenshot_after: Path to after screenshot
            expected_change: Description of expected change
            
        Returns:
            (success, reason) tuple
        """
        try:
            from PIL import Image
            import hashlib
            
            def get_image_hash(path: str) -> Optional[str]:
                if not os.path.exists(path):
                    return None
                img = Image.open(path)
                # Resize for faster comparison
                img = img.resize((100, 100))
                return hashlib.md5(img.tobytes()).hexdigest()
            
            hash_before = get_image_hash(screenshot_before)
            hash_after = get_image_hash(screenshot_after)
            
            if hash_before is None:
                return False, "Before screenshot not found"
            if hash_after is None:
                return False, "After screenshot not found"
            
            if hash_before == hash_after:
                return False, f"No visible change detected (expected: {expected_change})"
            
            return True, "Change detected"
            
        except Exception as e:
            return False, f"Verification failed: {e}"


# Singleton instance
_logger_instance: Optional[UIActionLogger] = None
_instance_lock = threading.Lock()


def get_logger() -> UIActionLogger:
    """Get singleton logger instance."""
    global _logger_instance
    if _logger_instance is None:
        with _instance_lock:
            if _logger_instance is None:
                _logger_instance = UIActionLogger()
    return _logger_instance
