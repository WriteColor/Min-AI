"""
providers/registry.py — Provider Registry and Factory
======================================================
Central registry for all AI providers with factory pattern for instantiation.
Manages provider lifecycle, configuration validation, and capabilities.
"""

import asyncio
import threading
from typing import Dict, Optional, List, Type, Any

from .base import (
    BaseProvider, ProviderConfig, ProviderCapability,
    UnifiedProvider, get_provider_class, list_registered_providers,
    register_provider
)


class ProviderRegistry:
    """
    Singleton registry for managing all AI providers.
    Provides factory methods for provider instantiation and lifecycle management.
    """
    
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._providers: Dict[str, UnifiedProvider] = {}
        self._configs: Dict[str, ProviderConfig] = {}
        self._provider_classes: Dict[str, Type[BaseProvider]] = {}
        self._active_provider_name: Optional[str] = None
        self._initialized = True
    
    def register(self, name: str, provider_class: Type[BaseProvider], config: ProviderConfig):
        """
        Register a provider class with its configuration.
        
        Args:
            name: Unique provider identifier
            provider_class: Class inheriting from BaseProvider
            config: ProviderConfig instance with API keys and settings
        """
        self._configs[name] = config
        self._provider_classes[name] = provider_class
    
    def create_provider(self, name: str) -> Optional[UnifiedProvider]:
        """
        Create a provider instance by name.
        
        Args:
            name: Provider identifier (e.g., 'openai', 'gemini', 'claude')
            
        Returns:
            UnifiedProvider instance or None if not found/config invalid
        """
        if name not in self._configs:
            return None
        
        config = self._configs[name]
        provider_class = self._provider_classes.get(name)
        
        if not provider_class:
            return None
        
        try:
            provider = provider_class(config)
            unified = UnifiedProvider(provider)
            self._providers[name] = unified
            return unified
        except Exception as e:
            print(f"[Registry] Failed to create provider '{name}': {e}")
            return None
    
    async def initialize_provider(self, name: str) -> bool:
        """
        Initialize a registered provider asynchronously.
        
        Args:
            name: Provider identifier
            
        Returns:
            True if initialization successful
        """
        provider = self.get_provider(name)
        if not provider:
            return False
        
        return await provider.initialize()
    
    def get_provider(self, name: str) -> Optional[UnifiedProvider]:
        """Get an active provider instance by name."""
        return self._providers.get(name)
    
    def get_active_provider(self) -> Optional[UnifiedProvider]:
        """Get the currently active provider."""
        if self._active_provider_name:
            return self._providers.get(self._active_provider_name)
        return None
    
    def set_active_provider(self, name: str) -> bool:
        """
        Set the active provider for chat operations.
        
        Args:
            name: Provider identifier
            
        Returns:
            True if successful
        """
        if name in self._providers:
            self._active_provider_name = name
            return True
        return False
    
    def list_providers(self) -> List[str]:
        """List all registered provider names."""
        return list(self._configs.keys())
    
    def list_active_providers(self) -> List[str]:
        """List all initialized provider names."""
        return list(self._providers.keys())
    
    async def shutdown_all(self):
        """Gracefully shutdown all active providers."""
        for provider in self._providers.values():
            try:
                await provider.shutdown()
            except Exception as e:
                print(f"[Registry] Error shutting down provider: {e}")
        
        self._providers.clear()
        self._active_provider_name = None
    
    def get_provider_config(self, name: str) -> Optional[ProviderConfig]:
        """Get configuration for a provider."""
        return self._configs.get(name)
    
    def validate_configs(self) -> Dict[str, List[str]]:
        """
        Validate all registered provider configurations.
        
        Returns:
            Dict mapping provider names to list of validation errors
        """
        results = {}
        for name, config in self._configs.items():
            provider_class = self._provider_classes.get(name)
            if provider_class:
                provider = provider_class(config)
                results[name] = provider.validate_config()
            else:
                results[name] = ["Provider class not found"]
        return results


class ProviderManager:
    """
    High-level manager for provider operations.
    Provides a simple interface for common provider tasks.
    """
    
    def __init__(self):
        self.registry = ProviderRegistry()
        self._event_callbacks: Dict[str, List[callable]] = {}
    
    async def add_provider(
        self,
        name: str,
        provider_class: Type[BaseProvider],
        config: ProviderConfig,
        auto_initialize: bool = True
    ) -> bool:
        """
        Add and optionally initialize a new provider.
        
        Args:
            name: Unique provider identifier
            provider_class: BaseProvider subclass
            config: Provider configuration
            auto_initialize: Whether to initialize immediately
            
        Returns:
            True if successful
        """
        self.registry.register(name, provider_class, config)
        
        if auto_initialize:
            provider = self.registry.create_provider(name)
            if provider:
                return await self.registry.initialize_provider(name)
        
        return True
    
    async def remove_provider(self, name: str):
        """Remove a provider from the registry."""
        provider = self.registry.get_provider(name)
        if provider:
            await provider.shutdown()
        
        if name in self.registry._configs:
            del self.registry._configs[name]
        
        if self.registry._active_provider_name == name:
            self.registry._active_provider_name = None
    
    async def switch_provider(self, name: str) -> bool:
        """
        Switch to a different provider.
        
        Args:
            name: Provider identifier
            
        Returns:
            True if switch successful
        """
        if name not in self.registry._providers:
            provider = self.registry.create_provider(name)
            if not provider:
                return False
            if not await self.registry.initialize_provider(name):
                return False
        
        return self.registry.set_active_provider(name)
    
    def on_provider_event(self, event: str, callback: callable):
        """Register event callback."""
        if event not in self._event_callbacks:
            self._event_callbacks[event] = []
        self._event_callbacks[event].append(callback)
    
    async def _emit_event(self, event: str, data: Any):
        """Emit event to callbacks."""
        for callback in self._event_callbacks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                print(f"[ProviderManager] Event callback error: {e}")


_provider_manager_instance = None


def get_provider_manager() -> ProviderManager:
    """Get the global provider manager instance (singleton)."""
    global _provider_manager_instance
    if _provider_manager_instance is None:
        _provider_manager_instance = ProviderManager()
    return _provider_manager_instance


def get_registry() -> ProviderRegistry:
    """Get the global provider registry instance."""
    return ProviderRegistry()