"""
core/config_manager.py — Centralized Configuration Management
==============================================================
Manages all configuration for MIN AI system.
Handles loading, validation, and persistence of configs.

Author: MIN AI Team
Version: 2.0
"""

import json
import os
import traceback
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field, asdict


BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"


@dataclass
class AppConfig:
    """Main application configuration."""
    # API Keys & Credentials (all AI providers)
    gemini_api_key: str = ""
    openai_api_key: str = ""
    groq_api_key: str = ""
    openrouter_api_key: str = ""
    opencode_api_key: str = ""
    opencode_model: str = "opencodeofficial/qwen2.5-72b-instruct"
    minimax_api_key: str = ""
    pollinations_api_key: str = ""
    nvidia_nim_api_key: str = ""
    ollama_cloud_api_key: str = ""
    compatible_local_openai_api_key: str = ""

    # OAuth
    spotify_client_id: str = ""
    spotify_client_secret: str = ""
    spotify_redirect_uri: str = "http://127.0.0.1:8888/callback"
    
    # Provider settings
    llm_provider: str = "gemini"
    active_provider: str = "gemini"  # Aliased/synced with llm_provider
    active_model: str = "gemini-2.5-flash"
    live_model: str = ""
    vision_model: str = ""
    openrouter_default_model: str = "google/gemini-2.5-flash:free"
    
    # Pollinations.ai settings (image generation)
    pollinations_default_model: str = "flux"
    pollinations_image_width: int = 1024
    pollinations_image_height: int = 1024

    # MiniMax music generation settings
    minimax_music_model: str = "music-2.6"
    minimax_music_output_dir: str = "~/Music/MIN Generated Music"
    minimax_llm_model: str = "MiniMax-M2.7"

    # Ollama Cloud settings (cloud.ollama.com - hosted models)
    ollama_cloud_base_url: str = "https://cloud.ollama.com/v1"
    ollama_cloud_model: str = "nemotron-3-super:cloud"

    # NVIDIA NIM settings (integrate.api.nvidia.com - AI Foundation Models)
    nvidia_nim_base_url: str = "https://integrate.api.nvidia.com/v1"
    nvidia_nim_model: str = "meta/llama-3.1-70b-instruct"

    # Compatible Local LLM settings (OpenAI-compatible local endpoints like Ollama, LM Studio, Jan AI, etc.)
    compatible_local_openai_base_url: str = "http://127.0.0.1:1337/v1"
    compatible_local_openai_model: str = "mistral-7b-instruct"
    compatible_local_openai_reasoning: bool = False

    # Model assignments by task type
    model_assignments: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "general_reasoning": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "vision": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "voice_realtime": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "fast_response": {"provider": "groq", "model": "llama-3.1-8b-instant"},
        "code_generation": {"provider": "openrouter", "model": "google/gemini-2.5-flash:free"},
        "image_generation": {"provider": "pollinations", "model": "flux"},
        "music_generation": {"provider": "minimax", "model": "music-2.6"},
        "local_ai": {"provider": "compatible_local_openai", "model": "mistral-7b-instruct"},
        "minimax_llm": {"provider": "minimax", "model": "MiniMax-M2.7"},
        "ollama_cloud": {"provider": "ollama_cloud", "model": "nemotron-3-super:cloud"},
        "nvidia_nim": {"provider": "nvidia_nim", "model": "meta/llama-3.1-70b-instruct"},
    })
    
    # UI settings
    theme: str = "dark"
    language: str = "es-ES"
    
    # Audio/Voice settings
    voice_enabled: bool = True
    speech_rate: float = 1.0
    min_voice: str = "Aoede"
    voice_preference: str = "AUDIO"  # AUDIO or TEXT — controls Gemini Live response modality
    mic_device: int = 0
    speaker_device: str = ""
    mic_sensitivity: float = 0.003
    
    # Camera settings
    camera_enabled: bool = True
    camera_index: int = 0
    
    # System settings
    gpu_acceleration: bool = True
    max_memory_mb: float = 500.0
    os_system: str = "windows"
    timezone: str = "America/Tegucigalpa"
    
    # Browser settings
    browser_preference: str = "auto"
    browser_paths: Dict[str, str] = field(default_factory=lambda: {
        "chrome": "",
        "brave": "",
        "edge": "",
        "firefox": "",
        "opera": "",
        "opera_gx": "",
        "vivaldi": "",
        "tor": ""
    })
    
    # Location settings
    location_mode: str = "system"
    location_city: str = ""
    location_lat: str = ""
    location_lon: str = ""

    # Behavior settings
    memory_enabled: bool = True
    context_depth: int = 10
    auto_execution: bool = True
    confirmation_required: bool = False
    
    # Paths
    vosk_model_path: str = str(CONFIG_DIR / "vosk_model")
    assets_path: str = str(BASE_DIR / "assets")
    
    # System log/debug
    debug_mode: bool = False
    log_level: str = "INFO"


class ConfigManager:
    """
    Centralized configuration management.
    Singleton pattern for global config access.
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self._config = AppConfig()
        self._loaded = False
        self._config_file = CONFIG_DIR / "config.json"
        self._load()
        self._initialized = True
    
    def _load(self):
        """Load configuration from file."""
        try:
            if self._config_file.exists():
                with open(self._config_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._apply_loaded_config(data)
                self._loaded = True
            else:
                # If config.json doesn't exist, try to load from old app_config.json if exists
                old_file = CONFIG_DIR / "app_config.json"
                if old_file.exists():
                    with open(old_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        self._apply_loaded_config(data)
                    self.save()
                    old_file.unlink()  # Clean up old file
                    self._loaded = True
        except Exception as e:
            print(f"[ConfigManager] Load error: {e}")
            self._loaded = False
    
    def _apply_loaded_config(self, data: Dict):
        """Apply loaded data to config object, keeping active_provider & llm_provider synced."""
        for key, value in data.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
        
        # Keep aliases synchronized
        if "llm_provider" in data and "active_provider" not in data:
            self._config.active_provider = data["llm_provider"]
        elif "active_provider" in data and "llm_provider" not in data:
            self._config.llm_provider = data["active_provider"]
            
        if "active_model" in data and "live_model" not in data:
            self._config.live_model = data["active_model"]
        elif "live_model" in data and "active_model" not in data:
            self._config.active_model = data["live_model"]
    
    def save(self) -> bool:
        """Save current configuration to file."""
        try:
            # Sync properties before saving
            self._config.llm_provider = self._config.active_provider
            self._config.live_model = self._config.active_model
            
            data = asdict(self._config)
            
            # Ensure directory exists
            self._config_file.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self._config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"[ConfigManager] Save error: {e}")
            traceback.print_exc()
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return getattr(self._config, key, default)
    
    def set(self, key: str, value: Any):
        """Set configuration value and persist."""
        if hasattr(self._config, key):
            setattr(self._config, key, value)
            # Sync aliases
            if key == "active_provider":
                self._config.llm_provider = value
            elif key == "llm_provider":
                self._config.active_provider = value
            elif key == "active_model":
                self._config.live_model = value
            elif key == "live_model":
                self._config.active_model = value
                
            self.save()
    
    def get_model_for_task(self, task_type: str) -> Dict[str, str]:
        """
        Get provider/model assignment for a task type.
        
        Args:
            task_type: One of: general_reasoning, vision, voice_realtime,
                     fast_response, code_generation, image_generation
                     
        Returns:
            Dict with 'provider' and 'model' keys
        """
        return self._config.model_assignments.get(task_type, {
            'provider': self._config.active_provider,
            'model': self._config.active_model
        })
    
    def set_model_for_task(self, task_type: str, provider: str, model: str):
        """Set provider/model for a task type."""
        self._config.model_assignments[task_type] = {
            'provider': provider,
            'model': model
        }
        self.save()
    
    @property
    def is_loaded(self) -> bool:
        return self._loaded
    
    def reload(self):
        """Reload configuration from file."""
        self._load()


# Global config instance
import threading

_config_instance = None
_config_lock = threading.Lock()


def get_config_manager() -> ConfigManager:
    """Get global configuration manager."""
    global _config_instance
    if _config_instance is None:
        with _config_lock:
            if _config_instance is None:
                _config_instance = ConfigManager()
    return _config_instance


def get_config() -> AppConfig:
    """Get current application config."""
    return get_config_manager()._config