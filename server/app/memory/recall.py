"""
Memory Recall - Retrieves similar problems and learned patterns.
Implements self-learning through pattern matching and context retrieval.
"""

from typing import List, Dict, Any, Optional, Tuple
from app.memory.repository import get_memory_repository, MemoryEntry
from app.rag.retriever import get_rag_retriever
from app.core.logger import setup_logger


logger = setup_logger(__name__)


class MemoryRecall:
    """
    Memory recall system for retrieving similar solved problems.
    Combines database search with vector similarity.
    """
    
    def __init__(self):
        """Initialize the memory recall system."""
        self.repository = get_memory_repository()
        self.rag = get_rag_retriever()
        logger.info("Memory recall system initialized")
    
    def find_similar_problems(
        self,
        query: str,
        topic: Optional[str] = None,
        limit: int = 3
    ) -> List[MemoryEntry]:
        """
        Find similar previously solved problems.
        
        Args:
            query: The problem text to match against
            topic: Optional topic to filter by
            limit: Maximum number of results
            
        Returns:
            List of similar MemoryEntry objects
        """
        results = []
        
        try:
            # First, try topic-based search if topic provided
            if topic:
                topic_results = self.repository.get_entries_by_topic(topic, limit)
                results.extend(topic_results)
            
            # Then, do text-based search
            # Extract key words for search
            keywords = self._extract_keywords(query)
            for keyword in keywords[:3]:  # Use top 3 keywords
                text_results = self.repository.search_by_text(keyword, limit)
                for entry in text_results:
                    if entry.id not in [r.id for r in results]:
                        results.append(entry)
            
            # Sort by recency and correctness
            results = sorted(
                results,
                key=lambda e: (
                    1 if e.user_feedback == "correct" else 0,
                    e.created_at
                ),
                reverse=True
            )[:limit]
            
            logger.info(f"Found {len(results)} similar problems")
            return results
            
        except Exception as e:
            logger.error(f"Failed to find similar problems: {e}")
            return []
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from problem text for search."""
        # Remove common words and extract meaningful terms
        stop_words = {
            'the', 'a', 'an', 'is', 'are', 'was', 'were', 'be', 'been',
            'being', 'have', 'has', 'had', 'do', 'does', 'did', 'will',
            'would', 'could', 'should', 'may', 'might', 'must', 'shall',
            'can', 'of', 'to', 'in', 'for', 'on', 'with', 'at', 'by',
            'from', 'as', 'into', 'through', 'during', 'before', 'after',
            'above', 'below', 'and', 'but', 'or', 'if', 'then', 'else',
            'when', 'where', 'why', 'how', 'all', 'each', 'every', 'both',
            'few', 'more', 'most', 'other', 'some', 'such', 'no', 'nor',
            'not', 'only', 'own', 'same', 'so', 'than', 'too', 'very',
            'just', 'what', 'find', 'solve', 'calculate', 'determine',
            'evaluate', 'compute', 'given', 'that', 'this'
        }
        
        # Tokenize and filter
        words = text.lower().replace('?', '').replace('.', '').split()
        keywords = [w for w in words if w not in stop_words and len(w) > 2]
        
        return keywords
    
    def get_solution_patterns(
        self,
        topic: str,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Get successful solution patterns for a topic.
        Returns patterns from correctly solved problems.
        
        Args:
            topic: Mathematical topic
            limit: Maximum patterns to return
            
        Returns:
            List of pattern dictionaries
        """
        try:
            # Get correct entries for the topic
            entries = self.repository.get_correct_entries(limit * 2)
            topic_entries = [e for e in entries if e.topic.lower() == topic.lower()]
            
            patterns = []
            for entry in topic_entries[:limit]:
                patterns.append({
                    "problem": entry.parsed_question,
                    "solution_steps": entry.solution_steps,
                    "answer": entry.final_answer,
                    "confidence": entry.confidence
                })
            
            logger.info(f"Found {len(patterns)} solution patterns for {topic}")
            return patterns
            
        except Exception as e:
            logger.error(f"Failed to get solution patterns: {e}")
            return []
    
    def get_combined_context(
        self,
        query: str,
        topic: Optional[str] = None
    ) -> Tuple[List[str], List[Dict[str, Any]]]:
        """
        Get combined context from both RAG and memory.
        
        Args:
            query: The problem text
            topic: Optional topic filter
            
        Returns:
            Tuple of (rag_contexts, memory_patterns)
        """
        # Get RAG context
        rag_contexts = self.rag.retrieve(query, k=3) if self.rag._is_initialized else []
        
        # Get memory patterns
        memory_patterns = []
        if topic:
            patterns = self.get_solution_patterns(topic, limit=2)
            memory_patterns.extend(patterns)
        
        # Get similar solved problems
        similar = self.find_similar_problems(query, topic, limit=2)
        for entry in similar:
            if entry.user_feedback == "correct":
                memory_patterns.append({
                    "type": "similar_problem",
                    "problem": entry.parsed_question,
                    "solution": entry.final_answer,
                    "confidence": entry.confidence
                })
        
        logger.info(
            f"Combined context: {len(rag_contexts)} RAG docs, "
            f"{len(memory_patterns)} memory patterns"
        )
        
        return rag_contexts, memory_patterns


# Singleton instance
_memory_recall: Optional[MemoryRecall] = None


def get_memory_recall() -> MemoryRecall:
    """Get or create the singleton memory recall instance."""
    global _memory_recall
    if _memory_recall is None:
        _memory_recall = MemoryRecall()
    return _memory_recall
