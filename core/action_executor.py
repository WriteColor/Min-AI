"""
Action Executor
==============
Ejecutor de acciones con validación, reintentos y manejo de errores.

Proporciona:
- Ejecución validada de acciones
- Reintentos automáticos configurables
- Timeout por acción
- Manejo de errores robusto
- Tracking de ejecuciones
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import time

from core.action_registry import ActionRegistry, ActionMetadata, ActionResult, ActionPriority


class ExecutionStatus(Enum):
    """Estado de ejecución."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"
    RETRYING = "retrying"


@dataclass
class ExecutionContext:
    """Contexto de una ejecución."""
    action_name: str
    parameters: Dict[str, Any]
    priority: ActionPriority
    retry_count: int = 0
    max_retries: int = 3
    timeout_ms: float = 30000
    status: ExecutionStatus = ExecutionStatus.PENDING
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExecutionPolicy:
    """Política de ejecución para reintentos."""
    max_retries: int = 3
    base_delay_ms: float = 100
    max_delay_ms: float = 5000
    exponential_backoff: bool = True
    retry_on_timeout: bool = True
    retry_on_errors: List[str] = field(default_factory=lambda: ["timeout", "connection", "temporary"])


class ActionExecutor:
    """
    Ejecutor de acciones con validación y reintentos.
    
    Uso:
        executor = ActionExecutor(registry)
        
        # Ejecutar acción
        result = executor.execute('restore_window', {'hwnd': 123})
        
        # Ejecutar con política custom
        policy = ExecutionPolicy(max_retries=5, exponential_backoff=False)
        result = executor.execute('action_name', params, policy=policy)
    """
    
    def __init__(
        self,
        registry: Optional[ActionRegistry] = None,
        default_policy: Optional[ExecutionPolicy] = None
    ):
        self._registry = registry or ActionRegistry()
        self._default_policy = default_policy or ExecutionPolicy()
        self._executors: Dict[str, Callable] = {}
        self._lock = threading.RLock()
        self._execution_history: List[ExecutionContext] = []
        self._max_history: int = 1000
    
    def register_executor(self, action_name: str, executor: Callable) -> None:
        """
        Registrar un ejecutor custom para una acción.
        
        Args:
            action_name: Nombre de la acción
            executor: Función que ejecuta la acción
        """
        with self._lock:
            self._executors[action_name] = executor
    
    def execute(
        self,
        action_name: str,
        parameters: Optional[Dict[str, Any]] = None,
        policy: Optional[ExecutionPolicy] = None,
        context: Optional[ExecutionContext] = None
    ) -> ActionResult:
        """
        Ejecutar una acción con validación y reintentos.
        
        Args:
            action_name: Nombre de la acción a ejecutar
            parameters: Parámetros para la acción
            policy: Política de ejecución (usa default si no se provee)
            context: Contexto de ejecución (para tracking)
        
        Returns:
            ActionResult con el resultado de la ejecución
        """
        start_time = time.perf_counter()
        parameters = parameters or {}
        policy = policy or self._default_policy
        
        if context is None:
            context = ExecutionContext(
                action_name=action_name,
                parameters=parameters,
                priority=ActionPriority.NORMAL
            )
        
        context.status = ExecutionStatus.RUNNING
        context.started_at = datetime.now()
        
        metadata = self._registry.get(action_name)
        if not metadata:
            return self._create_error_result(
                action_name, start_time,
                f"Acción '{action_name}' no encontrada en registry"
            )
        
        validation_result = self._registry.validate_params(action_name, parameters)
        if not validation_result[0]:
            return self._create_error_result(
                action_name, start_time,
                f"Validación falló: {validation_result[1]}"
            )
        
        last_error = None
        for attempt in range(policy.max_retries + 1):
            if attempt > 0:
                context.status = ExecutionStatus.RETRYING
                context.retry_count = attempt
                delay = self._calculate_delay(policy, attempt)
                time.sleep(delay / 1000)
            
            try:
                result = self._execute_action(action_name, parameters, metadata)
                context.status = ExecutionStatus.SUCCESS
                context.completed_at = datetime.now()
                return self._create_success_result(action_name, start_time, result)
                
            except TimeoutError as e:
                last_error = f"Timeout: {e}"
                if not policy.retry_on_timeout or attempt >= policy.max_retries:
                    context.status = ExecutionStatus.TIMEOUT
                    context.error = last_error
                    break
                    
            except Exception as e:
                last_error = str(e)
                error_type = self._classify_error(e)
                if error_type not in policy.retry_on_errors or attempt >= policy.max_retries:
                    context.status = ExecutionStatus.FAILED
                    context.error = last_error
                    break
        
        context.completed_at = datetime.now()
        return self._create_error_result(action_name, start_time, last_error or "Unknown error")
    
    def execute_batch(
        self,
        actions: List[Dict[str, Any]],
        policy: Optional[ExecutionPolicy] = None
    ) -> List[ActionResult]:
        """
        Ejecutar múltiples acciones en secuencia.
        
        Args:
            actions: Lista de dicts con 'action_name' y 'parameters'
            policy: Política de ejecución (aplicada a todas)
        
        Returns:
            Lista de ActionResult en el mismo orden
        """
        results = []
        for action_spec in actions:
            result = self.execute(
                action_spec.get('action_name'),
                action_spec.get('parameters', {}),
                policy
            )
            results.append(result)
            if not result.success and not self._should_continue_batch(result):
                break
        return results
    
    def _execute_action(
        self,
        action_name: str,
        parameters: Dict[str, Any],
        metadata: ActionMetadata
    ) -> Any:
        """Ejecutar la acción real."""
        if action_name in self._executors:
            return self._executors[action_name](**parameters)
        
        handler = self._registry.get_handler(action_name)
        if handler:
            return handler(**parameters)
        
        raise ValueError(f"No executor or handler found for action '{action_name}'")
    
    def _calculate_delay(self, policy: ExecutionPolicy, attempt: int) -> float:
        """Calcular delay para retry con exponential backoff."""
        if policy.exponential_backoff:
            delay = policy.base_delay_ms * (2 ** (attempt - 1))
        else:
            delay = policy.base_delay_ms * attempt
        return min(delay, policy.max_delay_ms)
    
    def _classify_error(self, error: Exception) -> str:
        """Clasificar tipo de error para políticas de retry."""
        error_str = str(error).lower()
        if "timeout" in error_str or "timed out" in error_str:
            return "timeout"
        if "connection" in error_str or "network" in error_str:
            return "connection"
        if "temporary" in error_str or "transient" in error_str:
            return "temporary"
        return "permanent"
    
    def _should_continue_batch(self, result: ActionResult) -> bool:
        """Determinar si continuar ejecución batch."""
        return result.success
    
    def _create_success_result(
        self,
        action_name: str,
        start_time: float,
        result: Any
    ) -> ActionResult:
        """Crear resultado exitoso."""
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ActionResult(
            action_name=action_name,
            success=True,
            result=result,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
    
    def _create_error_result(
        self,
        action_name: str,
        start_time: float,
        error: str
    ) -> ActionResult:
        """Crear resultado de error."""
        execution_time_ms = (time.perf_counter() - start_time) * 1000
        return ActionResult(
            action_name=action_name,
            success=False,
            error=error,
            execution_time_ms=execution_time_ms,
            timestamp=datetime.now()
        )
    
    def get_execution_history(
        self,
        action_name: Optional[str] = None,
        limit: int = 100
    ) -> List[ExecutionContext]:
        """Obtener historial de ejecuciones."""
        with self._lock:
            history = self._execution_history
            if action_name:
                history = [h for h in history if h.action_name == action_name]
            return history[-limit:]
