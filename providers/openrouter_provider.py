"""
providers/openrouter_provider.py — OpenRouter Provider
=====================================================
Provider implementation for OpenRouter API with access to multiple models.
Supports text, vision, and various model providers through OpenRouter's unified API.
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


OPENROUTER_MODELS = {
    "openai/gpt-4o": {
        "name": "GPT-4o (OpenAI via OpenRouter)",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "tool_call", "streaming"]
    },
    "openai/gpt-4o-mini": {
        "name": "GPT-4o Mini (OpenAI via OpenRouter)",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "tool_call", "streaming"]
    },
    "anthropic/claude-3.5-sonnet": {
        "name": "Claude 3.5 Sonnet (Anthropic via OpenRouter)",
        "context_window": 200000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "tool_call", "streaming"]
    },
    "google/gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash (Google via OpenRouter)",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "tool_call", "streaming"]
    },
    "meta-llama/llama-3.1-70b-instruct": {
        "name": "Llama 3.1 70B (Meta via OpenRouter)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    }
}


class OpenRouterProvider(MultimodalProvider):
    """
    Provider for OpenRouter API.
    
    Features:
    - Access to multiple model providers through single API
    - Models from OpenAI, Anthropic, Google, Meta, and more
    - Text, vision, and function calling support
    
    Note: Requires OpenRouter API key from https://openrouter.ai
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "openai/gpt-4o"
        self._base_url = "https://openrouter.ai/api/v1"
    
    @property
    def name(self) -> str:
        return "openrouter"
    
    @property
    def display_name(self) -> str:
        return "OpenRouter"
    
    async def connect(self) -> bool:
        """Initialize OpenRouter API connection."""
        try:
            from openai import AsyncOpenAI
            
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self._base_url
            )
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[OpenRouter] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close OpenRouter connection."""
        self._client = None
        self._is_connected = False
    
    async def send_text(
        self,
        text: str,
        tools: Optional[List[dict]] = None
    ) -> str:
        """Send text and get response."""
        if not self._client:
            raise RuntimeError("Provider not connected")
        
        try:
            messages = [{"role": "user", "content": text}]
            
            params = {
                "model": self._model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
            }
            
            if tools:
                params["tools"] = tools
            
            response = await self._client.chat.completions.create(**params)
            return response.choices[0].message.content or ""
            
        except Exception as e:
            print(f"[OpenRouter] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """OpenRouter does not support direct audio input."""
        return "Error: OpenRouter does not support audio input directly. Use a provider with native audio support."
    
    def list_models(self) -> List[ModelInfo]:
        """List available OpenRouter models."""
        models = []
        for model_id, info in OPENROUTER_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass
            
            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="openrouter",
                capabilities=capabilities,
                context_window=info.get("context_window", 128000),
                supports_multimodal=info.get("supports_multimodal", False)
            ))
        
        return models
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Return provider capabilities."""
        return [
            ProviderCapability.TEXT,
            ProviderCapability.VISION,
            ProviderCapability.TOOL_CALL,
            ProviderCapability.STREAMING,
        ]
    
    async def stream_text(
        self,
        text: str,
        tools: Optional[List[dict]] = None
    ) -> AsyncGenerator[str, None]:
        """Stream response chunks."""
        if not self._client:
            raise RuntimeError("Provider not connected")
        
        try:
            messages = [{"role": "user", "content": text}]
            
            params = {
                "model": self._model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True
            }
            
            if tools:
                params["tools"] = tools
            
            stream = await self._client.chat.completions.create(**params)
            
            async for chunk in stream:
                if chunk.choices[0].delta.content:
                    yield chunk.choices[0].delta.content
                    
        except Exception as e:
            yield f"Error: {str(e)}"


register_provider("openrouter", OpenRouterProvider)