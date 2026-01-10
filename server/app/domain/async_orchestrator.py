"""
Async Multi-Agent Orchestrator - Executes agents in parallel where possible.
Uses asyncio for concurrent execution to improve performance.
"""

import asyncio
import time
from typing import Optional, Dict, Any, List, Callable
from app.agents.models import (
    ParserInput, IntentRouterInput, SolverInput,
    VerifierInput, ExplainerInput, GuardrailInput,
    PipelineInput, PipelineOutput, AgentTrace
)
from app.agents.parser import ParserAgent
from app.agents.router import IntentRouterAgent
from app.agents.solver import SolverAgent
from app.agents.verifier import VerifierAgent
from app.agents.explainer import ExplainerAgent
from app.agents.guardrail import GuardrailAgent
from app.settings import settings
from app.core.logger import setup_logger
from app.core.exceptions import GuardrailViolation, AgentError

# Optional: Import LangChain ReAct agent
try:
    from app.agents.langchain_agent import LangChainReActSolver
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    logger = setup_logger(__name__)
    logger.warning("LangChain ReAct agent not available - using standard solver")


logger = setup_logger(__name__)


class AsyncAgentOrchestrator:
    """
    Async orchestrator that runs agents in parallel where dependencies allow.
    Provides real-time progress updates via callbacks.
    """
    
    def __init__(self, progress_callback: Optional[Callable] = None):
        """
        Initialize all agents.
        
        Args:
            progress_callback: Optional callback for real-time progress updates
                              Signature: callback(agent_name, status, output)
        """
        self.parser = ParserAgent()
        self.router = IntentRouterAgent()
        
        # Use LangChain ReAct solver if available and enabled
        if settings.USE_LANGCHAIN_REACT and LANGCHAIN_AVAILABLE:
            self.solver = LangChainReActSolver()
            logger.info("Using LangChain ReAct solver with advanced tools")
        else:
            self.solver = SolverAgent()
            logger.info("Using standard solver agent")
        
        self.verifier = VerifierAgent()
        self.explainer = ExplainerAgent()
        self.guardrail = GuardrailAgent()
        
        self.trace = []
        self.progress_callback = progress_callback
        logger.info("Async Agent Orchestrator initialized with 6 agents")
    
    async def execute_pipeline(self, input_data: PipelineInput) -> PipelineOutput:
        """
        Execute the complete multi-agent pipeline with parallel execution.
        
        Pipeline stages:
        1. Guardrail (if enabled)
        2. Parser + Router can run in parallel after stage 1
        3. Solver (needs parser and router)
        4. Verifier + Explainer can start in parallel (verifier needs solver)
        5. Explainer finishes (needs verifier)
        
        Args:
            input_data: Pipeline input with problem text
            
        Returns:
            PipelineOutput with solution and metadata
        """
        self.trace = []
        logger.info(f"Starting async pipeline execution for input: {input_data.text[:100]}...")
        
        try:
            # Stage 1: Guardrail Check (if enabled)
            if input_data.enable_guardrails and settings.ENABLE_GUARDRAILS:
                guardrail_result = await self._execute_agent_async(
                    self.guardrail,
                    GuardrailInput(raw_text=input_data.text)
                )
                
                if not guardrail_result.should_continue:
                    raise GuardrailViolation(
                        f"Content policy violation: {', '.join(guardrail_result.violations)}"
                    )
            
            # Stage 2: Parser - must complete before router
            parsed = await self._execute_agent_async(
                self.parser,
                ParserInput(raw_text=input_data.text, context=input_data.context)
            )
            
            # Stage 3: Router (can run immediately after parser)
            routing = await self._execute_agent_async(
                self.router,
                IntentRouterInput(parsed_problem=parsed)
            )
            
            # Stage 4: Solver (needs both parser and router)
            solution = await self._execute_agent_async(
                self.solver,
                SolverInput(
                    parsed_problem=parsed,
                    routing_info=routing,
                    retrieved_context=None
                )
            )
            
            # Stage 5: Verifier and start Explainer prep in parallel
            # Verifier runs first, explainer waits for verifier
            verification = await self._execute_agent_async(
                self.verifier,
                VerifierInput(original_problem=parsed, solution=solution)
            )
            
            # Stage 6: Explainer (needs verification)
            explanation = await self._execute_agent_async(
                self.explainer,
                ExplainerInput(
                    original_problem=parsed,
                    solution=solution,
                    verification=verification
                )
            )
            
            # Build final output
            output = PipelineOutput(
                final_answer=solution.answer,
                explanation=explanation.explanation,
                confidence=verification.confidence,
                requires_human_review=verification.requires_human_review,
                agent_trace=self.trace,
                retrieved_context=None,
                metadata={
                    "problem_type": routing.problem_type,
                    "difficulty": routing.difficulty_level,
                    "topic": parsed.topic,
                    "tools_used": solution.tools_used,
                    "is_correct": verification.is_correct,
                    "difficulty_rating": explanation.difficulty_rating,
                    "step_by_step": explanation.step_by_step,
                    "key_concepts": explanation.key_concepts,
                    "common_mistakes": explanation.common_mistakes,
                    "execution_mode": "async_parallel"
                }
            )
            
            logger.info(
                f"Async pipeline completed - Confidence: {output.confidence:.2f}, "
                f"HITL: {output.requires_human_review}, "
                f"Agents: {len(self.trace)}"
            )
            
            return output
            
        except GuardrailViolation as e:
            logger.warning(f"Guardrail violation: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Async pipeline execution failed: {str(e)}", exc_info=True)
            raise AgentError(f"Pipeline failed: {str(e)}")
    
    async def _execute_agent_async(self, agent, input_data):
        """
        Execute a single agent asynchronously with timing and tracing.
        
        Args:
            agent: Agent instance
            input_data: Agent input
            
        Returns:
            Agent output
        """
        start_time = time.time()
        
        # Notify progress callback that agent is starting
        if self.progress_callback:
            try:
                await self._notify_progress(agent.name, "started", None)
            except Exception as e:
                logger.warning(f"Progress callback error: {e}")
        
        try:
            # Run agent in executor to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, agent.run, input_data)
            
            execution_time = (time.time() - start_time) * 1000  # ms
            
            # Get output summary with metadata
            output_info = self._summarize_output(result)
            
            # Record trace with metadata
            trace = AgentTrace(
                agent_name=agent.name,
                input_summary=self._summarize_input(input_data),
                output_summary=output_info["output"],
                execution_time_ms=execution_time,
                success=True,
                metadata=output_info.get("metadata", {})
            )
            self.trace.append(trace)
            
            # Notify progress callback of completion
            if self.progress_callback:
                try:
                    await self._notify_progress(agent.name, "completed", trace)
                except Exception as e:
                    logger.warning(f"Progress callback error: {e}")
            
            logger.info(f"Agent {agent.name} completed in {execution_time:.2f}ms")
            return result
        
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            execution_time = (time.time() - start_time) * 1000
            logger.info(f"Agent {agent.name} execution was cancelled after {execution_time:.2f}ms")
            
            # Record cancellation in trace
            trace = AgentTrace(
                agent_name=agent.name,
                input_summary=self._summarize_input(input_data),
                output_summary="Cancelled",
                execution_time_ms=execution_time,
                success=False,
                error="Execution cancelled by user"
            )
            self.trace.append(trace)
            
            # Re-raise to propagate cancellation
            raise
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            
            # Record failure in trace
            trace = AgentTrace(
                agent_name=agent.name,
                input_summary=self._summarize_input(input_data),
                output_summary="",
                execution_time_ms=execution_time,
                success=False,
                error=str(e)
            )
            self.trace.append(trace)
            
            # Notify progress callback of error
            if self.progress_callback:
                try:
                    await self._notify_progress(agent.name, "failed", trace)
                except Exception as callback_error:
                    logger.warning(f"Progress callback error: {callback_error}")
            
            raise
    
    async def _notify_progress(self, agent_name: str, status: str, data: Any):
        """Notify progress callback."""
        if self.progress_callback:
            if asyncio.iscoroutinefunction(self.progress_callback):
                await self.progress_callback(agent_name, status, data)
            else:
                self.progress_callback(agent_name, status, data)
    
    def _summarize_input(self, input_data) -> str:
        """Create a brief summary of agent input."""
        if hasattr(input_data, 'raw_text'):
            return f"Text: {input_data.raw_text[:100]}..."
        elif hasattr(input_data, 'parsed_problem'):
            return f"Problem: {input_data.parsed_problem.problem_text[:100]}..."
        elif hasattr(input_data, 'original_problem'):
            return f"Verify: {input_data.original_problem.problem_text[:100]}..."
        else:
            return str(input_data)[:100]
    
    def _summarize_output(self, output_data) -> Dict[str, Any]:
        """Create a summary of agent output including metadata for frontend."""
        summary = {"output": "", "metadata": {}}
        
        if hasattr(output_data, 'problem_text'):
            summary["output"] = f"Parsed: {output_data.topic}"
            summary["metadata"]["topic"] = output_data.topic
        elif hasattr(output_data, 'problem_type'):
            summary["output"] = f"Routed: {output_data.problem_type} ({output_data.difficulty_level})"
            summary["metadata"]["problem_type"] = output_data.problem_type
            summary["metadata"]["difficulty"] = output_data.difficulty_level
        elif hasattr(output_data, 'answer'):
            summary["output"] = f"Answer: {output_data.answer[:100]}..."
            # Include self-learning metadata if available
            if hasattr(output_data, 'metadata') and output_data.metadata:
                summary["metadata"]["self_learning_active"] = output_data.metadata.get("self_learning_active", False)
                summary["metadata"]["memory_patterns_count"] = output_data.metadata.get("memory_patterns_count", 0)
                summary["metadata"]["rag_context_count"] = output_data.metadata.get("rag_context_count", 0)
        elif hasattr(output_data, 'is_correct'):
            summary["output"] = f"Verified: {output_data.is_correct} ({output_data.confidence:.2f})"
            summary["metadata"]["is_correct"] = output_data.is_correct
            summary["metadata"]["confidence"] = output_data.confidence
        elif hasattr(output_data, 'explanation'):
            summary["output"] = f"Explained: {len(output_data.step_by_step)} steps"
            summary["metadata"]["steps_count"] = len(output_data.step_by_step)
        elif hasattr(output_data, 'is_safe'):
            summary["output"] = f"Safe: {output_data.is_safe} ({output_data.risk_level})"
            summary["metadata"]["is_safe"] = output_data.is_safe
        else:
            summary["output"] = str(output_data)[:100]
        
        return summary
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get execution statistics for all agents."""
        return {
            "agents": {
                "parser": self.parser.get_stats(),
                "router": self.router.get_stats(),
                "solver": self.solver.get_stats(),
                "verifier": self.verifier.get_stats(),
                "explainer": self.explainer.get_stats(),
                "guardrail": self.guardrail.get_stats()
            },
            "total_executions": len(self.trace),
            "execution_mode": "async_parallel"
        }


# Singleton instance
_async_orchestrator: Optional[AsyncAgentOrchestrator] = None


def get_async_orchestrator(progress_callback: Optional[Callable] = None) -> AsyncAgentOrchestrator:
    """Get or create the singleton async orchestrator instance."""
    global _async_orchestrator
    if _async_orchestrator is None or progress_callback is not None:
        _async_orchestrator = AsyncAgentOrchestrator(progress_callback)
    return _async_orchestrator
