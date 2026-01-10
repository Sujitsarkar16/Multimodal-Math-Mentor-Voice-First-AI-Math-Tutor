"""
FastAPI application entry point.
Multi-agent mathematical problem solver API.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.router import router
from app.settings import settings
from app.core.logger import setup_logger
from app.rag.knowledge_loader import initialize_rag_with_knowledge_base


logger = setup_logger(__name__)


# Application metadata
app = FastAPI(
    title=settings.APP_NAME,
    description="Multi-Agent Mathematical Problem Solver with LangChain",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS middleware (configure as needed)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000", "*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routers
app.include_router(router)


@app.get("/", tags=["Health"])
def root():
    """Root endpoint - API information."""
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "environment": settings.ENVIRONMENT
    }


@app.get("/health", tags=["Health"])
def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "service": "multi-agent-solver",
        "version": settings.APP_VERSION
    }


@app.on_event("startup")
async def startup_event():
    """Application startup event."""
    logger.info(f"Starting {settings.APP_NAME} v{settings.APP_VERSION}")
    logger.info(f"Environment: {settings.ENVIRONMENT}")
    logger.info(f"Guardrails enabled: {settings.ENABLE_GUARDRAILS}")
    
    # Initialize RAG with knowledge base
    if initialize_rag_with_knowledge_base():
        logger.info("Knowledge base loaded successfully")
    else:
        logger.warning("Knowledge base initialization failed - RAG may not work properly")


@app.on_event("shutdown")
async def shutdown_event():
    """Application shutdown event."""
    logger.info(f"Shutting down {settings.APP_NAME}")


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level=settings.LOG_LEVEL.lower()
    )
