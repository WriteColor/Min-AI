"""
Hybrid Memory System
====================
Coordina todos los subsistemas de memoria:
- EpisodicMemory: interacciones de la sesión actual
- SemanticMemory: hechos persistentes sobre el usuario
- PreferencesMemory: configuraciones y preferencias del usuario
- ContextManager: inyecta contexto dinámico en prompts

Este módulo es el punto de entrada unificado para el sistema de memoria.
"""

from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass
import json
import os

from memory.episodic import EpisodicMemory, Episode, InteractionType
from memory.semantic import SemanticMemory, MemoryCategory


@dataclass
class ContextWindow:
    """Representa el contexto disponible para un prompt."""
    system_prompt: str
    memory_context: str
    episodic_context: str
    preferences: Dict[str, Any]
    recent_history: str
    
    def to_prompt_parts(self) -> List[str]:
        """Convierte a lista de partes para el prompt."""
        parts = []
        if self.system_prompt:
            parts.append(self.system_prompt)
        if self.memory_context:
            parts.append(self.memory_context)
        if self.episodic_context:
            parts.append(f"[RECENT SESSION]\n{self.episodic_context}")
        return parts
    
    def to_combined(self, separator: str = "\n\n") -> str:
        """Combina todos los contextos en un solo string."""
        return separator.join(self.to_prompt_parts())


class HybridMemory:
    """
    Sistema de memoria híbrida que coordina múltiples subsistemas.
    Provee una interfaz unificada para guardar y recuperar contexto.
    """
    
    def __init__(self, base_path: str = "memory"):
        self.base_path = base_path
        
        # Inicializar subsistemas
        self.episodic = EpisodicMemory(storage_path=f"{base_path}/episodic/sessions")
        self.semantic = SemanticMemory(storage_dir=f"{base_path}/semantic")
        
        # Config
        self.max_episodic_turns = 20
        self.max_memory_entries = 30
        self.auto_save_interval = 300  # seconds
        
        # State
        self._session_start = datetime.now(timezone.utc)
        
    def start_session(self, tags: Optional[List[str]] = None):
        """Inicia una nueva sesión de memoria."""
        self.episodic.start_episode(tags=tags)
        self._session_start = datetime.now(timezone.utc)
    
    def end_session(self, outcome: str = "success"):
        """Finaliza la sesión actual y persiste."""
        self.episodic.end_episode(outcome=outcome)
        self.episodic.save()
    
    # ── Episodic Operations ──────────────────────────────────────────────────
    
    def add_user_message(self, text: str, audio: bool = False):
        """Registra un mensaje del usuario."""
        return self.episodic.add_user_input(text, audio=audio)
    
    def add_min_response(self, text: str, is_streaming: bool = False):
        """Registra respuesta de MIN."""
        return self.episodic.add_min_response(text, is_streaming=is_streaming)
    
    def add_tool_use(self, tool_name: str, args: Dict[str, Any], result: str = ""):
        """Registra uso de herramienta."""
        return self.episodic.add_tool_call(tool_name, args, result)
    
    def get_recent_context(self, max_turns: int = 10) -> str:
        """Obtiene contexto de interacciones recientes."""
        return self.episodic.get_recent_context(max_turns=max_turns)
    
    # ── Semantic Memory Operations ─────────────────────────────────────────
    
    def save_fact(self, category: MemoryCategory, key: str, value: str,
                  confidence: float = 1.0, source: str = "manual"):
        """Guarda un hecho sobre el usuario."""
        return self.semantic.save(category, key, value, confidence, source)
    
    def get_fact(self, key: str, category: Optional[MemoryCategory] = None) -> Optional[str]:
        """Recupera un hecho específico."""
        return self.semantic.get(key, category)
    
    def search_memory(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Búsqueda semántica en memoria."""
        return self.semantic.search(query, top_k)
    
    def learn_identity(self, key: str, value: str):
        """Aprende identidad del usuario."""
        self.save_fact(MemoryCategory.IDENTITY, key, value, source="learned")
    
    def learn_preference(self, key: str, value: str):
        """Aprende preferencia del usuario."""
        self.save_fact(MemoryCategory.PREFERENCES, key, value, source="learned")
    
    def learn_project(self, key: str, value: str):
        """Aprende proyecto activo del usuario."""
        self.save_fact(MemoryCategory.PROJECTS, key, value, source="learned")
    
    def learn_habit(self, key: str, value: str):
        """Aprende hábito del usuario."""
        self.save_fact(MemoryCategory.HABITS, key, value, source="learned")
    
    # ── Context Generation ───────────────────────────────────────────────────
    
    def build_context(self, system_prompt: str, 
                      include_episodic: bool = True,
                      include_semantic: bool = True,
                      include_preferences: bool = True) -> ContextWindow:
        """Construye el contexto completo para un prompt."""
        
        # Memory context (semantic)
        memory_context = ""
        if include_semantic:
            memory_context = self.semantic.get_context_for_prompt(self.max_memory_entries)
        
        # Episodic context
        episodic_context = ""
        if include_episodic:
            episodic_context = self.get_recent_context(self.max_episodic_turns)
        
        # Preferences (from semantic)
        preferences = {}
        if include_preferences:
            pref_entries = self.semantic.get_by_category(MemoryCategory.PREFERENCES)
            preferences = pref_entries
        
        # Recent history formatted
        recent_history = self.episodic.get_recent_context(5) if include_episodic else ""
        
        return ContextWindow(
            system_prompt=system_prompt,
            memory_context=memory_context,
            episodic_context=episodic_context,
            preferences=preferences,
            recent_history=recent_history
        )
    
    def format_for_llm(self, system_prompt: str, 
                       include_episodic: bool = True,
                       include_semantic: bool = True) -> str:
        """Formatea todo el contexto como string para inyectar en LLM."""
        ctx = self.build_context(
            system_prompt=system_prompt,
            include_episodic=include_episodic,
            include_semantic=include_semantic
        )
        return ctx.to_combined()
    
    # ── Automatic Learning ──────────────────────────────────────────────────
    
    def auto_learn_from_text(self, text: str):
        """
        Analiza texto del usuario y detecta hechos para guardar.
        Este método puede ser expandido con NLP más sofisticado.
        """
        text_lower = text.lower()
        
        # Simple pattern detection for identity
        name_patterns = [
            ("me llamo ", "name"),
            ("mi nombre es ", "name"),
            ("i am ", "name_en"),
            ("my name is ", "name_en"),
        ]
        
        for pattern, key in name_patterns:
            if pattern in text_lower:
                idx = text_lower.find(pattern) + len(pattern)
                name = text[idx:].split()[0] if idx < len(text) else ""
                if name and len(name) > 1:
                    self.learn_identity(key, name)
        
        # City/work patterns
        if "vivo en" in text_lower or "living in" in text_lower:
            words = text.split()
            for i, w in enumerate(words):
                if w.lower() in ["vivo", "living"] and i + 2 < len(words):
                    city = words[i + 2].rstrip(".,")
                    if city and len(city) > 2:
                        self.learn_identity("city", city)
                        break
    
    # ── Session Statistics ───────────────────────────────────────────────────
    
    def get_session_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de la sesión actual."""
        return {
            "session_id": self.episodic.session_id,
            "session_duration_minutes": (
                datetime.now(timezone.utc) - self._session_start
            ).total_seconds() / 60,
            "interactions": self.episodic.get_interaction_count(),
            "episodes": len(self.episodic.episodes),
            "current_episode": self.episodic.current_episode.id if self.episodic.current_episode else None
        }
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Retorna todas las estadísticas de memoria."""
        return {
            "session": self.get_session_stats(),
            "semantic": self.semantic.get_stats()
        }
    
    # ── Persistence ──────────────────────────────────────────────────────────
    
    def save_all(self):
        """Persiste todos los subsistemas de memoria."""
        self.episodic.save()
        print("[HybridMemory] Memoria persistida")
    
    def prune_expired(self) -> int:
        """Elimina entradas expiradas de todos los subsistemas."""
        return self.semantic.prune_expired()