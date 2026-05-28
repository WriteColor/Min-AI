"""
providers/minimax_provider.py — MiniMax Provider
================================================
Provider implementation for MiniMax (minimax.io) - free AI models.
MiniMax provides various AI models including their own speech and vision models.
"""

import asyncio
import hashlib
import hmac
import base64
import time
import json
from typing import Optional, List, Dict, Any, AsyncGenerator

from .base import (
    BaseProvider, ProviderConfig, ModelInfo, ProviderCapability,
    MultimodalProvider, register_provider
)


MINIMAX_MODELS = {
    "MiniMax-Text-01": {
        "name": "MiniMax Text 01 (Free)",
        "context_window": 1000000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming", "reasoning"]
    },
    "abab6.5s-chat": {
        "name": "ABAB 6.5S Chat (Free)",
        "context_window": 245000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "abab6.5-chat": {
        "name": "ABAB 6.5 Chat (Free)",
        "context_window": 245000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    },
    "abab5.5-chat": {
        "name": "ABAB 5.5 Chat (Free)",
        "context_window": 180000,
        "supports_multimodal": False,
        "capabilities": ["text", "streaming"]
    }
}


class MiniMaxProvider(MultimodalProvider):
    """
    Provider for MiniMax (minimax.io).
    
    Features:
    - Free access to various AI models
    - Supports very large context windows
    - Text generation with streaming
    
    Note: MiniMax may require API key for full access.
    """

    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self._client = None
        self._model = config.model or "MiniMax-Text-01"
        self._base_url = "https://api.minimax.chat/v"
    
    @property
    def name(self) -> str:
        return "minimax"
    
    @property
    def display_name(self) -> str:
        return "MiniMax (Free)"
    
    def _generate_auth_signature(self, api_key: str, api_secret: str) -> tuple:
        """Generate MiniMax authentication signature."""
        timestamp = int(time.time())
        expires = timestamp + 60  # 1 minute expiry
        
        # Create signature string
        sign_str = f"{api_key}:{expires}"
        
        # HMAC-SHA256
        signature = hmac.new(
            api_secret.encode(),
            sign_str.encode(),
            hashlib.sha256
        ).digest()
        
        signature_b64 = base64.b64encode(signature).decode()
        
        return signature_b64, expires
    
    async def connect(self) -> bool:
        """Initialize MiniMax API connection."""
        try:
            import httpx
            
            api_key = self.config.api_key
            api_secret = self.config.extra.get("api_secret", "")
            
            if not api_key:
                print("[MiniMax] API key required")
                return False
            
            # For MiniMax, we store credentials in extra
            # If no secret provided, try using just API key auth
            self._auth_data = {
                "api_key": api_key,
                "api_secret": api_secret
            }
            
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
        if not self._is_connected:
            raise RuntimeError("Provider not connected")
        
        try:
            import httpx
            
            api_key = self._auth_data.get("api_key", "")
            api_secret = self._auth_data.get("api_secret", "")
            
            # Generate signature if secret available
            headers = {"Content-Type": "application/json"}
            
            if api_secret:
                signature, expires = self._generate_auth_signature(api_key, api_secret)
                group_id = self.config.extra.get("group_id", "")
                
                auth_header = f"Bearer;{api_key};{signature};{expires}"
                if group_id:
                    auth_header += f";{group_id}"
                headers["Authorization"] = auth_header
            else:
                headers["Authorization"] = f"Bearer {api_key}"
            
            messages = [{"role": "user", "content": text}]
            
            data = {
                "model": self._model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }
            
            if tools:
                data["tools"] = tools
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                response = await client.post(
                    f"{self._base_url}/text/chatcompletion_v2",
                    headers=headers,
                    json=data
                )
                
                if response.status_code == 200:
                    result = response.json()
                    return result.get("choices", [{}])[0].get("messages", [{}])[0].get("text", "")
                else:
                    return f"Error: {response.status_code} - {response.text}"
            
        except Exception as e:
            print(f"[MiniMax] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """MiniMax does not support audio input in standard text endpoint."""
        return "Error: MiniMax does not support audio input directly. Use a multimodal provider."
    
    def list_models(self) -> List[ModelInfo]:
        """List available MiniMax models."""
        models = []
        for model_id, info in MINIMAX_MODELS.items():
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
        if not self._is_connected:
            raise RuntimeError("Provider not connected")
        
        try:
            import httpx
            
            api_key = self._auth_data.get("api_key", "")
            api_secret = self._auth_data.get("api_secret", "")
            
            headers = {"Content-Type": "application/json"}
            
            if api_secret:
                signature, expires = self._generate_auth_signature(api_key, api_secret)
                group_id = self.config.extra.get("group_id", "")
                
                auth_header = f"Bearer;{api_key};{signature};{expires}"
                if group_id:
                    auth_header += f";{group_id}"
                headers["Authorization"] = auth_header
            else:
                headers["Authorization"] = f"Bearer {api_key}"
            
            messages = [{"role": "user", "content": text}]
            
            data = {
                "model": self._model,
                "messages": messages,
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens,
                "stream": True
            }
            
            if tools:
                data["tools"] = tools
            
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "POST",
                    f"{self._base_url}/text/chatcompletion_v2",
                    headers=headers,
                    json=data
                ) as response:
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            if data_str == "[DONE]":
                                break
                            try:
                                chunk = json.loads(data_str)
                                content = chunk.get("choices", [{}])[0].get("messages", [{}])[0].get("text", "")
                                if content:
                                    yield content
                            except:
                                pass
                        
        except Exception as e:
            yield f"Error: {str(e)}"


register_provider("minimax", MiniMaxProvider)
