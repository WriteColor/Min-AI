# JARVIS AI - Architecture Guide

> **Last updated:** 2025-05-28
> **Phase:** 1 (Foundation) - 70% Complete

---

## Project Structure

```
C:\React-Nextjs-Projects\Jarvis AI\
├── main.py                    # Entry point
├── ui.py                      # WebSocket UI server
│
├── core/                      # Core system modules
│   ├── interfaces.py          # Standard interfaces (MemoryInterface, ProviderInterface, etc.)
│   ├── system_prompts.py      # Centralized AI prompts
│   ├── agent.py               # Task queue and orchestration
│   ├── provider_router.py      # Intelligent model routing
│   ├── context_builder.py     # Context assembly
│   ├── config_manager.py      # Configuration management
│   ├── state_manager.py       # Application state
│   ├── action_executor.py     # Action execution engine
│   ├── intent_parser.py       # Intent detection
│   ├── prompt_builder.py       # Dynamic prompt construction
│   ├── action_registry.py      # Action registration
│   ├── parameter_validator.py  # Input validation
│   └── response_generator.py   # Response formatting
│
├── actions/                   # Action modules (organized by domain)
│   ├── system/               # OS control (open_app, desktop, etc.)
│   ├── files/                # File operations
│   ├── automation/           # External integrations (gmail, calendar, etc.)
│   ├── media/                # Media control (spotify, youtube, etc.)
│   ├── vision/               # Screen vision and image generation
│   ├── web/                  # Browser and web operations
│   └── utils/                # Utility actions
│
├── providers/                 # AI provider abstraction
│   ├── base.py              # BaseProvider abstract class
│   ├── registry.py          # Provider registry/factory
│   ├── model_selector.py    # Model selection logic
│   ├── gemini_provider.py   # Google Gemini
│   ├── openai_provider.py   # OpenAI
│   ├── openrouter_provider.py # OpenRouter
│   ├── groq_provider.py     # Groq
│   ├── local_provider.py    # Ollama/LM Studio
│   └── minimax_provider.py  # MiniMax
│
├── services/                 # Platform services
│   ├── windows_api.py       # Windows API (flat structure)
│   └── win32_api.py        # Win32 bindings
│
├── memory/                   # Memory subsystem
├── config/                   # Configuration files
│   └── vosk_model/          # Speech recognition (PRESERVED - no changes)
│
├── assets/                   # Static resources
├── logs/                     # Audit logs
└── Min-UI/                  # Frontend (Tauri + React + TS)
```

---

## Core Interfaces (`core/interfaces.py`)

Standard contracts for module communication:

| Interface | Purpose |
|-----------|---------|
| `MemoryInterface` | Persistent memory operations |
| `ProviderInterface` | AI provider abstraction |
| `ActionInterface` | Action execution |
| `ConfigInterface` | Configuration management |
| `WindowManagerInterface` | Window management |
| `FileSystemInterface` | File operations |
| `AudioInterface` | Audio input/output |
| `IntentParserInterface` | Intent detection |

---

## Adding New Actions

### 1. Create the action module

```python
# actions/<domain>/my_action.py
from typing import Dict, Any

def execute(params: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute my action."""
    # Implementation
    return {"success": True, "result": "..."}
```

### 2. Register in `actions/<domain>/__init__.py`

```python
from .my_action import execute as my_action
```

### 3. Action is auto-discovered via `action_executor.py`

---

## Adding New Providers

### 1. Implement `BaseProvider`

```python
# providers/my_provider.py
from providers.base import BaseProvider, ProviderConfig

class MyProvider(BaseProvider):
    @property
    def name(self) -> str:
        return "myprovider"
    
    async def connect(self) -> bool:
        # Initialize connection
        pass
    
    async def send_text(self, text: str, tools=None) -> str:
        # Send to model
        pass
```

### 2. Register in `providers/registry.py`

---

## Key Architectural Patterns

1. **Provider Router**: Routes requests to optimal provider based on task type
2. **Action Registry**: Discovers and executes actions dynamically
3. **Context Builder**: Assembles context from memory, state, and config
4. **Interface Contracts**: All core modules communicate via standard interfaces

---

## Preserved Components

- `config/vosk_model/` - Speech recognition model (DO NOT MODIFY)

---

## Phase 1 Completion

| Area | Status |
|------|--------|
| Area 1: Memory | ~90% |
| Area 2: Architecture | ~60% |
| Area 3: Multi-Provider | ~80% |
| Area 4: Dynamic Prompting | ~70% |

**Overall Phase 1:** ~70% Complete
