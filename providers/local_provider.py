"""
providers/local_provider.py — Local Provider (Ollama/LM Studio)
==============================================================
Provider implementation for local AI models via OpenAI-compatible API.
Supports Ollama, LM Studio, and other local inference servers.
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability, register_provider
)


LOCAL_MODELS = {
    "qwen2.5": {
        "name": "Qwen 2.5",
        "context_window": 32000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "streaming"]
    },
    "llama3.1": {
        "name": "Llama 3.1",
        "context_window": 32000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "codellama": {
        "name": "Code Llama",
        "context_window": 16000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "mistral": {
        "name": "Mistral",
        "context_window": 32000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "nomic-embed-text": {
        "name": "Nomic Embed Text",
        "context_window": 8000,
        "supports_multimodal": False,
        "capabilities": ["text", "embeddings"]
    }
}


class LocalProvider(BaseProvider):
    """
    Provider for local AI inference servers (Ollama, LM Studio, etc.).
    
    Features:
    - OpenAI-compatible API interface
    - Local inference (no data leaves machine)
    - Configurable base URL (default: http://localhost:11434/v1)
    - Support for various local models
    
    Note: Requires local inference server running (Ollama or LM Studio).
    """
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "llama3.1"
        self._base_url = self.config.base_url or "http://localhost:11434/v1"
    
    @property
    def name(self) -> str:
        return "local"
    
    @property
    def display_name(self) -> str:
        return "Local (Ollama/LM Studio)"
    
    async def connect(self) -> bool:
        """Initialize local inference server connection."""
        try:
            from openai import AsyncOpenAI
            
            self._client = AsyncOpenAI(
                api_key=self.config.api_key or "local",
                base_url=self._base_url
            )
            
            models = await self._client.models.list()
            models_list = []
            async for m in models:
                models_list.append(m)
            if models_list:
                self._is_connected = True
                return True
            
            return False
        except Exception as e:
            print(f"[Local] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close local connection."""
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
            print(f"[Local] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """Local providers typically don't support audio."""
        return "Error: Local provider does not support audio input."
    
    def list_models(self) -> List[ModelInfo]:
        """List available local models."""
        models = []
        for model_id, info in LOCAL_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass
            
            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="local",
                capabilities=capabilities,
                context_window=info.get("context_window", 32000),
                supports_multimodal=info.get("supports_multimodal", False)
            ))
        
        return models
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Return provider capabilities."""
        return [
            ProviderCapability.TEXT,
            ProviderCapability.STREAMING,
        ]
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using local embedding model."""
        if not self._client:
            raise RuntimeError("Provider not connected")
        
        try:
            response = await self._client.embeddings.create(
                model="nomic-embed-text",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[Local] embedding error: {e}")
            return []
    
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


register_provider("local", LocalProvider)