"""
core/interfaces.py — Standard Interfaces for Module Communication
============================================================
Defines abstract interfaces for communication between modules.
Ensures loose coupling and high cohesion across the architecture.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Iterator, TypeVar, Generic
from dataclasses import dataclass
from enum import Enum


T = TypeVar('T')


class MemoryInterface(ABC):
    """Interface for memory system operations."""
    
    @abstractmethod
    def get_context(self, query: str, limit: int = 10) -> Dict[str, Any]:
        """Retrieve relevant context from memory."""
        pass
    
    @abstractmethod
    def store_interaction(self, interaction: Dict[str, Any]) -> bool:
        """Store an interaction in episodic memory."""
        pass
    
    @abstractmethod
    def get_episodic_memory(self, session_id: str) -> List[Dict[str, Any]]:
        """Get episodic memory for a session."""
        pass
    
    @abstractmethod
    def get_semantic_memory(self, category: str) -> List[Dict[str, Any]]:
        """Get semantic memory entries by category."""
        pass
    
    @abstractmethod
    def store_fact(self, fact: Dict[str, Any]) -> bool:
        """Store a fact in semantic memory."""
        pass
    
    @abstractmethod
    def search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search memory using semantic similarity."""
        pass


class ProviderInterface(ABC):
    """Interface for AI provider operations."""
    
    @abstractmethod
    def generate(self, prompt: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Generate response from prompt."""
        pass
    
    @abstractmethod
    def generate_streaming(self, prompt: str, config: Dict[str, Any]) -> Iterator[str]:
        """Generate streaming response."""
        pass
    
    @abstractmethod
    def analyze_vision(self, image: bytes, prompt: str) -> Dict[str, Any]:
        """Analyze image with vision capabilities."""
        pass
    
    @abstractmethod
    def generate_speech(self, text: str, voice: str) -> bytes:
        """Generate speech from text."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available models."""
        pass
    
    @abstractmethod
    def validate_config(self) -> bool:
        """Validate provider configuration."""
        pass


class ActionInterface(ABC):
    """Interface for action execution."""
    
    @abstractmethod
    def execute(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Execute an action with parameters."""
        pass
    
    @abstractmethod
    def validate(self, action_name: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Validate action parameters."""
        pass
    
    @abstractmethod
    def get_available_actions(self) -> List[Dict[str, Any]]:
        """Get metadata for all available actions."""
        pass
    
    @abstractmethod
    def get_action_schema(self, action_name: str) -> Optional[Dict[str, Any]]:
        """Get the parameter schema for an action."""
        pass


@dataclass
class ActionResult:
    """Standard action result format."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0
    verified: bool = False
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


@dataclass
class ValidationResult:
    """Standard validation result format."""
    valid: bool
    errors: List[str]
    warnings: List[str]


class ConfigInterface(ABC):
    """Interface for configuration management."""
    
    @abstractmethod
    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        pass
    
    @abstractmethod
    def set(self, key: str, value: Any) -> bool:
        """Set configuration value."""
        pass
    
    @abstractmethod
    def save(self) -> bool:
        """Persist configuration to storage."""
        pass
    
    @abstractmethod
    def reload(self) -> bool:
        """Reload configuration from storage."""
        pass


class WindowManagerInterface(ABC):
    """Interface for window management operations."""
    
    @abstractmethod
    def get_window_info(self, hwnd: int) -> Optional[Dict[str, Any]]:
        """Get information about a window."""
        pass
    
    @abstractmethod
    def list_windows(self) -> List[Dict[str, Any]]:
        """List all visible windows."""
        pass
    
    @abstractmethod
    def bring_to_front(self, hwnd: int) -> bool:
        """Bring window to foreground."""
        pass
    
    @abstractmethod
    def minimize(self, hwnd: int) -> bool:
        """Minimize a window."""
        pass
    
    @abstractmethod
    def maximize(self, hwnd: int) -> bool:
        """Maximize a window."""
        pass
    
    @abstractmethod
    def restore(self, hwnd: int) -> bool:
        """Restore a window."""
        pass
    
    @abstractmethod
    def close(self, hwnd: int) -> bool:
        """Close a window."""
        pass


class FileSystemInterface(ABC):
    """Interface for file operations."""
    
    @abstractmethod
    def read_file(self, path: str, limit: int = 5000) -> ActionResult:
        """Read file contents."""
        pass
    
    @abstractmethod
    def write_file(self, path: str, content: str) -> ActionResult:
        """Write content to file."""
        pass
    
    @abstractmethod
    def delete_file(self, path: str) -> ActionResult:
        """Delete a file."""
        pass
    
    @abstractmethod
    def list_directory(self, path: str, limit: int = 40) -> ActionResult:
        """List directory contents."""
        pass
    
    @abstractmethod
    def create_directory(self, path: str) -> ActionResult:
        """Create a directory."""
        pass
    
    @abstractmethod
    def move_file(self, source: str, destination: str) -> ActionResult:
        """Move a file."""
        pass
    
    @abstractmethod
    def copy_file(self, source: str, destination: str) -> ActionResult:
        """Copy a file."""
        pass


class SearchInterface(ABC):
    """Interface for web search operations."""
    
    @abstractmethod
    def search(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Perform a web search."""
        pass
    
    @abstractmethod
    def get_cached_results(self, query: str) -> Optional[List[Dict[str, Any]]]:
        """Get cached search results."""
        pass


class AudioInterface(ABC):
    """Interface for audio operations."""
    
    @abstractmethod
    def recognize_speech(self, audio: bytes, language: str = "es") -> str:
        """Convert speech to text."""
        pass
    
    @abstractmethod
    def generate_speech(self, text: str, voice: str = "default") -> bytes:
        """Convert text to speech."""
        pass
    
    @abstractmethod
    def get_audio_devices(self) -> List[Dict[str, Any]]:
        """Get list of audio devices."""
        pass
    
    @abstractmethod
    def set_volume(self, level: float) -> bool:
        """Set system volume."""
        pass


class IntentParserInterface(ABC):
    """Interface for intent parsing."""
    
    @abstractmethod
    def parse(self, text: str) -> Dict[str, Any]:
        """Parse user text into structured intent."""
        pass
    
    @abstractmethod
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text."""
        pass
    
    @abstractmethod
    def detect_urgency(self, text: str) -> str:
        """Detect urgency level."""
        pass
