"""
memory/work_memory.py — Work Memory Implementation
====================================================
Short-term, high-priority memory for current context.
Fast access with automatic expiration for temporary data.
"""

from typing import Optional, Dict, Any, List
from datetime import datetime, timezone, timedelta
from dataclasses import dataclass, field
from threading import Lock
import time

from .db import get_db


@dataclass
class WorkEntry:
    """A work memory entry with metadata."""
    key: str
    value: str
    priority: int = 0
    created_at: str = ""
    last_accessed: str = ""
    access_count: int = 0
    expires_at: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.expires_at is None:
            return False
        return datetime.now(timezone.utc).isoformat() > self.expires_at
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "key": self.key,
            "value": self.value,
            "priority": self.priority,
            "created_at": self.created_at,
            "last_accessed": self.last_accessed,
            "access_count": self.access_count,
            "expires_at": self.expires_at,
            "metadata": self.metadata
        }


class WorkMemory:
    """
    High-speed, short-term memory for current task context.
    
    Features:
    - Fast read/write with in-memory cache
    - Priority-based access
    - Automatic expiration
    - Context preservation during sessions
    """
    
    _instance: Optional["WorkMemory"] = None
    _lock = Lock()
    
    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, default_ttl: int = 3600):
        if self._initialized:
            return
        self._initialized = True
        
        self.db = get_db()
        self.default_ttl = default_ttl  # 1 hour default
        self._cache: Dict[str, WorkEntry] = {}
        self._max_cache_size = 100
        self._last_cleanup = time.time()
        self._cleanup_interval = 300  # 5 minutes
    
    def _now_iso(self) -> str:
        return datetime.now(timezone.utc).isoformat()
    
    def _cleanup_expired(self) -> int:
        """Remove expired entries from cache and database."""
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return 0
        
        self._last_cleanup = now
        expired_keys = [
            key for key, entry in self._cache.items()
            if entry.is_expired()
        ]
        
        for key in expired_keys:
            del self._cache[key]
        
        # Also clean database
        count = self.db.work_clear_expired()
        
        return len(expired_keys) + count
    
    def set(
        self,
        key: str,
        value: str,
        priority: int = 0,
        ttl: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Set a work memory entry.
        
        Args:
            key: Entry key
            value: Entry value
            priority: Priority (higher = more important)
            ttl: Time-to-live in seconds
            metadata: Optional metadata
        """
        self._cleanup_expired()
        
        now = self._now_iso()
        expires_at = None
        if ttl is None:
            ttl = self.default_ttl
        if ttl > 0:
            expires_at = (datetime.now(timezone.utc) + timedelta(seconds=ttl)).isoformat()
        
        entry = WorkEntry(
            key=key,
            value=value,
            priority=priority,
            created_at=now,
            last_accessed=now,
            access_count=1,
            expires_at=expires_at,
            metadata=metadata or {}
        )
        
        self._cache[key] = entry
        self.db.work_set(key, value, priority, expires_at)
        
        # Enforce cache size limit
        if len(self._cache) > self._max_cache_size:
            # Remove lowest priority entries
            sorted_entries = sorted(
                self._cache.items(),
                key=lambda x: (x[1].priority, x[1].access_count)
            )
            to_remove = len(self._cache) - self._max_cache_size
            for i in range(to_remove):
                del self._cache[sorted_entries[i][0]]
    
    def get(self, key: str, default: Optional[str] = None) -> Optional[str]:
        """
        Get a work memory entry.
        
        Args:
            key: Entry key
            default: Default value if not found
            
        Returns:
            Value or default
        """
        # Check cache first
        if key in self._cache:
            entry = self._cache[key]
            if not entry.is_expired():
                entry.last_accessed = self._now_iso()
                entry.access_count += 1
                return entry.value
            else:
                del self._cache[key]
                return default
        
        # Check database
        value = self.db.work_get(key)
        if value is not None:
            # Re-cache it
            now = self._now_iso()
            entry = WorkEntry(
                key=key,
                value=value,
                priority=0,
                created_at=now,
                last_accessed=now,
                access_count=1
            )
            self._cache[key] = entry
            return value
        
        return default
    
    def get_or_compute(
        self,
        key: str,
        compute_fn: callable,
        ttl: Optional[int] = None,
        priority: int = 0
    ) -> str:
        """
        Get value or compute if not exists.
        
        Args:
            key: Entry key
            compute_fn: Function to compute value
            ttl: Optional TTL
            priority: Priority level
            
        Returns:
            Computed or cached value
        """
        value = self.get(key)
        if value is None:
            value = compute_fn()
            self.set(key, value, priority, ttl)
        return value
    
    def delete(self, key: str) -> bool:
        """Delete a work memory entry."""
        if key in self._cache:
            del self._cache[key]
        return self.db.work_delete(key)
    
    def clear(self) -> None:
        """Clear all work memory."""
        self._cache.clear()
        self.db.work_clear_expired()
    
    def update_priority(self, key: str, priority: int) -> bool:
        """Update the priority of an entry."""
        if key in self._cache:
            self._cache[key].priority = priority
        
        now = self._now_iso()
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE work_memory SET priority = ? WHERE key = ?
            """, (priority, key))
        
        return cursor.rowcount > 0
    
    def get_all(self, sort_by_priority: bool = True) -> Dict[str, str]:
        """
        Get all work memory entries.
        
        Args:
            sort_by_priority: Sort by priority descending
            
        Returns:
            Dict of key -> value
        """
        self._cleanup_expired()
        
        # Get from database
        db_entries = self.db.work_get_all()
        
        # Filter expired in cache
        valid_cache = {
            k: v for k, v in self._cache.items()
            if not v.is_expired()
        }
        
        # Merge
        result = {**db_entries, **{k: v.value for k, v in valid_cache.items()}}
        
        if sort_by_priority:
            # Get priorities and sort
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT key, priority FROM work_memory")
                priorities = {row["key"]: row["priority"] for row in cursor.fetchall()}
            
            # Add cache priorities
            for k, v in valid_cache.items():
                if k not in priorities:
                    priorities[k] = v.priority
            
            # Sort by priority
            sorted_keys = sorted(priorities.keys(), key=lambda k: priorities[k], reverse=True)
            result = {k: result[k] for k in sorted_keys if k in result}
        
        return result
    
    def get_recent(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get most recently accessed entries.
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of entry dicts sorted by last_accessed
        """
        all_entries = self.get_all(sort_by_priority=False)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT key, value, last_accessed, priority 
                FROM work_memory 
                ORDER BY last_accessed DESC 
                LIMIT ?
            """, (limit,))
            
            results = []
            for row in cursor.fetchall():
                results.append({
                    "key": row["key"],
                    "value": row["value"],
                    "last_accessed": row["last_accessed"],
                    "priority": row["priority"]
                })
        
        return results
    
    def get_context_string(self, max_entries: int = 10) -> str:
        """
        Get work memory as formatted context string.
        
        Args:
            max_entries: Maximum entries to include
            
        Returns:
            Formatted context string
        """
        entries = self.get_recent(max_entries)
        
        if not entries:
            return ""
        
        lines = ["[WORK CONTEXT]"]
        for entry in entries:
            lines.append(f"- {entry['key']}: {entry['value'][:100]}")
        
        return "\n".join(lines)
    
    def keys(self) -> List[str]:
        """Get all work memory keys."""
        return list(self.get_all().keys())
    
    def contains(self, key: str) -> bool:
        """Check if key exists and is not expired."""
        if key in self._cache:
            return not self._cache[key].is_expired()
        return self.db.work_get(key) is not None
    
    def expire_after(self, key: str, seconds: int) -> None:
        """Set entry to expire after given seconds."""
        expires_at = (datetime.now(timezone.utc) + timedelta(seconds=seconds)).isoformat()
        
        if key in self._cache:
            self._cache[key].expires_at = expires_at
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE work_memory SET expires_at = ? WHERE key = ?
            """, (expires_at, key))
    
    def touch(self, key: str) -> bool:
        """Update last accessed time."""
        now = self._now_iso()
        
        if key in self._cache:
            self._cache[key].last_accessed = now
            self._cache[key].access_count += 1
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE work_memory 
                SET last_accessed = ?, access_count = access_count + 1 
                WHERE key = ?
            """, (now, key))
        
        return cursor.rowcount > 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get work memory statistics."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM work_memory")
            total = cursor.fetchone()["count"]
            
            cursor.execute("SELECT SUM(access_count) as total_access FROM work_memory")
            total_access = cursor.fetchone()["total_access"] or 0
            
            cursor.execute("""
                SELECT priority, COUNT(*) as count 
                FROM work_memory 
                GROUP BY priority
            """)
            by_priority = {row["priority"]: row["count"] for row in cursor.fetchall()}
        
        return {
            "total_entries": total,
            "cached_entries": len(self._cache),
            "total_accesses": total_access,
            "by_priority": by_priority
        }


def get_work_memory() -> WorkMemory:
    """Get work memory singleton instance."""
    return WorkMemory()