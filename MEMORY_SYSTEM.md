# JARVIS AI - Memory System

> **Last updated:** 2025-05-31

---

## Overview

JARVIS uses a **three-tier hybrid memory architecture** combining:

1. **Semantic Memory** - Long-term facts, preferences, knowledge
2. **Episodic Memory** - Session interactions, conversations, events
3. **Work Memory** - Short-term cache with TTL

Plus a **JSON-based MemoryManager** for simple key-value storage with generous limits.

---

## Memory Config (`memory/config.py`)

```python
class MemoryConfig:
    DB_PATH: str = "memory/min_memory.db"
    SEMANTIC_MAX_CHARS: int = 50_000      # Per semantic entry
    EPISODIC_MAX_CHARS: int = 50_000     # Per episodic entry
    WORK_MEMORY_TTL_HOURS: int = 1       # Cache expiry
    EMBEDDING_MODEL: str = "all-MiniLM-L6-v2"
    VECTOR_DIMENSION: int = 384
    MAX_SEARCH_RESULTS: int = 10
```

---

## Memory Service (`memory/service.py`)

Main facade class:

```python
class MemoryService:
    def remember(self, category: str, key: str, value: str,
                 importance: float = 0.5, tags: list = None,
                 expires_at: str = None) -> bool
        """Store episodic memory."""

    def recall(self, category: str, key: str) -> Optional[str]
        """Retrieve episodic memory."""

    def search(self, query: str, limit: int = 5) -> list
        """Semantic search across memory."""

    def build_context(self, query: str, limit: int = 5) -> str
        """Build context string for AI prompts."""

    def get_recent(self, limit: int = 10) -> list
        """Get recent memories."""

    def save_semantic(self, category: str, key: str, value: str,
                      confidence: float = 1.0, source: str = "manual") -> bool
        """Store semantic memory (facts, preferences)."""

    def get_similar(self, text: str, limit: int = 5) -> list
        """Find similar semantic memories via embeddings."""
```

---

## Semantic Memory (`memory/semantic/`)

Stores long-term knowledge and facts.

### Schema

```sql
CREATE TABLE semantic_memory (
    id TEXT PRIMARY KEY,
    category TEXT,           -- e.g., "preferences", "facts", "knowledge"
    key TEXT,                -- e.g., "user_name", "coffee_preference"
    value TEXT,              -- The actual stored value
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    last_accessed TIMESTAMP,
    access_count INTEGER DEFAULT 0,
    relevance_score REAL DEFAULT 0.5,
    expires_at TIMESTAMP,    -- NULL = never expires
    source TEXT DEFAULT 'manual',  -- 'manual', 'ai', 'automation'
    confidence REAL DEFAULT 1.0,   -- 0.0-1.0
    metadata TEXT,            -- JSON for extra data
    embedding_id TEXT         -- Reference to vector embedding
);
```

### Categories

| Category | Description | Examples |
|----------|-------------|----------|
| `preferences` | User likes/dislikes | coffee_black=true, favorite_music=rock |
| `facts` | Verified facts | birth_date=1990, city=Buenos Aires |
| `knowledge` | Learned information | project_deadline=May 2025 |
| `habits` | Recurring patterns | always_checks_email=morning |
| `relationships` | People and context | boss_name=Juan, colleague=Maria |

---

## Episodic Memory (`memory/episodic/`)

Stores session interactions and conversation history.

### Tables

```sql
-- Sessions
CREATE TABLE episodic_sessions (
    id TEXT PRIMARY KEY,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    summary TEXT,
    interaction_count INTEGER DEFAULT 0,
    metadata TEXT
);

-- Individual interactions
CREATE TABLE episodic_interactions (
    id TEXT PRIMARY KEY,
    session_id TEXT,
    role TEXT,           -- 'user', 'assistant', 'system'
    content TEXT,
    timestamp TIMESTAMP,
    tokens_used INTEGER,
    metadata TEXT,
    embedding_id TEXT
);

-- Higher-level episodes
CREATE TABLE episodic_episodes (
    id TEXT PRIMARY KEY,
    name TEXT,
    description TEXT,
    started_at TIMESTAMP,
    ended_at TIMESTAMP,
    key_moments TEXT,    -- JSON array
    lessons TEXT,
    metadata TEXT
);
```

### Session Flow

```
User query → New Interaction → Associated with Session
                                        ↓
                              Session can be grouped into
                              Episodes (e.g., "Setup project")
```

---

## Work Memory (`memory/work_memory.py`)

Short-term cache with automatic expiry.

```python
class WorkMemory:
    """In-memory cache with TTL. Singleton."""

    def set(self, key: str, value: str, ttl_seconds: int = 3600) -> None
    def get(self, key: str) -> Optional[str]
    def delete(self, key: str) -> bool
    def cleanup_expired(self) -> int  # Returns count of removed items
    def get_stats(self) -> dict       # {"size": n, "expired": m}
```

**TTL**: Default 1 hour. Items auto-deleted on access if expired.

---

## Vector Store (`memory/vector_store.py`)

Embedding-based similarity search using scikit-learn.

```python
class VectorStore:
    def __init__(self, dimension: int = 384)

    def add(self, doc_id: str, text: str, metadata: dict = None) -> str
        """Add document, returns embedding_id."""

    def search(self, query: str, limit: int = 5) -> list[dict]
        """Find similar documents by text query."""

    def delete(self, doc_id: str) -> bool
    def get(self, doc_id: str) -> dict
    def count(self) -> int
```

**Model**: `all-MiniLM-L6-v2` (sentence-transformers) - 384 dimensions

---

## Hybrid Memory (`memory/hybrid/`)

Unified interface combining all three tiers.

```python
class HybridMemory:
    """Coordinates semantic + episodic + work memory."""

    def store(self, text: str, memory_type: str = "semantic",
              category: str = "general", importance: float = 0.5) -> bool
        """Store to appropriate memory tier."""

    def retrieve(self, query: str, limit: int = 5) -> list
        """Retrieve from all tiers."""

    def build_context(self, query: str, limit: int = 5) -> str
        """Build prompt-ready context string."""

    def get_recent(self, limit: int = 10) -> list
        """Get recent from episodic."""

    def clear_session(self) -> None
        """Clear work memory for new session."""
```

---

## Memory Manager (`memory/memory_manager.py`)

JSON-based simple key-value storage with generous limits.

### Limits

| Setting | Old Value | New Value |
|---------|-----------|-----------|
| `MEMORY_MAX_CHARS` | 4,000 | **150,000** |
| `MAX_VALUE_LENGTH` | 500 | **10,000** |

### Session Memory

Separate storage for temporary session data:

- Directory: `memory/sessions/`
- Limit: 50,000 chars per session
- Auto-loaded on session start

### Public API

```python
# Store
def save_memory(category: str, key: str, value: str,
                persist: bool = True, session_only: bool = False) -> bool

# Retrieve
def load_memory(category: str, key: str) -> Optional[str]

# Search
def search_memory(query: str, limit: int = 5) -> list[dict]

# Recent
def get_recent_memories(limit: int = 10) -> list[dict]

# Delete
def delete_memory(category: str, key: str) -> bool

# All in category
def get_category(category: str) -> dict

# Bulk operations
def get_all_memories() -> dict
def clear_category(category: str) -> bool
def clear_all_memory() -> bool
```

### Storage Location

```
memory/
├── memories.json           # Long-term memory (150K char limit per entry)
├── sessions/               # Session temporary storage
│   └── {session_id}.json  # Per-session data (50K char limit)
├── semantic/              # Semantic memory (SQLite)
├── episodic/              # Episodic memory (SQLite)
└── vectors/               # Vector embeddings
```

---

## Context Building

When AI needs context about the user:

```python
context = memory_service.build_context(
    query="What does the user like for coffee?",
    limit=5
)
# Returns formatted string like:
# "[Memory: preferences/coffee] User drinks coffee black, no sugar."
# "[Memory: habits] User checks email every morning at 8am."
```

---

## Embedding Pipeline

1. Text input
2. `sentence-transformers` (all-MiniLM-L6-v2)
3. 384-dim vector stored in SQLite
4. Cosine similarity search

---

## Importing Memory

```python
from memory import (
    MemoryService,      # Main facade
    HybridMemory,        # Three-tier coordinator
    SemanticMemory,      # Facts/preferences
    EpisodicMemory,      # Sessions/interactions
    WorkMemory,          # Short-term cache
    VectorStore,         # Embeddings
    memory_manager,      # JSON store
    save_memory,
    load_memory,
    search_memory,
    get_recent_memories,
)
```

---

## Database Schema (Full)

```sql
-- Semantic (facts, preferences)
CREATE TABLE semantic_memory (
    id TEXT PRIMARY KEY,
    category TEXT, key TEXT, value TEXT,
    created_at TIMESTAMP, updated_at TIMESTAMP,
    last_accessed TIMESTAMP, access_count INTEGER DEFAULT 0,
    relevance_score REAL DEFAULT 0.5, expires_at TIMESTAMP,
    source TEXT DEFAULT 'manual', confidence REAL DEFAULT 1.0,
    metadata TEXT, embedding_id TEXT
);

-- Episodic sessions
CREATE TABLE episodic_sessions (
    id TEXT PRIMARY KEY, started_at TIMESTAMP, ended_at TIMESTAMP,
    summary TEXT, interaction_count INTEGER DEFAULT 0, metadata TEXT
);

-- Episodic interactions
CREATE TABLE episodic_interactions (
    id TEXT PRIMARY KEY, session_id TEXT,
    role TEXT, content TEXT, timestamp TIMESTAMP,
    tokens_used INTEGER, metadata TEXT, embedding_id TEXT,
    FOREIGN KEY (session_id) REFERENCES episodic_sessions(id)
);

-- Episodic episodes
CREATE TABLE episodic_episodes (
    id TEXT PRIMARY KEY, name TEXT, description TEXT,
    started_at TIMESTAMP, ended_at TIMESTAMP,
    key_moments TEXT, lessons TEXT, metadata TEXT
);

-- Work memory (short-term)
CREATE TABLE work_memory (
    key TEXT PRIMARY KEY,
    value TEXT, created_at TIMESTAMP, expires_at TIMESTAMP
);

-- Vector embeddings
CREATE TABLE embeddings (
    id TEXT PRIMARY KEY, doc_id TEXT, text TEXT,
    vector BLOB, metadata TEXT, created_at TIMESTAMP
);
```
