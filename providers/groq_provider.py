"""
providers/groq_provider.py — Groq Provider
===========================================
Provider implementation for Groq API with ultra-low latency inference.
Optimized for real-time applications and fast responses.
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


GROQ_MODELS = {
    "llama-3.1-70b-versatile": {
        "name": "Llama 3.1 70B Versatile",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "tool_call", "streaming"]
    },
    "llama-3.1-8b-instant": {
        "name": "Llama 3.1 8B Instant",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "mixtral-8x7b-32768": {
        "name": "Mixtral 8x7B",
        "context_window": 32768,
        "supports_multimodal": False,
        "capabilities": ["text", "tool_call", "streaming"]
    }
}


class GroqProvider(MultimodalProvider):
    """
    Provider for Groq API.
    
    Features:
    - Ultra-low latency inference
    - Fast response times for real-time applications
    - Text generation with streaming support
    
    Note: Groq does not support vision or audio directly.
    For multimodal needs, route to another provider.
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "llama-3.1-8b-instant"
    
    @property
    def name(self) -> str:
        return "groq"
    
    @property
    def display_name(self) -> str:
        return "Groq"
    
    async def connect(self) -> bool:
        """Initialize Groq API connection."""
        try:
            from groq import AsyncGroq
            
            self._client = AsyncGroq(
                api_key=self.config.api_key,
                base_url=self.config.base_url or "https://api.groq.com"
            )
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[Groq] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close Groq connection."""
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
            print(f"[Groq] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """Groq does not support audio input directly."""
        return "Error: Groq does not support audio input. Use a multimodal provider."
    
    def list_models(self) -> List[ModelInfo]:
        """List available Groq models."""
        models = []
        for model_id, info in GROQ_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass
            
            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="groq",
                capabilities=capabilities,
                context_window=info.get("context_window", 128000),
                supports_multimodal=info.get("supports_multimodal", False)
            ))
        
        return models
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Return provider capabilities."""
        return [
            ProviderCapability.TEXT,
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


register_provider("groq", GroqProvider)