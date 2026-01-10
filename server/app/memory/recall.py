"""
Memory Recall - Self-learning through pattern matching and context retrieval.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
from functools import lru_cache
from app.memory.repository import get_memory_repository, MemoryEntry
from app.rag.retriever import get_rag_retriever
from app.core.logger import setup_logger

logger = setup_logger(__name__)

# Pre-compiled stop words set for O(1) lookup
STOP_WORDS: Set[str] = frozenset({
    'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been', 'being',
    'have', 'has', 'had', 'do', 'does', 'did', 'will', 'would', 'could',
    'should', 'may', 'might', 'must', 'shall', 'can', 'of', 'to', 'in',
    'for', 'on', 'with', 'at', 'by', 'from', 'as', 'into', 'through',
    'during', 'before', 'after', 'above', 'below', 'and', 'but', 'or',
    'if', 'then', 'else', 'when', 'where', 'why', 'how', 'all', 'each',
    'every', 'both', 'few', 'more', 'most', 'other', 'some', 'such', 'no',
    'nor', 'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
    'just', 'what', 'find', 'solve', 'calculate', 'determine', 'evaluate',
    'compute', 'given', 'that', 'this'
})


class MemoryRecall:
    """Memory recall system combining database search with vector similarity."""
    
    __slots__ = ('repository', 'rag')
    
    def __init__(self):
        self.repository = get_memory_repository()
        self.rag = get_rag_retriever()
        logger.info("Memory recall initialized")
    
    def find_similar_problems(
        self,
        query: str,
        topic: Optional[str] = None,
        limit: int = 3
    ) -> List[MemoryEntry]:
        """Find similar problems using topic and keyword search."""
        try:
            seen_ids: Set[str] = set()  # O(1) deduplication
            results: List[MemoryEntry] = []
            
            # Topic-based search
            if topic:
                for entry in self.repository.get_entries_by_topic(topic, limit):
                    if entry.id not in seen_ids:
                        seen_ids.add(entry.id)
                        results.append(entry)
            
            # Keyword-based search
            for keyword in self._extract_keywords(query)[:3]:
                for entry in self.repository.search_by_text(keyword, limit):
                    if entry.id not in seen_ids:
                        seen_ids.add(entry.id)
                        results.append(entry)
            
            # Sort: correct first, then by recency
            results.sort(
                key=lambda e: (e.user_feedback == "correct", e.created_at),
                reverse=True
            )
            
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Similar problem search failed: {e}")
            return []
    
    @staticmethod
    def _extract_keywords(text: str, max_keywords: int = 5) -> List[str]:
        """Extract keywords with O(n) complexity."""
        words = text.lower().translate(str.maketrans('', '', '?.,')).split()
        keywords = [w for w in words if w not in STOP_WORDS and len(w) > 2]
        return keywords[:max_keywords]
    
    def get_solution_patterns(self, topic: str, limit: int = 5) -> List[Dict[str, Any]]:
        """Get successful solution patterns for a topic."""
        try:
            entries = self.repository.get_correct_entries(limit * 2)
            topic_lower = topic.lower()
            
            return [
                {
                    "problem": e.parsed_question,
                    "solution_steps": e.solution_steps,
                    "answer": e.final_answer,
                    "confidence": e.confidence
                }
                for e in entries
                if e.topic.lower() == topic_lower
            ][:limit]
            
        except Exception as e:
            logger.error(f"Pattern retrieval failed: {e}")
            return []
    
    def get_combined_context(
        self,
        query: str,
        topic: Optional[str] = None
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """Get combined RAG + memory context."""
        # RAG context
        rag_contexts = self.rag.retrieve(query, k=3) if self.rag._is_initialized else []
        
        # Memory patterns
        memory_patterns: List[Dict[str, Any]] = []
        
        if topic:
            memory_patterns.extend(self.get_solution_patterns(topic, limit=2))
        
        # Add similar correct problems
        for entry in self.find_similar_problems(query, topic, limit=2):
            if entry.user_feedback == "correct":
                memory_patterns.append({
                    "type": "similar_problem",
                    "problem": entry.parsed_question,
                    "solution": entry.final_answer,
                    "confidence": entry.confidence
                })
        
        logger.debug(f"Context: {len(rag_contexts)} RAG, {len(memory_patterns)} memory")
        return rag_contexts, memory_patterns


# Singleton
_instance: Optional[MemoryRecall] = None


def get_memory_recall() -> MemoryRecall:
    """Get singleton MemoryRecall instance."""
    global _instance
    if _instance is None:
        _instance = MemoryRecall()
    return _instance
