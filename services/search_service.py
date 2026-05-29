"""
Search Service
=============
Servicio de búsqueda de alto nivel con cache y fallback.

Proporciona:
- Cacheo de búsquedas recientes
- Fallback automático entre proveedores
- Procesamiento de resultados
- Interfaz simple para el agente
"""

import time
import threading
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta

from .search_provider import (
    BaseSearchProvider,
    SearchProviderType,
    SearchResult,
    SearchResponse,
    SearchProviderFactory,
    get_default_provider
)


@dataclass
class CachedSearchResponse:
    """Respuesta en cache."""
    response: SearchResponse
    cached_at: datetime
    expires_at: datetime
    
    @property
    def is_expired(self) -> bool:
        return datetime.now() > self.expires_at


@dataclass
class SearchConfig:
    """Configuración del servicio de búsqueda."""
    cache_ttl_minutes: int = 15
    max_results: int = 10
    preferred_provider: SearchProviderType = SearchProviderType.DUCKDUCKGO
    enable_cache: bool = True
    enable_fallback: bool = True
    timeout_seconds: int = 10


class SearchCache:
    """Cache simple de búsquedas."""
    
    def __init__(self, ttl_minutes: int = 15):
        self._cache: Dict[str, CachedSearchResponse] = {}
        self._lock = threading.RLock()
        self._ttl = timedelta(minutes=ttl_minutes)
    
    def get(self, query: str) -> Optional[SearchResponse]:
        """Obtener respuesta en cache si existe y no ha expirado."""
        key = query.lower().strip()
        
        with self._lock:
            if key not in self._cache:
                return None
            
            cached = self._cache[key]
            
            if cached.is_expired:
                del self._cache[key]
                return None
            
            # Return cached response with cached flag
            response = cached.response
            response.cached = True
            return response
    
    def set(self, query: str, response: SearchResponse) -> None:
        """Guardar respuesta en cache."""
        key = query.lower().strip()
        
        with self._lock:
            self._cache[key] = CachedSearchResponse(
                response=response,
                cached_at=datetime.now(),
                expires_at=datetime.now() + self._ttl
            )
    
    def invalidate(self, query: Optional[str] = None) -> None:
        """Invalidar cache."""
        with self._lock:
            if query is None:
                self._cache.clear()
            else:
                key = query.lower().strip()
                if key in self._cache:
                    del self._cache[key]
    
    def get_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache."""
        with self._lock:
            now = datetime.now()
            expired = sum(1 for c in self._cache.values() if c.is_expired)
            return {
                "total_cached": len(self._cache),
                "expired": expired,
                "active": len(self._cache) - expired
            }


class SearchService:
    """
    Servicio de búsqueda de alto nivel.
    
    Uso:
        service = SearchService()
        
        # Búsqueda simple
        response = service.search("python tutorial")
        
        # Búsqueda con configuración custom
        config = SearchConfig(max_results=20, enable_cache=False)
        response = service.search("machine learning", config=config)
    """
    
    def __init__(
        self,
        provider: Optional[BaseSearchProvider] = None,
        config: Optional[SearchConfig] = None
    ):
        self._provider = provider or get_default_provider()
        self._config = config or SearchConfig()
        self._cache = SearchCache(ttl_minutes=self._config.cache_ttl_minutes)
        self._fallback_providers: List[BaseSearchProvider] = []
        
        # Register DuckDuckGo provider if not already the default
        try:
            from .duckduckgo_provider import DuckDuckGoProvider
        except ImportError:
            pass
    
    def search(
        self,
        query: str,
        config: Optional[SearchConfig] = None
    ) -> SearchResponse:
        """
        Ejecutar búsqueda con cache y fallback.
        
        Args:
            query: Término de búsqueda
            config: Configuración opcional (sobreescribe la default)
            
        Returns:
            SearchResponse con resultados
        """
        cfg = config or self._config
        
        # Check cache first
        if cfg.enable_cache:
            cached = self._cache.get(query)
            if cached:
                return cached
        
        # Execute search
        response = self._execute_with_fallback(query, cfg)
        
        # Cache successful results
        if cfg.enable_cache and response.results and not response.error:
            self._cache.set(query, response)
        
        return response
    
    def _execute_with_fallback(
        self,
        query: str,
        config: SearchConfig
    ) -> SearchResponse:
        """Ejecutar búsqueda con fallback a otros proveedores."""
        # Try primary provider
        response = self._provider.search(query)
        
        if response.results or not config.enable_fallback:
            return self._limit_results(response, config.max_results)
        
        # Try fallback providers
        for fallback in self._fallback_providers:
            if fallback.provider_type == self._provider.provider_type:
                continue
            
            try:
                fallback_response = fallback.search(query)
                if fallback_response.results:
                    result = self._limit_results(fallback_response, config.max_results)
                    # Copy provider info for fallback
                    result.provider = fallback.provider_type
                    return result
            except Exception:
                continue
        
        return self._limit_results(response, config.max_results)
    
    def _limit_results(self, response: SearchResponse, max_results: int) -> SearchResponse:
        """Limitar número de resultados."""
        if len(response.results) <= max_results:
            return response
        
        response.results = response.results[:max_results]
        response.total_results = len(response.results)
        return response
    
    def add_fallback_provider(self, provider: BaseSearchProvider) -> None:
        """Añadir proveedor de fallback."""
        self._fallback_providers.append(provider)
    
    def clear_cache(self) -> None:
        """Limpiar cache."""
        self._cache.invalidate()
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Obtener estadísticas del cache."""
        return self._cache.get_stats()
    
    def search_and_summarize(
        self,
        query: str,
        max_results: int = 5
    ) -> str:
        """
        Búsqueda con resumen de resultados.
        
        Args:
            query: Término de búsqueda
            max_results: Máximo de resultados a incluir
            
        Returns:
            String formateado con resultados resumidos
        """
        response = self.search(query, SearchConfig(max_results=max_results))
        
        if not response.results:
            if response.error:
                return f"Búsqueda falló: {response.error}"
            return f"No encontré resultados para '{query}'"
        
        lines = [f"Resultados para '{query}' ({response.provider.value}):\n"]
        
        for i, result in enumerate(response.results, 1):
            lines.append(f"{i}. {result.title}")
            lines.append(f"   {result.snippet[:150]}..." if len(result.snippet) > 150 else f"   {result.snippet}")
            lines.append(f"   Fuente: {result.url}\n")
        
        return "\n".join(lines)


# Singleton instance
_search_service_instance: Optional[SearchService] = None
_search_service_lock = threading.Lock()


def get_search_service() -> SearchService:
    """Get singleton search service instance."""
    global _search_service_instance
    if _search_service_instance is None:
        with _search_service_lock:
            if _search_service_instance is None:
                _search_service_instance = SearchService()
    return _search_service_instance


def search(query: str, max_results: int = 10) -> SearchResponse:
    """
    Función de conveniencia para búsqueda rápida.
    
    Uso:
        results = search("python tutorial")
    """
    service = get_search_service()
    return service.search(query, SearchConfig(max_results=max_results))
