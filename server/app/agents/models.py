"""
Data models for agent inputs and outputs.
Provides type safety and validation using Pydantic.
"""

from typing import List, Optional, Dict, Any, Literal
from pydantic import BaseModel, Field
from app.agents.base import AgentInput, AgentOutput


# ============================================================================
# Input Verifier Agent Models (NEW - runs before Parser)
# ============================================================================

class InputVerifierInput(AgentInput):
    """Input for the Input Verifier Agent."""
    extracted_text: str = Field(..., description="Text extracted from OCR/ASR")
    extraction_confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence from OCR/ASR")
    input_type: str = Field(..., description="Source type: 'ocr', 'asr', or 'text'")
    warnings: List[str] = Field(default_factory=list, description="Warnings from extraction")
    needs_confirmation: bool = Field(default=False, description="Flag from extractor")


class InputVerifierOutput(AgentOutput):
    """Output from the Input Verifier Agent."""
    is_valid: bool = Field(..., description="Whether extraction quality is acceptable")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Verified confidence")
    requires_human_review: bool = Field(default=False, description="Needs HITL before proceeding")
    hitl_reason: Optional[str] = Field(None, description="Reason for HITL trigger")
    verified_text: str = Field(..., description="Text to proceed with (may be same as input)")
    quality_issues: List[str] = Field(default_factory=list, description="Identified quality issues")
    can_proceed: bool = Field(default=True, description="Whether pipeline can proceed")


# ============================================================================
# Parser Agent Models
# ============================================================================

class ParserInput(AgentInput):
    """Input for the Parser Agent."""
    raw_text: str = Field(..., description="Raw problem text")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")


class ParserOutput(AgentOutput):
    """Output from the Parser Agent."""
    problem_text: str = Field(..., description="Cleaned problem text")
    topic: str = Field(..., description="Identified topic/domain")
    variables: List[str] = Field(default_factory=list, description="Extracted variables")
    constraints: List[str] = Field(default_factory=list, description="Identified constraints")
    needs_clarification: bool = Field(default=False, description="Whether clarification is needed")
    ambiguities: List[str] = Field(default_factory=list, description="Identified ambiguities")
    requires_human_review: bool = Field(default=False, description="HITL trigger from parser ambiguity")


# ============================================================================
# Intent Router Agent Models
# ============================================================================

class IntentRouterInput(AgentInput):
    """Input for the Intent Router Agent."""
    parsed_problem: ParserOutput


class IntentRouterOutput(AgentOutput):
    """Output from the Intent Router Agent."""
    problem_type: str = Field(..., description="Classified problem type")
    difficulty_level: Literal["easy", "medium", "hard"] = Field(..., description="Difficulty level")
    recommended_strategy: str = Field(..., description="Recommended solving strategy")
    requires_tools: List[str] = Field(default_factory=list, description="Tools needed")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Classification confidence")


# ============================================================================
# Solver Agent Models
# ============================================================================

class SolverInput(AgentInput):
    """Input for the Solver Agent."""
    parsed_problem: ParserOutput
    routing_info: IntentRouterOutput
    retrieved_context: Optional[List[str]] = Field(default=None, description="RAG context")


class SolverOutput(AgentOutput):
    """Output from the Solver Agent."""
    answer: str = Field(..., description="Final answer")
    solution_steps: List[str] = Field(default_factory=list, description="Solution steps")
    used_context: bool = Field(default=False, description="Whether RAG context was used")
    tools_used: List[str] = Field(default_factory=list, description="Tools used in solving")
    reasoning: str = Field(..., description="Reasoning process")


# ============================================================================
# Verifier Agent Models
# ============================================================================

class VerifierInput(AgentInput):
    """Input for the Verifier Agent."""
    original_problem: ParserOutput
    solution: SolverOutput


class VerifierOutput(AgentOutput):
    """Output from the Verifier Agent."""
    is_correct: bool = Field(..., description="Whether solution appears correct")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Verification confidence")
    correctness_issues: List[str] = Field(default_factory=list, description="Identified issues")
    unit_check_passed: bool = Field(default=True, description="Units are correct")
    domain_check_passed: bool = Field(default=True, description="Answer in valid domain")
    edge_cases_checked: List[str] = Field(default_factory=list, description="Edge cases verified")
    requires_human_review: bool = Field(default=False, description="Needs HITL")


# ============================================================================
# Explainer Agent Models
# ============================================================================

class ExplainerInput(AgentInput):
    """Input for the Explainer Agent."""
    original_problem: ParserOutput
    solution: SolverOutput
    verification: VerifierOutput


class ExplainerOutput(AgentOutput):
    """Output from the Explainer Agent."""
    explanation: str = Field(..., description="Student-friendly explanation")
    step_by_step: List[str] = Field(default_factory=list, description="Detailed steps")
    key_concepts: List[str] = Field(default_factory=list, description="Key concepts used")
    common_mistakes: List[str] = Field(default_factory=list, description="Common pitfalls")
    difficulty_rating: int = Field(..., ge=1, le=5, description="Difficulty 1-5")


# ============================================================================
# Guardrail Agent Models
# ============================================================================

class GuardrailInput(AgentInput):
    """Input for the Guardrail Agent."""
    raw_text: str
    context: Optional[str] = None


class GuardrailOutput(AgentOutput):
    """Output from the Guardrail Agent."""
    is_safe: bool = Field(..., description="Content is safe")
    violations: List[str] = Field(default_factory=list, description="Policy violations")
    risk_level: Literal["low", "medium", "high"] = Field(default="low", description="Risk level")
    should_continue: bool = Field(..., description="Whether to continue processing")


# ============================================================================
# Pipeline Models
# ============================================================================

class PipelineInput(BaseModel):
    """Input for the complete pipeline."""
    text: str = Field(..., description="Raw problem text")
    context: Optional[Dict[str, Any]] = Field(default=None, description="Additional context")
    enable_guardrails: bool = Field(default=True, description="Enable safety checks")


class AgentTrace(BaseModel):
    """Trace of a single agent execution."""
    agent_name: str
    input_summary: str
    output_summary: str
    execution_time_ms: float
    success: bool
    error: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Agent-specific metadata (e.g., self-learning status)")


class PipelineOutput(BaseModel):
    """Output from the complete pipeline."""
    final_answer: str
    explanation: str
    confidence: float
    requires_human_review: bool
    agent_trace: List[AgentTrace]
    retrieved_context: Optional[List[str]] = None
    metadata: Dict[str, Any] = {}
