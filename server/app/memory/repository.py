"""
Memory Repository - Storage layer for problem-solving history.
Implements self-learning by storing solved problems and feedback.
"""

import json
import sqlite3
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from app.core.logger import setup_logger


logger = setup_logger(__name__)

# Default database path
DB_PATH = Path(__file__).parent.parent / "data" / "memory.db"


class MemoryEntry(BaseModel):
    """Model for a stored problem-solving entry."""
    id: Optional[str] = None
    original_input: str
    input_type: str = Field(..., description="text, image, or audio")
    parsed_question: str
    topic: str = ""
    retrieved_context: Optional[List[str]] = []
    final_answer: str = ""
    solution_steps: Any = []  # Can be List[str] or List[dict] from agent_trace
    verifier_outcome: Dict[str, Any] = {}
    confidence: float = 0.0
    requires_human_review: bool = False
    user_feedback: Optional[str] = None  # "correct", "incorrect", None
    feedback_comment: Optional[str] = None
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat())


class MemoryRepository:
    """
    Repository for storing and retrieving problem-solving history.
    Uses SQLite for persistence.
    """
    
    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the memory repository."""
        self.db_path = db_path or DB_PATH
        self._ensure_db_exists()
        logger.info(f"Memory repository initialized at {self.db_path}")
    
    def _ensure_db_exists(self):
        """Create database and tables if they don't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS memory_entries (
                    id TEXT PRIMARY KEY,
                    original_input TEXT NOT NULL,
                    input_type TEXT NOT NULL,
                    parsed_question TEXT NOT NULL,
                    topic TEXT,
                    retrieved_context TEXT,
                    final_answer TEXT,
                    solution_steps TEXT,
                    verifier_outcome TEXT,
                    confidence REAL,
                    requires_human_review INTEGER,
                    user_feedback TEXT,
                    feedback_comment TEXT,
                    created_at TEXT,
                    updated_at TEXT
                )
            """)
            conn.commit()
    
    def _generate_id(self) -> str:
        """Generate a unique ID for an entry."""
        import uuid
        return f"mem_{uuid.uuid4().hex[:12]}"
    
    def store_entry(self, entry: MemoryEntry) -> str:
        """
        Store a new memory entry.
        
        Args:
            entry: MemoryEntry to store
            
        Returns:
            ID of stored entry
        """
        if not entry.id:
            entry.id = self._generate_id()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO memory_entries 
                    (id, original_input, input_type, parsed_question, topic,
                     retrieved_context, final_answer, solution_steps, verifier_outcome,
                     confidence, requires_human_review, user_feedback, feedback_comment,
                     created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    entry.id,
                    entry.original_input,
                    entry.input_type,
                    entry.parsed_question,
                    entry.topic,
                    json.dumps(entry.retrieved_context or []),
                    entry.final_answer,
                    json.dumps(entry.solution_steps or [], default=str),
                    json.dumps(entry.verifier_outcome),
                    entry.confidence,
                    1 if entry.requires_human_review else 0,
                    entry.user_feedback,
                    entry.feedback_comment,
                    entry.created_at,
                    entry.updated_at
                ))
                conn.commit()
            
            logger.info(f"Stored memory entry: {entry.id}")
            return entry.id
            
        except Exception as e:
            logger.error(f"Failed to store memory entry: {e}")
            raise
    
    def get_entry(self, entry_id: str) -> Optional[MemoryEntry]:
        """
        Get a memory entry by ID.
        
        Args:
            entry_id: ID of entry to retrieve
            
        Returns:
            MemoryEntry if found, None otherwise
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM memory_entries WHERE id = ?",
                    (entry_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return self._row_to_entry(row)
                return None
                
        except Exception as e:
            logger.error(f"Failed to get memory entry: {e}")
            return None
    
    def _row_to_entry(self, row: sqlite3.Row) -> MemoryEntry:
        """Convert a database row to MemoryEntry."""
        return MemoryEntry(
            id=row['id'],
            original_input=row['original_input'],
            input_type=row['input_type'],
            parsed_question=row['parsed_question'],
            topic=row['topic'] or "",
            retrieved_context=json.loads(row['retrieved_context'] or "[]"),
            final_answer=row['final_answer'] or "",
            solution_steps=json.loads(row['solution_steps'] or "[]"),
            verifier_outcome=json.loads(row['verifier_outcome'] or "{}"),
            confidence=row['confidence'] or 0.0,
            requires_human_review=bool(row['requires_human_review']),
            user_feedback=row['user_feedback'],
            feedback_comment=row['feedback_comment'],
            created_at=row['created_at'],
            updated_at=row['updated_at']
        )
    
    def update_feedback(
        self,
        entry_id: str,
        feedback: str,
        comment: Optional[str] = None
    ) -> bool:
        """
        Update user feedback for an entry.
        
        Args:
            entry_id: ID of entry to update
            feedback: "correct" or "incorrect"
            comment: Optional feedback comment
            
        Returns:
            True if updated successfully
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    UPDATE memory_entries 
                    SET user_feedback = ?, feedback_comment = ?, updated_at = ?
                    WHERE id = ?
                """, (feedback, comment, datetime.utcnow().isoformat(), entry_id))
                conn.commit()
            
            logger.info(f"Updated feedback for entry {entry_id}: {feedback}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update feedback: {e}")
            return False
    
    def get_recent_entries(self, limit: int = 20) -> List[MemoryEntry]:
        """
        Get recent memory entries.
        
        Args:
            limit: Maximum number of entries to return
            
        Returns:
            List of MemoryEntry objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM memory_entries ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                return [self._row_to_entry(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get recent entries: {e}")
            return []
    
    def get_entries_by_topic(self, topic: str, limit: int = 10) -> List[MemoryEntry]:
        """
        Get memory entries by topic.
        
        Args:
            topic: Topic to filter by
            limit: Maximum number of entries
            
        Returns:
            List of MemoryEntry objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM memory_entries WHERE topic = ? ORDER BY created_at DESC LIMIT ?",
                    (topic, limit)
                )
                rows = cursor.fetchall()
                return [self._row_to_entry(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get entries by topic: {e}")
            return []
    
    def get_correct_entries(self, limit: int = 20) -> List[MemoryEntry]:
        """
        Get entries that were marked as correct by user.
        These can be used as learning examples.
        
        Args:
            limit: Maximum number of entries
            
        Returns:
            List of correct MemoryEntry objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM memory_entries WHERE user_feedback = 'correct' ORDER BY created_at DESC LIMIT ?",
                    (limit,)
                )
                rows = cursor.fetchall()
                return [self._row_to_entry(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to get correct entries: {e}")
            return []
    
    def search_by_text(self, query: str, limit: int = 5) -> List[MemoryEntry]:
        """
        Simple text search in parsed questions.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of matching MemoryEntry objects
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute(
                    "SELECT * FROM memory_entries WHERE parsed_question LIKE ? ORDER BY created_at DESC LIMIT ?",
                    (f"%{query}%", limit)
                )
                rows = cursor.fetchall()
                return [self._row_to_entry(row) for row in rows]
                
        except Exception as e:
            logger.error(f"Failed to search entries: {e}")
            return []


# Singleton instance
_memory_repository: Optional[MemoryRepository] = None


def get_memory_repository() -> MemoryRepository:
    """Get or create the singleton memory repository instance."""
    global _memory_repository
    if _memory_repository is None:
        _memory_repository = MemoryRepository()
    return _memory_repository
