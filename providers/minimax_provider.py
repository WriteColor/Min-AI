"""
providers/minimax_provider.py — MiniMax Provider
================================================
Provider implementation for MiniMax (minimax.io) - Token Plan LLM models.
Supports MiniMax M2.7, M2.5, M2.1 text generation via OpenAI-compatible API.

API Docs: https://platform.minimax.io/docs/api-reference/text-chat-openai
"""

import asyncio
import time
import json
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


MINIMAX_LLM_MODELS = {
    "MiniMax-M2.7": {
        "name": "MiniMax M2.7 (204.8K context)",
        "context_window": 204800,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "MiniMax-M2.7-highspeed": {
        "name": "MiniMax M2.7 Highspeed (204.8K context)",
        "context_window": 204800,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "MiniMax-M2.5": {
        "name": "MiniMax M2.5 (204.8K context)",
        "context_window": 204800,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "MiniMax-M2.5-highspeed": {
        "name": "MiniMax M2.5 Highspeed (204.8K context)",
        "context_window": 204800,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "MiniMax-M2.1": {
        "name": "MiniMax M2.1 (204.8K context)",
        "context_window": 204800,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "MiniMax-M2.1-highspeed": {
        "name": "MiniMax M2.1 Highspeed (204.8K context)",
        "context_window": 204800,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
}


class MiniMaxProvider(MultimodalProvider):
    """
    Provider for MiniMax Token Plan LLM (M2.7, M2.5, M2.1).

    Features:
    - OpenAI-compatible API (https://api.minimax.io/v1)
    - Supports MiniMax M2.7, M2.7-highspeed, M2.5, M2.5-highspeed, M2.1, M2.1-highspeed
    - Up to 204,800 token context window
    - Text generation with streaming
    - Reasoning capabilities

    API Docs: https://platform.minimax.io/docs/api-reference/text-chat-openai
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "MiniMax-M2.7"
        self._base_url = "https://api.minimax.io/v1"

    @property
    def name(self) -> str:
        return "minimax"

    @property
    def display_name(self) -> str:
        return "MiniMax (M2.7)"

    async def connect(self) -> bool:
        """Initialize MiniMax API connection using OpenAI-compatible endpoint."""
        try:
            from openai import AsyncOpenAI

            api_key = self.config.api_key
            if not api_key:
                print("[MiniMax] API key required (Token Plan key)")
                return False

            self._client = AsyncOpenAI(
                api_key=api_key,
                base_url=self._base_url,
                timeout=60.0
            )

            self._is_connected = True
            return True

        except Exception as e:
            print(f"[MiniMax] Connection error: {e}")
            return False

    async def disconnect(self):
        """Close MiniMax connection."""
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
            print(f"[MiniMax] send_text error: {e}")
            return f"Error: {str(e)}"

    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """MiniMax LLM does not support audio input."""
        return "Error: MiniMax M2.7 does not support audio input."

    def list_models(self) -> List[ModelInfo]:
        """List available MiniMax LLM models."""
        models = []
        for model_id, info in MINIMAX_LLM_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass

            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="minimax",
                capabilities=capabilities,
                context_window=info.get("context_window", 204800),
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


register_provider("minimax", MiniMaxProvider)
