"""
memory/service.py — MIN Memory Service Layer
=============================================
High-level memory operations with semantic search,
context management, and LLM integration hooks.
"""

from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timezone
from .db import get_db, MemoryDatabase


class MemoryService:
    """
    High-level service for MIN's hybrid memory system.
    Provides semantic search, context injection, and memory management.
    """
    
    def __init__(self):
        self.db = get_db()
        self._semantic_cache: Dict[str, str] = {}
        self._work_cache: Dict[str, str] = {}
        self._session_id: Optional[str] = None
    
    # ── Session Management ─────────────────────────────────────────────────
    
    def start_session(self, tags: Optional[List[str]] = None) -> str:
        """Start a new episodic session."""
        self._session_id = self.db.episodic_start_session(tags)
        return self._session_id
    
    def end_session(self, outcome: str = "success") -> None:
        """End the current session."""
        if self._session_id:
            self.db.episodic_end_session(self._session_id, outcome)
            self._session_id = None
    
    @property
    def session_id(self) -> Optional[str]:
        return self._session_id
    
    # ── Semantic Memory ────────────────────────────────────────────────────
    
    def remember(
        self,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source: str = "manual",
        ttl_seconds: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Store a fact in semantic memory.
        
        Args:
            category: Memory category (e.g., 'preferences', 'facts', 'relationships')
            key: Unique key within category
            value: The fact to remember
            confidence: Confidence level 0-1
            source: Source of the information
            ttl_seconds: Optional time-to-live in seconds
            metadata: Additional metadata
        """
        expires_at = None
        if ttl_seconds:
            from datetime import timedelta
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl_seconds)).isoformat()
        
        entry_id = self.db.semantic_save(
            category=category,
            key=key,
            value=value,
            confidence=confidence,
            source=source,
            expires_at=expires_at,
            metadata=metadata
        )
        
        self._semantic_cache[f"{category}:{key}"] = value
        return entry_id
    
    def recall(self, category: str, key: str) -> Optional[str]:
        """
        Recall a specific fact from semantic memory.
        
        Args:
            category: Memory category
            key: Fact key
            
        Returns:
            The fact value or None if not found
        """
        cache_key = f"{category}:{key}"
        if cache_key in self._semantic_cache:
            return self._semantic_cache[cache_key]
        
        value = self.db.semantic_get(category, key)
        if value is not None:
            self._semantic_cache[cache_key] = value
        return value
    
    def recall_all(self, category: str) -> Dict[str, str]:
        """Recall all facts in a category."""
        return self.db.semantic_get_by_category(category)
    
    def search_memory(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Search semantic memory for relevant facts.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of (value, score) tuples
        """
        return self.db.semantic_search(query, top_k)
    
    def forget(self, category: str, key: str) -> bool:
        """Remove a fact from semantic memory."""
        cache_key = f"{category}:{key}"
        if cache_key in self._semantic_cache:
            del self._semantic_cache[cache_key]
        return self.db.semantic_delete(category, key)
    
    def get_context(self, max_entries: int = 20) -> str:
        """Get formatted memory context for LLM injection."""
        return self.db.semantic_get_context(max_entries)
    
    def get_categories(self) -> List[str]:
        """Get all semantic memory categories."""
        return self.db.semantic_get_all_categories()
    
    def prune_expired(self) -> int:
        """Remove expired semantic memory entries."""
        count = self.db.semantic_prune_expired()
        self._semantic_cache.clear()
        return count
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        return self.db.semantic_get_stats()
    
    # ── Episodic Memory ────────────────────────────────────────────────────
    
    def log_interaction(
        self,
        interaction_type: str,
        content: str,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Log an interaction to episodic memory.
        
        Args:
            interaction_type: Type of interaction (user_text, min_response, tool_call, etc.)
            content: Interaction content
            importance: Importance score 0-1
            metadata: Additional metadata
        """
        if not self._session_id:
            self.start_session()
        
        return self.db.episodic_add_interaction(
            session_id=self._session_id,
            interaction_type=interaction_type,
            content=content,
            importance=importance,
            metadata=metadata
        )
    
    def log_user_message(self, content: str, importance: float = 1.0) -> str:
        """Log a user message."""
        return self.log_interaction("user_text", content, importance)
    
    def log_min_response(self, content: str, importance: float = 1.0) -> str:
        """Log a MIN response."""
        return self.log_interaction("min_response", content, importance)
    
    def log_tool_use(self, tool_name: str, args: Dict[str, Any], result: str) -> str:
        """Log a tool execution."""
        return self.log_interaction(
            "tool_call",
            f"{tool_name}({args}) -> {result[:200]}",
            importance=0.8,
            metadata={"tool_name": tool_name, "args": args}
        )
    
    def start_episode(self, tags: Optional[List[str]] = None) -> str:
        """Start a new episode within the current session."""
        if not self._session_id:
            self.start_session()
        return self.db.episodic_start_episode(self._session_id, tags)
    
    def end_episode(self, outcome: str = "success") -> None:
        """End the current episode."""
        # Would need to track current episode ID
        pass
    
    def get_recent_context(self, max_interactions: int = 20) -> str:
        """Get recent interactions formatted for context."""
        if not self._session_id:
            return ""
        return self.db.episodic_get_recent(self._session_id, max_interactions)
    
    def get_interaction_count(self) -> int:
        """Get total interactions in current session."""
        if not self._session_id:
            return 0
        return self.db.episodic_get_interaction_count(self._session_id)
    
    # ── Work Memory ────────────────────────────────────────────────────────
    
    def work_set(self, key: str, value: str, priority: int = 0) -> None:
        """Set a work memory value."""
        self.db.work_set(key, value, priority)
        self._work_cache[key] = value
    
    def work_get(self, key: str) -> Optional[str]:
        """Get a work memory value."""
        if key in self._work_cache:
            return self._work_cache[key]
        
        value = self.db.work_get(key)
        if value is not None:
            self._work_cache[key] = value
        return value
    
    def work_delete(self, key: str) -> bool:
        """Delete a work memory entry."""
        if key in self._work_cache:
            del self._work_cache[key]
        return self.db.work_delete(key)
    
    def work_clear_expired(self) -> int:
        """Clear expired work memory entries."""
        count = self.db.work_clear_expired()
        self._work_cache.clear()
        return count
    
    def work_get_all(self) -> Dict[str, str]:
        """Get all work memory entries."""
        return self.db.work_get_all()
    
    # ── Context Building ──────────────────────────────────────────────────
    
    def build_system_context(self) -> str:
        """
        Build the complete system context for LLM injection.
        Combines semantic memory, work memory, and recent interactions.
        """
        parts = []
        
        semantic = self.get_context(max_entries=15)
        if semantic:
            parts.append(semantic)
        
        work = self.work_get_all()
        if work:
            work_lines = ["\n[CURRENT WORK]", *(f"- {k}: {v}" for k, v in work.items())]
            parts.append("\n".join(work_lines))
        
        episodic = self.get_recent_context(max_interactions=10)
        if episodic:
            parts.append(f"\n[RECENT EPISODES]\n{episodic}")
        
        return "\n".join(parts) if parts else ""
    
    # ── Embedding Integration ──────────────────────────────────────────────
    
    def embed_and_store(self, text: str, model: str = "min-embed-v1") -> Optional[str]:
        """
        Create and store an embedding for text.
        This would integrate with an embedding model.
        """
        try:
            import numpy as np
            import hashlib
            
            # Placeholder for actual embedding generation
            # In production, this would call an embedding model API
            vector = np.random.rand(384).astype(np.float32)
            vector_bytes = vector.tobytes()
            
            content_hash = hashlib.sha256(text.encode()).hexdigest()
            
            # Check if embedding already exists
            if self.db.embed_exists(content_hash):
                return None
            
            embed_id = self.db.embed_store(text, vector_bytes, model, content_hash)
            return embed_id
        except Exception:
            return None
    
    def find_similar(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """
        Find similar memories using embeddings.
        Falls back to keyword search if embeddings not available.
        """
        # First try semantic search
        results = self.search_memory(query, top_k)
        if results:
            return results
        
        # Fallback to work memory search
        work = self.work_get_all()
        matches = [(v, 0.5) for k, v in work.items() if query.lower() in v.lower()]
        return matches[:top_k]
    
    # ── Utility ────────────────────────────────────────────────────────────
    
    def clear_all_caches(self) -> None:
        """Clear in-memory caches."""
        self._semantic_cache.clear()
        self._work_cache.clear()
    
    def reset_session(self) -> None:
        """Reset for a new session."""
        self._session_id = None
        self.clear_all_caches()
    
    def vacuum_db(self) -> None:
        """Optimize database storage."""
        self.db.vacuum()


def get_memory_service() -> MemoryService:
    """Get memory service instance."""
    return MemoryService()