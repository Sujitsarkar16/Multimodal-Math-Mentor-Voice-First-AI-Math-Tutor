"""
Main problem-solving pipeline.
Clean interface to the multi-agent system.
"""

from typing import Dict, Any, AsyncGenerator, Optional, Callable
from app.domain.orchestrator import get_orchestrator
from app.domain.async_orchestrator import get_async_orchestrator
from app.agents.models import PipelineInput, PipelineOutput
from app.core.logger import setup_logger


logger = setup_logger(__name__)


def solve_problem(
    text: str,
    context: Dict[str, Any] = None,
    enable_guardrails: bool = True
) -> Dict[str, Any]:
    """
    Solve a mathematical problem using the multi-agent system.
    
    Args:
        text: Problem statement
        context: Optional additional context
        enable_guardrails: Whether to enable safety checks
        
    Returns:
        Dictionary with solution and metadata
    """
    logger.info(f"Solving problem: {text[:100]}...")
    
    try:
        # Get orchestrator
        orchestrator = get_orchestrator()
        
        # Create pipeline input
        pipeline_input = PipelineInput(
            text=text,
            context=context,
            enable_guardrails=enable_guardrails
        )
        
        # Execute pipeline
        result: PipelineOutput = orchestrator.execute_pipeline(pipeline_input)
        
        # Convert to dict for API response
        output = {
            "final_answer": result.final_answer,
            "explanation": result.explanation,
            "confidence": result.confidence,
            "requires_human_review": result.requires_human_review,
            "retrieved_context": result.retrieved_context or [],
            "agent_trace": [
                {
                    "agent": trace.agent_name,
                    "input": trace.input_summary,
                    "output": trace.output_summary,
                    "time_ms": trace.execution_time_ms,
                    "success": trace.success,
                    "error": trace.error,
                    "metadata": trace.metadata  # Include agent-specific metadata
                }
                for trace in result.agent_trace
            ],
            "metadata": {
                **result.metadata,
                "parsed_question": result.metadata.get("problem_text", "")
            }
        }
        
        logger.info(f"Problem solved successfully - Confidence: {result.confidence:.2f}")
        return output
        
    except Exception as e:
        logger.error(f"Problem solving failed: {str(e)}", exc_info=True)
        raise


async def solve_problem_async(
    text: str,
    context: Dict[str, Any] = None,
    enable_guardrails: bool = True,
    progress_callback: Optional[Callable] = None
) -> Dict[str, Any]:
    """
    Solve a mathematical problem using async multi-agent system with parallel execution.
    
    Args:
        text: Problem statement
        context: Optional additional context
        enable_guardrails: Whether to enable safety checks
        progress_callback: Optional callback for progress updates
        
    Returns:
        Dictionary with solution and metadata
    """
    logger.info(f"Solving problem async: {text[:100]}...")
    
    try:
        # Get async orchestrator with progress callback
        orchestrator = get_async_orchestrator(progress_callback)
        
        # Create pipeline input
        pipeline_input = PipelineInput(
            text=text,
            context=context,
            enable_guardrails=enable_guardrails
        )
        
        # Execute pipeline asynchronously
        result: PipelineOutput = await orchestrator.execute_pipeline(pipeline_input)
        
        # Convert to dict for API response
        output = {
            "final_answer": result.final_answer,
            "explanation": result.explanation,
            "confidence": result.confidence,
            "requires_human_review": result.requires_human_review,
            "retrieved_context": result.retrieved_context or [],
            "agent_trace": [
                {
                    "agent": trace.agent_name,
                    "input": trace.input_summary,
                    "output": trace.output_summary,
                    "time_ms": trace.execution_time_ms,
                    "success": trace.success,
                    "error": trace.error,
                    "metadata": trace.metadata  # Include agent-specific metadata (e.g., self-learning)
                }
                for trace in result.agent_trace
            ],
            "metadata": {
                **result.metadata,
                "parsed_question": result.metadata.get("problem_text", "")
            }
        }
        
        logger.info(f"Problem solved async successfully - Confidence: {result.confidence:.2f}")
        return output
        
    except Exception as e:
        logger.error(f"Async problem solving failed: {str(e)}", exc_info=True)
        raise


async def solve_problem_streaming(
    text: str,
    context: Dict[str, Any] = None,
    enable_guardrails: bool = True
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Solve a mathematical problem with streaming progress updates.
    
    Args:
        text: Problem statement
        context: Optional additional context
        enable_guardrails: Whether to enable safety checks
        
    Yields:
        Progress updates and final result
    """
    import asyncio
    from queue import Queue
    
    progress_queue = asyncio.Queue()
    is_cancelled = False
    
    async def progress_callback(agent_name: str, status: str, data: Any):
        """Callback to capture progress including metadata for self-learning."""
        if is_cancelled:
            return
        await progress_queue.put({
            "type": "agent_update",
            "agent": agent_name,
            "status": status,
            "data": {
                "input": data.input_summary if data and hasattr(data, 'input_summary') else "",
                "output": data.output_summary if data and hasattr(data, 'output_summary') else "",
                "time_ms": data.execution_time_ms if data and hasattr(data, 'execution_time_ms') else 0,
                "success": data.success if data and hasattr(data, 'success') else True,
                "error": data.error if data and hasattr(data, 'error') else None,
                "metadata": data.metadata if data and hasattr(data, 'metadata') else {}
            }
        })
    
    # Start solving in background
    solve_task = asyncio.create_task(
        solve_problem_async(text, context, enable_guardrails, progress_callback)
    )
    
    try:
        # Stream progress updates
        while not solve_task.done():
            try:
                # Get progress update with timeout
                update = await asyncio.wait_for(progress_queue.get(), timeout=0.1)
                yield update
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                is_cancelled = True
                solve_task.cancel()
                raise
        
        # Get any remaining updates
        while not progress_queue.empty():
            update = await progress_queue.get()
            yield update
        
        # Get final result
        try:
            result = await solve_task
            yield {
                "type": "final_result",
                "data": result
            }
        except asyncio.CancelledError:
            logger.info("Solve task was cancelled")
            yield {
                "type": "cancelled",
                "message": "Operation was cancelled"
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": str(e)
            }
    except asyncio.CancelledError:
        is_cancelled = True
        if not solve_task.done():
            solve_task.cancel()
            try:
                await solve_task
            except asyncio.CancelledError:
                pass
        logger.info("Streaming pipeline was cancelled")
        yield {
            "type": "cancelled",
            "message": "Operation was cancelled"
        }


def get_pipeline_stats() -> Dict[str, Any]:
    """Get statistics about pipeline executions."""
    orchestrator = get_orchestrator()
    return orchestrator.get_statistics()
