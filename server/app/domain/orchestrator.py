"""
Multi-Agent Orchestrator - Coordinates agent execution workflow.
Manages the complete problem-solving pipeline with proper error handling.
"""

import time
from typing import Optional, Dict, Any
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


logger = setup_logger(__name__)


class AgentOrchestrator:
    """
    Orchestrates the multi-agent workflow for problem solving.
    Manages agent dependencies, error handling, and execution tracking.
    """
    
    def __init__(self):
        """Initialize all agents."""
        self.parser = ParserAgent()
        self.router = IntentRouterAgent()
        self.solver = SolverAgent()
        self.verifier = VerifierAgent()
        self.explainer = ExplainerAgent()
        self.guardrail = GuardrailAgent()
        
        self.trace = []
        logger.info("Agent Orchestrator initialized with 6 agents")
    
    def execute_pipeline(self, input_data: PipelineInput) -> PipelineOutput:
        """
        Execute the complete multi-agent pipeline.
        
        Args:
            input_data: Pipeline input with problem text
            
        Returns:
            PipelineOutput with solution and metadata
        """
        self.trace = []
        logger.info(f"Starting pipeline execution for input: {input_data.text[:100]}...")
        
        try:
            # Step 1: Guardrail Check (if enabled)
            if input_data.enable_guardrails and settings.ENABLE_GUARDRAILS:
                guardrail_result = self._execute_agent(
                    self.guardrail,
                    GuardrailInput(raw_text=input_data.text)
                )
                
                if not guardrail_result.should_continue:
                    raise GuardrailViolation(
                        f"Content policy violation: {', '.join(guardrail_result.violations)}"
                    )
            
            # Step 2: Parser Agent
            parsed = self._execute_agent(
                self.parser,
                ParserInput(raw_text=input_data.text, context=input_data.context)
            )
            
            # Step 3: Intent Router Agent
            routing = self._execute_agent(
                self.router,
                IntentRouterInput(parsed_problem=parsed)
            )
            
            # Step 4: Solver Agent
            solution = self._execute_agent(
                self.solver,
                SolverInput(
                    parsed_problem=parsed,
                    routing_info=routing,
                    retrieved_context=None  # RAG retrieval happens inside solver
                )
            )
            
            # Step 5: Verifier Agent
            verification = self._execute_agent(
                self.verifier,
                VerifierInput(original_problem=parsed, solution=solution)
            )
            
            # Step 6: Explainer Agent
            explanation = self._execute_agent(
                self.explainer,
                ExplainerInput(
                    original_problem=parsed,
                    solution=solution,
                    verification=verification
                )
            )
            
            # Build final output
            # Combine HITL triggers from all agents:
            # 1. Parser ambiguity detected
            # 2. Verifier low confidence
            hitl_reasons = []
            if parsed.requires_human_review:
                hitl_reasons.append("parser_ambiguity")
            if verification.requires_human_review:
                hitl_reasons.append("verifier_low_confidence")
            
            requires_hitl = len(hitl_reasons) > 0
            
            output = PipelineOutput(
                final_answer=solution.answer,
                explanation=explanation.explanation,
                confidence=verification.confidence,
                requires_human_review=requires_hitl,
                agent_trace=self.trace,
                retrieved_context=None,  # Could expose from solver if needed
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
                    "hitl_reasons": hitl_reasons,  # Track why HITL was triggered
                    "parser_ambiguities": parsed.ambiguities,
                    "verifier_issues": verification.correctness_issues
                }
            )
            
            logger.info(
                f"Pipeline completed - Confidence: {output.confidence:.2f}, "
                f"HITL: {output.requires_human_review} (reasons: {hitl_reasons})"
            )
            
            return output
            
        except GuardrailViolation as e:
            logger.warning(f"Guardrail violation: {str(e)}")
            raise
            
        except Exception as e:
            logger.error(f"Pipeline execution failed: {str(e)}", exc_info=True)
            raise AgentError(f"Pipeline failed: {str(e)}")
    
    def _execute_agent(self, agent, input_data):
        """
        Execute a single agent with timing and tracing.
        
        Args:
            agent: Agent instance
            input_data: Agent input
            
        Returns:
            Agent output
        """
        start_time = time.time()
        
        try:
            result = agent.run(input_data)
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
            
            return result
            
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
            
            raise
    
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
            "total_executions": len(self.trace)
        }


# Singleton instance
_orchestrator: Optional[AgentOrchestrator] = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create the singleton orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator
