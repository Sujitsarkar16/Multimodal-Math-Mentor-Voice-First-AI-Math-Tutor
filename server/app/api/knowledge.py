"""
Knowledge Base API - CRUD operations for RAG knowledge entries.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from functools import lru_cache

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

from app.core.logger import setup_logger
from app.rag.retriever import get_rag_retriever

logger = setup_logger(__name__)
router = APIRouter(prefix="/knowledge")

KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "data" / "math_knowledge.json"


# ============================================================================
# Models
# ============================================================================

class KnowledgeMetadata(BaseModel):
    topic: str
    type: str
    difficulty: str = "medium"
    tags: List[str] = Field(default_factory=list)


class KnowledgeEntry(BaseModel):
    id: str
    content: str
    metadata: KnowledgeMetadata
    created_at: Optional[str] = None


class KnowledgeEntryCreate(BaseModel):
    content: str = Field(..., min_length=10)
    topic: str
    type: str = "formula"
    difficulty: str = "medium"
    tags: List[str] = Field(default_factory=list)


class KnowledgeEntryUpdate(BaseModel):
    content: Optional[str] = Field(None, min_length=10)
    topic: Optional[str] = None
    type: Optional[str] = None
    difficulty: Optional[str] = None
    tags: Optional[List[str]] = None


class KnowledgeStats(BaseModel):
    total_entries: int
    topics: Dict[str, int]
    types: Dict[str, int]
    difficulties: Dict[str, int]


class KnowledgeResponse(BaseModel):
    entries: List[KnowledgeEntry]
    total: int
    stats: Optional[KnowledgeStats] = None


# ============================================================================
# Data Access Layer
# ============================================================================

class KnowledgeRepository:
    """Repository pattern for knowledge base CRUD operations."""
    
    def __init__(self, file_path: Path):
        self._path = file_path
        self._cache: Optional[List[Dict]] = None
        self._cache_time: float = 0
    
    def _read(self) -> List[Dict[str, Any]]:
        """Read entries from file with simple caching."""
        try:
            mtime = self._path.stat().st_mtime if self._path.exists() else 0
            if self._cache and mtime == self._cache_time:
                return self._cache
            
            if not self._path.exists():
                return []
            
            with open(self._path, 'r', encoding='utf-8') as f:
                self._cache = json.load(f)
                self._cache_time = mtime
                return self._cache
        except Exception as e:
            logger.error(f"Read failed: {e}")
            return []
    
    def _write(self, entries: List[Dict]) -> bool:
        """Write entries to file and invalidate cache."""
        try:
            with open(self._path, 'w', encoding='utf-8') as f:
                json.dump(entries, f, indent=4, ensure_ascii=False)
            self._cache = entries
            self._cache_time = self._path.stat().st_mtime
            return True
        except Exception as e:
            logger.error(f"Write failed: {e}")
            return False
    
    def get_all(self) -> List[Dict]:
        return self._read()
    
    def get_by_id(self, entry_id: str) -> Optional[Dict]:
        return next((e for e in self._read() if e.get("id") == entry_id), None)
    
    def create(self, entry: Dict) -> bool:
        entries = self._read()
        entries.append(entry)
        return self._write(entries)
    
    def update(self, entry_id: str, updates: Dict) -> Optional[Dict]:
        entries = self._read()
        for i, e in enumerate(entries):
            if e.get("id") == entry_id:
                entries[i] = {**e, **updates, "updated_at": datetime.utcnow().isoformat()}
                if self._write(entries):
                    return entries[i]
                return None
        return None
    
    def delete(self, entry_id: str) -> bool:
        entries = self._read()
        filtered = [e for e in entries if e.get("id") != entry_id]
        if len(filtered) == len(entries):
            return False
        return self._write(filtered)
    
    def compute_stats(self) -> KnowledgeStats:
        """Compute statistics in O(n) time."""
        entries = self._read()
        topics, types, difficulties = {}, {}, {}
        
        for e in entries:
            m = e.get("metadata", {})
            topics[m.get("topic", "unknown")] = topics.get(m.get("topic", "unknown"), 0) + 1
            types[m.get("type", "unknown")] = types.get(m.get("type", "unknown"), 0) + 1
            difficulties[m.get("difficulty", "unknown")] = difficulties.get(m.get("difficulty", "unknown"), 0) + 1
        
        return KnowledgeStats(
            total_entries=len(entries),
            topics=topics,
            types=types,
            difficulties=difficulties
        )


# Singleton repository instance
_repo = KnowledgeRepository(KNOWLEDGE_BASE_PATH)


def _generate_id(topic: str, content: str) -> str:
    """Generate unique entry ID."""
    words = content.split()[:3]
    slug = "_".join(w.lower()[:10] for w in words if w.isalnum())
    return f"{topic.lower()}_{slug}_{uuid.uuid4().hex[:8]}"


def _to_response(entry: Dict) -> KnowledgeEntry:
    """Convert dict to response model."""
    m = entry.get("metadata", {})
    return KnowledgeEntry(
        id=entry.get("id", ""),
        content=entry.get("content", ""),
        metadata=KnowledgeMetadata(
            topic=m.get("topic", "general"),
            type=m.get("type", "formula"),
            difficulty=m.get("difficulty", "medium"),
            tags=m.get("tags", [])
        ),
        created_at=entry.get("created_at")
    )


# ============================================================================
# Endpoints
# ============================================================================

@router.get("", response_model=KnowledgeResponse)
async def list_entries(
    topic: Optional[str] = Query(None),
    type: Optional[str] = Query(None),
    difficulty: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    include_stats: bool = Query(True)
) -> KnowledgeResponse:
    """List entries with optional filtering - O(n) complexity."""
    entries = _repo.get_all()
    search_lower = search.lower() if search else None
    
    # Filter in single pass
    filtered = []
    for e in entries:
        m = e.get("metadata", {})
        
        if topic and m.get("topic", "").lower() != topic.lower():
            continue
        if type and m.get("type", "").lower() != type.lower():
            continue
        if difficulty and m.get("difficulty", "").lower() != difficulty.lower():
            continue
        if search_lower:
            content_match = search_lower in e.get("content", "").lower()
            tag_match = any(search_lower in t.lower() for t in m.get("tags", []))
            if not (content_match or tag_match):
                continue
        
        filtered.append(_to_response(e))
    
    return KnowledgeResponse(
        entries=filtered,
        total=len(filtered),
        stats=_repo.compute_stats() if include_stats else None
    )


@router.get("/topics", response_model=List[str])
async def get_topics() -> List[str]:
    """Get unique topics - O(n) time, O(k) space where k = unique topics."""
    topics = {e.get("metadata", {}).get("topic") for e in _repo.get_all()}
    return sorted(t for t in topics if t)


@router.get("/{entry_id}", response_model=KnowledgeEntry)
async def get_entry(entry_id: str) -> KnowledgeEntry:
    """Get single entry by ID - O(n) lookup."""
    entry = _repo.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entry '{entry_id}' not found")
    return _to_response(entry)


@router.post("", response_model=KnowledgeEntry, status_code=status.HTTP_201_CREATED)
async def create_entry(request: KnowledgeEntryCreate) -> KnowledgeEntry:
    """Create new entry and add to RAG system."""
    entry_id = _generate_id(request.topic, request.content)
    
    # Ensure unique ID
    existing = {e.get("id") for e in _repo.get_all()}
    while entry_id in existing:
        entry_id = _generate_id(request.topic, request.content)
    
    new_entry = {
        "id": entry_id,
        "content": request.content,
        "metadata": {
            "topic": request.topic,
            "type": request.type,
            "difficulty": request.difficulty,
            "tags": request.tags
        },
        "created_at": datetime.utcnow().isoformat()
    }
    
    if not _repo.create(new_entry):
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to save")
    
    # Add to RAG (non-blocking)
    try:
        retriever = get_rag_retriever()
        retriever.add_documents([{"content": request.content, "metadata": new_entry["metadata"]}])
        logger.info(f"Added to RAG: {entry_id}")
    except Exception as e:
        logger.warning(f"RAG add failed: {e}")
    
    return _to_response(new_entry)


@router.put("/{entry_id}", response_model=KnowledgeEntry)
async def update_entry(entry_id: str, request: KnowledgeEntryUpdate) -> KnowledgeEntry:
    """Update existing entry."""
    entry = _repo.get_by_id(entry_id)
    if not entry:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entry '{entry_id}' not found")
    
    updates = {}
    if request.content is not None:
        updates["content"] = request.content
    
    metadata = entry.get("metadata", {}).copy()
    if request.topic is not None:
        metadata["topic"] = request.topic
    if request.type is not None:
        metadata["type"] = request.type
    if request.difficulty is not None:
        metadata["difficulty"] = request.difficulty
    if request.tags is not None:
        metadata["tags"] = request.tags
    updates["metadata"] = metadata
    
    updated = _repo.update(entry_id, updates)
    if not updated:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Failed to update")
    
    logger.info(f"Updated: {entry_id}")
    return _to_response(updated)


@router.delete("/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_entry(entry_id: str):
    """Delete entry."""
    if not _repo.delete(entry_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"Entry '{entry_id}' not found")
    logger.info(f"Deleted: {entry_id}")
