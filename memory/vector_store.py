"""
memory/vector_store.py — Vector Store for Semantic Search
=========================================================
Provides embedding storage and similarity search capabilities.
Supports OpenAI embeddings, local embeddings (Ollama), and 
numpy-based vector operations for semantic memory retrieval.
"""

import hashlib
import json
import numpy as np
from typing import Optional, List, Tuple, Dict, Any
from datetime import datetime, timezone
from pathlib import Path

from .db import get_db


class VectorStore:
    """
    Vector store for semantic similarity search.
    Uses SQLite for metadata and numpy arrays for vectors.
    """
    
    def __init__(self, dimension: int = 384, model: str = "min-embed-v1"):
        self.db = get_db()
        self.dimension = dimension
        self.model = model
        self._cache: Dict[str, np.ndarray] = {}
        self._cache_size = 1000
    
    def _normalize(self, vector: np.ndarray) -> np.ndarray:
        """Normalize vector to unit length for cosine similarity."""
        norm = np.linalg.norm(vector)
        if norm == 0:
            return vector
        return vector / norm
    
    def _cosine_similarity(self, a: np.ndarray, b: np.ndarray) -> float:
        """Calculate cosine similarity between two vectors."""
        return float(np.dot(self._normalize(a), self._normalize(b)))
    
    def generate_embedding(self, text: str) -> np.ndarray:
        """
        Generate embedding for text.
        In production, this would call an embedding model API.
        
        Args:
            text: Text to embed
            
        Returns:
            Numpy array of embedding vector
        """
        # Placeholder implementation
        # In production, integrate with OpenAI, Ollama, or other embedding providers
        
        import hashlib
        seed = int(hashlib.md5(text.encode()).hexdigest()[:8], 16) % (2**32)
        rng = np.random.RandomState(seed)
        vector = rng.randn(self.dimension).astype(np.float32)
        
        return self._normalize(vector)
    
    def store(
        self,
        text: str,
        metadata: Optional[Dict[str, Any]] = None,
        content_hash: Optional[str] = None
    ) -> str:
        """
        Store an embedding with its text content.
        
        Args:
            text: Text content
            metadata: Optional metadata dict
            content_hash: Optional pre-computed hash
            
        Returns:
            Embedding ID
        """
        if content_hash is None:
            content_hash = hashlib.sha256(text.encode()).hexdigest()
        
        # Check if already exists
        existing = self.db.embed_get_by_hash(content_hash)
        if existing:
            return content_hash
        
        # Generate embedding
        vector = self.generate_embedding(text)
        vector_bytes = vector.tobytes()
        
        # Store in database
        embed_id = self.db.embed_store(
            text_content=text,
            vector=vector_bytes,
            model=self.model,
            content_hash=content_hash
        )
        
        # Cache the vector
        self._cache[content_hash] = vector
        if len(self._cache) > self._cache_size:
            # Remove oldest entries
            oldest = list(self._cache.keys())[:-self._cache_size]
            for k in oldest:
                del self._cache[k]
        
        return content_hash
    
    def get_vector(self, content_hash: str) -> Optional[np.ndarray]:
        """
        Get embedding vector by content hash.
        
        Args:
            content_hash: Hash of the content
            
        Returns:
            Numpy array or None if not found
        """
        # Check cache first
        if content_hash in self._cache:
            return self._cache[content_hash]
        
        # Fetch from database
        vector_bytes = self.db.embed_get_by_hash(content_hash)
        if vector_bytes is None:
            return None
        
        vector = np.frombuffer(vector_bytes, dtype=np.float32)
        
        # Cache it
        self._cache[content_hash] = vector
        
        return vector
    
    def search(
        self,
        query: str,
        top_k: int = 5,
        include_text: bool = True
    ) -> List[Dict[str, Any]]:
        """
        Search for most similar texts to query.
        
        Args:
            query: Search query
            top_k: Number of results to return
            include_text: Include text content in results
            
        Returns:
            List of dicts with 'id', 'score', and optionally 'text'
        """
        query_vector = self.generate_embedding(query)
        
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, content_hash, text_content, vector FROM embeddings")
            rows = cursor.fetchall()
        
        results = []
        for row in rows:
            content_hash = row["content_hash"]
            text_content = row["text_content"]
            
            try:
                vector = np.frombuffer(row["vector"], dtype=np.float32)
            except Exception:
                continue
            
            score = self._cosine_similarity(query_vector, vector)
            
            result = {
                "id": row["id"],
                "content_hash": content_hash,
                "score": score
            }
            
            if include_text:
                result["text"] = text_content
            
            results.append(result)
        
        # Sort by score descending
        results.sort(key=lambda x: x["score"], reverse=True)
        
        return results[:top_k]
    
    def find_similar(
        self,
        text: str,
        top_k: int = 5
    ) -> List[Tuple[str, float]]:
        """
        Find similar texts to given text.
        
        Args:
            text: Reference text
            top_k: Number of results
            
        Returns:
            List of (text, score) tuples
        """
        results = self.search(text, top_k, include_text=True)
        return [(r["text"], r["score"]) for r in results]
    
    def delete(self, content_hash: str) -> bool:
        """Delete an embedding by content hash."""
        # Remove from cache
        if content_hash in self._cache:
            del self._cache[content_hash]
        
        # Would need to add delete method to db
        return True
    
    def exists(self, content_hash: str) -> bool:
        """Check if embedding exists."""
        if content_hash in self._cache:
            return True
        return self.db.embed_exists(content_hash)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get vector store statistics."""
        with self.db.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM embeddings")
            count = cursor.fetchone()["count"]
            
            cursor.execute("SELECT SUM(dimension) as total_dim FROM embeddings")
            # Not stored, so estimate
            total_dim = count * self.dimension
            
            return {
                "total_embeddings": count,
                "dimension": self.dimension,
                "model": self.model,
                "cached": len(self._cache)
            }


class SemanticSearch:
    """
    High-level semantic search interface.
    Combines vector store with semantic memory for contextual retrieval.
    """
    
    def __init__(self, vector_store: Optional[VectorStore] = None):
        self.vector_store = vector_store or VectorStore()
        self.db = get_db()
    
    def index_memory(
        self,
        category: str,
        key: str,
        value: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Index a memory entry with its embedding.
        
        Args:
            category: Memory category
            key: Memory key
            value: Memory value
            metadata: Optional metadata
            
        Returns:
            Entry ID
        """
        # Store embedding
        content_hash = self.vector_store.store(value, metadata)
        
        # Update semantic memory with embedding reference
        entry_id = self.db.semantic_save(
            category=category,
            key=key,
            value=value,
            embedding_id=content_hash,
            metadata=metadata
        )
        
        return entry_id
    
    def retrieve(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5
    ) -> List[Tuple[str, float, str]]:
        """
        Retrieve memories similar to query.
        
        Args:
            query: Search query
            category: Optional category filter
            top_k: Number of results
            
        Returns:
            List of (value, score, entry_id) tuples
        """
        # Search vector store
        vector_results = self.vector_store.search(query, top_k * 2, include_text=False)
        
        results = []
        for result in vector_results:
            content_hash = result["content_hash"]
            score = result["score"]
            
            # Find corresponding semantic memory entry
            with self.db.get_connection() as conn:
                cursor = conn.cursor()
                if category:
                    cursor.execute("""
                        SELECT id, value FROM semantic_memory 
                        WHERE embedding_id = ? AND category = ?
                    """, (content_hash, category))
                else:
                    cursor.execute("""
                        SELECT id, value FROM semantic_memory 
                        WHERE embedding_id = ?
                    """, (content_hash,))
                
                row = cursor.fetchone()
                if row:
                    results.append((row["value"], score, row["id"]))
        
        # Sort by score and limit
        results.sort(key=lambda x: x[1], reverse=True)
        return results[:top_k]
    
    def contextual_recall(
        self,
        query: str,
        max_results: int = 10
    ) -> str:
        """
        Recall relevant memories for context injection.
        
        Args:
            query: Context query
            max_results: Maximum number of results
            
        Returns:
            Formatted context string
        """
        results = self.retrieve(query, top_k=max_results)
        
        if not results:
            return ""
        
        lines = ["[RELEVANT MEMORIES]"]
        for value, score, entry_id in results:
            if score > 0.5:  # Only include relevant results
                lines.append(f"- [{score:.2f}] {value[:200]}")
        
        return "\n".join(lines)


def get_vector_store(dimension: int = 384) -> VectorStore:
    """Get vector store instance."""
    return VectorStore(dimension=dimension)


def get_semantic_search() -> SemanticSearch:
    """Get semantic search instance."""
    return SemanticSearch()