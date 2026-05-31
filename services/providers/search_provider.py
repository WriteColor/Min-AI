"""
Search Provider Base
==================
Abstracción base para proveedores de búsqueda web.

Proporciona una interfaz común para múltiples motores de búsqueda,
permitiendo switching entre proveedores y fallback automático.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum
import threading


class SearchProviderType(Enum):
    """Tipos de proveedores de búsqueda."""
    BRAVE = "brave"
    GOOGLE = "google"
    DUCKDUCKGO = "duckduckgo"
    FALLBACK = "fallback"


@dataclass
class SearchResult:
    """Resultado individual de búsqueda."""
    title: str
    url: str
    snippet: str
    source: str
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SearchResponse:
    """Respuesta completa de una búsqueda."""
    query: str
    results: List[SearchResult]
    provider: SearchProviderType
    total_results: int
    execution_time_ms: float
    cached: bool = False
    error: Optional[str] = None


class BaseSearchProvider(ABC):
    """
    Clase base abstracta para proveedores de búsqueda.
    
    Uso:
        class DuckDuckGoProvider(BaseSearchProvider):
            def _execute(self, query: str) -> List[SearchResult]:
                # Implementación específica
                ...
        
        provider = DuckDuckGoProvider()
        response = provider.search("python tutorial")
    """
    
    provider_type: SearchProviderType = SearchProviderType.FALLBACK
    requires_api_key: bool = False
    rate_limit_requests_per_minute: int = 30
    
    def __init__(self):
        self._last_request_times: List[float] = []
        self._lock = threading.Lock()
    
    @abstractmethod
    def _execute(self, query: str, **kwargs) -> List[SearchResult]:
        """
        Ejecutar búsqueda específica del proveedor.
        
        Args:
            query: Término de búsqueda
            **kwargs: Parámetros adicionales específicos del proveedor
            
        Returns:
            Lista de SearchResult
        """
        pass
    
    def search(self, query: str, **kwargs) -> SearchResponse:
        """
        Ejecutar búsqueda con validaciones y manejo de errores.
        
        Args:
            query: Término de búsqueda
            **kwargs: Parámetros adicionales
            
        Returns:
            SearchResponse con resultados o error
        """
        import time
        start_time = time.time()
        
        # Validate query
        if not query or not query.strip():
            return SearchResponse(
                query=query,
                results=[],
                provider=self.provider_type,
                total_results=0,
                execution_time_ms=0,
                error="Empty query"
            )
        
        # Rate limiting
        if not self._check_rate_limit():
            return SearchResponse(
                query=query,
                results=[],
                provider=self.provider_type,
                total_results=0,
                execution_time_ms=0,
                error="Rate limit exceeded"
            )
        
        try:
            results = self._execute(query.strip(), **kwargs)
            execution_time = (time.time() - start_time) * 1000
            
            return SearchResponse(
                query=query,
                results=results,
                provider=self.provider_type,
                total_results=len(results),
                execution_time_ms=execution_time,
                cached=False
            )
        except Exception as e:
            return SearchResponse(
                query=query,
                results=[],
                provider=self.provider_type,
                total_results=0,
                execution_time_ms=(time.time() - start_time) * 1000,
                error=str(e)
            )
    
    def _check_rate_limit(self) -> bool:
        """Verificar si se puede hacer otra request."""
        import time
        
        with self._lock:
            now = time.time()
            # Limpiar requests antiguos (más de 1 minuto)
            self._last_request_times = [
                t for t in self._last_request_times
                if now - t < 60
            ]
            
            if len(self._last_request_times) >= self.rate_limit_requests_per_minute:
                return False
            
            self._last_request_times.append(now)
            return True
    
    def _clean_html(self, text: str) -> str:
        """Limpiar HTML básico de texto."""
        import re
        # Remove HTML tags
        text = re.sub(r'<[^>]+>', '', text)
        # Decode HTML entities
        text = text.replace('&amp;', '&').replace('&lt;', '<').replace('&gt;', '>')
        text = text.replace('&quot;', '"').replace('&#39;', "'")
        # Normalize whitespace
        text = re.sub(r'\s+', ' ', text).strip()
        return text


class SearchProviderFactory:
    """Fábrica de proveedores de búsqueda."""
    
    _providers: Dict[SearchProviderType, type] = {}
    _lock = threading.Lock()
    
    @classmethod
    def register(cls, provider_type: SearchProviderType, provider_class: type):
        """Registrar un proveedor."""
        with cls._lock:
            cls._providers[provider_type] = provider_class
    
    @classmethod
    def create(cls, provider_type: SearchProviderType, **kwargs) -> BaseSearchProvider:
        """Crear instancia de proveedor."""
        if provider_type not in cls._providers:
            # Default to DuckDuckGo
            provider_type = SearchProviderType.DUCKDUCKGO
        
        return cls._providers[provider_type](**kwargs)
    
    @classmethod
    def get_available_providers(cls) -> List[SearchProviderType]:
        """Obtener lista de proveedores disponibles."""
        return list(cls._providers.keys())


def get_default_provider() -> BaseSearchProvider:
    """Obtener proveedor de búsqueda por defecto (DuckDuckGo)."""
    return SearchProviderFactory.create(SearchProviderType.DUCKDUCKGO)
