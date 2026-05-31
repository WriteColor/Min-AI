# JARVIS AI - API Reference

> **Last updated:** 2025-05-31

---

## Public Imports

### Core Modules

```python
from core.agent import MINAgent
from core.config_manager import ConfigManager
from core.state_manager import StateManager
from core.provider_router import ProviderRouter
from core.context_builder import ContextBuilder
from core.prompt_builder import PromptBuilder
from core.response_generator import ResponseGenerator
from core.intent_parser import IntentParser
from core.action_executor import ActionExecutor
from core.action_registry import ActionRegistry
from core.parameter_validator import ParameterValidator
from core.tool_schemas import TOOL_DECLARATIONS
```

### Providers

```python
from providers.base import BaseProvider, MultimodalProvider, LocalProvider
from providers.registry import ProviderRegistry, ProviderManager
from providers.model_selector import ModelSelector
from providers.gemini_provider import GeminiProvider
from providers.openai_provider import OpenAIProvider
from providers.openrouter_provider import OpenRouterProvider
from providers.groq_provider import GroqProvider
from providers.minimax_provider import MiniMaxProvider
from providers.ollama_cloud_provider import OllamaCloudProvider
from providers.nvidia_nim_provider import NvidiaNimProvider
from providers.local_provider import LocalProvider
```

### Memory

```python
from memory import (
    MemoryService,
    HybridMemory,
    SemanticMemory,
    EpisodicMemory,
    WorkMemory,
    VectorStore,
    memory_manager,
    save_memory,
    load_memory,
    search_memory,
    get_recent_memories,
)
```

### Services

```python
from services.audio.service import AudioService
from services.ai.llm import LLM
from services.ai.image_generator import ImageGenerator
from services.ai.music_generator import MusicGenerator
from services.vision.service import VisionService
```

---

## MINAgent (`core/agent.py`)

Main agent orchestrator.

```python
class MINAgent:
    def __init__(self):
        self.config = ConfigManager()
        self.memory = MemoryService()
        self.registry = ProviderRegistry()
        self.router = ProviderRouter(self.registry)

    async def process_message(self, message: str, context: dict = None) -> str
        """Process user message and return response."""

    async def process_voice(self, audio_data: bytes) -> str
        """Process voice input and return response."""

    def set_provider(self, provider_name: str) -> None
        """Switch active provider."""
```

---

## ConfigManager (`core/config_manager.py`)

Singleton configuration manager.

```python
class ConfigManager:
    @property
    def config(self) -> dict

    def get(self, key: str, default: Any = None) -> Any
    def set(self, key: str, value: Any) -> None
    def save(self) -> None
    def reload(self) -> None

    # Convenience properties
    @property
    def active_provider(self) -> str
    @property
    def api_keys(self) -> dict
    @property
    def model_assignments(self) -> dict
```

---

## ProviderRegistry (`providers/registry.py`)

```python
class ProviderRegistry:
    def register_provider(self, name: str, provider_class: type,
                         api_key: str = None, **kwargs) -> None

    def create_provider(self, name: str, **config) -> BaseProvider

    def get_provider(self, name: str = None) -> BaseProvider

    def set_active_provider(self, name: str) -> None

    def get_active_provider(self) -> BaseProvider

    def list_providers(self) -> list[str]
```

---

## BaseProvider (`providers/base.py`)

Abstract base for all AI providers.

```python
class BaseProvider(ABC):
    @property
    def name(self) -> str
    @property
    def supports_streaming(self) -> bool

    async def connect(self) -> bool
    async def disconnect(self) -> None
    async def send_messages(self, messages: list, **kwargs) -> str
    async def send_text(self, text: str, **kwargs) -> str
    async def send_audio(self, audio_data: bytes, **kwargs) -> str
    async def send_image(self, image_path: str, prompt: str = None, **kwargs) -> str
    async def list_models(self) -> list[str]
    async def stream_response(self, messages: list, **kwargs) -> AsyncIterator[str]
```

### MultimodalProvider

Extended base with vision capabilities.

```python
class MultimodalProvider(BaseProvider):
    async def send_image_url(self, image_url: str, prompt: str = None, **kwargs) -> str
    async def send_base64_image(self, base64_data: str, prompt: str = None, **kwargs) -> str
```

### LocalProvider

For Ollama/LM Studio-style local APIs.

```python
class LocalProvider(MultimodalProvider):
    async def connect(self) -> bool
    async def disconnect(self) -> None
    async def send_messages(self, messages: list, **kwargs) -> str
    async def send_text(self, text: str, **kwargs) -> str
    async def send_image(self, image_path: str, prompt: str = None, **kwargs) -> str
    async def list_models(self) -> list[str]
```

---

## ModelSelector (`providers/model_selector.py`)

```python
class ModelSelector:
    def __init__(self, registry: ProviderRegistry)

    def get_model_for_task(self, task: str, **kwargs) -> tuple[str, BaseProvider]

    def validate_model(self, provider_name: str, model_name: str) -> bool

    def list_compatible_models(self, task: str) -> list[dict]
```

---

## MemoryService (`memory/service.py`)

```python
class MemoryService:
    def remember(self, category: str, key: str, value: str,
                importance: float = 0.5, tags: list = None,
                expires_at: str = None) -> bool

    def recall(self, category: str, key: str) -> Optional[str]

    def forget(self, category: str, key: str) -> bool

    def search(self, query: str, limit: int = 5) -> list

    def build_context(self, query: str, limit: int = 5) -> str

    def get_recent(self, limit: int = 10) -> list

    def save_semantic(self, category: str, key: str, value: str,
                     confidence: float = 1.0, source: str = "manual") -> bool

    def get_similar(self, text: str, limit: int = 5) -> list

    def get_all_categories(self) -> list[str]
```

---

## HybridMemory (`memory/hybrid/hybrid.py`)

```python
class HybridMemory:
    def store(self, text: str, memory_type: str = "semantic",
              category: str = "general", importance: float = 0.5) -> bool

    def retrieve(self, query: str, limit: int = 5) -> list

    def build_context(self, query: str, limit: int = 5) -> str

    def get_recent(self, limit: int = 10) -> list

    def clear_session(self) -> None

    def get_stats(self) -> dict
```

---

## WorkMemory (`memory/work_memory.py`)

```python
class WorkMemory:
    def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None
    def get(self, key: str) -> Optional[str]
    def delete(self, key: str) -> bool
    def cleanup_expired(self) -> int
    def get_stats(self) -> dict
    def clear(self) -> None
```

---

## AudioService (`services/audio/service.py`)

```python
class AudioService:
    def __init__(self, config: dict)

    async def start(self) -> None
    async def stop(self) -> None

    async def send_realtime(self, audio_data: bytes) -> str
    async def listen_audio(self, timeout: float = 30.0) -> Optional[str]
    async def receive_audio(self) -> Optional[bytes]
    async def play_audio(self, audio_data: bytes) -> bool

    def set_voice(self, voice_name: str) -> None
    def set_speech_rate(self, rate: str) -> None
```

---

## ImageGenerator (`services/ai/image_generator.py`)

```python
class ImageGenerator:
    def __init__(self, api_key: str = None)

    async def generate(self, prompt: str, model: str = "flux",
                      width: int = 1024, height: int = 1024,
                      seed: int = None) -> str
        """Returns URL to generated image."""
```

---

## MusicGenerator (`services/ai/music_generator.py`)

```python
class MusicGenerator:
    def __init__(self, api_key: str)

    async def generate(self, description: str, duration: int = 30,
                      format: str = "mp3") -> str
        """Returns path to generated audio file."""
```

---

## ActionRegistry (`core/action_registry.py`)

```python
class ActionRegistry:
    def __init__(self)

    def register_action(self, name: str, handler: Callable,
                       schema: dict, category: str = "general") -> None

    def get_action(self, name: str) -> dict

    def list_actions(self, category: str = None) -> list[dict]

    def list_categories(self) -> list[str]

    def get_tool_declarations(self) -> list[dict]
```

---

## ActionExecutor (`core/action_executor.py`)

```python
class ActionExecutor:
    def __init__(self, registry: ActionRegistry,
                 validator: ParameterValidator)

    async def execute(self, action_name: str,
                      parameters: dict, player=None) -> str

    def validate(self, action_name: str,
                parameters: dict) -> tuple[bool, str]
```

---

## ParameterValidator (`core/parameter_validator.py`)

```python
class ParameterValidator:
    @staticmethod
    def validate_parameters(schema: dict,
                           parameters: dict) -> tuple[bool, str]

    @staticmethod
    def validate_type(value: Any, expected_type: str) -> bool

    @staticmethod
    def validate_enum(value: Any, allowed: list) -> bool

    @staticmethod
    def validate_range(value: Any, min_val: Any = None,
                      max_val: Any = None) -> bool
```

---

## StateManager (`core/state_manager.py`)

```python
class StateManager:
    def __init__(self)

    def get_state(self, key: str, default: Any = None) -> Any
    def set_state(self, key: str, value: Any) -> None
    def update_state(self, updates: dict) -> None
    def delete_state(self, key: str) -> None

    def subscribe(self, key: str, callback: Callable) -> None
    def unsubscribe(self, key: str, callback: Callable) -> None

    def take_snapshot(self, label: str) -> None
    def restore_snapshot(self, snapshot_id: str) -> None
    def list_snapshots(self) -> list[dict]
```

---

## ContextBuilder (`core/context_builder.py`)

```python
class ContextBuilder:
    def build_system_context(self) -> str
    def build_memory_context(self, query: str, limit: int = 5) -> str
    def build_conversation_context(self, limit: int = 10) -> str
    def assemble_full_context(self, query: str) -> dict
```

---

## PromptBuilder (`core/prompt_builder.py`)

```python
class PromptBuilder:
    def build_prompt(self, task: str, context: dict = None) -> str
    def build_tool_prompt(self, tool_name: str, parameters: dict) -> str
    def build_vision_prompt(self, image_path: str, question: str) -> str
```

---

## ResponseGenerator (`core/response_generator.py`)

```python
class ResponseGenerator:
    def format_response(self, content: str,
                       format: str = "text") -> str
    def format_error(self, error: str) -> str
    def format_tool_result(self, tool_name: str,
                          result: str) -> str
```

---

## IntentParser (`core/intent_parser.py`)

```python
class IntentParser:
    def parse(self, user_input: str) -> dict
        """Returns {"intent": str, "entities": dict, "confidence": float}"""

    def is_follow_up(self, user_input: str) -> bool
    def get_topic(self, user_input: str) -> str
```
