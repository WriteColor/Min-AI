"""
providers/ollama_cloud_provider.py — Ollama Cloud Provider
========================================================
Provider implementation for Ollama Cloud (cloud.ollama.com) - hosted models.
Supports OpenAI-compatible API with cloud-hosted Ollama models.

API Docs: https://docs.ollama.com/api/introduction
OpenAI-compatible: https://docs.ollama.com/api/openai-compatibility
Authentication: https://docs.ollama.com/api/authentication

Free-to-use cloud models (no subscription required):
  - nemotron-3-super:cloud
  - gemma4:31b-cloud
  - And other Ollama community models uploaded to the cloud
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


OLLAMA_CLOUD_MODELS = {
    "nemotron-3-super:cloud": {
        "name": "Nemotron 3 Super (Cloud)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "gemma4:31b-cloud": {
        "name": "Gemma 4 31B (Cloud)",
        "context_window": 32000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "llama3.2:70b-cloud": {
        "name": "Llama 3.2 70B (Cloud)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "qwen2.5:72b-cloud": {
        "name": "Qwen 2.5 72B (Cloud)",
        "context_window": 32000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "mistral-nemo:12b-cloud": {
        "name": "Mistral Nemo 12B (Cloud)",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
}


class OllamaCloudProvider(MultimodalProvider):
    """
    Provider for Ollama Cloud hosted models via OpenAI-compatible API.

    Features:
    - OpenAI-compatible API (https://cloud.ollama.com/v1)
    - API key authentication (from cloud.ollama.com)
    - No subscription required for open community models
    - Streaming support
    - Tool calling support (some models)

    API Docs: https://docs.ollama.com/api/introduction
    """

    DEFAULT_BASE_URL = "https://cloud.ollama.com/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "nemotron-3-super:cloud"
        self._base_url = self.config.base_url or self.DEFAULT_BASE_URL

    @property
    def name(self) -> str:
        return "ollama_cloud"

    @property
    def display_name(self) -> str:
        return "Ollama Cloud"

    async def connect(self) -> bool:
        """Initialize Ollama Cloud API connection."""
        try:
            from openai import AsyncOpenAI

            api_key = self.config.api_key
            if not api_key:
                print("[OllamaCloud] API key required (get from cloud.ollama.com)")
                return False

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._base_url,
                timeout=60.0
            )

            self._is_connected = True
            return True

        except Exception as e:
            print(f"[OllamaCloud] Connection error: {e}")
            return False

    async def disconnect(self):
        """Close Ollama Cloud connection."""
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
            print(f"[OllamaCloud] send_text error: {e}")
            return f"Error: {str(e)}"

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """Ollama Cloud does not support audio input directly."""
        return "Error: Ollama Cloud does not support audio input."

    def list_models(self) -> List[ModelInfo]:
        """List available Ollama Cloud models."""
        models = []
        for model_id, info in OLLAMA_CLOUD_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass

            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="ollama_cloud",
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
        ]

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using Ollama Cloud embeddings endpoint."""
        if not self._client:
            raise RuntimeError("Provider not connected")

        try:
            response = await self._client.embeddings.create(
                model="nomic-embed-text",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[OllamaCloud] embedding error: {e}")
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


register_provider("ollama_cloud", OllamaCloudProvider)
