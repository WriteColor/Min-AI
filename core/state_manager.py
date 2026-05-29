"""
State Manager
=============
Gestor de estado del sistema con snapshots y rollback.

Proporciona:
- Estado global del sistema
- Snapshots para undo/redo
- Tracking de cambios
- Persistencia de estado
"""

from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import threading
import json
import copy


class StateChangeType(Enum):
    """Tipos de cambio de estado."""
    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    BULK = "bulk"


@dataclass
class StateSnapshot:
    """Snapshot del estado en un punto en el tiempo."""
    id: str
    timestamp: datetime
    state: Dict[str, Any]
    description: str
    tags: List[str] = field(default_factory=list)


@dataclass
class StateChange:
    """Registro de un cambio de estado."""
    change_type: StateChangeType
    key: str
    old_value: Any
    new_value: Any
    timestamp: datetime = field(default_factory=datetime.now)


class StateManager:
    """
    Gestor centralizado de estado del sistema.
    
    Uso:
        state = StateManager()
        
        # Setear valor
        state.set('window.title', 'Notepad')
        
        # Obtener valor
        title = state.get('window.title')
        
        # Snapshot para undo
        state.snapshot('before_close')
        
        # Undo
        state.undo()
    """
    
    def __init__(self, persist_path: Optional[str] = None):
        self._state: Dict[str, Any] = {}
        self._snapshots: List[StateSnapshot] = []
        self._change_history: List[StateChange] = []
        self._locks: Dict[str, threading.RLock] = {}
        self._global_lock = threading.RLock()
        self._persist_path = persist_path
        self._max_snapshots = 100
        self._max_history = 500
        self._subscribers: Dict[str, List[Callable]] = {}
        
        if self._persist_path:
            self._load()
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtener valor del estado.
        
        Args:
            key: Path con puntos (ej: 'window.title')
            default: Valor por defecto si no existe
        
        Returns:
            Valor almacenado o default
        """
        with self._get_lock(key):
            keys = key.split('.')
            value = self._state
            
            for k in keys:
                if isinstance(value, dict) and k in value:
                    value = value[k]
                else:
                    return default
            
            return copy.deepcopy(value)
    
    def set(self, key: str, value: Any, tags: Optional[List[str]] = None) -> None:
        """
        Setear valor en el estado.
        
        Args:
            key: Path con puntos (ej: 'window.title')
            value: Valor a guardar
            tags: Tags para el cambio (para tracking)
        """
        with self._get_lock(key):
            old_value = self.get(key)
            
            keys = key.split('.')
            target = self._state
            
            for k in keys[:-1]:
                if k not in target:
                    target[k] = {}
                target = target[k]
            
            target[keys[-1]] = copy.deepcopy(value)
            
            change = StateChange(
                change_type=StateChangeType.UPDATE if old_value is not None else StateChangeType.CREATE,
                key=key,
                old_value=copy.deepcopy(old_value),
                new_value=copy.deepcopy(value)
            )
            self._change_history.append(change)
            
            self._notify_subscribers(key, old_value, value)
            
            if len(self._change_history) > self._max_history:
                self._change_history.pop(0)
            
            if self._persist_path:
                self._save()
    
    def delete(self, key: str) -> bool:
        """
        Eliminar clave del estado.
        
        Returns:
            True si existía y se eliminó
        """
        with self._get_lock(key):
            old_value = self.get(key)
            if old_value is None:
                return False
            
            keys = key.split('.')
            target = self._state
            
            for k in keys[:-1]:
                if k not in target:
                    return False
                target = target[k]
            
            del target[keys[-1]]
            
            self._change_history.append(StateChange(
                change_type=StateChangeType.DELETE,
                key=key,
                old_value=copy.deepcopy(old_value),
                new_value=None
            ))
            
            self._notify_subscribers(key, old_value, None)
            
            if self._persist_path:
                self._save()
            
            return True
    
    def snapshot(self, description: str, tags: Optional[List[str]] = None) -> str:
        """
        Crear snapshot del estado actual.
        
        Args:
            description: Descripción del snapshot
            tags: Tags opcionales
        
        Returns:
            ID del snapshot creado
        """
        with self._global_lock:
            import uuid
            snapshot_id = str(uuid.uuid4())[:8]
            
            snapshot = StateSnapshot(
                id=snapshot_id,
                timestamp=datetime.now(),
                state=copy.deepcopy(self._state),
                description=description,
                tags=tags or []
            )
            
            self._snapshots.append(snapshot)
            
            if len(self._snapshots) > self._max_snapshots:
                self._snapshots.pop(0)
            
            return snapshot_id
    
    def restore(self, snapshot_id: str) -> bool:
        """
        Restaurar estado a un snapshot.
        
        Args:
            snapshot_id: ID del snapshot a restaurar
        
        Returns:
            True si se restauró correctamente
        """
        with self._global_lock:
            snapshot = self._find_snapshot(snapshot_id)
            if not snapshot:
                return False
            
            self._state = copy.deepcopy(snapshot.state)
            
            if self._persist_path:
                self._save()
            
            return True
    
    def undo(self, steps: int = 1) -> bool:
        """
        Deshacer último cambio.
        
        Args:
            steps: Número de cambios a deshacer
        
        Returns:
            True si se pudieron deshacer cambios
        """
        with self._global_lock:
            for _ in range(steps):
                if not self._change_history:
                    return False
                
                change = self._change_history.pop()
                
                if change.change_type == StateChangeType.CREATE:
                    keys = change.key.split('.')
                    target = self._state
                    for k in keys[:-1]:
                        if k not in target:
                            break
                        target = target[k]
                    if keys[-1] in target:
                        del target[keys[-1]]
                
                elif change.change_type == StateChangeType.UPDATE:
                    keys = change.key.split('.')
                    target = self._state
                    for k in keys[:-1]:
                        if k not in target:
                            target[k] = {}
                            break
                        target = target[k]
                    target[keys[-1]] = copy.deepcopy(change.old_value)
                
                elif change.change_type == StateChangeType.DELETE:
                    keys = change.key.split('.')
                    target = self._state
                    for k in keys[:-1]:
                        if k not in target:
                            target[k] = {}
                            break
                        target = target[k]
                    target[keys[-1]] = copy.deepcopy(change.old_value)
            
            if self._persist_path:
                self._save()
            
            return True
    
    def get_snapshots(self) -> List[StateSnapshot]:
        """Obtener lista de snapshots."""
        with self._global_lock:
            return copy.deepcopy(self._snapshots)
    
    def get_change_history(self, key: Optional[str] = None, limit: int = 50) -> List[StateChange]:
        """Obtener historial de cambios."""
        with self._global_lock:
            changes = self._change_history
            if key:
                changes = [c for c in changes if c.key == key]
            return copy.deepcopy(changes[-limit:])
    
    def subscribe(self, key: str, callback: Callable[[str, Any, Any], None]) -> None:
        """
        Suscribirse a cambios de una clave.
        
        Args:
            key: Clave a monitorear (usa * como wildcard)
            callback: Función llamada en cada cambio (key, old_value, new_value)
        """
        with self._global_lock:
            if key not in self._subscribers:
                self._subscribers[key] = []
            self._subscribers[key].append(callback)
    
    def unsubscribe(self, key: str, callback: Callable) -> None:
        """Desuscribirse de cambios."""
        with self._global_lock:
            if key in self._subscribers:
                self._subscribers[key] = [c for c in self._subscribers[key] if c != callback]
    
    def clear(self) -> None:
        """Limpiar todo el estado."""
        with self._global_lock:
            self._state.clear()
            self._change_history.clear()
            
            if self._persist_path:
                self._save()
    
    def _get_lock(self, key: str) -> threading.RLock:
        """Obtener lock para una clave específica."""
        with self._global_lock:
            if key not in self._locks:
                self._locks[key] = threading.RLock()
            return self._locks[key]
    
    def _find_snapshot(self, snapshot_id: str) -> Optional[StateSnapshot]:
        """Buscar snapshot por ID."""
        for s in self._snapshots:
            if s.id == snapshot_id:
                return s
        return None
    
    def _notify_subscribers(self, key: str, old_value: Any, new_value: Any) -> None:
        """Notificar a subscribers de un cambio."""
        with self._global_lock:
            for pattern, callbacks in self._subscribers.items():
                if self._matches_pattern(key, pattern):
                    for callback in callbacks:
                        try:
                            callback(key, old_value, new_value)
                        except Exception:
                            pass
    
    def _matches_pattern(self, key: str, pattern: str) -> bool:
        """Ver si key matchea con patrón (soporta *)."""
        if pattern == "*":
            return True
        if pattern.endswith(".*"):
            prefix = pattern[:-2]
            return key.startswith(prefix)
        return key == pattern
    
    def _save(self) -> None:
        """Guardar estado a disco."""
        try:
            with open(self._persist_path, 'w') as f:
                json.dump({
                    'state': self._state,
                    'snapshots': [
                        {
                            'id': s.id,
                            'timestamp': s.timestamp.isoformat(),
                            'state': s.state,
                            'description': s.description,
                            'tags': s.tags
                        }
                        for s in self._snapshots
                    ]
                }, f, indent=2, default=str)
        except Exception:
            pass
    
    def _load(self) -> None:
        """Cargar estado desde disco."""
        try:
            with open(self._persist_path, 'r') as f:
                data = json.load(f)
                self._state = data.get('state', {})
                self._snapshots = [
                    StateSnapshot(
                        id=s['id'],
                        timestamp=datetime.fromisoformat(s['timestamp']),
                        state=s['state'],
                        description=s['description'],
                        tags=s.get('tags', [])
                    )
                    for s in data.get('snapshots', [])
                ]
        except Exception:
            pass
