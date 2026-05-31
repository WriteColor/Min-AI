"""
providers/nvidia_nim_provider.py — NVIDIA NIM Provider
======================================================
Provider implementation for NVIDIA NIM (NVIDIA AI Foundation Models).
Supports OpenAI-compatible API for hosted inference endpoints.

API Docs: https://docs.nvidia.com/nim/lager/2.0/
Authentication: API key from console.nvidia.com

Free tier available with rate limits for open models.
Popular models:
  - meta/llama-3.1-405b-instruct
  - meta/llama-3.1-70b-instruct
  - mistralai/mixtral-8x7b-instruct-v0.1
  - nvidia/llama-3.1-nemotron-70b-instruct
"""

import asyncio
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


NVIDIA_NIM_MODELS = {
    "meta/llama-3.1-405b-instruct": {
        "name": "Llama 3.1 405B Instruct",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "tool_call"]
    },
    "meta/llama-3.1-70b-instruct": {
        "name": "Llama 3.1 70B Instruct",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "tool_call"]
    },
    "meta/llama-3.1-8b-instruct": {
        "name": "Llama 3.1 8B Instruct",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "mistralai/mixtral-8x7b-instruct-v0.1": {
        "name": "Mixtral 8x7B Instruct",
        "context_window": 32000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "tool_call"]
    },
    "mistralai/mistral-7b-instruct-v0.3": {
        "name": "Mistral 7B Instruct v0.3",
        "context_window": 32000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "nvidia/llama-3.1-nemotron-70b-instruct": {
        "name": "Nemotron 70B Instruct",
        "context_window": 128000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "google/gemma-2-27b-instruct": {
        "name": "Gemma 2 27B Instruct",
        "context_window": 8192,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "snowflake/arctic": {
        "name": "Snowflake Arctic",
        "context_window": 4000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
}


class NvidiaNimProvider(MultimodalProvider):
    """
    Provider for NVIDIA NIM (AI Foundation Models) via OpenAI-compatible API.

    Features:
    - OpenAI-compatible API (https://integrate.api.nvidia.com/v1)
    - API key authentication (from console.nvidia.com)
    - Free tier with rate limits available
    - Streaming support
    - Tool calling (varies by model)

    API Docs: https://docs.nvidia.com/nim/lager/2.0/
    """

    DEFAULT_BASE_URL = "https://integrate.api.nvidia.com/v1"

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "meta/llama-3.1-70b-instruct"
        self._base_url = self.config.base_url or self.DEFAULT_BASE_URL

    @property
    def name(self) -> str:
        return "nvidia_nim"

    @property
    def display_name(self) -> str:
        return "NVIDIA NIM"

    async def connect(self) -> bool:
        """Initialize NVIDIA NIM API connection."""
        try:
            from openai import AsyncOpenAI

            api_key = self.config.api_key
            if not api_key:
                print("[NvidiaNim] API key required (get from console.nvidia.com)")
                return False

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._base_url,
                timeout=60.0
            )

            self._is_connected = True
            return True

        except Exception as e:
            print(f"[NvidiaNim] Connection error: {e}")
            return False

    async def disconnect(self):
        """Close NVIDIA NIM connection."""
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
            print(f"[NvidiaNim] send_text error: {e}")
            return f"Error: {str(e)}"

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """NVIDIA NIM does not support audio input."""
        return "Error: NVIDIA NIM does not support audio input."

    def list_models(self) -> List[ModelInfo]:
        """List available NVIDIA NIM models."""
        models = []
        for model_id, info in NVIDIA_NIM_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass

            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="nvidia_nim",
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
            ProviderCapability.TOOL_CALL,
        ]

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using NVIDIA NIM embeddings endpoint."""
        if not self._client:
            raise RuntimeError("Provider not connected")

        try:
            response = await self._client.embeddings.create(
                model="nvidia/nvolm-qa-4bembedding",
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"[NvidiaNim] embedding error: {e}")
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


register_provider("nvidia_nim", NvidiaNimProvider)
