"""
core/context_builder.py — Dynamic Context Builder
==================================================
Builds contextual prompts from memory, session state, and user input.
Handles dynamic context injection without treating historical fragments as instructions.

Author: MIN AI Team
Version: 1.0
"""

import time
from typing import Dict, Any, List, Optional
from dataclasses import dataclass
from datetime import datetime, timedelta

from memory.hybrid import HybridMemory


@dataclass
class ContextEntry:
    content: str
    source: str  # 'semantic', 'episodic', 'work', 'system'
    timestamp: datetime
    relevance_score: float
    priority: int  # 1-5, higher = more important


class ContextBuilder:
    """
    Builds dynamic context for prompts.
    Integrates memory layers and provides relevance-based context injection.
    """
    
    def __init__(self, memory: HybridMemory):
        self.memory = memory
        self._max_context_entries = 10
        self._max_context_age = timedelta(hours=24)
        self._last_build_time = 0
        self._cached_context: Optional[List[ContextEntry]] = None
    
    async def build(self, query: str, max_entries: int = 10) -> Dict[str, Any]:
        """
        Build context for a query.
        
        Args:
            query: User query string
            max_entries: Maximum context entries to include
            
        Returns:
            Dict with context components
        """
        self._max_context_entries = max_entries
        
        # Get semantic memory relevant to query
        semantic_context = await self._get_semantic_context(query)
        
        # Get recent episodic memories
        episodic_context = await self._get_episodic_context()
        
        # Get work memory context
        work_context = self._get_work_context()
        
        # Get system context
        system_context = self._get_system_context()
        
        # Combine and score all contexts
        combined = self._combine_and_score(
            semantic_context,
            episodic_context,
            work_context,
            system_context
        )
        
        # Cache the result
        self._cached_context = combined
        self._last_build_time = time.time()
        
        return {
            'semantic': semantic_context,
            'episodic': episodic_context,
            'work': work_context,
            'system': system_context,
            'combined': combined,
            'query': query,
            'timestamp': datetime.now().isoformat()
        }
    
    async def _get_semantic_context(self, query: str) -> List[ContextEntry]:
        """Get semantically relevant facts from memory."""
        context = []
        
        try:
            facts = await self.memory.get_semantic_facts(query=query, limit=5)
            for fact in facts:
                entry = ContextEntry(
                    content=str(fact.get('content', '')),
                    source='semantic',
                    timestamp=datetime.fromisoformat(fact.get('timestamp', datetime.now().isoformat())),
                    relevance_score=fact.get('relevance', 0.5),
                    priority=3
                )
                context.append(entry)
        except Exception as e:
            print(f"[ContextBuilder] Semantic context error: {e}")
        
        return context
    
    async def _get_episodic_context(self) -> List[ContextEntry]:
        """Get recent episodic memories (last session's interactions)."""
        context = []
        
        try:
            recent = await self.memory.get_recent_episodes(limit=3)
            for episode in recent:
                entry = ContextEntry(
                    content=episode.get('summary', ''),
                    source='episodic',
                    timestamp=datetime.fromisoformat(episode.get('timestamp', datetime.now().isoformat())),
                    relevance_score=0.6,
                    priority=2
                )
                context.append(entry)
        except Exception as e:
            print(f"[ContextBuilder] Episodic context error: {e}")
        
        return context
    
    def _get_work_context(self) -> List[ContextEntry]:
        """Get current work memory context."""
        context = []
        
        try:
            work_data = self.memory.get_work_context()
            if work_data:
                entry = ContextEntry(
                    content=f"Current task: {work_data.get('current_task', 'None')}",
                    source='work',
                    timestamp=datetime.now(),
                    relevance_score=0.9,
                    priority=5
                )
                context.append(entry)
        except Exception as e:
            print(f"[ContextBuilder] Work context error: {e}")
        
        return context
    
    def _get_system_context(self) -> List[ContextEntry]:
        """Get system-level context."""
        return [
            ContextEntry(
                content="MIN AI Assistant - Task oriented AI helper",
                source='system',
                timestamp=datetime.now(),
                relevance_score=0.3,
                priority=1
            )
        ]
    
    def _combine_and_score(
        self,
        semantic: List[ContextEntry],
        episodic: List[ContextEntry],
        work: List[ContextEntry],
        system: List[ContextEntry]
    ) -> List[ContextEntry]:
        """Combine all contexts and apply final scoring."""
        all_entries = semantic + episodic + work + system
        
        # Sort by priority then relevance
        all_entries.sort(key=lambda e: (e.priority * e.relevance_score), reverse=True)
        
        # Filter by max entries and age
        now = datetime.now()
        filtered = [
            e for e in all_entries
            if (now - e.timestamp) < self._max_context_age
        ][:self._max_context_entries]
        
        return filtered
    
    def format_context_for_prompt(self, context: Dict[str, Any]) -> str:
        """
        Format context dict into a string for prompt injection.
        
        Args:
            context: Output from build()
            
        Returns:
            Formatted string suitable for prompt injection
        """
        if not context or not context.get('combined'):
            return ""
        
        lines = ["[CONTEXT FROM MEMORY]"]
        
        for entry in context['combined']:
            source_tag = f"[{entry.source.upper()}]"
            lines.append(f"{source_tag} {entry.content}")
        
        lines.append("[END CONTEXT]")
        
        return "\n".join(lines)
    
    def should_inject_context(self, query: str) -> bool:
        """
        Determine if context injection is needed for this query.
        
        Args:
            query: User query
            
        Returns:
            True if context should be injected
        """
        # Don't inject for very short queries
        if len(query.strip()) < 10:
            return False
        
        # Don't inject for certain intent patterns
        skip_patterns = [
            'hola', 'hello', 'hi', 'buenos días', 'buenas tardes',
            'what time', 'qué hora', 'help', 'ayuda'
        ]
        
        query_lower = query.lower()
        for pattern in skip_patterns:
            if pattern in query_lower:
                return False
        
        return True


def create_context_builder(memory: HybridMemory) -> ContextBuilder:
    """Factory function to create ContextBuilder with memory."""
    return ContextBuilder(memory)