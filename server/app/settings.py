"""
Application settings and configuration management.
Centralized configuration using pydantic-settings for type safety.
"""

import os
from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application configuration settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    # API Keys
    GEMINI_API_KEY: str = ""  # Required for production, set in .env
    OPENAI_API_KEY: Optional[str] = None
    
    # LLM Configuration
    DEFAULT_LLM_MODEL: str = "gemini-2.0-flash-exp"
    DEFAULT_TEMPERATURE: float = 0.2
    MAX_OUTPUT_TOKENS: int = 2000
    
    # Agent Configuration
    ENABLE_GUARDRAILS: bool = True
    MAX_RETRIES: int = 3
    USE_LANGCHAIN_REACT: bool = True  # Use LangChain ReAct agent for enhanced solving
    
    # HITL (Human-in-the-Loop) Confidence Thresholds
    # Standardized at 75% across all components
    OCR_CONFIDENCE_THRESHOLD: float = 0.75  # Trigger HITL if OCR confidence < 75%
    ASR_CONFIDENCE_THRESHOLD: float = 0.75  # Trigger HITL if ASR confidence < 75%
    VERIFIER_CONFIDENCE_THRESHOLD: float = 0.75  # Trigger HITL if Verifier confidence < 75%
    PARSER_AMBIGUITY_THRESHOLD: int = 1  # Trigger HITL if parser finds >= 1 ambiguity
    
    # RAG Configuration
    EMBEDDING_MODEL: str = "models/embedding-001"
    TOP_K_RESULTS: int = 5
    SIMILARITY_THRESHOLD: float = 0.75
    
    # Logging
    LOG_LEVEL: str = "INFO"
    ENABLE_TRACE_LOGGING: bool = False
    
    # Application
    APP_NAME: str = "AI_Planet_AutoGrader"
    APP_VERSION: str = "2.0.0"
    ENVIRONMENT: str = "development"


# Global settings instance
settings = Settings()
