"""
Logger
======
Sistema de logging estructurado con múltiples outputs y niveles.

Proporciona:
- Logging estructurado en JSON
- Múltiples outputs (file, console, remote)
- Niveles configurables por componente
- Rotación de logs automática
- Context providers para tracking
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import json
import logging
import os
from pathlib import Path


class LogLevel(Enum):
    """Niveles de logging."""
    DEBUG = 10
    INFO = 20
    WARNING = 30
    ERROR = 40
    CRITICAL = 50


class LogFormat(Enum):
    """Formatos de salida."""
    TEXT = "text"
    JSON = "json"
    STRUCTURED = "structured"


@dataclass
class LogEntry:
    """Entrada de log estructurada."""
    timestamp: datetime
    level: LogLevel
    message: str
    component: str
    context: Dict[str, Any]
    extra: Dict[str, Any] = field(default_factory=dict)


class LogHandler:
    """Handler base para diferentes outputs."""
    
    def __init__(self, min_level: LogLevel = LogLevel.INFO):
        self._min_level = min_level
        self._formatter: Optional[Callable[[LogEntry], str]] = None
    
    def set_formatter(self, formatter: Callable[[LogEntry], str]) -> None:
        """Setear formatador custom."""
        self._formatter = formatter
    
    def should_handle(self, level: LogLevel) -> bool:
        """Verificar si el nivel debe ser manejado."""
        return level.value >= self._min_level.value
    
    def emit(self, entry: LogEntry) -> None:
        """Emitir entrada de log (override en subclasses)."""
        raise NotImplementedError


class ConsoleHandler(LogHandler):
    """Handler para consola con colores."""
    
    COLOR_MAP = {
        LogLevel.DEBUG: '\033[36m',
        LogLevel.INFO: '\033[32m',
        LogLevel.WARNING: '\033[33m',
        LogLevel.ERROR: '\033[31m',
        LogLevel.CRITICAL: '\033[35m',
    }
    RESET = '\033[0m'
    
    def __init__(self, min_level: LogLevel = LogLevel.INFO, use_colors: bool = True):
        super().__init__(min_level)
        self._use_colors = use_colors
    
    def emit(self, entry: LogEntry) -> None:
        """Emitir a consola."""
        if self._formatter:
            output = self._formatter(entry)
        else:
            output = self._default_format(entry)
        print(output)
    
    def _default_format(self, entry: LogEntry) -> str:
        """Format por defecto."""
        level_str = entry.level.name[:4].upper()
        timestamp = entry.timestamp.strftime('%H:%M:%S.%f')[:-3]
        
        if self._use_colors:
            color = self.COLOR_MAP.get(entry.level, '')
            reset = self.RESET
            return f"{color}[{timestamp}] {level_str} [{entry.component}]{reset} {entry.message}"
        else:
            return f"[{timestamp}] {level_str} [{entry.component}] {entry.message}"


class FileHandler(LogHandler):
    """Handler para archivo con rotación."""
    
    def __init__(
        self,
        path: str,
        min_level: LogLevel = LogLevel.DEBUG,
        max_bytes: int = 10 * 1024 * 1024,
        backup_count: int = 5
    ):
        super().__init__(min_level)
        self._path = Path(path)
        self._max_bytes = max_bytes
        self._backup_count = backup_count
        self._lock = threading.Lock()
        self._path.parent.mkdir(parents=True, exist_ok=True)
    
    def emit(self, entry: LogEntry) -> None:
        """Emitir a archivo."""
        with self._lock:
            if self._should_rotate():
                self._rotate()
            
            output = self._format_json(entry) if self._formatter is None else self._formatter(entry)
            
            with open(self._path, 'a', encoding='utf-8') as f:
                f.write(output + '\n')
    
    def _should_rotate(self) -> bool:
        """Verificar si debe rotar."""
        if not self._path.exists():
            return False
        return self._path.stat().st_size >= self._max_bytes
    
    def _rotate(self) -> None:
        """Rotar archivos."""
        self._path.unlink(missing_ok=True)
        
        for i in range(self._backup_count - 1, 0, -1):
            src = self._path.with_suffix(f'.{i}')
            dst = self._path.with_suffix(f'.{i + 1}')
            if src.exists():
                src.rename(dst)
    
    def _format_json(self, entry: LogEntry) -> str:
        """Format JSON."""
        return json.dumps({
            'timestamp': entry.timestamp.isoformat(),
            'level': entry.level.name,
            'component': entry.component,
            'message': entry.message,
            'context': entry.context,
            **entry.extra
        }, default=str)


class StructuredLogger:
    """
    Logger estructurado con context y múltiples handlers.
    
    Uso:
        logger = StructuredLogger('my_component')
        
        # Logging básico
        logger.info("User logged in", user_id=123)
        
        # Con context
        logger.with_context(request_id="abc").info("Processing request")
        
        # Child logger
        child = logger.bind(component="sub_component")
    """
    
    _instances: Dict[str, 'StructuredLogger'] = {}
    _global_handlers: List[LogHandler] = []
    _global_lock = threading.Lock()
    
    def __init__(
        self,
        component: str,
        min_level: LogLevel = LogLevel.INFO,
        add_to_global: bool = True
    ):
        self._component = component
        self._min_level = min_level
        self._context: Dict[str, Any] = {}
        self._extra: Dict[str, Any] = {}
        self._handlers: List[LogHandler] = []
        self._lock = threading.Lock()
        
        if add_to_global and not StructuredLogger._instances:
            self._setup_default_handlers()
    
    @classmethod
    def get_logger(cls, component: str) -> 'StructuredLogger':
        """Obtener o crear logger para componente."""
        with cls._global_lock:
            if component not in cls._instances:
                cls._instances[component] = StructuredLogger(component)
            return cls._instances[component]
    
    @classmethod
    def add_global_handler(cls, handler: LogHandler) -> None:
        """Agregar handler global."""
        with cls._global_lock:
            cls._global_handlers.append(handler)
    
    @classmethod
    def clear_handlers(cls) -> None:
        """Limpiar todos los handlers."""
        with cls._global_lock:
            cls._global_handlers.clear()
    
    def set_level(self, level: LogLevel) -> None:
        """Setear nivel mínimo."""
        self._min_level = level
    
    def add_handler(self, handler: LogHandler) -> None:
        """Agregar handler específico."""
        with self._lock:
            self._handlers.append(handler)
    
    def bind(self, **kwargs) -> 'StructuredLogger':
        """Crear logger hijo con bindings adicionales."""
        child = StructuredLogger(
            self._component,
            self._min_level,
            add_to_global=False
        )
        child._context = {**self._context, **kwargs}
        child._extra = dict(self._extra)
        child._handlers = list(self._handlers)
        return child
    
    def with_context(self, **kwargs) -> 'StructuredLogger':
        """Añadir context temporalmente."""
        child = self.bind()
        child._context.update(kwargs)
        return child
    
    def add_extra(self, **kwargs) -> 'StructuredLogger':
        """Añadir extra fields a todos los logs."""
        child = self.bind()
        child._extra.update(kwargs)
        return child
    
    def _log(self, level: LogLevel, message: str, **kwargs) -> None:
        """Loggear mensaje."""
        if level.value < self._min_level.value:
            return
        
        entry = LogEntry(
            timestamp=datetime.now(),
            level=level,
            message=message,
            component=self._component,
            context={**self._context, **kwargs},
            extra=dict(self._extra)
        )
        
        self._emit(entry)
    
    def _emit(self, entry: LogEntry) -> None:
        """Emitir a todos los handlers."""
        handlers = self._handlers if self._handlers else StructuredLogger._global_handlers
        
        for handler in handlers:
            if handler.should_handle(entry.level):
                try:
                    handler.emit(entry)
                except Exception:
                    pass
    
    def debug(self, message: str, **kwargs) -> None:
        self._log(LogLevel.DEBUG, message, **kwargs)
    
    def info(self, message: str, **kwargs) -> None:
        self._log(LogLevel.INFO, message, **kwargs)
    
    def warning(self, message: str, **kwargs) -> None:
        self._log(LogLevel.WARNING, message, **kwargs)
    
    def error(self, message: str, **kwargs) -> None:
        self._log(LogLevel.ERROR, message, **kwargs)
    
    def critical(self, message: str, **kwargs) -> None:
        self._log(LogLevel.CRITICAL, message, **kwargs)
    
    def exception(self, message: str, **kwargs) -> None:
        kwargs['exc_info'] = True
        self._log(LogLevel.ERROR, message, **kwargs)
    
    @classmethod
    def _setup_default_handlers(cls) -> None:
        """Setup handlers por defecto."""
        console = ConsoleHandler(LogLevel.DEBUG)
        cls._global_handlers.append(console)


def get_logger(component: str) -> StructuredLogger:
    """Helper para obtener logger."""
    return StructuredLogger.get_logger(component)
