"""
core/config_manager.py — Centralized Configuration Management
==============================================================
Manages all configuration for MIN AI system.
Handles loading, validation, and persistence of configs.

Author: MIN AI Team
Version: 1.0
"""

import json
import os
import traceback
from typing import Dict, Any, Optional, List
from pathlib import Path
from dataclasses import dataclass, field


BASE_DIR = Path(__file__).parent.parent
CONFIG_DIR = BASE_DIR / "config"


@dataclass
class AppConfig:
    """Main application configuration."""
    # Provider settings
    active_provider: str = "gemini"
    active_model: str = "gemini-2.5-flash"
    
    # Model assignments by task type
    model_assignments: Dict[str, Dict[str, str]] = field(default_factory=lambda: {
        "general_reasoning": {"provider": "gemini", "model": "gemini-2.5-pro"},
        "vision": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "voice_realtime": {"provider": "gemini", "model": "gemini-2.5-flash"},
        "fast_response": {"provider": "groq", "model": "llama-3.1-8b-instant"},
        "code_generation": {"provider": "openrouter", "model": "openai/gpt-4o"},
    })
    
    # UI settings
    theme: str = "dark"
    language: str = "es"
    voice_enabled: bool = True
    speech_rate: float = 1.0
    
    # Behavior settings
    memory_enabled: bool = True
    context_depth: int = 10
    auto_execution: bool = True
    confirmation_required: bool = False
    
    # Paths
    vosk_model_path: str = str(CONFIG_DIR / "vosk_model")
    assets_path: str = str(BASE_DIR / "assets")
    
    # System
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
        self._config_file = CONFIG_DIR / "app_config.json"
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
        except Exception as e:
            print(f"[ConfigManager] Load error: {e}")
            self._loaded = False
    
    def _apply_loaded_config(self, data: Dict):
        """Apply loaded data to config object."""
        for key, value in data.items():
            if hasattr(self._config, key):
                setattr(self._config, key, value)
    
    def save(self) -> bool:
        """Save current configuration to file."""
        try:
            data = {
                'active_provider': self._config.active_provider,
                'active_model': self._config.active_model,
                'model_assignments': self._config.model_assignments,
                'theme': self._config.theme,
                'language': self._config.language,
                'voice_enabled': self._config.voice_enabled,
                'speech_rate': self._config.speech_rate,
                'memory_enabled': self._config.memory_enabled,
                'context_depth': self._config.context_depth,
                'auto_execution': self._config.auto_execution,
                'confirmation_required': self._config.confirmation_required,
                'vosk_model_path': self._config.vosk_model_path,
                'assets_path': self._config.assets_path,
                'debug_mode': self._config.debug_mode,
                'log_level': self._config.log_level,
            }
            
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
_config_instance = None


def get_config_manager() -> ConfigManager:
    """Get global configuration manager."""
    global _config_instance
    if _config_instance is None:
        _config_instance = ConfigManager()
    return _config_instance


def get_config() -> AppConfig:
    """Get current application config."""
    return get_config_manager()._config