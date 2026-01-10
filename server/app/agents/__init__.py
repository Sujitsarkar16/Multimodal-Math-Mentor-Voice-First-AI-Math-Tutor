"""
Multi-Agent System for Mathematical Problem Solving.

Exports all agent classes and orchestrator for easy imports.
"""

from app.agents.base import BaseAgent, AgentInput, AgentOutput
from app.agents.parser import ParserAgent
from app.agents.router import IntentRouterAgent
from app.agents.solver import SolverAgent
from app.agents.verifier import VerifierAgent
from app.agents.explainer import ExplainerAgent
from app.agents.guardrail import GuardrailAgent
from app.agents.input_verifier import InputVerifierAgent

__all__ = [
    # Base classes
    "BaseAgent",
    "AgentInput",
    "AgentOutput",
    
    # Agent implementations
    "InputVerifierAgent",  # NEW: Validates OCR/ASR before parsing
    "ParserAgent",
    "IntentRouterAgent",
    "SolverAgent",
    "VerifierAgent",
    "ExplainerAgent",
    "GuardrailAgent",
]

