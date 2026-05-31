# JARVIS AI - Configuration Reference

> **Last updated:** 2025-05-31

---

## Config File Location

- **Runtime**: `config/config.json`
- **Template**: `config/config.example.json`

---

## Full Config Schema

```json
{
  "gemini_api_key": "AIza...",
  "openai_api_key": "sk-...",
  "openrouter_api_key": "sk-or-...",
  "minimax_api_key": "sk-cp-...",
  "ollama_cloud_api_key": "sk-oc-...",
  "nvidia_nim_api_key": "Y BoxerYW...",
  "pollinations_api_key": "",

  "active_provider": "gemini",
  "fallback_provider": "openai",
  "model_assignments": {
    "general_reasoning": {"provider": "gemini", "model": "gemini-2.5-pro"},
    "vision": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "fast_response": {"provider": "groq", "model": "llama-3.1-8b-instant"},
    "minimax_llm": {"provider": "minimax", "model": "MiniMax-M2.7"},
    "ollama_cloud": {"provider": "ollama_cloud", "model": "nemotron-3-super:cloud"},
    "nvidia_nim": {"provider": "nvidia_nim", "model": "meta/llama-3.1-405b-instruct"}
  },

  "voice": {
    "min_voice": "Aoede",
    "speech_rate": "+0%",
    "volume": 1.0,
    "stt_provider": "vosk",
    "stt_model": "vosk-model-small-es-0.3",
    "wake_word": "min",
    "wake_word_path": "models/jarvis_wakeword.ppn",
    "vad_sensitivity": 3,
    "noise_threshold": 0.3,
    "silence_timeout": 3.0
  },

  "video": {
    "capture_method": "mss",
    "quality": 85,
    "max_fps": 30,
    "enable_gpu": true
  },

  "providers": {
    "gemini": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.7,
      "max_tokens": 8192
    },
    "openai": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "openrouter": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "groq": {
      "timeout": 30,
      "max_retries": 3,
      "temperature": 0.6,
      "max_tokens": 4096
    },
    "minimax": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.8,
      "max_tokens": 8192
    },
    "ollama_cloud": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "nvidia_nim": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.7,
      "max_tokens": 4096
    },
    "local": {
      "timeout": 120,
      "max_retries": 1,
      "temperature": 0.7,
      "max_tokens": 2048
    },
    "opencode": {
      "timeout": 60,
      "max_retries": 3,
      "temperature": 0.7,
      "max_tokens": 8192
    }
  },

  "ollama_base_url": "http://127.0.0.1:11434",
  "ollama_cloud_base_url": "https://cloud.ollama.com/v1",
  "nvidia_nim_base_url": "https://integrate.api.nvidia.com/v1",

  "memory": {
    "max_chars": 150000,
    "session_max_chars": 50000,
    "work_memory_ttl_hours": 1
  },

  "paths": {
    "log_dir": "logs",
    "memory_db": "memory/min_memory.db",
    "vector_store": "memory/vectors",
    "session_dir": "memory/sessions"
  },

  "features": {
    "screen_vision": true,
    "voice_control": true,
    "wake_word_detection": true,
    "proactive_monitoring": true
  },

  "polling": {
    "system_monitor_interval": 5.0,
    "screen_observer_interval": 2.0,
    "media_monitor_interval": 1.0
  }
}
```

---

## Voice Settings

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `min_voice` | string | `"Aoede"` | Edge TTS voice name |
| `speech_rate` | string | `"+0%"` | Speech rate adjustment |
| `volume` | float | `1.0` | Output volume (0.0-1.0) |
| `stt_provider` | string | `"vosk"` | Speech-to-text provider |
| `wake_word` | string | `"min"` | Wake word phrase |
| `vad_sensitivity` | int | `3` | Voice activity detection (1-10) |
| `noise_threshold` | float | `0.3` | Background noise threshold |

### Available Voices (Edge TTS)

| Name | Gender | Description |
|------|--------|-------------|
| `Aoede` | Female | English US |
| `Kore` | Male | English US |
| `Leda` | Female | English UK |
| `Zephyr` | Male | English UK |
| `Charon` | Male | English US |
| `Puck` | Male | English US |
| `Fenrir` | Male | English US |
| `Orus` | Male | English US |

---

## Provider Settings

### Timeout Defaults (seconds)

| Provider | Default | Config Field |
|----------|---------|--------------|
| `gemini` | 60 | `providers.gemini.timeout` |
| `openai` | 60 | `providers.openai.timeout` |
| `openrouter` | 60 | `providers.openrouter.timeout` |
| `groq` | 30 | `providers.groq.timeout` |
| `minimax` | 60 | `providers.minimax.timeout` |
| `ollama_cloud` | 60 | `providers.ollama_cloud.timeout` |
| `nvidia_nim` | 60 | `providers.nvidia_nim.timeout` |
| `local` | 120 | `providers.local.timeout` |

### Max Retries

| Provider | Default |
|----------|---------|
| `groq` | 3 |
| `local` | 1 |
| others | 3 |

---

## Memory Settings

| Field | Default | Description |
|-------|---------|-------------|
| `memory.max_chars` | 150,000 | Max chars per entry in JSON memory |
| `memory.session_max_chars` | 50,000 | Max chars per session in session memory |
| `memory.work_memory_ttl_hours` | 1 | TTL for work memory cache |

---

## Paths

| Field | Default | Description |
|-------|---------|-------------|
| `paths.log_dir` | `"logs"` | Log file directory |
| `paths.memory_db` | `"memory/min_memory.db"` | SQLite database path |
| `paths.vector_store` | `"memory/vectors"` | Vector embedding storage |
| `paths.session_dir` | `"memory/sessions"` | Session memory directory |

---

## Environment Variables

These override config.json:

| Variable | Config Field | Description |
|----------|--------------|-------------|
| `GEMINI_API_KEY` | `gemini_api_key` | Gemini API key |
| `OPENAI_API_KEY` | `openai_api_key` | OpenAI API key |
| `OPENROUTER_API_KEY` | `openrouter_api_key` | OpenRouter API key |
| `MINIMAX_API_KEY` | `minimax_api_key` | MiniMax API key |

---

## Ollama Cloud Configuration

```json
{
  "ollama_cloud_api_key": "sk-oc-...",
  "ollama_cloud_base_url": "https://cloud.ollama.com/v1",
  "model_assignments": {
    "ollama_cloud": {
      "provider": "ollama_cloud",
      "model": "nemotron-3-super:cloud"
    }
  }
}
```

---

## NVIDIA NIM Configuration

```json
{
  "nvidia_nim_api_key": "Y BoxerYW...",
  "nvidia_nim_base_url": "https://integrate.api.nvidia.com/v1",
  "model_assignments": {
    "nvidia_nim": {
      "provider": "nvidia_nim",
      "model": "meta/llama-3.1-405b-instruct"
    }
  }
}
```

---

## Local Provider Configuration

```json
{
  "active_provider": "local",
  "ollama_base_url": "http://127.0.0.1:11434",
  "providers": {
    "local": {
      "timeout": 120,
      "max_retries": 1
    }
  }
}
```

Requires Ollama or LM Studio running at `ollama_base_url`.

---

## Example: Multi-Provider Setup

```json
{
  "active_provider": "gemini",
  "fallback_provider": "openai",
  "model_assignments": {
    "vision": {"provider": "gemini", "model": "gemini-2.5-flash"},
    "fast": {"provider": "groq", "model": "llama-3.1-8b-instant"},
    "reasoning": {"provider": "nvidia_nim", "model": "meta/llama-3.1-405b-instruct"},
    "creative": {"provider": "openai", "model": "gpt-4o"}
  }
}
```

---

## Installation Config Template

The `install.py` script generates the initial `config.json` with all fields:

```python
DEFAULT_CONFIG = {
    "gemini_api_key": "",
    "openai_api_key": "",
    "openrouter_api_key": "",
    "minimax_api_key": "",
    "ollama_cloud_api_key": "",
    "nvidia_nim_api_key": "",
    "pollinations_api_key": "",
    "active_provider": "gemini",
    "fallback_provider": "openai",
    "model_assignments": {...},
    "voice": {...},
    "video": {...},
    "providers": {...},
    "ollama_base_url": "http://127.0.0.1:11434",
    "ollama_cloud_base_url": "https://cloud.ollama.com/v1",
    "nvidia_nim_base_url": "https://integrate.api.nvidia.com/v1",
    "memory": {...},
    "paths": {...},
    "features": {...},
    "polling": {...}
}
```
