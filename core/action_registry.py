"""
Action Registry
==============
Registro centralizado de acciones disponibles del sistema.

Proporciona:
- Catálogo de acciones con metadatos
- Validación de parámetros antes de ejecución
- Documentación de acciones
- Tracking de uso y errores

El registry permite que el sistema sepa qué acciones existen,
qué parámetros aceptan, y cómo validarlas.
"""

from typing import Any, Dict, List, Optional, Callable, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading


class ActionCategory(Enum):
    """Categorías de acciones."""
    WINDOW = "window"  # Control de ventanas
    APPLICATION = "application"  # Control de aplicaciones
    FILE = "file"  # Gestión de archivos
    SYSTEM = "system"  # Control del sistema
    MEDIA = "media"  # Multimedia
    VISION = "vision"  # Visión por computadora
    NETWORK = "network"  # Red e internet
    MEMORY = "memory"  # Memoria
    CONVERSATION = "conversation"  # Conversación
    UTILITY = "utility"  # Utilidades varias


class ActionPriority(Enum):
    """Prioridad de ejecución."""
    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


@dataclass
class ActionParameter:
    """Definición de un parámetro de acción."""
    name: str
    param_type: type
    required: bool
    default: Any = None
    description: str = ""
    allowed_values: Optional[List[Any]] = None


@dataclass
class ActionMetadata:
    """Metadatos de una acción."""
    name: str
    description: str
    category: ActionCategory
    priority: ActionPriority
    parameters: List[ActionParameter]
    examples: List[str] = field(default_factory=list)
    requires_verification: bool = False
    can_undo: bool = False
    undo_action: Optional[str] = None
    deprecated: bool = False
    deprecation_message: Optional[str] = None
    version: str = "1.0"
    tags: List[str] = field(default_factory=list)


@dataclass
class ActionResult:
    """Resultado de una ejecución de acción."""
    action_name: str
    success: bool
    result: Any = None
    error: Optional[str] = None
    verified: bool = False
    execution_time_ms: float = 0
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ActionUsageStats:
    """Estadísticas de uso de una acción."""
    action_name: str
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    total_execution_time_ms: float = 0
    last_called: Optional[datetime] = None
    last_success: Optional[datetime] = None
    last_failure: Optional[datetime] = None
    
    @property
    def success_rate(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.successful_calls / self.total_calls
    
    @property
    def avg_execution_time_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_execution_time_ms / self.total_calls


class ActionRegistry:
    """
    Registro central de acciones.
    
    Uso:
        registry = ActionRegistry()
        
        # Registrar acción
        registry.register(ActionMetadata(...))
        
        # Listar acciones
        actions = registry.list_actions(category=ActionCategory.WINDOW)
        
        # Obtener acción
        action = registry.get('restore_window')
        
        # Validar parámetros
        result = registry.validate_params('restore_window', {'hwnd': 123})
    """
    
    def __init__(self):
        self._actions: Dict[str, ActionMetadata] = {}
        self._handlers: Dict[str, Callable] = {}
        self._stats: Dict[str, ActionUsageStats] = {}
        self._lock = threading.RLock()
    
    def register(
        self,
        metadata: ActionMetadata,
        handler: Optional[Callable] = None
    ) -> None:
        """
        Registrar una acción.
        
        Args:
            metadata: Metadatos de la acción
            handler: Función que ejecuta la acción (opcional)
        """
        with self._lock:
            self._actions[metadata.name] = metadata
            if handler:
                self._handlers[metadata.name] = handler
            if metadata.name not in self._stats:
                self._stats[metadata.name] = ActionUsageStats(action_name=metadata.name)
    
    def register_handler(self, action_name: str, handler: Callable) -> None:
        """Registrar solo el handler de una acción existente."""
        with self._lock:
            if action_name in self._actions:
                self._handlers[action_name] = handler
    
    def get(self, action_name: str) -> Optional[ActionMetadata]:
        """Obtener metadatos de una acción."""
        return self._actions.get(action_name)
    
    def get_handler(self, action_name: str) -> Optional[Callable]:
        """Obtener handler de una acción."""
        return self._handlers.get(action_name)
    
    def list_actions(
        self,
        category: Optional[ActionCategory] = None,
        include_deprecated: bool = False
    ) -> List[ActionMetadata]:
        """Listar acciones, opcionalmente filtradas por categoría."""
        with self._lock:
            actions = list(self._actions.values())
            
            if category:
                actions = [a for a in actions if a.category == category]
            
            if not include_deprecated:
                actions = [a for a in actions if not a.deprecated]
            
            return actions
    
    def list_action_names(
        self,
        category: Optional[ActionCategory] = None,
        include_deprecated: bool = False
    ) -> List[str]:
        """Listar nombres de acciones."""
        return [a.name for a in self.list_actions(category, include_deprecated)]
    
    def validate_params(
        self,
        action_name: str,
        params: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validar parámetros contra el esquema de la acción.
        
        Returns:
            (is_valid, error_messages)
        """
        action = self.get(action_name)
        if not action:
            return False, [f"Unknown action: {action_name}"]
        
        errors = []
        
        for param_def in action.parameters:
            value = params.get(param_def.name)
            
            # Required check
            if param_def.required and value is None:
                errors.append(f"Missing required parameter: {param_def.name}")
                continue
            
            if value is None:
                continue
            
            # Type check
            if not isinstance(value, param_def.param_type):
                errors.append(
                    f"Invalid type for {param_def.name}: "
                    f"expected {param_def.param_type.__name__}, got {type(value).__name__}"
                )
                continue
            
            # Allowed values check
            if param_def.allowed_values and value not in param_def.allowed_values:
                errors.append(
                    f"Invalid value for {param_def.name}: "
                    f"'{value}' not in allowed values: {param_def.allowed_values}"
                )
        
        return len(errors) == 0, errors
    
    def update_stats(self, result: ActionResult) -> None:
        """Actualizar estadísticas después de una ejecución."""
        with self._lock:
            if result.action_name not in self._stats:
                self._stats[result.action_name] = ActionUsageStats(action_name=result.action_name)
            
            stats = self._stats[result.action_name]
            stats.total_calls += 1
            stats.total_execution_time_ms += result.execution_time_ms
            stats.last_called = result.timestamp
            
            if result.success:
                stats.successful_calls += 1
                stats.last_success = result.timestamp
            else:
                stats.failed_calls += 1
                stats.last_failure = result.timestamp
    
    def get_stats(self, action_name: str) -> Optional[ActionUsageStats]:
        """Obtener estadísticas de una acción."""
        return self._stats.get(action_name)
    
    def get_all_stats(self) -> Dict[str, ActionUsageStats]:
        """Obtener todas las estadísticas."""
        return dict(self._stats)
    
    def search(self, query: str) -> List[ActionMetadata]:
        """Buscar acciones por nombre o descripción."""
        query_lower = query.lower()
        results = []
        
        for action in self._actions.values():
            if action.deprecated:
                continue
            
            if query_lower in action.name.lower():
                results.append(action)
                continue
            
            if query_lower in action.description.lower():
                results.append(action)
                continue
            
            for tag in action.tags:
                if query_lower in tag.lower():
                    results.append(action)
                    break
        
        return results
    
    def get_categories(self) -> List[ActionCategory]:
        """Obtener lista de categorías con acciones."""
        categories = set()
        for action in self._actions.values():
            if not action.deprecated:
                categories.add(action.category)
        return list(categories)
    
    def get_total_count(self, include_deprecated: bool = False) -> int:
        """Obtener conteo total de acciones."""
        if include_deprecated:
            return len(self._actions)
        return len([a for a in self._actions.values() if not a.deprecated])


# Pre-built action definitions for common system actions
BUILTIN_ACTIONS = [
    ActionMetadata(
        name="restore_window",
        description="Restore a minimized window to its previous state",
        category=ActionCategory.WINDOW,
        priority=ActionPriority.NORMAL,
        requires_verification=True,
        can_undo=True,
        undo_action="minimize_window",
        parameters=[
            ActionParameter("hwnd", int, True, description="Window handle (HWND)"),
            ActionParameter("verify", bool, False, True, "Verify action succeeded"),
            ActionParameter("log_action", bool, False, False, "Log with screenshots")
        ],
        tags=["window", "restore", "minimized", "unminimize"]
    ),
    ActionMetadata(
        name="minimize_window",
        description="Minimize a window to the taskbar",
        category=ActionCategory.WINDOW,
        priority=ActionPriority.NORMAL,
        requires_verification=True,
        can_undo=True,
        undo_action="restore_window",
        parameters=[
            ActionParameter("hwnd", int, True, description="Window handle (HWND)"),
            ActionParameter("verify", bool, False, True),
            ActionParameter("log_action", bool, False, False)
        ],
        tags=["window", "minimize", "hide", "taskbar"]
    ),
    ActionMetadata(
        name="maximize_window",
        description="Maximize a window to fill the screen",
        category=ActionCategory.WINDOW,
        priority=ActionPriority.NORMAL,
        requires_verification=True,
        can_undo=True,
        undo_action="restore_window",
        parameters=[
            ActionParameter("hwnd", int, True),
            ActionParameter("verify", bool, False, True),
            ActionParameter("log_action", bool, False, False)
        ],
        tags=["window", "maximize", "fullscreen", "expand"]
    ),
    ActionMetadata(
        name="close_window",
        description="Close a window gracefully",
        category=ActionCategory.WINDOW,
        priority=ActionPriority.HIGH,
        requires_verification=True,
        parameters=[
            ActionParameter("hwnd", int, True),
            ActionParameter("verify", bool, False, True),
            ActionParameter("log_action", bool, False, False)
        ],
        tags=["window", "close", "quit", "exit"]
    ),
    ActionMetadata(
        name="open_app",
        description="Open an application by name",
        category=ActionCategory.APPLICATION,
        priority=ActionPriority.NORMAL,
        requires_verification=True,
        parameters=[
            ActionParameter("app_name", str, True, description="Application name"),
            ActionParameter("check_running", bool, False, True, "Check if already running"),
            ActionParameter("focus", bool, False, True, "Focus if already running")
        ],
        examples=["Open Chrome", "Abrir Spotify", "Launch Notepad"],
        tags=["app", "open", "launch", "start"]
    ),
    ActionMetadata(
        name="close_app",
        description="Close an application by name or window",
        category=ActionCategory.APPLICATION,
        priority=ActionPriority.HIGH,
        requires_verification=True,
        parameters=[
            ActionParameter("app_name", str, True),
            ActionParameter("force", bool, False, False, "Force close without saving")
        ],
        tags=["app", "close", "quit", "exit", "kill"]
    ),
    ActionMetadata(
        name="generate_image",
        description="Generate an image from a text prompt using AI",
        category=ActionCategory.MEDIA,
        priority=ActionPriority.NORMAL,
        parameters=[
            ActionParameter("prompt", str, True, description="Image description"),
            ActionParameter("style", str, False, None, "Style preset"),
            ActionParameter("width", int, False, 1024),
            ActionParameter("height", int, False, 1024)
        ],
        examples=["Generate a cyberpunk cityscape", "Crear imagen de un gato"],
        tags=["image", "generate", "create", "AI", "art"]
    ),
    ActionMetadata(
        name="take_screenshot",
        description="Take a screenshot of the screen or a region",
        category=ActionCategory.VISION,
        priority=ActionPriority.LOW,
        parameters=[
            ActionParameter("monitor", int, False, 1, "Monitor number (1 = primary)"),
            ActionParameter("save", bool, False, True, "Save to disk")
        ],
        tags=["screenshot", "capture", "screen", "image"]
    ),
    ActionMetadata(
        name="set_volume",
        description="Set the system master volume",
        category=ActionCategory.MEDIA,
        priority=ActionPriority.NORMAL,
        parameters=[
            ActionParameter("level", int, True, description="Volume level 0-100"),
            ActionParameter("device", str, False, "master", "Audio device")
        ],
        tags=["volume", "audio", "sound", "mute", "unmute"]
    )
]


# Singleton instance
_registry_instance: Optional[ActionRegistry] = None
_registry_lock = threading.Lock()


def get_registry() -> ActionRegistry:
    """Get singleton action registry with built-in actions registered."""
    global _registry_instance
    if _registry_instance is None:
        with _registry_lock:
            if _registry_instance is None:
                _registry_instance = ActionRegistry()
                # Register built-in actions
                for action_meta in BUILTIN_ACTIONS:
                    _registry_instance.register(action_meta)
    return _registry_instance
