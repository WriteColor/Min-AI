"""
memory/db.py — SQLite Database Layer for MIN Hybrid Memory System
===================================================================
Provides persistent storage with vector embeddings for semantic search,
ACID transactions, and expiration management.

Tables:
  - semantic_memory: Long-term facts about the user
  - episodic_memory: Session interactions and episodes  
  - work_memory: Current conversation context
  - embeddings: Vector embeddings for semantic search
"""

import sqlite3
import json
import uuid
import os
import threading
from datetime import datetime, timezone
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
from contextlib import contextmanager

BASE_DIR = Path(__file__).resolve().parent.parent
DB_PATH = BASE_DIR / "memory" / "min_memory.db"


class MemoryDatabase:
    """
    SQLite database for MIN's hybrid memory system.
    Thread-safe with connection pooling.
    """
    
    _instance: Optional["MemoryDatabase"] = None
    _lock = threading.Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, db_path: Optional[str] = None):
        if self._initialized:
            return
        self._initialized = True
        
        self.db_path = db_path or str(DB_PATH)
        self._conn_pool: Dict[int, sqlite3.Connection] = {}
        self._pool_lock = threading.Lock()
        
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()
    
    def _get_conn(self) -> sqlite3.Connection:
        """Get thread-local connection from pool."""
        thread_id = threading.get_ident()
        with self._pool_lock:
            if thread_id not in self._conn_pool:
                self._conn_pool[thread_id] = sqlite3.connect(
                    self.db_path,
                    check_same_thread=False,
                    timeout=30.0
                )
                self._conn_pool[thread_id].row_factory = sqlite3.Row
            return self._conn_pool[thread_id]
    
    @contextmanager
    def get_connection(self):
        """Context manager for database connections with automatic cleanup."""
        conn = self._get_conn()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
    
    def _init_db(self):
        """Initialize database schema."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS semantic_memory (
                    id TEXT PRIMARY KEY,
                    category TEXT NOT NULL,
                    key TEXT NOT NULL,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0,
                    relevance_score REAL DEFAULT 1.0,
                    expires_at TEXT,
                    source TEXT DEFAULT 'manual',
                    confidence REAL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    embedding_id TEXT,
                    UNIQUE(category, key)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_sessions (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    ended_at TEXT,
                    outcome TEXT,
                    tags TEXT DEFAULT '[]',
                    summary TEXT DEFAULT ''
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_interactions (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    episode_id TEXT,
                    timestamp TEXT NOT NULL,
                    type TEXT NOT NULL,
                    content TEXT NOT NULL,
                    importance REAL DEFAULT 1.0,
                    metadata TEXT DEFAULT '{}',
                    embedding_id TEXT,
                    FOREIGN KEY (session_id) REFERENCES episodic_sessions(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS episodic_episodes (
                    id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    summary TEXT DEFAULT '',
                    tags TEXT DEFAULT '[]',
                    outcome TEXT,
                    parent_episode TEXT,
                    FOREIGN KEY (session_id) REFERENCES episodic_sessions(id)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS work_memory (
                    id TEXT PRIMARY KEY,
                    key TEXT NOT NULL UNIQUE,
                    value TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_accessed TEXT,
                    access_count INTEGER DEFAULT 0,
                    expires_at TEXT,
                    priority INTEGER DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS embeddings (
                    id TEXT PRIMARY KEY,
                    content_hash TEXT NOT NULL,
                    text_content TEXT NOT NULL,
                    vector BLOB NOT NULL,
                    model TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    dimension INTEGER NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_category 
                ON semantic_memory(category)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_key 
                ON semantic_memory(key)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_semantic_embedding 
                ON semantic_memory(embedding_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_episodic_session 
                ON episodic_interactions(session_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_work_key 
                ON work_memory(key)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_embeddings_hash 
                ON embeddings(content_hash)
            """)
    
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    # ── Semantic Memory Operations ──────────────────────────────────────────
    
    def semantic_save(
        self,
        category: str,
        key: str,
        value: str,
        confidence: float = 1.0,
        source: str = "manual",
        expires_at: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_id: Optional[str] = None
    ) -> str:
        """Save or update a semantic memory entry."""
        now = self._now_iso()
        entry_id = f"{category}_{key}"
        metadata_json = json.dumps(metadata or {}, ensure_ascii=False)
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO semantic_memory 
                (id, category, key, value, created_at, updated_at, last_accessed, 
                 access_count, relevance_score, expires_at, source, confidence, metadata, embedding_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(id) DO UPDATE SET
                    value = excluded.value,
                    updated_at = excluded.updated_at,
                    last_accessed = excluded.last_accessed,
                    access_count = access_count + 1,
                    relevance_score = excluded.relevance_score,
                    expires_at = excluded.expires_at,
                    source = excluded.source,
                    confidence = excluded.confidence,
                    metadata = excluded.metadata,
                    embedding_id = excluded.embedding_id
            """, (entry_id, category, key, value, now, now, now, 0, 1.0, expires_at, source, confidence, metadata_json, embedding_id))
            
        return entry_id
    
    def semantic_get(self, category: str, key: str) -> Optional[str]:
        """Get a semantic memory value by category and key."""
        entry_id = f"{category}_{key}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE semantic_memory 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE id = ?
            """, (self._now_iso(), entry_id))
            
            cursor.execute("SELECT value FROM semantic_memory WHERE id = ?", (entry_id,))
            row = cursor.fetchone()
            
        return row["value"] if row else None
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Tuple[str, float]]:
        """Search semantic memory using embeddings (fallback to keyword search)."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, category, key, value,
                       (CASE WHEN value LIKE ? THEN 0.7 ELSE 0.0 END +
                        CASE WHEN key LIKE ? THEN 0.5 ELSE 0.0 END) as score
                FROM semantic_memory
                WHERE value LIKE ? OR key LIKE ?
                ORDER BY score DESC, access_count DESC
                LIMIT ?
            """, (f"%{query}%", f"%{query}%", f"%{query}%", f"%{query}%", top_k))
            
            results = [(row["value"], row["score"]) for row in cursor.fetchall()]
        
        return results
    
    def semantic_get_by_category(self, category: str) -> Dict[str, str]:
        """Get all entries in a category."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, value FROM semantic_memory 
                WHERE category = ?
                ORDER BY relevance_score DESC, access_count DESC
            """, (category,))
            
            return {row["key"]: row["value"] for row in cursor.fetchall()}
    
    def semantic_delete(self, category: str, key: str) -> bool:
        """Delete a semantic memory entry."""
        entry_id = f"{category}_{key}"
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM semantic_memory WHERE id = ?", (entry_id,))
            
        return cursor.rowcount > 0
    
    def semantic_get_all_categories(self) -> List[str]:
        """Get all unique categories in semantic memory."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT DISTINCT category FROM semantic_memory ORDER BY category")
            return [row["category"] for row in cursor.fetchall()]
    
    def semantic_get_context(self, max_entries: int = 20) -> str:
        """Get formatted context string for LLM injection."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT category, key, value FROM semantic_memory
                ORDER BY relevance_score DESC, access_count DESC
                LIMIT ?
            """, (max_entries,))
            
            if not cursor.fetchone():
                return ""
            
            cursor.execute("""
                SELECT category, key, value FROM semantic_memory
                ORDER BY relevance_score DESC, access_count DESC
                LIMIT ?
            """, (max_entries,))
            
            lines = ["[USER MEMORY]"]
            current_cat = None
            for row in cursor.fetchall():
                if row["category"] != current_cat:
                    lines.append(f"\n## {row['category'].upper()}")
                    current_cat = row["category"]
                lines.append(f"- {row['key']}: {row['value']}")
            
            return "\n".join(lines)
    
    def semantic_prune_expired(self) -> int:
        """Remove expired entries from semantic memory."""
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM semantic_memory WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
            
        return cursor.rowcount
    
    def semantic_get_stats(self) -> Dict[str, Any]:
        """Get statistics about semantic memory."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as total FROM semantic_memory")
            total = cursor.fetchone()["total"]
            
            cursor.execute("""
                SELECT category, COUNT(*) as count 
                FROM semantic_memory 
                GROUP BY category
            """)
            by_category = {row["category"]: row["count"] for row in cursor.fetchall()}
            
            cursor.execute("SELECT SUM(access_count) as total_accesses FROM semantic_memory")
            total_accesses = cursor.fetchone()["total_accesses"] or 0
            
            return {
                "total_entries": total,
                "by_category": by_category,
                "total_accesses": total_accesses
            }
    
    # ── Episodic Memory Operations ──────────────────────────────────────────
    
    def episodic_start_session(self, tags: Optional[List[str]] = None) -> str:
        """Start a new episodic session."""
        session_id = str(uuid.uuid4())[:12]
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO episodic_sessions (id, created_at, tags)
                VALUES (?, ?, ?)
            """, (session_id, now, json.dumps(tags or [], ensure_ascii=False)))
        
        return session_id
    
    def episodic_end_session(self, session_id: str, outcome: str = "success") -> None:
        """End an episodic session."""
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE episodic_sessions 
                SET ended_at = ?, outcome = ?
                WHERE id = ?
            """, (now, outcome, session_id))
    
    def episodic_add_interaction(
        self,
        session_id: str,
        interaction_type: str,
        content: str,
        importance: float = 1.0,
        metadata: Optional[Dict[str, Any]] = None,
        embedding_id: Optional[str] = None
    ) -> str:
        """Add an interaction to the current session."""
        interaction_id = str(uuid.uuid4())[:16]
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO episodic_interactions 
                (id, session_id, timestamp, type, content, importance, metadata, embedding_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (interaction_id, session_id, now, interaction_type, content, importance, 
                  json.dumps(metadata or {}, ensure_ascii=False), embedding_id))
        
        return interaction_id
    
    def episodic_start_episode(self, session_id: str, tags: Optional[List[str]] = None) -> str:
        """Start a new episode within a session."""
        episode_id = str(uuid.uuid4())[:12]
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO episodic_episodes (id, session_id, created_at, tags)
                VALUES (?, ?, ?, ?)
            """, (episode_id, session_id, now, json.dumps(tags or [], ensure_ascii=False)))
        
        return episode_id
    
    def episodic_end_episode(self, episode_id: str, outcome: str = "success") -> None:
        """End an episode."""
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE episodic_episodes 
                SET outcome = ?
                WHERE id = ?
            """, (outcome, episode_id))
    
    def episodic_get_recent(self, session_id: str, max_interactions: int = 20) -> str:
        """Get recent interactions formatted for context injection."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT timestamp, type, content 
                FROM episodic_interactions
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, max_interactions))
            
            if not cursor.fetchone():
                return ""
            
            cursor.execute("""
                SELECT timestamp, type, content 
                FROM episodic_interactions
                WHERE session_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
            """, (session_id, max_interactions))
            
            lines = []
            type_labels = {
                "user_text": "Usuario",
                "user_audio": "Usuario [AUDIO]",
                "min_response": "MIN",
                "tool_call": "Herramienta",
                "tool_result": "Resultado",
                "error": "Error",
                "system": "Sistema"
            }
            
            for row in cursor.fetchall():
                label = type_labels.get(row["type"], "?")
                ts = datetime.fromisoformat(row["timestamp"]).strftime("%H:%M:%S")
                lines.append(f"[{ts}] {label}: {row['content'][:300]}")
            
            return "\n".join(lines)
    
    def episodic_get_interaction_count(self, session_id: str) -> int:
        """Get total interaction count for a session."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) as count FROM episodic_interactions WHERE session_id = ?
            """, (session_id,))
            return cursor.fetchone()["count"]
    
    # ── Work Memory Operations ──────────────────────────────────────────────
    
    def work_set(self, key: str, value: str, priority: int = 0, expires_at: Optional[str] = None) -> None:
        """Set a work memory entry."""
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO work_memory (id, key, value, created_at, last_accessed, access_count, expires_at, priority)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    last_accessed = excluded.last_accessed,
                    access_count = access_count + 1,
                    expires_at = excluded.expires_at,
                    priority = excluded.priority
            """, (key, key, value, now, now, 0, expires_at, priority))
    
    def work_get(self, key: str) -> Optional[str]:
        """Get a work memory value."""
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE work_memory 
                SET last_accessed = ?, access_count = access_count + 1
                WHERE key = ?
            """, (now, key))
            
            cursor.execute("SELECT value FROM work_memory WHERE key = ?", (key,))
            row = cursor.fetchone()
            
        return row["value"] if row else None
    
    def work_delete(self, key: str) -> bool:
        """Delete a work memory entry."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_memory WHERE key = ?", (key,))
        return cursor.rowcount > 0
    
    def work_clear_expired(self) -> int:
        """Clear expired work memory entries."""
        now = self._now_iso()
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM work_memory WHERE expires_at IS NOT NULL AND expires_at < ?", (now,))
        return cursor.rowcount
    
    def work_get_all(self) -> Dict[str, str]:
        """Get all work memory entries sorted by priority."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, value FROM work_memory 
                ORDER BY priority DESC, last_accessed DESC
            """)
            return {row["key"]: row["value"] for row in cursor.fetchall()}
    
    # ── Embedding Operations ────────────────────────────────────────────────
    
    def embed_store(
        self,
        text_content: str,
        vector: bytes,
        model: str,
        content_hash: Optional[str] = None
    ) -> str:
        """Store an embedding vector."""
        embed_id = str(uuid.uuid4())[:16]
        now = self._now_iso()
        
        if content_hash is None:
            import hashlib
            content_hash = hashlib.sha256(text_content.encode()).hexdigest()
        
        import numpy as np
        dimension = len(np.frombuffer(vector, dtype=np.float32))
        
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO embeddings (id, content_hash, text_content, vector, model, created_at, dimension)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (embed_id, content_hash, text_content, vector, model, now, dimension))
        
        return embed_id
    
    def embed_get_by_hash(self, content_hash: str) -> Optional[bytes]:
        """Get embedding vector by content hash."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT vector FROM embeddings WHERE content_hash = ?", (content_hash,))
            row = cursor.fetchone()
        return row["vector"] if row else None
    
    def embed_exists(self, content_hash: str) -> bool:
        """Check if embedding exists for content hash."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT 1 FROM embeddings WHERE content_hash = ?", (content_hash,))
            return cursor.fetchone() is not None
    
    # ── Utility Operations ──────────────────────────────────────────────────
    
    def vacuum(self) -> None:
        """Optimize database by vacuuming."""
        with self.get_connection() as conn:
            conn.execute("VACUUM")
    
    def close(self) -> None:
        """Close all connections in the pool."""
        with self._pool_lock:
            for conn in self._conn_pool.values():
                conn.close()
            self._conn_pool.clear()
            MemoryDatabase._instance = None
            self._initialized = False


def get_db() -> MemoryDatabase:
    """Get singleton database instance."""
    return MemoryDatabase()