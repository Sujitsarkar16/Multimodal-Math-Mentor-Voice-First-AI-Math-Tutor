"""
Custom exceptions for the application.
Provides clear error handling and domain-specific exceptions.
"""


class AgentError(Exception):
    """Base exception for all agent-related errors."""
    pass


class ParsingError(AgentError):
    """Raised when parsing fails."""
    pass


class SolvingError(AgentError):
    """Raised when problem solving fails."""
    pass


class VerificationError(AgentError):
    """Raised when verification fails."""
    pass


class GuardrailViolation(AgentError):
    """Raised when safety guardrails are violated."""
    pass


class RAGError(Exception):
    """Base exception for RAG-related errors."""
    pass


class RetrievalError(RAGError):
    """Raised when context retrieval fails."""
    pass


class EmbeddingError(RAGError):
    """Raised when embedding generation fails."""
    pass
