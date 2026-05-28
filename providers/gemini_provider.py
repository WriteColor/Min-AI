"""
providers/gemini_provider.py — Google Gemini Provider
=====================================================
Provider implementation for Google Gemini API with full multimodal support.
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


GEMINI_MODELS = {
    "gemini-2.5-flash": {
        "name": "Gemini 2.5 Flash",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "audio_input", "tool_call", "streaming"]
    },
    "gemini-2.5-pro": {
        "name": "Gemini 2.5 Pro",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "audio_input", "tool_call", "streaming", "reasoning"]
    },
    "gemini-1.5-flash": {
        "name": "Gemini 1.5 Flash",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "audio_input", "tool_call"]
    },
    "gemini-1.5-pro": {
        "name": "Gemini 1.5 Pro",
        "context_window": 128000,
        "supports_multimodal": True,
        "capabilities": ["text", "vision", "audio_input", "tool_call"]
    }
}


class GeminiProvider(MultimodalProvider):
    """
    Provider for Google Gemini API.
    
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
        self._model = config.model or "gemini-2.5-flash"
    
    @property
    def name(self) -> str:
        return "gemini"
    
    @property
    def display_name(self) -> str:
        return "Google Gemini"
    
    async def connect(self) -> bool:
        """Initialize Gemini API connection."""
        try:
            import google.generativeai as genai
            
            genai.configure(api_key=self.config.api_key)
            self._client = genai.GenerativeModel(self._model)
            self._is_connected = True
            return True
        except Exception as e:
            print(f"[Gemini] Connection error: {e}")
            return False
    
    async def disconnect(self):
        """Close Gemini connection."""
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
            generation_config = {
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
            
            if tools:
                # Convert tools to Gemini format
                gemini_tools = []
                for tool in tools:
                    gemini_tools.append({
                        "function_declarations": [
                            {
                                "name": tool.get("name"),
                                "description": tool.get("description", ""),
                                "parameters": tool.get("parameters", {"type": "object", "properties": {}})
                            }
                        ]
                    })
                
                response = await asyncio.to_thread(
                    self._client.generate_content,
                    text,
                    generation_config=generation_config,
                    tools=gemini_tools
                )
            else:
                response = await asyncio.to_thread(
                    self._client.generate_content,
                    text,
                    generation_config=generation_config
                )
            
            return response.text
            
        except Exception as e:
            print(f"[Gemini] send_text error: {e}")
            return f"Error: {str(e)}"
    
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """Send audio and get transcription/response."""
        if not self._client:
            raise RuntimeError("Provider not connected")
        
        try:
            from google.generativeai import Audio
            
            audio_part = Audio(audio_data, mime_type=mime_type)
            response = await asyncio.to_thread(
                self._client.generate_content,
                [text_input, audio_part]
            )
            
            return response.text
            
        except Exception as e:
            print(f"[Gemini] send_audio error: {e}")
            return f"Error: {str(e)}"
    
    def list_models(self) -> List[ModelInfo]:
        """List available Gemini models."""
        models = []
        for model_id, info in GEMINI_MODELS.items():
            capabilities = []
            for cap in info.get("capabilities", []):
                try:
                    capabilities.append(ProviderCapability(cap))
                except ValueError:
                    pass
            
            models.append(ModelInfo(
                id=model_id,
                name=info["name"],
                provider="gemini",
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
            from google.generativeai import GenerativeModel
            
            model = GenerativeModel(self._model)
            response = await asyncio.to_thread(
                model.generate_content,
                [prompt, image_data]
            )
            
            return response.text
            
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
            generation_config = {
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            }
            
            response = await asyncio.to_thread(
                self._client.generate_content,
                text,
                generation_config=generation_config,
                stream=True
            )
            
            for chunk in response:
                if chunk.text:
                    yield chunk.text
                    
        except Exception as e:
            yield f"Error: {str(e)}"


register_provider("gemini", GeminiProvider)