"""
providers/model_selector.py — Model Selection and Validation
=========================================================
Handles model compatibility validation and task-based model selection.
Ensures UI only shows valid provider/model combinations.

Author: MIN AI Team
Version: 1.0
"""

from typing import Dict, List, Optional, Set
from dataclasses import dataclass

from .base import ProviderCapability, ModelInfo


COMPATIBLE_COMBINATIONS: Dict[str, Dict[str, List[str]]] = {
    "gemini": {
        "text": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ],
        "vision": [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-1.5-pro",
            "gemini-1.5-flash"
        ],
        "audio_input": [
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ],
        "audio_output": [
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ],
        "tool_call": [
            "gemini-2.5-pro",
            "gemini-2.5-flash"
        ],
        "reasoning": [
            "gemini-2.5-pro"
        ]
    },
    "openrouter": {
        "text": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-flash"
        ],
        "vision": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini"
        ],
        "tool_call": [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet"
        ]
    },
    "groq": {
        "text": [
            "llama-3.1-70b-versatile",
            "llama-3.1-8b-instant",
            "mixtral-8x7b-32768"
        ]
    },
    "opencode": {
        "text": [
            "qwen2.5-72b-instruct",
            "llama3.1-70b-instruct",
            "deepseek-v3",
            "qwq-32b",
            "mistral-nemo-12b",
            "codellama-70b"
        ]
    },
    "minimax": {
        "text": [
            "Text-01",
            "MiniMax-Text-01",
            "abab6.5s-chat",
            "abab6.5g-chat"
        ]
    },
    "ollama_cloud": {
        "text": [
            "nemotron-3-super:cloud",
            "gemma4:31b-cloud",
            "llama3.2:70b-cloud",
            "qwen2.5:72b-cloud",
            "mistral-nemo:12b-cloud"
        ]
    },
    "nvidia_nim": {
        "text": [
            "meta/llama-3.1-405b-instruct",
            "meta/llama-3.1-70b-instruct",
            "meta/llama-3.1-8b-instruct",
            "mistralai/mixtral-8x7b-instruct-v0.1",
            "mistralai/mistral-7b-instruct-v0.3",
            "nvidia/llama-3.1-nemotron-70b-instruct",
            "google/gemma-2-27b-instruct"
        ]
    },
    "openai": {
        "text": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo",
            "gpt-3.5-turbo"
        ],
        "vision": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo"
        ],
        "tool_call": [
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-4-turbo"
        ]
    },
    "local": {
        "text": [
            "qwen2.5",
            "llama3.1",
            "mistral",
            "codellama",
            "phi3",
            "gemma2"
        ],
        "vision": [
            "llava",
            "qwen2.5-vl",
            "llama3.2-vision"
        ]
    }
}


CAPABILITY_MODELS: Dict[ProviderCapability, List[str]] = {
    ProviderCapability.TEXT: ["text"],
    ProviderCapability.VISION: ["vision"],
    ProviderCapability.AUDIO_INPUT: ["audio_input"],
    ProviderCapability.AUDIO_OUTPUT: ["audio_output"],
    ProviderCapability.TOOL_CALL: ["tool_call"],
    ProviderCapability.STREAMING: ["text"],
    ProviderCapability.REASONING: ["reasoning"]
}


@dataclass
class ModelValidationResult:
    is_valid: bool
    errors: List[str]
    compatible_capabilities: List[str]


class ModelSelector:
    """
    Handles model selection and validation based on provider capabilities.
    Provides validation for provider/model combinations.
    """
    
    def __init__(self):
        self._provider_models = COMPATIBLE_COMBINATIONS
    
    def get_models_for_provider(self, provider: str) -> List[str]:
        """
        Get all available models for a provider.
        
        Args:
            provider: Provider name
            
        Returns:
            List of model names
        """
        if provider not in self._provider_models:
            return []
        
        all_models: Set[str] = set()
        for cap_models in self._provider_models[provider].values():
            all_models.update(cap_models)
        
        return sorted(list(all_models))
    
    def get_models_for_capability(
        self,
        provider: str,
        capability: ProviderCapability
    ) -> List[str]:
        """
        Get models that support a specific capability for a provider.
        
        Args:
            provider: Provider name
            capability: Required capability
            
        Returns:
            List of model names supporting the capability
        """
        if provider not in self._provider_models:
            return []
        
        cap_key = CAPABILITY_MODELS.get(capability, [])
        if isinstance(cap_key, list):
            cap_key = cap_key[0] if cap_key else None
        
        if not cap_key or cap_key not in self._provider_models[provider]:
            return []
        
        return self._provider_models[provider][cap_key]
    
    def validate_model_for_provider(
        self,
        provider: str,
        model: str
    ) -> ModelValidationResult:
        """
        Validate if a model is available for a provider.
        
        Args:
            provider: Provider name
            model: Model name
            
        Returns:
            ModelValidationResult with validation status
        """
        errors = []
        
        if provider not in self._provider_models:
            return ModelValidationResult(
                is_valid=False,
                errors=[f"Unknown provider: {provider}"],
                compatible_capabilities=[]
            )
        
        available_models = self.get_models_for_provider(provider)
        
        if model not in available_models:
            errors.append(
                f"Model '{model}' not available for provider '{provider}'. "
                f"Available models: {', '.join(available_models[:5])}"
            )
            return ModelValidationResult(
                is_valid=False,
                errors=errors,
                compatible_capabilities=[]
            )
        
        compatible_caps = []
        for cap, cap_key in CAPABILITY_MODELS.items():
            cap_key_str = cap_key[0] if isinstance(cap_key, list) else cap_key
            if (cap_key_str in self._provider_models[provider] and
                model in self._provider_models[provider][cap_key_str]):
                compatible_caps.append(cap.value)
        
        return ModelValidationResult(
            is_valid=True,
            errors=[],
            compatible_capabilities=compatible_caps
        )
    
    def get_compatible_models(
        self,
        provider: str,
        required_capabilities: List[ProviderCapability]
    ) -> List[str]:
        """
        Get models that support all required capabilities.
        
        Args:
            provider: Provider name
            required_capabilities: List of required capabilities
            
        Returns:
            List of model names supporting all capabilities
        """
        if not required_capabilities:
            return self.get_models_for_provider(provider)
        
        candidate_models = None
        
        for capability in required_capabilities:
            models_for_cap = set(self.get_models_for_capability(provider, capability))
            
            if candidate_models is None:
                candidate_models = models_for_cap
            else:
                candidate_models &= models_for_cap
            
            if not candidate_models:
                break
        
        return sorted(list(candidate_models)) if candidate_models else []
    
    def get_default_model_for_task(
        self,
        provider: str,
        task_type: str
    ) -> Optional[str]:
        """
        Get the default model for a provider and task type.
        
        Args:
            provider: Provider name
            task_type: Task type string
            
        Returns:
            Recommended model name or None
        """
        task_to_capability = {
            "general_reasoning": [ProviderCapability.TEXT, ProviderCapability.REASONING],
            "vision": [ProviderCapability.VISION],
            "voice_realtime": [ProviderCapability.AUDIO_INPUT, ProviderCapability.AUDIO_OUTPUT],
            "fast_response": [ProviderCapability.TEXT],
            "code_generation": [ProviderCapability.TEXT, ProviderCapability.TOOL_CALL],
            "image_generation": [ProviderCapability.TEXT],
            "long_context": [ProviderCapability.TEXT],
            "creative": [ProviderCapability.TEXT],
            "analytical": [ProviderCapability.TEXT, ProviderCapability.REASONING]
        }
        
        capabilities = task_to_capability.get(
            task_type,
            [ProviderCapability.TEXT]
        )
        
        compatible = self.get_compatible_models(provider, capabilities)
        
        return compatible[0] if compatible else None
    
    def is_provider_available(self, provider: str) -> bool:
        """Check if provider is in the registry."""
        return provider in self._provider_models
    
    def list_all_providers(self) -> List[str]:
        """List all registered providers."""
        return sorted(list(self._provider_models.keys()))
    
    def get_provider_info(self, provider: str) -> Dict[str, any]:
        """
        Get information about a provider including capabilities.
        
        Args:
            provider: Provider name
            
        Returns:
            Dict with provider information
        """
        if provider not in self._provider_models:
            return {}
        
        models = self.get_models_for_provider(provider)
        capabilities = set()
        
        for cap_key, model_list in self._provider_models[provider].items():
            for model in model_list:
                if model in models:
                    for cap, cap_name in CAPABILITY_MODELS.items():
                        cap_str = cap_name[0] if isinstance(cap_name, list) else cap_name
                        if cap_str == cap_key:
                            capabilities.add(cap)
        
        return {
            "name": provider,
            "models": models,
            "model_count": len(models),
            "capabilities": [c.value for c in capabilities],
            "supports_multimodal": ProviderCapability.VISION in capabilities or
                                  ProviderCapability.AUDIO_INPUT in capabilities
        }


_model_selector = None


def get_model_selector() -> ModelSelector:
    """Get global model selector instance."""
    global _model_selector
    if _model_selector is None:
        _model_selector = ModelSelector()
    return _model_selector
