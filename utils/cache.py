"""
Cache
=====
Sistema de cache en memoria con TTL y políticas de evict.

Proporciona:
- Cache en memoria con Thread-safe
- TTL por entrada
- Políticas LRU/LFU/FIFO
- Cache de funciones (memoization)
- Serialización opcional
"""

from typing import Any, Optional, Callable, Dict, List, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
import threading
import hashlib
import json
import copy
import pickle


class EvictionPolicy(Enum):
    """Política de evicted."""
    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"


@dataclass
class CacheEntry:
    """Entrada individual del cache."""
    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    ttl_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Verificar si la entrada expiró."""
        if self.ttl_seconds is None:
            return False
        age = (datetime.now() - self.created_at).total_seconds()
        return age >= self.ttl_seconds
    
    def touch(self) -> None:
        """Actualizar timestamp de acceso."""
        self.last_accessed = datetime.now()
        self.access_count += 1


class Cache:
    """
    Cache en memoria con TTL y políticas de evict.
    
    Uso:
        cache = Cache(max_size=1000, ttl_seconds=300)
        
        # Set y get
        cache.set('key', 'value')
        value = cache.get('key')
        
        # Con TTL
        cache.set('temp', 'data', ttl_seconds=60)
        
        # Memoization
        @cache.memoize(ttl_seconds=300)
        def expensive_function(x):
            return x * x
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        on_evict: Optional[Callable[[str, Any], None]] = None
    ):
        self._max_size = max_size
        self._default_ttl = default_ttl
        self._eviction_policy = eviction_policy
        self._on_evict = on_evict
        
        self._cache: Dict[str, CacheEntry] = {}
        self._lock = threading.RLock()
        self._hits = 0
        self._misses = 0
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Obtener valor del cache.
        
        Args:
            key: Clave a buscar
            default: Valor por defecto si no existe o expiró
        
        Returns:
            Valor almacenado o default
        """
        with self._lock:
            entry = self._cache.get(key)
            
            if entry is None:
                self._misses += 1
                return default
            
            if entry.is_expired():
                self._evict(key)
                self._misses += 1
                return default
            
            entry.touch()
            return copy.deepcopy(entry.value)
    
    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Guardar valor en el cache.
        
        Args:
            key: Clave
            value: Valor a guardar
            ttl: Time-to-live en segundos (override default)
            metadata: Metadata adicional
        """
        with self._lock:
            if len(self._cache) >= self._max_size and key not in self._cache:
                self._evict_one()
            
            now = datetime.now()
            entry = CacheEntry(
                key=key,
                value=copy.deepcopy(value),
                created_at=now,
                last_accessed=now,
                ttl_seconds=ttl if ttl is not None else self._default_ttl,
                metadata=metadata or {}
            )
            
            self._cache[key] = entry
    
    def delete(self, key: str) -> bool:
        """
        Eliminar entrada del cache.
        
        Returns:
            True si existía y se eliminó
        """
        with self._lock:
            if key in self._cache:
                self._evict(key)
                return True
            return False
    
    def clear(self) -> None:
        """Limpiar todo el cache."""
        with self._lock:
            if self._on_evict:
                for key, entry in self._cache.items():
                    self._on_evict(key, entry.value)
            self._cache.clear()
            self._hits = 0
            self._misses = 0
    
    def has(self, key: str) -> bool:
        """Verificar si clave existe y no expiró."""
        with self._lock:
            entry = self._cache.get(key)
            if entry is None:
                return False
            if entry.is_expired():
                self._evict(key)
                return False
            return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = self._hits / total if total > 0 else 0
            return {
                'size': len(self._cache),
                'max_size': self._max_size,
                'hits': self._hits,
                'misses': self._misses,
                'hit_rate': hit_rate,
                'eviction_policy': self._eviction_policy.value
            }
    
    def cleanup_expired(self) -> int:
        """
        Limpiar entradas expiradas.
        
        Returns:
            Número de entradas eliminadas
        """
        with self._lock:
            expired = [
                key for key, entry in self._cache.items()
                if entry.is_expired()
            ]
            for key in expired:
                self._evict(key)
            return len(expired)
    
    def _evict(self, key: str) -> None:
        """Evict entrada."""
        if key in self._cache:
            entry = self._cache.pop(key)
            if self._on_evict:
                self._on_evict(key, entry.value)
    
    def _evict_one(self) -> None:
        """Evict una entrada según política."""
        if not self._cache:
            return
        
        if self._eviction_policy == EvictionPolicy.LRU:
            victim_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].last_accessed
            )
        elif self._eviction_policy == EvictionPolicy.LFU:
            victim_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].access_count
            )
        elif self._eviction_policy == EvictionPolicy.FIFO:
            victim_key = min(
                self._cache.keys(),
                key=lambda k: self._cache[k].created_at
            )
        else:
            victim_key = next(iter(self._cache))
        
        self._evict(victim_key)
    
    def memoize(
        self,
        ttl: Optional[float] = None,
        key_func: Optional[Callable[..., str]] = None
    ) -> Callable:
        """
        Decorador para memoización de funciones.
        
        Usage:
            @cache.memoize(ttl_seconds=300)
            def expensive_func(a, b):
                return a + b
        """
        def decorator(func: Callable) -> Callable:
            def wrapper(*args, **kwargs) -> Any:
                if key_func:
                    cache_key = key_func(*args, **kwargs)
                else:
                    key_parts = [func.__name__]
                    key_parts.extend(str(arg) for arg in args)
                    key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))
                    cache_key = hashlib.md5(":".join(key_parts).encode()).hexdigest()
                
                cached = self.get(cache_key)
                if cached is not None:
                    return cached
                
                result = func(*args, **kwargs)
                self.set(cache_key, result, ttl=ttl)
                return result
            
            wrapper.cache_info = lambda: self.get_stats()
            wrapper.cache_clear = lambda: self.clear()
            return wrapper
        return decorator


class SerializedCache(Cache):
    """Cache con serialización para valores complejos."""
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        eviction_policy: EvictionPolicy = EvictionPolicy.LRU,
        serializer: str = "pickle"
    ):
        super().__init__(max_size, default_ttl, eviction_policy)
        self._serializer = serializer
    
    def set_serialized(
        self,
        key: str,
        value: Any,
        ttl: Optional[float] = None
    ) -> None:
        """Guardar con serialización."""
        if self._serializer == "pickle":
            serialized = pickle.dumps(value)
        elif self._serializer == "json":
            serialized = json.dumps(value, default=str)
        else:
            serialized = value
        
        self.set(key, serialized, ttl=ttl)
    
    def get_deserialized(self, key: str, default: Any = None) -> Any:
        """Obtener y deserializar."""
        value = self.get(key)
        if value is None:
            return default
        
        try:
            if self._serializer == "pickle":
                return pickle.loads(value)
            elif self._serializer == "json":
                return json.loads(value)
            return value
        except Exception:
            return value
