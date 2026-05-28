"""
providers/opencode_provider.py — OpenCode Provider
================================================
Provider implementation for OpenCode (opencode.ai) - free AI models.
OpenCode provides free access to various AI models via OpenAI-compatible API.
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, LocalProvider, register_provider
)


OPENCODE_MODELS = {
    "opencode闲聊": {
        "name": "OpenCode Chat (Free)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "opencodeofficial/qwen2.5-72b-instruct": {
        "name": "Qwen 2.5 72B (Free)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "opencodeofficial/qwq-32b": {
        "name": "QWQ 32B (Free)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "opencodeofficial/llama3.1-70b": {
        "name": "Llama 3.1 70B (Free)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "opencodeofficial/deepseek-v3-0324": {
        "name": "DeepSeek V3 (Free)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "opencodeofficial/coding": {
        "name": "OpenCode Coding (Free)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    }
}


class OpenCodeProvider(LocalProvider):
    """
    Provider for OpenCode (opencode.ai).
    
    Features:
    - Free access to various AI models
    - OpenAI-compatible API
    - No API key required for basic usage
    
    Note: OpenCode does not support vision or audio directly.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "opencodeofficial/qwen2.5-72b-instruct"
        self._base_url = "https://api.opencode.ai/v1"
    
    @property
    def name(self) -> str:
        return "opencode"
    
    @property
    def display_name(self) -> str:
        return "OpenCode (Free)"
    
    async def connect(self) -> bool:
        """Initialize OpenCode API connection."""
        try:
            from openai import AsyncOpenAI
            
            api_key = self.config.api_key or "not-needed"
            
            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._base_url
            )
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[OpenCode] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close OpenCode connection."""
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
            print(f"[OpenCode] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """OpenCode does not support audio input directly."""
        return "Error: OpenCode does not support audio input. Use a multimodal provider."
    
    def list_models(self) -> List[ModelInfo]:
        """List available OpenCode models."""
        models = []
        for model_id, info in OPENCODE_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass
            
            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="opencode",
                capabilities=capabilities,
                context_window=info.get("context_window", 128000),
                supports_multimodal=info.get("supports_multimodal", False)
            ))
        
        return models
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Return provider capabilities."""
        return [
            ProviderCapability.TEXT,
            ProviderCapability.STREAMING,
            ProviderCapability.REASONING,
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


register_provider("opencode", OpenCodeProvider)
