"""
memory/config.py — MIN Memory System Configuration
===================================================
Configurable settings for the hybrid memory system.
"""

from typing import Optional, Dict, Any
from pathlib import Path
import os


class MemoryConfig:
    """
    Configuration for MIN's memory system.
    All settings can be overridden via environment variables.
    """
    
    # Database
    DB_PATH: str = os.environ.get("MIN_DB_PATH", "memory/min_memory.db")
    DB_TIMEOUT: float = 30.0
    
    # Semantic Memory
    SEMANTIC_MAX_CATEGORIES: int = 100
    SEMANTIC_MAX_ENTRIES: int = 10000
    SEMANTIC_DEFAULT_TTL: Optional[int] = 60 * 60 * 24 * 30  # 30 days
    SEMANTIC_PRUNE_INTERVAL: int = 60 * 60  # 1 hour
    SEMANTIC_CONTEXT_MAX_ENTRIES: int = 20
    
    # Episodic Memory
    EPISODIC_MAX_SESSIONS: int = 1000
    EPISODIC_SESSION_TIMEOUT: int = 60 * 60 * 24  # 24 hours
    EPISODIC_MAX_INTERACTIONS_PER_SESSION: int = 1000
    EPISODIC_RECENT_CONTEXT_LIMIT: int = 20
    
    # Work Memory
    WORK_MAX_ENTRIES: int = 100
    WORK_DEFAULT_TTL: int = 60 * 60  # 1 hour
    WORK_HIGH_PRIORITY_THRESHOLD: int = 5
    
    # Embeddings
    EMBED_MODEL: str = os.environ.get("MIN_EMBED_MODEL", "min-embed-v1")
    EMBED_DIMENSION: int = 384
    EMBED_BATCH_SIZE: int = 32
    
    # Memory Management
    AUTO_PRUNE_ON_START: bool = True
    AUTO_VACUUM_INTERVAL: int = 60 * 60 * 24  # 1 day
    CACHE_SIZE: int = 1000
    
    # Context Injection
    CONTEXT_MAX_TOKENS: int = 4000
    CONTEXT_INCLUDE_EPISODIC: bool = True
    CONTEXT_INCLUDE_WORK: bool = True
    CONTEXT_INCLUDE_SEMANTIC: bool = True
    
    def __init__(self, **overrides):
        """
        Initialize config with optional overrides.
        
        Example:
            config = MemoryConfig(SEMANTIC_DEFAULT_TTL=86400)
        """
        for key, value in overrides.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    @classmethod
    def from_env(cls) -> "MemoryConfig":
        """Create config from environment variables."""
        return cls()
    
    def to_dict(self) -> Dict[str, Any]:
        """Export config as dictionary."""
        return {k: v for k, v in self.__dict__.items() if not k.startswith("_")}
    
    @property
    def memory_dir(self) -> Path:
        """Get the memory directory path."""
        base = Path(__file__).resolve().parent.parent
        return base / "memory"
    
    def ensure_directories(self) -> None:
        """Ensure memory directories exist."""
        self.memory_dir.mkdir(parents=True, exist_ok=True)


# Singleton config instance
_config: Optional[MemoryConfig] = None


def get_config(**overrides) -> MemoryConfig:
    """Get or create config singleton with optional overrides."""
    global _config
    if _config is None:
        _config = MemoryConfig(**overrides)
    return _config


def reset_config() -> None:
    """Reset config singleton (mainly for testing)."""
    global _config
    _config = None