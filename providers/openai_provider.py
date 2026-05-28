"""
providers/openai_provider.py — OpenAI Provider
==============================================
Provider implementation for OpenAI API with full multimodal support.
Supports text, vision, audio input, and function calling.
"""

import asyncio
import json
from typing import Optional, List, Dict, Any, AsyncGenerator
from datetime import datetime, timezone

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


OPENAI_MODELS = {
    "gpt-4o": {
        "name": "GPT-4o",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "audio_input", "tool_call", "streaming"]
    },
    "gpt-4-turbo": {
        "name": "GPT-4 Turbo",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "tool_call", "streaming"]
    },
    "gpt-3.5-turbo": {
        "name": "GPT-3.5 Turbo",
        "context_window": 16385,
        "supports_multimodal": False,
        "capabilities": ["text", "tool_call", "streaming"]
    },
    "gpt-4": {
        "name": "GPT-4",
        "context_window": 8192,
        "supports_multimodal": False,
        "capabilities": ["text", "tool_call", "streaming"]
    }
}


class OpenAIProvider(MultimodalProvider):
    """
    Provider for OpenAI API.
    
    Supports:
    - Text generation
    - Vision analysis (images)
    - Audio input
    - Function calling / Tools
    - Streaming responses
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "gpt-4o"
    
    @property
    def name(self) -> str:
        return "openai"
    
    @property
    def display_name(self) -> str:
        return "OpenAI"
    
    async def connect(self) -> bool:
        """Initialize OpenAI API connection."""
        try:
            from openai import AsyncOpenAI
            
            self._client = AsyncOpenAI(
                api_key=self.config.api_key,
                base_url=self.config.base_url or "https://api.openai.com/v1"
            )
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[OpenAI] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close OpenAI connection."""
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
            print(f"[OpenAI] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """Send audio and get transcription/response."""
        if not self._client:
            raise RuntimeError("Provider not connected")
        
        try:
            import base64
            
            audio_b64 = base64.b64encode(audio_data).decode("utf-8")
            
            messages = [{
                "role": "user",
                "content": [
                    {"type": "input_audio", "audio": audio_b64, "format": mime_type}
                ]
            }]
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                temperature=self.config.temperature,
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            print(f"[OpenAI] send_audio error: {e}")
            return f"Error: {str(e)}"
    
    def list_models(self) -> List[ModelInfo]:
        """List available OpenAI models."""
        models = []
        for model_id, info in OPENAI_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass
            
            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="openai",
                capabilities=capabilities,
                context_window=info.get("context_window", 128000),
                supports_multimodal=info.get("supports_multimodal", False)
            ))
        
        return models
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Return provider capabilities."""
        return [
            ProviderCapability.TEXT,
            ProviderCapability.AUDIO_INPUT,
            ProviderCapability.VISION,
            ProviderCapability.TOOL_CALL,
            ProviderCapability.STREAMING,
        ]
    
    async def analyze_vision(self, image_data: bytes, prompt: str) -> str:
        """Analyze image and return description."""
        if not self._client:
            raise RuntimeError("Provider not connected")
        
        try:
            import base64
            
            image_b64 = base64.b64encode(image_data).decode("utf-8")
            
            messages = [{
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_b64}"}}
                ]
            }]
            
            response = await self._client.chat.completions.create(
                model=self._model,
                messages=messages,
                max_tokens=self.config.max_tokens,
            )
            
            return response.choices[0].message.content or ""
            
        except Exception as e:
            return f"Vision error: {str(e)}"
    
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


register_provider("openai", OpenAIProvider)