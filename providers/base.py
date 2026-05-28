"""
Provider Abstract Layer
=======================
Abstrae completamente la lógica de proveedores de IA, permitiendo intercambiar
modelos y backends en tiempo real sin reinicios ni pérdida de estado.

Cada provider implementa:
- connect(): Inicializa la sesión/conexión
- disconnect(): Cierra la sesión
- send_text(text): Envía texto al modelo
- send_audio(audio_data): Envía audio al modelo  
- receive(): Recibe respuesta (texto o audio)
- list_models(): Lista modelos disponibles
- get_capabilities(): Retorna capacidades (text, audio, vision, etc.)
"""

from abc import ABC, abstractmethod
from typing import Optional, Callable, AsyncGenerator, Dict, Any, List
from dataclasses import dataclass, field
from enum import Enum
import asyncio
import threading
import traceback


class ProviderCapability(Enum):
    TEXT = "text"
    AUDIO_INPUT = "audio_input"
    AUDIO_OUTPUT = "audio_output"
    VISION = "vision"
    TOOL_CALL = "tool_call"
    STREAMING = "streaming"
    REASONING = "reasoning"


@dataclass
class ModelInfo:
    id: str
    name: str
    provider: str
    capabilities: List[ProviderCapability]
    context_window: int = 128000
    supports_multimodal: bool = False
    max_audio_length_sec: int = 60


@dataclass
class ProviderConfig:
    api_key: str
    base_url: Optional[str] = None
    model: str = ""
    voice: str = "Aoede"
    temperature: float = 0.2
    max_tokens: int = 8192
    thinking_budget: int = 0
    extra: Dict[str, Any] = field(default_factory=dict)


class BaseProvider(ABC):
    """Clase base abstracta para todos los proveedores de IA."""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self._session = None
        self._is_connected = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._lock = threading.Lock()
        
    @property
    @abstractmethod
    def name(self) -> str:
        """Nombre único del proveedor."""
        pass
    
    @property
    @abstractmethod
    def display_name(self) -> str:
        """Nombre para mostrar en la UI."""
        pass
    
    @abstractmethod
    async def connect(self) -> bool:
        """Establece conexión con el proveedor. Retorna True si exitoso."""
        pass
    
    @abstractmethod
    async def disconnect(self):
        """Cierra la conexión con el proveedor."""
        pass
    
    @abstractmethod
    async def send_text(self, text: str, tools: Optional[List[dict]] = None) -> str:
        """Envía texto y retorna respuesta."""
        pass
    
    @abstractmethod
    async def send_audio(self, audio_data: bytes, mime_type: str = "audio/pcm") -> str:
        """Envía audio y retorna transcripción/respuesta."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[ModelInfo]:
        """Lista modelos disponibles para este proveedor."""
        pass
    
    def get_capabilities(self) -> List[ProviderCapability]:
        """Retorna lista de capacidades del proveedor."""
        return [ProviderCapability.TEXT]
    
    async def stream_text(self, text: str, tools: Optional[List[dict]] = None) -> AsyncGenerator[str, None]:
        """Versión streaming de send_text. Yield chunks de respuesta."""
        result = await self.send_text(text, tools)
        yield result
    
    @property
    def is_connected(self) -> bool:
        return self._is_connected
    
    def validate_config(self) -> List[str]:
        """Valida configuración y retorna lista de errores. Lista vacía = válido."""
        errors = []
        if not self.config.api_key:
            errors.append("API key es requerida")
        if not self.config.model:
            errors.append("Modelo es requerido")
        return errors


class MultimodalProvider(BaseProvider):
    """Provider que soporta entrada multimodal (texto + audio + visión)."""
    
    def get_capabilities(self) -> List[ProviderCapability]:
        caps = super().get_capabilities()
        caps.extend([
            ProviderCapability.AUDIO_INPUT,
            ProviderCapability.AUDIO_OUTPUT,
            ProviderCapability.VISION,
            ProviderCapability.TOOL_CALL,
            ProviderCapability.STREAMING,
        ])
        return caps


class LocalProvider(BaseProvider):
    """Provider para modelos locales (OpenAI-compatible API en puerto 1337)."""
    
    def get_capabilities(self) -> List[ProviderCapability]:
        caps = super().get_capabilities()
        caps.append(ProviderCapability.STREAMING)
        return caps


# Registry de providers
_PROVIDER_REGISTRY: Dict[str, type] = {}


def register_provider(name: str, provider_class: type):
    """Decora una clase para registrarla como provider disponible."""
    _PROVIDER_REGISTRY[name] = provider_class


def get_provider_class(name: str) -> Optional[type]:
    """Retorna la clase del provider por nombre."""
    return _PROVIDER_REGISTRY.get(name)


def list_registered_providers() -> List[str]:
    """Lista todos los providers registrados."""
    return list(_PROVIDER_REGISTRY.keys())


# Interfaz unificada para el sistema
class UnifiedProvider:
    """Envuelve un provider y provee interfaz unificada para MIN."""
    
    def __init__(self, provider: BaseProvider, ui=None):
        self.provider = provider
        self.ui = ui
        self._is_speaking = False
        self._speaking_lock = threading.Lock()
        
    @property
    def name(self) -> str:
        return self.provider.name
    
    @property
    def display_name(self) -> str:
        return self.provider.display_name
    
    async def initialize(self) -> bool:
        """Inicializa el provider y retorna éxito."""
        try:
            return await self.provider.connect()
        except Exception as e:
            print(f"[Provider] Error inicializando {self.name}: {e}")
            traceback.print_exc()
            return False
    
    async def shutdown(self):
        """Cierra el provider gracefully."""
        await self.provider.disconnect()
    
    async def chat(self, text: str, tools: Optional[List[dict]] = None) -> str:
        """Envía mensaje de texto y retorna respuesta."""
        return await self.provider.send_text(text, tools)
    
    async def chat_stream(self, text: str, tools: Optional[List[dict]] = None) -> AsyncGenerator[str, None]:
        """Versión streaming de chat."""
        async for chunk in self.provider.stream_text(text, tools):
            yield chunk
    
    def list_models(self) -> List[ModelInfo]:
        return self.provider.list_models()
    
    def get_capabilities(self) -> List[ProviderCapability]:
        return self.provider.get_capabilities()
    
    def set_ui(self, ui):
        self.ui = ui
        
    def set_speaking(self, value: bool):
        with self._speaking_lock:
            self._is_speaking = value
        if self.ui:
            if value:
                self.ui.set_state("SPEAKING")
            elif not getattr(self.ui, 'muted', False):
                self.ui.set_state("LISTENING")
    
    @property
    def is_speaking(self) -> bool:
        return self._is_speaking
    
    @property
    def is_connected(self) -> bool:
        return self.provider.is_connected