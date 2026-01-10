"""
Knowledge Base Loader - Initializes RAG with curated math documents.
Loads knowledge base on application startup.
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from app.rag.retriever import get_rag_retriever
from app.core.logger import setup_logger


logger = setup_logger(__name__)

# Path to knowledge base JSON file
KNOWLEDGE_BASE_PATH = Path(__file__).parent.parent / "data" / "math_knowledge.json"


def load_knowledge_base(file_path: Optional[Path] = None) -> List[Dict[str, Any]]:
    """
    Load knowledge base documents from JSON file.
    
    Args:
        file_path: Optional custom path to knowledge base file
        
    Returns:
        List of document dictionaries with 'content' and 'metadata'
    """
    path = file_path or KNOWLEDGE_BASE_PATH
    
    try:
        if not path.exists():
            logger.warning(f"Knowledge base file not found: {path}")
            return []
        
        with open(path, 'r', encoding='utf-8') as f:
            raw_documents = json.load(f)
        
        # Transform to RAG format
        documents = [
            {
                "content": doc.get("content", ""),
                "metadata": {
                    "id": doc.get("id", f"doc_{i}"),
                    **doc.get("metadata", {})
                }
            }
            for i, doc in enumerate(raw_documents)
        ]
        
        logger.info(f"Loaded {len(documents)} documents from knowledge base")
        return documents
        
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in knowledge base: {e}")
        return []
    except Exception as e:
        logger.error(f"Failed to load knowledge base: {e}")
        return []


def initialize_rag_with_knowledge_base() -> bool:
    """
    Initialize the RAG retriever with knowledge base documents.
    Called on application startup.
    
    Returns:
        True if initialization successful, False otherwise
    """
    try:
        # Load documents
        documents = load_knowledge_base()
        
        if not documents:
            logger.warning("No documents loaded - RAG will operate without knowledge base")
            return False
        
        # Get retriever and initialize
        retriever = get_rag_retriever()
        retriever.initialize_with_documents(documents)
        
        logger.info(f"RAG initialized with {len(documents)} knowledge base documents")
        return True
        
    except Exception as e:
        logger.error(f"Failed to initialize RAG with knowledge base: {e}")
        return False


def add_document_to_knowledge_base(document: Dict[str, Any]) -> bool:
    """
    Add a new document to the RAG system at runtime.
    
    Args:
        document: Dictionary with 'content' and optional 'metadata'
        
    Returns:
        True if added successfully
    """
    try:
        retriever = get_rag_retriever()
        retriever.add_documents([document])
        logger.info(f"Added document to knowledge base")
        return True
    except Exception as e:
        logger.error(f"Failed to add document: {e}")
        return False
