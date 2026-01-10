"""
Feedback and HITL (Human-In-The-Loop) API.
Handles user feedback, solution corrections, and HITL workflow.
"""

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from app.memory.repository import get_memory_repository, MemoryEntry
from app.core.logger import setup_logger


logger = setup_logger(__name__)
router = APIRouter(prefix="/feedback", tags=["Feedback & HITL"])


# Request/Response Models

class FeedbackRequest(BaseModel):
    """Request model for submitting feedback."""
    entry_id: Optional[str] = Field(None, description="ID of the memory entry")
    is_correct: bool = Field(..., description="Whether the solution was correct")
    comment: Optional[str] = Field(None, description="Optional feedback comment")


class FeedbackResponse(BaseModel):
    """Response model for feedback submission."""
    success: bool
    message: str
    entry_id: str


class HITLApproveRequest(BaseModel):
    """Request for HITL approval of parsed/solved result."""
    entry_id: str = Field(..., description="ID of the entry to approve")
    edited_text: Optional[str] = Field(None, description="Optional edited text")


class HITLRejectRequest(BaseModel):
    """Request for HITL rejection."""
    entry_id: str = Field(..., description="ID of the entry to reject")
    reason: str = Field(..., description="Reason for rejection")


class HistoryResponse(BaseModel):
    """Response model for history entries."""
    entries: List[Dict[str, Any]]
    total: int


# Endpoints

@router.post("/correct", response_model=FeedbackResponse)
async def mark_correct(request: FeedbackRequest) -> FeedbackResponse:
    """
    Mark a solution as correct.
    
    This feedback is used to train the system by identifying
    successful solution patterns.
    """
    try:
        if not request.entry_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entry_id is required. The solution was not stored in memory."
            )
        
        if not request.is_correct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use /incorrect endpoint for incorrect feedback"
            )
        
        repository = get_memory_repository()
        success = repository.update_feedback(
            entry_id=request.entry_id,
            feedback="correct",
            comment=request.comment
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry {request.entry_id} not found"
            )
        
        logger.info(f"Marked entry {request.entry_id} as correct")
        return FeedbackResponse(
            success=True,
            message="Solution marked as correct. Thank you for your feedback!",
            entry_id=request.entry_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process correct feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process feedback"
        )


@router.post("/incorrect", response_model=FeedbackResponse)
async def mark_incorrect(request: FeedbackRequest) -> FeedbackResponse:
    """
    Mark a solution as incorrect.
    
    Include a comment explaining what was wrong to help
    improve future solutions.
    """
    try:
        if not request.entry_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="entry_id is required. The solution was not stored in memory."
            )
        
        if request.is_correct:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Use /correct endpoint for correct feedback"
            )
        
        repository = get_memory_repository()
        success = repository.update_feedback(
            entry_id=request.entry_id,
            feedback="incorrect",
            comment=request.comment
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry {request.entry_id} not found"
            )
        
        logger.info(f"Marked entry {request.entry_id} as incorrect: {request.comment}")
        return FeedbackResponse(
            success=True,
            message="Feedback recorded. We'll use this to improve.",
            entry_id=request.entry_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process incorrect feedback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process feedback"
        )


@router.post("/hitl/approve", response_model=FeedbackResponse)
async def hitl_approve(request: HITLApproveRequest) -> FeedbackResponse:
    """
    Approve a parsed or solved result during HITL review.
    
    Optionally include edited text if the user made corrections.
    """
    try:
        repository = get_memory_repository()
        entry = repository.get_entry(request.entry_id)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry {request.entry_id} not found"
            )
        
        # If edited text provided, update the entry
        if request.edited_text:
            entry.parsed_question = request.edited_text
            entry.requires_human_review = False
            repository.store_entry(entry)
        
        logger.info(f"HITL approved entry {request.entry_id}")
        return FeedbackResponse(
            success=True,
            message="HITL approval recorded. Proceeding with solution.",
            entry_id=request.entry_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process HITL approval: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process HITL approval"
        )


@router.post("/hitl/reject", response_model=FeedbackResponse)
async def hitl_reject(request: HITLRejectRequest) -> FeedbackResponse:
    """
    Reject a parsed or solved result during HITL review.
    
    The system will attempt to re-solve with different parameters.
    """
    try:
        repository = get_memory_repository()
        success = repository.update_feedback(
            entry_id=request.entry_id,
            feedback="rejected",
            comment=request.reason
        )
        
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry {request.entry_id} not found"
            )
        
        logger.info(f"HITL rejected entry {request.entry_id}: {request.reason}")
        return FeedbackResponse(
            success=True,
            message="Rejection recorded. Please try again with a clearer input.",
            entry_id=request.entry_id
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to process HITL rejection: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process HITL rejection"
        )


@router.get("/history", response_model=HistoryResponse)
async def get_history(limit: int = 20) -> HistoryResponse:
    """
    Get recent problem-solving history.
    
    Returns a list of recently solved problems with their outcomes.
    """
    try:
        repository = get_memory_repository()
        entries = repository.get_recent_entries(limit=limit)
        
        return HistoryResponse(
            entries=[
                {
                    "id": e.id,
                    "original_input": e.original_input[:100] + "..." if len(e.original_input) > 100 else e.original_input,
                    "input_type": e.input_type,
                    "topic": e.topic,
                    "final_answer": e.final_answer,
                    "confidence": e.confidence,
                    "user_feedback": e.user_feedback,
                    "created_at": e.created_at
                }
                for e in entries
            ],
            total=len(entries)
        )
        
    except Exception as e:
        logger.error(f"Failed to get history: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve history"
        )


@router.get("/entry/{entry_id}")
async def get_entry(entry_id: str) -> Dict[str, Any]:
    """
    Get details of a specific memory entry.
    """
    try:
        repository = get_memory_repository()
        entry = repository.get_entry(entry_id)
        
        if not entry:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Entry {entry_id} not found"
            )
        
        return entry.model_dump()
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get entry: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve entry"
        )
