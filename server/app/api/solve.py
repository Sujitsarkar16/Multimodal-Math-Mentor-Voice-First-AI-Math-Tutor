"""
API router for problem solving endpoints.
Clean REST API interface to the multi-agent system.
"""

from fastapi import APIRouter, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any, List
from app.domain.pipeline import solve_problem, solve_problem_async, solve_problem_streaming, get_pipeline_stats
from app.core.logger import setup_logger
from app.core.exceptions import GuardrailViolation, AgentError
from app.memory.repository import get_memory_repository, MemoryEntry
import json


logger = setup_logger(__name__)
router = APIRouter(prefix="/solve", tags=["Problem Solving"])


class SolveRequest(BaseModel):
    """Request model for problem solving."""
    text: str = Field(..., description="Problem statement", min_length=1)
    context: Optional[Dict[str, Any]] = Field(None, description="Additional context")
    enable_guardrails: bool = Field(True, description="Enable safety checks")


class SolveResponse(BaseModel):
    """Response model for problem solving."""
    memory_id: Optional[str] = None
    final_answer: str
    explanation: str
    confidence: float
    requires_human_review: bool
    retrieved_context: List[str] = []
    agent_trace: list
    metadata: Dict[str, Any]


class StatsResponse(BaseModel):
    """Response model for pipeline statistics."""
    agents: Dict[str, Any]
    total_executions: int


@router.post("/async", response_model=SolveResponse, status_code=status.HTTP_200_OK)
async def solve_async(request: SolveRequest) -> SolveResponse:
    """
    Solve a mathematical problem using async multi-agent system (faster with parallel execution).
    
    - **text**: The problem statement to solve
    - **context**: Optional additional context or constraints
    - **enable_guardrails**: Whether to enable content safety checks
    
    Returns the solution with explanation, confidence, and agent execution trace.
    """
    try:
        logger.info(f"Received async solve request: {request.text[:100]}...")
        
        result = await solve_problem_async(
            text=request.text,
            context=request.context,
            enable_guardrails=request.enable_guardrails
        )
        
        # Store result in memory
        memory_id = None
        try:
            repository = get_memory_repository()
            entry = MemoryEntry(
                original_input=request.text,
                input_type="text",
                parsed_question=result.get("metadata", {}).get("parsed_question", request.text),
                topic=result.get("metadata", {}).get("topic", ""),
                retrieved_context=result.get("retrieved_context", []),
                final_answer=result.get("final_answer", ""),
                solution_steps=result.get("agent_trace", []),
                verifier_outcome={
                    "is_correct": result.get("metadata", {}).get("is_correct", False),
                    "confidence": result.get("confidence", 0)
                },
                confidence=result.get("confidence", 0),
                requires_human_review=result.get("requires_human_review", False)
            )
            memory_id = repository.store_entry(entry)
            logger.info(f"Stored solution in memory: {memory_id}")
        except Exception as mem_error:
            logger.warning(f"Failed to store in memory: {mem_error}")
        
        return SolveResponse(
            memory_id=memory_id,
            retrieved_context=result.get("retrieved_context", []),
            **result
        )
        
    except GuardrailViolation as e:
        logger.warning(f"Guardrail violation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content policy violation: {str(e)}"
        )
        
    except AgentError as e:
        logger.error(f"Agent error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Problem solving failed: {str(e)}"
        )
        
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Unexpected error: {error_detail}", exc_info=True)
        
        # Provide more helpful error messages
        if "GEMINI_API_KEY" in error_detail or "API key" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key configuration error. Please check your GEMINI_API_KEY environment variable."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {error_detail}"
        )


@router.post("/stream")
async def solve_stream(request: SolveRequest):
    """
    Solve a mathematical problem with real-time streaming of agent progress.
    
    - **text**: The problem statement to solve
    - **context**: Optional additional context or constraints
    - **enable_guardrails**: Whether to enable content safety checks
    
    Returns Server-Sent Events (SSE) stream with agent progress and final result.
    """
    import asyncio
    
    # Track whether client is still connected
    client_disconnected = False
    solve_task = None
    
    async def event_generator():
        nonlocal client_disconnected, solve_task
        try:
            logger.info(f"Received streaming solve request: {request.text[:100]}...")
            
            async for update in solve_problem_streaming(
                text=request.text,
                context=request.context,
                enable_guardrails=request.enable_guardrails
            ):
                # Check if client disconnected
                if client_disconnected:
                    logger.info("Client disconnected, stopping stream")
                    break
                
                # If this is the final result, store in memory
                if update.get("type") == "final_result" and update.get("data"):
                    result = update["data"]
                    memory_id = None
                    try:
                        repository = get_memory_repository()
                        entry = MemoryEntry(
                            original_input=request.text,
                            input_type="text",
                            parsed_question=result.get("metadata", {}).get("parsed_question", request.text),
                            topic=result.get("metadata", {}).get("topic", ""),
                            retrieved_context=result.get("retrieved_context", []),
                            final_answer=result.get("final_answer", ""),
                            solution_steps=result.get("agent_trace", []),
                            verifier_outcome={
                                "is_correct": result.get("metadata", {}).get("is_correct", False),
                                "confidence": result.get("confidence", 0)
                            },
                            confidence=result.get("confidence", 0),
                            requires_human_review=result.get("requires_human_review", False)
                        )
                        memory_id = repository.store_entry(entry)
                        logger.info(f"Stored streaming solution in memory: {memory_id}")
                        # Add memory_id to the result
                        result["memory_id"] = memory_id
                        update["data"] = result
                    except Exception as mem_error:
                        import traceback
                        logger.warning(f"Failed to store streaming result in memory: {mem_error}")
                        logger.warning(f"Traceback: {traceback.format_exc()}")
                
                # Format as SSE
                yield f"data: {json.dumps(update)}\n\n"
                
        except asyncio.CancelledError:
            logger.info("Streaming request was cancelled by client")
            client_disconnected = True
            # Send cancellation notice
            cancel_msg = {
                "type": "cancelled",
                "message": "Request was cancelled"
            }
            yield f"data: {json.dumps(cancel_msg)}\n\n"
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}", exc_info=True)
            error_msg = {
                "type": "error",
                "error": str(e)
            }
            yield f"data: {json.dumps(error_msg)}\n\n"
        finally:
            logger.info("Streaming connection closed")
    
    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache, no-store, must-revalidate",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
            "Pragma": "no-cache",
            "Expires": "0"
        }
    )


@router.post("", response_model=SolveResponse, status_code=status.HTTP_200_OK)
async def solve(request: SolveRequest) -> SolveResponse:
    """
    Solve a mathematical problem using the multi-agent system.
    
    - **text**: The problem statement to solve
    - **context**: Optional additional context or constraints
    - **enable_guardrails**: Whether to enable content safety checks
    
    Returns the solution with explanation, confidence, and agent execution trace.
    """
    try:
        logger.info(f"Received solve request: {request.text[:100]}...")
        
        result = solve_problem(
            text=request.text,
            context=request.context,
            enable_guardrails=request.enable_guardrails
        )
        
        # Store result in memory
        memory_id = None
        try:
            repository = get_memory_repository()
            entry = MemoryEntry(
                original_input=request.text,
                input_type="text",
                parsed_question=result.get("metadata", {}).get("parsed_question", request.text),
                topic=result.get("metadata", {}).get("topic", ""),
                retrieved_context=result.get("retrieved_context", []),
                final_answer=result.get("final_answer", ""),
                solution_steps=result.get("agent_trace", []),
                verifier_outcome={
                    "is_correct": result.get("metadata", {}).get("is_correct", False),
                    "confidence": result.get("confidence", 0)
                },
                confidence=result.get("confidence", 0),
                requires_human_review=result.get("requires_human_review", False)
            )
            memory_id = repository.store_entry(entry)
            logger.info(f"Stored solution in memory: {memory_id}")
        except Exception as mem_error:
            logger.warning(f"Failed to store in memory: {mem_error}")
        
        return SolveResponse(
            memory_id=memory_id,
            retrieved_context=result.get("retrieved_context", []),
            **result
        )
        
    except GuardrailViolation as e:
        logger.warning(f"Guardrail violation: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Content policy violation: {str(e)}"
        )
        
    except AgentError as e:
        logger.error(f"Agent error: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Problem solving failed: {str(e)}"
        )
        
    except Exception as e:
        error_detail = str(e)
        logger.error(f"Unexpected error: {error_detail}", exc_info=True)
        
        # Provide more helpful error messages
        if "GEMINI_API_KEY" in error_detail or "API key" in error_detail.lower():
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="API key configuration error. Please check your GEMINI_API_KEY environment variable."
            )
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred: {error_detail}"
        )


@router.get("/stats", response_model=StatsResponse, status_code=status.HTTP_200_OK)
async def get_stats() -> StatsResponse:
    """
    Get statistics about multi-agent pipeline executions.
    
    Returns execution counts and performance metrics for each agent.
    """
    try:
        stats = get_pipeline_stats()
        return StatsResponse(**stats)
        
    except Exception as e:
        logger.error(f"Failed to get stats: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve statistics"
        )


@router.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    """
    Health check endpoint for the solving service.
    """
    from app.settings import settings
    
    health_status = {
        "status": "healthy",
        "service": "multi-agent-solver",
        "version": "2.0.0",
        "api_key_configured": bool(settings.GEMINI_API_KEY),
        "model": settings.DEFAULT_LLM_MODEL
    }
    
    # Try to initialize orchestrator to check if agents can be created
    try:
        from app.domain.orchestrator import get_orchestrator
        orchestrator = get_orchestrator()
        health_status["agents_initialized"] = True
    except Exception as e:
        health_status["agents_initialized"] = False
        health_status["error"] = str(e)
        health_status["status"] = "degraded"
    
    return health_status