"""
providers/__init__.py — Provider Module Exports
================================================
Exports all provider classes, base abstractions, and utilities.
"""

from .base import (
    BaseProvider,
    ProviderConfig,
    ModelInfo,
    ProviderCapability,
    MultimodalProvider,
    LocalProvider,
    UnifiedProvider,
    register_provider,
    get_provider_class,
    list_registered_providers,
)

from .registry import (
    ProviderRegistry,
    ProviderManager,
    get_provider_manager,
    get_registry,
)

from .openai_provider import OpenAIProvider
from .gemini_provider import GeminiProvider
from .groq_provider import GroqProvider
from .local_provider import LocalProvider
from .openrouter_provider import OpenRouterProvider
from .opencode_provider import OpenCodeProvider
from .minimax_provider import MiniMaxProvider


__all__ = [
    # Base classes
    "BaseProvider",
    "ProviderConfig",
    "ModelInfo",
    "ProviderCapability",
    "MultimodalProvider",
    "LocalProvider",
    "UnifiedProvider",
    
    # Registry
    "ProviderRegistry",
    "ProviderManager",
    "get_provider_manager",
    "get_registry",
    
    # Provider implementations
    "OpenAIProvider",
    "GeminiProvider",
    "GroqProvider",
    "LocalProvider",
    "OpenRouterProvider",
    "OpenCodeProvider",
    "MiniMaxProvider",
    
    # Utilities
    "register_provider",
    "get_provider_class",
    "list_registered_providers",
]