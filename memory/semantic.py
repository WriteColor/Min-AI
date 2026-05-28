"""
Semantic Memory Module
=======================
Almacena hechos persistentes sobre el usuario: identidad, preferencias,
objetivos, hábitos. Utiliza embeddings para búsqueda semántica.
Se mantiene entre sesiones y se inyecta en el contexto del LLM.
"""

from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime, timezone
from enum import Enum
import json
import os
import numpy as np

# Import vector store if available
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False


class MemoryCategory(Enum):
    IDENTITY = "identity"           # name, age, birthday, city, job, language
    PREFERENCES = "preferences"     # favorite food/color/music/film/game/sport
    PROJECTS = "projects"           # active projects, goals, things being built
    RELATIONSHIPS = "relationships" # friends, family, partner, colleagues
    WISHES = "wishes"               # future plans, things to buy, travel dreams
    HABITS = "habits"               # routines, schedule patterns
    NOTES = "notes"                # anything else worth remembering


@dataclass
class MemoryEntry:
    """Una entrada individual de memoria semántica."""
    id: str
    category: MemoryCategory
    key: str                          # snake_case identifier
    value: str                        # valor stored en inglés
    created_at: datetime
    updated_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    relevance_score: float = 1.0      # 0.0-1.0, para priorizar
    expires_at: Optional[datetime] = None  # None = nunca expira
    source: str = "manual"            # manual, learned, inferred
    confidence: float = 1.0           # 0.0-1.0, qué tan seguro estamos
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "category": self.category.value,
            "key": self.key,
            "value": self.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "last_accessed": self.last_accessed.isoformat() if self.last_accessed else None,
            "access_count": self.access_count,
            "relevance_score": self.relevance_score,
            "expires_at": self.expires_at.isoformat() if self.expires_at else None,
            "source": self.source,
            "confidence": self.confidence,
            "metadata": self.metadata
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(
            id=data["id"],
            category=MemoryCategory(data["category"]),
            key=data["key"],
            value=data["value"],
            created_at=datetime.fromisoformat(data["created_at"]),
            updated_at=datetime.fromisoformat(data["updated_at"]),
            last_accessed=datetime.fromisoformat(data["last_accessed"]) if data.get("last_accessed") else None,
            access_count=data.get("access_count", 0),
            relevance_score=data.get("relevance_score", 1.0),
            expires_at=datetime.fromisoformat(data["expires_at"]) if data.get("expires_at") else None,
            source=data.get("source", "manual"),
            confidence=data.get("confidence", 1.0),
            metadata=data.get("metadata", {})
        )
    
    def is_expired(self) -> bool:
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc) > self.expires_at
    
    def touch(self):
        self.last_accessed = datetime.now(timezone.utc)
        self.access_count += 1
    
    def update_value(self, new_value: str, confidence: float = 1.0):
        self.value = new_value
        self.updated_at = datetime.now(timezone.utc)
        self.confidence = confidence


class SemanticMemory:
    """
    Memoria semántica de largo plazo.
    Permite almacenamiento, búsqueda y recuperación de hechos sobre el usuario.
    """
    
    # Storage paths
    MEMORY_FILE = "memory/semantic/long_term.json"
    INDEX_FILE = "memory/semantic/.index.json"
    VECTORS_FILE = "memory/semantic/.vectors.npz"
    
    def __init__(self, storage_dir: str = "memory/semantic"):
        self.storage_dir = storage_dir
        self.entries: Dict[str, MemoryEntry] = {}
        self._vectorizer = None
        self._vector_matrix = None
        self._keys_list = []
        self._load()
    
    def _load(self):
        """Carga memoria desde disco."""
        os.makedirs(self.storage_dir, exist_ok=True)
        memory_file = os.path.join(self.storage_dir, "long_term.json")
        
        if os.path.exists(memory_file):
            try:
                with open(memory_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                self.entries = {}
                for key, entry_data in data.get("entries", {}).items():
                    entry = MemoryEntry.from_dict(entry_data)
                    if not entry.is_expired():
                        self.entries[key] = entry
                
                print(f"[SemanticMemory] Cargados {len(self.entries)} entries")
            except Exception as e:
                print(f"[SemanticMemory] Error cargando memoria: {e}")
        
        self._rebuild_index()
    
    def _save(self):
        """Persiste memoria a disco."""
        os.makedirs(self.storage_dir, exist_ok=True)
        memory_file = os.path.join(self.storage_dir, "long_term.json")
        
        data = {
            "entries": {key: entry.to_dict() for key, entry in self.entries.items()}
        }
        
        with open(memory_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def _rebuild_index(self):
        """Rebuild el índice de búsqueda."""
        if not HAS_SKLEARN or not self.entries:
            return
        
        try:
            self._keys_list = list(self.entries.keys())
            texts = [self._entry_to_text(e) for e in self.entries.values()]
            
            if texts:
                self._vectorizer = TfidfVectorizer(max_features=500, stop_words="english")
                self._vector_matrix = self._vectorizer.fit_transform(texts)
        except Exception as e:
            print(f"[SemanticMemory] Error rebuilding index: {e}")
    
    def _entry_to_text(self, entry: MemoryEntry) -> str:
        """Convierte una entrada a texto para indexación."""
        return f"{entry.category.value} {entry.key} {entry.value}"
    
    def save(self, category: MemoryCategory, key: str, value: str, 
             confidence: float = 1.0, source: str = "manual",
             expires_at: Optional[datetime] = None) -> MemoryEntry:
        """Guarda o actualiza una entrada de memoria."""
        # Generate stable ID from category + key
        entry_id = f"{category.value}_{key}"
        now = datetime.now(timezone.utc)
        
        if entry_id in self.entries:
            entry = self.entries[entry_id]
            entry.update_value(value, confidence)
            entry.source = source
            if expires_at:
                entry.expires_at = expires_at
        else:
            entry = MemoryEntry(
                id=entry_id,
                category=category,
                key=key,
                value=value,
                created_at=now,
                updated_at=now,
                last_accessed=now,
                access_count=0,
                relevance_score=1.0,
                expires_at=expires_at,
                source=source,
                confidence=confidence
            )
            self.entries[entry_id] = entry
        
        self._save()
        self._rebuild_index()
        
        print(f"[SemanticMemory] Guardado: [{category.value}] {key} = {value}")
        return entry
    
    def get(self, key: str, category: Optional[MemoryCategory] = None) -> Optional[str]:
        """Obtiene el valor de una entrada por key."""
        if category:
            entry_id = f"{category.value}_{key}"
            entry = self.entries.get(entry_id)
        else:
            # Search all categories
            for cat in MemoryCategory:
                entry_id = f"{cat.value}_{key}"
                if entry_id in self.entries:
                    entry = self.entries[entry_id]
                    entry.touch()
                    return entry.value
        
        if entry:
            entry.touch()
            self._save()
            return entry.value
        return None
    
    def get_by_category(self, category: MemoryCategory) -> Dict[str, str]:
        """Obtiene todas las entradas de una categoría."""
        result = {}
        prefix = f"{category.value}_"
        for key, entry in self.entries.items():
            if key.startswith(prefix):
                short_key = key[len(prefix):]
                result[short_key] = entry.value
        return result
    
    def delete(self, key: str, category: Optional[MemoryCategory] = None) -> bool:
        """Elimina una entrada de memoria."""
        if category:
            entry_id = f"{category.value}_{key}"
        else:
            # Find whichever category has this key
            for cat in MemoryCategory:
                entry_id = f"{cat.value}_{key}"
                if entry_id in self.entries:
                    break
            else:
                return False
        
        if entry_id in self.entries:
            del self.entries[entry_id]
            self._save()
            self._rebuild_index()
            return True
        return False
    
    def search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Busca entradas similares a la query usando embeddings."""
        if not HAS_SKLEARN or self._vectorizer is None or not self.entries:
            # Fallback: simple text search
            return self._simple_search(query, top_k)
        
        try:
            query_vec = self._vectorizer.transform([query])
            similarities = cosine_similarity(query_vec, self._vector_matrix)[0]
            
            results = []
            for idx, score in enumerate(similarities):
                if score > 0.1:
                    key = self._keys_list[idx]
                    results.append((self.entries[key].value, score))
            
            results.sort(key=lambda x: x[1], reverse=True)
            return results[:top_k]
        except Exception as e:
            print(f"[SemanticMemory] Search error: {e}")
            return self._simple_search(query, top_k)
    
    def _simple_search(self, query: str, top_k: int) -> List[Tuple[str, float]]:
        """Fallback: búsqueda por texto simple."""
        query_lower = query.lower()
        results = []
        
        for entry in self.entries.values():
            if query_lower in entry.key.lower() or query_lower in entry.value.lower():
                results.append((entry.value, 0.5))
        
        return results[:top_k]
    
    def get_context_for_prompt(self, max_entries: int = 20) -> str:
        """Genera string formateado para inyectar en el prompt del LLM."""
        if not self.entries:
            return ""
        
        # Sort by relevance and recency
        sorted_entries = sorted(
            self.entries.values(),
            key=lambda e: (e.relevance_score * 0.6 + e.access_count * 0.1),
            reverse=True
        )[:max_entries]
        
        lines = ["[USER MEMORY]"]
        
        for cat in MemoryCategory:
            cat_entries = [e for e in sorted_entries if e.category == cat]
            if cat_entries:
                lines.append(f"\n## {cat.value.upper()}")
                for entry in cat_entries:
                    lines.append(f"- {entry.key}: {entry.value}")
        
        return "\n".join(lines)
    
    def learn_from_interaction(self, user_text: str, category: MemoryCategory, 
                              key: str, value: str):
        """Aprende automáticamente de interacciones del usuario."""
        # Only save if confidence is high enough
        self.save(
            category=category,
            key=key,
            value=value,
            confidence=0.8,
            source="learned"
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Retorna estadísticas de la memoria."""
        by_category = {}
        for cat in MemoryCategory:
            count = sum(1 for e in self.entries.values() if e.category == cat)
            by_category[cat.value] = count
        
        return {
            "total_entries": len(self.entries),
            "by_category": by_category,
            "total_accesses": sum(e.access_count for e in self.entries.values())
        }
    
    def prune_expired(self):
        """Elimina entradas expiradas."""
        expired = [k for k, v in self.entries.items() if v.is_expired()]
        for k in expired:
            del self.entries[k]
        
        if expired:
            self._save()
            self._rebuild_index()
            print(f"[SemanticMemory] Eliminadas {len(expired)} entradas expiradas")
        
        return len(expired)