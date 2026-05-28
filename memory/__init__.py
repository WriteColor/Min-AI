"""
memory/__init__.py — MIN Hybrid Memory System
=============================================
A three-tier memory system combining:
- Semantic Memory: Long-term facts and knowledge
- Episodic Memory: Session interactions and episodes  
- Work Memory: Current conversation context

Usage:
    from memory import get_memory_service, get_db
    
    memory = get_memory_service()
    memory.remember("preferences", "language", "Spanish")
    
    value = memory.recall("preferences", "language")
    
    context = memory.build_system_context()
"""

from .db import get_db, MemoryDatabase
from .service import get_memory_service, MemoryService
from .config import get_config, MemoryConfig, reset_config
from .vector_store import get_vector_store, VectorStore, get_semantic_search, SemanticSearch
from .work_memory import get_work_memory, WorkMemory

__all__ = [
    "get_db",
    "MemoryDatabase",
    "get_memory_service", 
    "MemoryService",
    "get_config",
    "MemoryConfig",
    "reset_config",
    "get_vector_store",
    "VectorStore",
    "get_semantic_search",
    "SemanticSearch",
    "get_work_memory",
    "WorkMemory"
]