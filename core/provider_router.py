"""
core/provider_router.py — Intelligent Provider and Model Router
==============================================================
Routes requests to the appropriate provider/model based on task type.
Implements dynamic switching, fallback chains, and capability matching.

Author: MIN AI Team
Version: 1.0
"""

import asyncio
from typing import Dict, Optional, List, Any, Callable
from dataclasses import dataclass
from enum import Enum

from providers.base import BaseProvider, ProviderCapability, UnifiedProvider
from providers.registry import get_registry, ProviderRegistry
from core.config_manager import get_config_manager


class TaskType(Enum):
    GENERAL_REASONING = "general_reasoning"
    VISION = "vision"
    VOICE_REALTIME = "voice_realtime"
    FAST_RESPONSE = "fast_response"
    CODE_GENERATION = "code_generation"
    IMAGE_GENERATION = "image_generation"
    LONG_CONTEXT = "long_context"
    CREATIVE = "creative"
    ANALYTICAL = "analytical"


@dataclass
class ProviderRoute:
    provider_name: str
    model_name: str
    capabilities: List[ProviderCapability]
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None


class ProviderRouter:
    """
    Intelligent routing of requests to appropriate providers.
    Selects optimal provider/model based on task requirements
    and system configuration.
    """
    
    def __init__(self):
        self.registry = get_registry()
        self.config = get_config_manager()
        self._active_routes: Dict[TaskType, ProviderRoute] = {}
        self._initialize_default_routes()
    
    def _initialize_default_routes(self):
        """Initialize default routing configuration with free/open model preference."""
        self._default_routes = {
            TaskType.GENERAL_REASONING: ProviderRoute(
                provider_name="gemini",
                model_name="gemini-2.5-flash",
                capabilities=[ProviderCapability.TEXT, ProviderCapability.VISION, ProviderCapability.TOOL_CALL],
                fallback_provider="openrouter",
                fallback_model="google/gemini-2.5-flash:free"
            ),
            TaskType.VISION: ProviderRoute(
                provider_name="gemini",
                model_name="gemini-2.5-flash",
                capabilities=[ProviderCapability.VISION, ProviderCapability.TEXT],
                fallback_provider="openrouter",
                fallback_model="openai/gpt-4o-mini"
            ),
            TaskType.VOICE_REALTIME: ProviderRoute(
                provider_name="gemini",
                model_name="gemini-2.5-flash",
                capabilities=[ProviderCapability.AUDIO_INPUT, ProviderCapability.AUDIO_OUTPUT, ProviderCapability.TEXT],
                fallback_provider="gemini",
                fallback_model="gemini-1.5-flash"
            ),
            TaskType.FAST_RESPONSE: ProviderRoute(
                provider_name="groq",
                model_name="llama-3.1-8b-instant",
                capabilities=[ProviderCapability.TEXT],
                fallback_provider="gemini",
                fallback_model="gemini-2.5-flash"
            ),
            TaskType.CODE_GENERATION: ProviderRoute(
                provider_name="openrouter",
                model_name="google/gemini-2.5-flash:free",
                capabilities=[ProviderCapability.TEXT, ProviderCapability.TOOL_CALL],
                fallback_provider="gemini",
                fallback_model="gemini-2.5-flash"
            ),
            TaskType.IMAGE_GENERATION: ProviderRoute(
                provider_name="pollinations",
                model_name="imagegeneration",
                capabilities=[],
                fallback_provider=None,
                fallback_model=None
            ),
            TaskType.LONG_CONTEXT: ProviderRoute(
                provider_name="gemini",
                model_name="gemini-2.5-flash",
                capabilities=[ProviderCapability.TEXT],
                fallback_provider="openrouter",
                fallback_model="google/gemini-2.5-flash:free"
            ),
            TaskType.CREATIVE: ProviderRoute(
                provider_name="gemini",
                model_name="gemini-2.5-flash",
                capabilities=[ProviderCapability.TEXT, ProviderCapability.VISION],
                fallback_provider="openrouter",
                fallback_model="openai/gpt-4o-mini"
            ),
            TaskType.ANALYTICAL: ProviderRoute(
                provider_name="gemini",
                model_name="gemini-2.5-flash",
                capabilities=[ProviderCapability.TEXT, ProviderCapability.REASONING],
                fallback_provider="openrouter",
                fallback_model="google/gemini-2.5-flash:free"
            ),
        }
    
    def get_route_for_task(self, task_type: TaskType) -> ProviderRoute:
        """
        Get the configured route for a task type.
        
        Args:
            task_type: Type of task to route
            
        Returns:
            ProviderRoute with provider/model info
        """
        # Check config for custom assignment first
        config_assignment = self.config.get_model_for_task(task_type.value)
        
        if config_assignment:
            return ProviderRoute(
                provider_name=config_assignment['provider'],
                model_name=config_assignment['model'],
                capabilities=[]  # Will be populated by provider
            )
        
        return self._default_routes.get(task_type, self._default_routes[TaskType.GENERAL_REASONING])
    
    async def route_request(
        self,
        task_type: TaskType,
        request_data: Dict[str, Any]
    ) -> Optional[UnifiedProvider]:
        """
        Route a request to the appropriate provider.
        
        Args:
            task_type: Type of task
            request_data: Request payload
            
        Returns:
            Configured UnifiedProvider or None
        """
        route = self.get_route_for_task(task_type)
        
        # Try primary provider
        provider = self.registry.get_provider(route.provider_name)
        if not provider:
            provider = self.registry.create_provider(route.provider_name)
        
        if provider:
            return provider
        
        # Try fallback if configured
        if route.fallback_provider:
            fallback_provider = self.registry.get_provider(route.fallback_provider)
            if not fallback_provider:
                fallback_provider = self.registry.create_provider(route.fallback_provider)
            if fallback_provider:
                return fallback_provider
        
        # Last resort: return any active provider
        active = self.registry.get_active_provider()
        if active:
            return active
        
        # List available providers
        available = self.registry.list_active_providers()
        if available:
            return self.registry.get_provider(available[0])
        
        return None
    
    def set_route_for_task(self, task_type: TaskType, provider: str, model: str):
        """
        Override the default route for a task type.
        
        Args:
            task_type: Task type to configure
            provider: Provider name
            model: Model name
        """
        self.config.set_model_for_task(task_type.value, provider, model)
    
    def get_compatible_providers(self, required_capabilities: List[ProviderCapability]) -> List[str]:
        """
        Get providers that support the required capabilities.
        
        Args:
            required_capabilities: List of needed capabilities
            
        Returns:
            List of provider names that support all required capabilities
        """
        compatible = []
        
        for provider_name in self.registry.list_providers():
            provider = self.registry.get_provider(provider_name)
            if provider:
                provider_caps = provider.get_capabilities()
                if all(cap in provider_caps for cap in required_capabilities):
                    compatible.append(provider_name)
        
        return compatible
    
    def detect_task_type(self, input_text: str) -> TaskType:
        """
        Auto-detect task type from input text.
        
        Args:
            input_text: User input text
            
        Returns:
            Detected TaskType
        """
        text_lower = input_text.lower()
        
        # Code detection
        code_indicators = ['code', 'programming', 'python', 'javascript', 'function', 'class ', 'def ']
        if any(ind in text_lower for ind in code_indicators):
            return TaskType.CODE_GENERATION
        
        # Image generation
        image_indicators = ['generate image', 'create image', 'draw', 'generate picture', 'crear imagen']
        if any(ind in text_lower for ind in image_indicators):
            return TaskType.IMAGE_GENERATION
        
        # Vision analysis
        vision_indicators = ['look at', 'see', 'screen', 'what is', 'analyze', 'describe']
        if any(ind in text_lower for ind in vision_indicators):
            return TaskType.VISION
        
        # Fast response (short questions)
        if len(input_text) < 50 and ('?' in input_text or 'what' in text_lower or 'how' in text_lower):
            return TaskType.FAST_RESPONSE
        
        # Long context tasks
        if len(input_text) > 1000:
            return TaskType.LONG_CONTEXT
        
        # Creative tasks
        creative_indicators = ['write', 'story', 'creative', 'imagine', 'invent', 'design']
        if any(ind in text_lower for ind in creative_indicators):
            return TaskType.CREATIVE
        
        # Analytical
        analytical_indicators = ['analyze', 'compare', 'evaluate', 'research', 'study']
        if any(ind in text_lower for ind in analytical_indicators):
            return TaskType.ANALYTICAL
        
        return TaskType.GENERAL_REASONING


# Global router instance
_router_instance = None


def get_provider_router() -> ProviderRouter:
    """Get global provider router."""
    global _router_instance
    if _router_instance is None:
        _router_instance = ProviderRouter()
    return _router_instance