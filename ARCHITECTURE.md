# JARVIS AI - Architecture Guide

> **Last updated:** 2025-05-31
> **Version:** 2.0
> **Status:** Production

---

## Project Overview

JARVIS AI is a comprehensive desktop AI assistant with voice interaction, system control, and automation capabilities. Built with Python for backend, React/TypeScript for frontend, and Tauri for desktop integration.

---

## Directory Structure

```
C:\React-Nextjs-Projects\Jarvis AI\
├── main.py                     # Application entry point
├── ui.py                       # WebSocket UI server (Tauri bridge)
├── install.py                   # Installation wizard
├── requirements.txt             # Python dependencies
│
├── core/                       # Core system modules
│   ├── __init__.py
│   ├── interfaces.py           # Abstract interfaces (MemoryInterface, ProviderInterface, etc.)
│   ├── system_prompts.py      # Centralized AI prompts
│   ├── agent.py                # MINAgent orchestration
│   ├── config_manager.py       # Configuration management (AppConfig singleton)
│   ├── state_manager.py        # Application state with snapshots
│   ├── provider_router.py       # Intelligent model routing
│   ├── context_builder.py      # Context assembly
│   ├── prompt_builder.py       # Dynamic prompt construction
│   ├── response_generator.py    # Response formatting
│   ├── intent_parser.py       # Intent detection
│   ├── action_registry.py      # Action catalog with metadata
│   ├── action_executor.py      # Action execution engine
│   ├── parameter_validator.py   # Input validation
│   └── tool_schemas.py        # TOOL_DECLARATIONS for AI
│
├── actions/                    # Action modules
│   ├── system/                # OS control
│   │   ├── open_app.py        # Application launcher
│   │   ├── computer_control.py # Keyboard/mouse control
│   │   ├── computer_settings.py # Volume, brightness, dark mode
│   │   ├── desktop.py         # Wallpaper, organize, stats
│   │   ├── terminal_agent.py  # Secure command execution
│   │   ├── native_ui.py       # Windows UI Automation
│   │   ├── system_monitor.py  # CPU, RAM, GPU monitoring
│   │   ├── accessibility.py   # Eye tracking, micro-movement
│   │   ├── accessibility_overlay.py
│   │   ├── windows_settings.py # Date/time settings
│   │   ├── screen_reader.py   # AI screen reader
│   │   └── git_control.py     # Git integration
│   ├── automation/            # High-level automation
│   │   ├── weather_report.py  # Weather via Open-Meteo
│   │   ├── google_drive.py   # Google Drive sync
│   │   ├── gmail_control.py   # Gmail integration
│   │   ├── whatsapp.py        # WhatsApp automation
│   │   ├── unified_communications.py # Multi-platform messaging
│   │   ├── goals.py          # Goal tracking system
│   │   ├── morning_brief.py   # Daily briefing
│   │   ├── reminder.py        # Timed reminders
│   │   ├── scheduler.py       # Task scheduling
│   │   ├── rules_engine.py    # Phrase-based automation
│   │   ├── proactive_automation.py # System trigger rules
│   │   ├── user_profile.py    # Habit recorder
│   │   ├── contextual_control.py # Context-aware settings
│   │   ├── google_maps.py      # Navigation
│   │   ├── self_edit.py       # Self-code editing
│   │   ├── tool_creator.py     # Dynamic tool creation
│   │   ├── auto_programmer.py # Autonomous programming
│   │   ├── knowledge_base.py  # Local KB
│   │   ├── smart_home.py       # Smart home control
│   │   ├── social_media.py     # Social media
│   │   ├── flight_finder.py    # Flight search
│   │   ├── codebase.py         # Codebase analysis
│   │   └──arca_invoice.py     # Argentine invoicing
│   ├── web/                    # Browser and web
│   │   ├── web_search.py      # Web search
│   │   ├── browser_registry.py # Browser detection/launching
│   │   ├── browser_control.py # Tab/URL control
│   │   ├── web_navigation.py # YouTube, Google
│   │   └── _browser_launch.py  # Thin launcher
│   ├── vision/                  # Computer vision
│   │   ├── screen_vision.py   # Screen analysis (multi-provider)
│   │   ├── visual_click.py    # AI coordinate clicking
│   │   ├── vision_guardian.py # Proactive monitoring
│   │   ├── image_generation.py # AI image generation
│   │   └── screen_process.py  # Screen capture
│   ├── media/                  # Media control
│   │   ├── spotify_control.py # Spotify control
│   │   ├── youtube_video.py   # YouTube control
│   │   ├── media_control.py   # System media keys
│   │   ├── camera_bus.py      # Camera control
│   │   └── tiktok_analyzer.py
│   ├── files/                  # File operations
│   │   ├── file_controller.py # CRUD operations
│   │   ├── smart_file_organizer.py # Auto-organization
│   │   ├── document_creator.py # Word/Excel creation
│   │   └── document_manager.py
│   ├── utils/                  # Utilities
│   │   └── openrouter_agent.py
│   └── music/                  # Music generation
│       └── music_control.py
│
├── providers/                  # AI provider abstraction
│   ├── __init__.py
│   ├── base.py                # BaseProvider, MultimodalProvider, LocalProvider
│   ├── registry.py            # ProviderRegistry, ProviderManager
│   ├── model_selector.py     # Model compatibility validation
│   ├── gemini_provider.py    # Google Gemini
│   ├── openai_provider.py     # OpenAI GPT-4o
│   ├── openrouter_provider.py # OpenRouter (multi-provider)
│   ├── groq_provider.py       # Groq (ultra-low latency)
│   ├── local_provider.py     # Ollama / LM Studio
│   ├── minimax_provider.py   # MiniMax M2.7
│   ├── ollama_cloud_provider.py # Ollama Cloud
│   ├── nvidia_nim_provider.py # NVIDIA NIM
│   └── opencode_provider.py   # OpenCode.ai
│
├── services/                   # Platform services
│   ├── _core/
│   │   ├── helpers.py       # Shared utilities
│   │   └── phrase_triggers.py # Phrase automation
│   ├── ai/
│   │   ├── llm.py           # Generic LLM consumer
│   │   ├── local_ai_detector.py # Ollama/LM Studio detection
│   │   ├── music_generator.py # MiniMax music
│   │   └── image_generator.py # Pollinations.ai images
│   ├── providers/
│   │   ├── search_service.py # High-level search
│   │   ├── search_provider.py # Provider factory
│   │   └── duckduckgo_provider.py
│   ├── session/
│   │   ├── session_builder.py # Gemini LiveConnect config
│   │   └── ui_action_logger.py # UI action logging
│   ├── system/
│   │   ├── windows_api.py   # Windows integration
│   │   ├── stability_monitor.py # RAM monitor
│   │   ├── media_monitor.py  # Media detection
│   │   └── screen_observer.py # Screen monitoring
│   ├── audio/
│   │   ├── service.py       # Main audio pipeline
│   │   ├── pipeline.py       # VAD + wake word + STT + TTS
│   │   ├── tts_service.py    # Edge-TTS service
│   │   ├── tts.py           # Low-level TTS
│   │   ├── stt.py           # Vosk/Whisper STT
│   │   ├── wake_word.py     # Wake word detection
│   │   └── vad.py           # Voice activity detection
│   └── vision/
│       └── gesture_controller.py # MediaPipe hand tracking
│
├── memory/                     # Memory subsystem
│   ├── __init__.py           # Public exports
│   ├── config.py             # MemoryConfig
│   ├── db.py                 # SQLite layer
│   ├── service.py            # MemoryService facade
│   ├── memory_manager.py     # JSON long-term memory
│   ├── work_memory.py        # Short-term cache
│   ├── vector_store.py       # Embeddings
│   ├── semantic/             # Facts/preferences
│   │   └── semantic.py       # SemanticMemory
│   ├── episodic/             # Session interactions
│   │   └── episodic.py       # EpisodicMemory
│   └── hybrid/               # Unified system
│       └── hybrid.py         # HybridMemory
│
├── config/                    # Configuration files
│   ├── config.json          # Runtime config (API keys, etc.)
│   ├── config.example.json   # Template
│   ├── accessibility_config.json
│   ├── app_registry.json    # App paths cache
│   ├── favorites.json
│   ├── goals.json
│   ├── morning_brief_state.json
│   ├── routines.json
│   ├── rules.json           # Automation rules
│   ├── user_profile.json
│   ├── vision_guardian_state.json
│   └── vosk_model/         # Spanish Vosk model
│
├── assets/                    # Static resources
│   └── min_icono.ico
│
├── logs/                      # Runtime logs
│   ├── ui_actions/
│   ├── screen_observer/
│   └── music_generation/
│
├── Min-UI/                   # Frontend (React/TypeScript)
│   ├── src/
│   │   ├── app/            # Next.js app
│   │   ├── components/      # UI components
│   │   │   ├── SettingsDialog.tsx
│   │   │   ├── ControlBar.tsx
│   │   │   ├── Orb.tsx
│   │   │   └── widgets/
│   │   ├── hooks/          # Custom hooks
│   │   └── types/          # TypeScript types
│   └── package.json
│
├── tests/                     # Test suite
│   ├── test_01_startup.py
│   ├── test_02_voice.py
│   ├── test_03_provider.py
│   ├── test_04_memory.py
│   ├── test_05_recycle_bin.py
│   ├── test_memory_extreme.py
│   └── README.md
│
└── utils/                     # Utilities
```

---

## Core Architecture

### Provider Abstraction Layer (`providers/`)

JARVIS uses a provider abstraction to switch between AI backends:

```
┌─────────────────────────────────────────────┐
│              Application Code                │
└──────────────────┬────────────────────────┘
                   │ uses UnifiedProvider
┌──────────────────▼────────────────────────┐
│          providers/registry.py             │
│         ProviderRegistry singleton         │
│    register(), create_provider(),         │
│    get_provider(), set_active_provider() │
└──────────────────┬────────────────────────┘
                   │
     ┌─────────────┼─────────────┐
     ▼             ▼             ▼
┌─────────┐  ┌──────────┐  ┌──────────┐
│ Gemini  │  │ OpenAI   │  │ Groq     │
│Provider │  │ Provider │  │ Provider │
└─────────┘  └──────────┘  └──────────┘
     │             │             │
     └─────────────┼─────────────┘
                   ▼
          BaseProvider (interface)
```

### Supported Providers

| Provider | Key Models | Capabilities |
|----------|-----------|--------------|
| `gemini` | gemini-2.5-flash, gemini-2.5-pro | TEXT, AUDIO_INPUT, VISION, TOOL_CALL, STREAMING |
| `openai` | gpt-4o, gpt-4-turbo | TEXT, AUDIO_INPUT, VISION, TOOL_CALL, STREAMING |
| `openrouter` | claude-3.5-sonnet, gpt-4o-mini | TEXT, VISION, TOOL_CALL, STREAMING |
| `groq` | llama-3.1-70b-versatile | TEXT, TOOL_CALL, STREAMING |
| `minimax` | MiniMax-M2.7 (204.8K context) | TEXT, STREAMING, REASONING |
| `ollama_cloud` | nemotron-3-super, gemma4-31b | TEXT, STREAMING |
| `nvidia_nim` | llama-3.1-405b-instruct | TEXT, TOOL_CALL, STREAMING |
| `local` | Ollama/LM Studio models | TEXT, STREAMING |
| `opencode` | qwen2.5-72b, deepseek-v3 | TEXT, STREAMING, REASONING |

### Memory Architecture (`memory/`)

Three-tier hybrid memory system:

```
┌────────────────────────────────────────────────────────┐
│                   HybridMemory                         │
│  (Coordinates Semantic + Episodic + Work Memory)      │
└──────────────────────┬────────────────────────────────┘
                       │
     ┌─────────────────┼─────────────────┐
     ▼                 ▼                 ▼
┌───────────┐   ┌───────────┐    ┌───────────┐
│ Semantic  │   │ Episodic  │    │   Work    │
│ Memory    │   │ Memory    │    │  Memory   │
│           │   │           │    │           │
│ Long-term │   │ Session   │    │ Short-term│
│ facts,    │   │ inter-    │    │  cache    │
│ preferences│   │ actions   │    │ 1hr TTL   │
└───────────┘   └───────────┘    └───────────┘
```

Additionally, `memory_manager.py` provides JSON-based long-term storage:
- Notes, habits, preferences, context, conversations
- 150,000 char limit
- Session-based temporary memory with 50,000 char limit
- Timestamp tracking on all entries
- Search and retrieval functions

### Audio Pipeline (`services/audio/`)

```
┌─────────────────────────────────────────────────────────┐
│                    AudioService                         │
│  (Coordinates send_realtime, listen_audio,           │
│   receive_audio, play_audio)                           │
└──────────────────────┬────────────────────────────────┘
                       │
         ┌─────────────┼─────────────┐
         ▼             ▼             ▼
    ┌─────────┐  ┌──────────┐  ┌─────────┐
    │   VAD   │  │Wake Word │  │   STT   │
    │(energy) │  │  (Vosk)  │  │(Vosk/Whisper)│
    └─────────┘  └──────────┘  └─────────┘
         │             │             │
         └─────────────┼─────────────┘
                       ▼
                  ┌────────┐
                  │  TTS   │
                  │(Edge) │
                  └────────┘
```

### Action System (`actions/`)

All actions follow a consistent interface:
- Named function `action_name(parameters, player=None) -> str`
- Registered in `TOOL_DECLARATIONS` for AI tool calling
- Security validation for destructive operations
- Parameter schema validation via `ParameterValidator`

---

## Key Design Patterns

1. **Singleton Pattern**: ConfigManager, MemoryDatabase, ProviderRegistry, WorkMemory
2. **Factory Pattern**: ProviderRegistry.create_provider(), SearchProviderFactory
3. **Facade Pattern**: MemoryService, HybridMemory, SessionBuilder
4. **Observer Pattern**: StateManager subscriptions, phrase triggers
5. **Strategy Pattern**: ProviderRouter.get_compatible_providers(), ModelSelector

---

## Data Flow: Voice Command

```
User speaks → Microphone → VAD (energy detection)
  → Wake word "MIN" (Vosk)
  → STT (Vosk/Whisper)
  → Gemini Live API (send_realtime)
  → AI processes with tools
  → Response streams back
  → TTS (Edge TTS) speaks
  → Tool calls execute via ActionExecutor
  → UI updates via WebSocket broadcast
```

---

## Security Architecture

| Layer | Component | Protection |
|-------|-----------|------------|
| 1 | `core/prompt.txt` | Prohibits destructive commands |
| 2 | `actions/terminal_agent.py` | 29 regex patterns + directory restrictions |
| 3 | `actions/self_edit.py` | Protected file list + syntax validation + backups |
| 4 | `ParameterValidator` | Type/range/enum validation before execution |
| 5 | Security audit logging | `logs/security_audit.log` |

---

## Configuration

All configuration via `config/config.json`:

**API Keys**: gemini_api_key, openrouter_api_key, minimax_api_key, ollama_cloud_api_key, nvidia_nim_api_key, pollinations_api_key

**Model Assignments** (task routing):
```json
"model_assignments": {
    "general_reasoning": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "vision": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "fast_response": {"provider": "groq", "model": "llama-3.1-8b-instant"},
    "minimax_llm": {"provider": "minimax", "model": "MiniMax-M2.7"},
    "ollama_cloud": {"provider": "ollama_cloud", "model": "nemotron-3-super:cloud"},
    "nvidia_nim": {"provider": "nvidia_nim", "model": "meta/llama-3.1-405b-instruct"}
}
```

**Voice Settings**: min_voice (8 voices: Aoede, Kore, Leda, Zephyr, Charon, Puck, Fenrir, Orus), speech_rate

---

## Frontend (Min-UI)

Built with:
- **Next.js** - React framework
- **TypeScript** - Type safety
- **Tailwind CSS** - Styling
- **Radix UI** - Accessible primitives
- **Three.js** - 3D Orb animation

Key components:
- `SettingsDialog.tsx` - 6-provider model selector, API key configuration
- `ControlBar.tsx` - Minimal auto-hide control bar
- `Orb.tsx` - 3D reactive orb (listening/speaking states)
- Widgets: Weather, Clock, Music, Tasks, Favorites

---

## Database Schema

SQLite at `memory/min_memory.db`:

```sql
-- Semantic memory (facts, preferences)
CREATE TABLE semantic_memory (
    id TEXT PRIMARY KEY,
    category TEXT,
    key TEXT,
    value TEXT,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    relevance_score REAL DEFAULT 0.5,
    expires_at TIMESTAMP,
    source TEXT DEFAULT 'manual',
    confidence REAL DEFAULT 1.0,
    metadata TEXT,
    embedding_id TEXT
);

-- Episodic memory (session interactions)
CREATE TABLE episodic_sessions (...);
CREATE TABLE episodic_interactions (...);
CREATE TABLE episodic_episodes (...);

-- Work memory (short-term cache)
CREATE TABLE work_memory (...);

-- Vector embeddings
CREATE TABLE embeddings (...);
```

---

## Tool Schemas

50+ tools declared in `TOOL_DECLARATIONS` for AI tool calling:

| Category | Tools |
|----------|-------|
| System | computer_control, terminal_agent, sleep_mode, shutdown_min |
| Window | restore/minimize/maximize/close_window |
| Apps | open_app, close_app |
| Files | file_controller, smart_file_organizer |
| Media | spotify_control, media_control, youtube_video |
| Vision | screen_vision, visual_click, image_generation |
| Web | web_search, browser_control, web_navigation |
| Automation | weather_report, reminder, scheduler, gmail_control |
| Memory | knowledge_base, save_memory |

---

## Extension Points

### Adding a New Provider

1. Create `providers/my_provider.py` extending `MultimodalProvider`
2. Define `MODEL_MAP` dict with model IDs
3. Implement required methods: `connect()`, `send_text()`, `list_models()`, etc.
4. Call `register_provider("my_provider", MyProviderProvider)` at module load
5. Add to `Min-UI/types/index.ts` settings

### Adding a New Action

1. Create `actions/category/my_action.py`
2. Define function `my_action(parameters, player=None) -> str`
3. Add TOOL_DECLARATIONS entry in `core/tool_schemas.py`
4. Register handler in `core/action_registry.py`

### Adding Memory Integration

1. Use `MemoryService.remember(category, key, value)` to store
2. Use `MemoryService.recall(category, key)` to retrieve
3. Use `HybridMemory.build_context()` to inject into prompts

---

## Dependencies

**Core**: google-generativeai, openai, groq, anthropic
**Audio**: edge-tts, sounddevice, vosk, whisper
**Vision**: opencv-python, mediapipe, mss, PIL
**System**: psutil, pywinauto, pycaw, pyautogui, win32gui
**Web**: requests, beautifulsoup4
**Memory**: sqlite3, numpy, scikit-learn
**UI**: tauri, next-js, react, three-js

---

## Glossary

| Term | Definition |
|------|------------|
| VAD | Voice Activity Detection - energy-based speech detection |
| Wake Word | "MIN" trigger phrase for voice activation |
| TOOL_DECLARATIONS | Schema definitions for AI function calling |
| ProviderRouter | Routes requests to appropriate AI models |
| HybridMemory | Three-tier memory: semantic + episodic + work |
| SessionBuilder | Builds Gemini LiveConnectConfig |
| Pollinations.ai | Free AI image generation service |
| Edge TTS | Microsoft Edge text-to-speech engine |
| MediaPipe | Google's hand tracking/gesture recognition |
