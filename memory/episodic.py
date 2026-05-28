"""
Episodic Memory Module
=======================
Almacena interacciones de la sesión actual:Commands, respuestas, acciones,
contexto inmediato. Se mantiene en memoria durante la sesión y se
persiste a disco al final para análisis futuro.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime, timezone
from enum import Enum
import json
import uuid


class InteractionType(Enum):
    USER_TEXT = "user_text"
    USER_AUDIO = "user_audio"
    MIN_RESPONSE = "min_response"
    TOOL_CALL = "tool_call"
    TOOL_RESULT = "tool_result"
    ERROR = "error"
    SYSTEM = "system"


@dataclass
class Interaction:
    """Representa una interacción individual en la sesión."""
    id: str
    timestamp: datetime
    type: InteractionType
    content: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    embedding: Optional[List[float]] = None
    importance: float = 1.0  # 0.0 - 1.0
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "timestamp": self.timestamp.isoformat(),
            "type": self.type.value,
            "content": self.content[:2000],  # Truncar contenido largo
            "metadata": self.metadata,
            "importance": self.importance
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "Interaction":
        return cls(
            id=data["id"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            type=InteractionType(data["type"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
            embedding=data.get("embedding"),
            importance=data.get("importance", 1.0)
        )


@dataclass
class Episode:
    """Agrupación de interacciones relacionadas (una tarea/contexto)."""
    id: str
    created_at: datetime
    interactions: List[Interaction] = field(default_factory=list)
    summary: str = ""
    tags: List[str] = field(default_factory=list)
    outcome: Optional[str] = None  # success, partial, failed
    parent_episode: Optional[str] = None
    
    def add_interaction(self, interaction: Interaction):
        self.interactions.append(interaction)
    
    def get_context_window(self, max_interactions: int = 20) -> List[Interaction]:
        """Retorna las últimas N interacciones para contexto."""
        return self.interactions[-max_interactions:]
    
    def summarize(self) -> str:
        """Genera resumen del episodio."""
        if self.summary:
            return self.summary
        
        user_inputs = [i for i in self.interactions if i.type == InteractionType.USER_TEXT]
        tool_calls = [i for i in self.interactions if i.type == InteractionType.TOOL_CALL]
        
        summary = f"Episode con {len(user_inputs)} inputs del usuario y {len(tool_calls)} llamadas a herramientas."
        if self.outcome:
            summary += f" Resultado: {self.outcome}."
        return summary


class EpisodicMemory:
    """
    Memoria episódica - mantiene registro de interacciones actuales.
    Se persiste a disco y permite búsqueda de episodios pasados.
    """
    
    def __init__(self, storage_path: str = "memory/episodic/sessions"):
        self.storage_path = storage_path
        self.current_episode: Optional[Episode] = None
        self.episodes: List[Episode] = []
        self.session_id = str(uuid.uuid4())[:8]
        self.created_at = datetime.now(timezone.utc)
        
    def start_episode(self, tags: Optional[List[str]] = None) -> Episode:
        """Inicia un nuevo episodio."""
        self.current_episode = Episode(
            id=str(uuid.uuid4())[:12],
            created_at=datetime.now(timezone.utc),
            tags=tags or []
        )
        return self.current_episode
    
    def end_episode(self, outcome: str = "success", summary: str = ""):
        """Finaliza el episodio actual."""
        if self.current_episode:
            self.current_episode.outcome = outcome
            self.current_episode.summary = summary or self.current_episode.summarize()
            self.episodes.append(self.current_episode)
            self.current_episode = None
    
    def add_interaction(
        self,
        interaction_type: InteractionType,
        content: str,
        metadata: Optional[Dict[str, Any]] = None,
        importance: float = 1.0
    ) -> Interaction:
        """Agrega una interacción al episodio actual."""
        if self.current_episode is None:
            self.start_episode()
        
        interaction = Interaction(
            id=str(uuid.uuid4())[:16],
            timestamp=datetime.now(timezone.utc),
            type=interaction_type,
            content=content,
            metadata=metadata or {},
            importance=importance
        )
        
        self.current_episode.add_interaction(interaction)
        return interaction
    
    def add_user_input(self, text: str, audio: bool = False) -> Interaction:
        """Shortcut para agregar input del usuario."""
        i_type = InteractionType.USER_AUDIO if audio else InteractionType.USER_TEXT
        return self.add_interaction(i_type, text)
    
    def add_min_response(self, text: str, is_streaming: bool = False) -> Interaction:
        """Agrega respuesta de MIN."""
        return self.add_interaction(
            InteractionType.MIN_RESPONSE,
            text,
            metadata={"streaming": is_streaming}
        )
    
    def add_tool_call(self, tool_name: str, args: Dict[str, Any], result: str = "") -> Interaction:
        """Agrega una llamada a herramienta."""
        content = f"{tool_name}({json.dumps(args, ensure_ascii=False)})"
        if result:
            content += f" -> {result[:200]}"
        return self.add_interaction(
            InteractionType.TOOL_CALL,
            content,
            metadata={"tool_name": tool_name, "args": args, "result": result[:500]}
        )
    
    def get_recent_context(self, max_turns: int = 10) -> str:
        """Genera string de contexto para inyección en prompt."""
        if not self.episodes and not self.current_episode:
            return ""
        
        recent = []
        for ep in self.episodes[-3:]:
            for interaction in ep.get_context_window(max_turns):
                recent.append(interaction)
        
        if self.current_episode:
            for interaction in self.current_episode.get_context_window(max_turns):
                recent.append(interaction)
        
        # Formatear como contexto legible
        lines = []
        for i in recent[-max_turns:]:
            prefix = {
                InteractionType.USER_TEXT: "Usuario",
                InteractionType.USER_AUDIO: "Usuario [AUDIO]",
                InteractionType.MIN_RESPONSE: "MIN",
                InteractionType.TOOL_CALL: "Herramienta",
                InteractionType.TOOL_RESULT: "Resultado",
                InteractionType.ERROR: "Error",
                InteractionType.SYSTEM: "Sistema"
            }.get(i.type, "?")
            lines.append(f"[{i.timestamp.strftime('%H:%M:%S')}] {prefix}: {i.content[:300]}")
        
        return "\n".join(lines)
    
    def get_interaction_count(self) -> int:
        """Cuenta total de interacciones."""
        count = sum(len(ep.interactions) for ep in self.episodes)
        if self.current_episode:
            count += len(self.current_episode.interactions)
        return count
    
    def to_json(self) -> dict:
        """Serializa la memoria episódica."""
        return {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "current_episode": self.current_episode.id if self.current_episode else None,
            "episodes": [
                {
                    "id": ep.id,
                    "created_at": ep.created_at.isoformat(),
                    "summary": ep.summary,
                    "tags": ep.tags,
                    "outcome": ep.outcome,
                    "interaction_count": len(ep.interactions)
                }
                for ep in self.episodes
            ]
        }
    
    def save(self, path: Optional[str] = None) -> str:
        """Persiste la memoria a disco. Retorna la ruta del archivo."""
        import os
        path = path or self.storage_path
        os.makedirs(path, exist_ok=True)
        
        filepath = os.path.join(path, f"session_{self.session_id}.json")
        
        data = {
            "session_id": self.session_id,
            "created_at": self.created_at.isoformat(),
            "episodes": [ep.__dict__ for ep in self.episodes],
            "current_episode_id": self.current_episode.id if self.current_episode else None
        }
        
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        
        return filepath
    
    @classmethod
    def load(cls, session_id: str, storage_path: str = "memory/episodic/sessions") -> "EpisodicMemory":
        """Carga una sesión desde disco."""
        import os
        filepath = os.path.join(storage_path, f"session_{session_id}.json")
        
        if not os.path.exists(filepath):
            return cls(storage_path=storage_path)
        
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        
        memory = cls(storage_path=storage_path)
        memory.session_id = data["session_id"]
        memory.created_at = datetime.fromisoformat(data["created_at"])
        
        for ep_data in data.get("episodes", []):
            ep = Episode(
                id=ep_data["id"],
                created_at=datetime.fromisoformat(ep_data["created_at"]),
                summary=ep_data.get("summary", ""),
                tags=ep_data.get("tags", []),
                outcome=ep_data.get("outcome")
            )
            memory.episodes.append(ep)
        
        return memory