"""
LangChain-based RAG (Retrieval-Augmented Generation) system.
Handles vector storage and retrieval for context-aware problem solving.
"""

from typing import List, Optional, Dict, Any
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from app.settings import settings
from app.core.logger import setup_logger
from app.core.exceptions import RAGError, RetrievalError


logger = setup_logger(__name__)


class RAGRetriever:
    """
    Retrieval-Augmented Generation system for context retrieval.
    Uses FAISS for efficient similarity search.
    """
    
    def __init__(self):
        """Initialize the RAG retriever."""
        if not settings.GEMINI_API_KEY:
            logger.warning("GEMINI_API_KEY not set - RAG features will not work")
        
        try:
            self.embeddings = GoogleGenerativeAIEmbeddings(
                model=settings.EMBEDDING_MODEL,
                google_api_key=settings.GEMINI_API_KEY
            )
            self.vectorstore: Optional[FAISS] = None
            self._is_initialized = False
            
            logger.info("RAG Retriever initialized")
        except Exception as e:
            logger.error(f"Failed to initialize RAG retriever: {str(e)}")
            raise
    
    def initialize_with_documents(self, documents: List[Dict[str, Any]]):
        """
        Initialize vector store with documents.
        
        Args:
            documents: List of documents with 'content' and 'metadata'
        """
        try:
            if not documents:
                logger.warning("No documents provided for RAG initialization")
                return
            
            # Convert to LangChain documents
            docs = [
                Document(
                    page_content=doc.get("content", ""),
                    metadata=doc.get("metadata", {})
                )
                for doc in documents
            ]
            
            # Create vector store
            self.vectorstore = FAISS.from_documents(docs, self.embeddings)
            self._is_initialized = True
            
            logger.info(f"Vector store initialized with {len(documents)} documents")
            
        except Exception as e:
            logger.error(f"Failed to initialize vector store: {str(e)}")
            raise RAGError(f"Vector store initialization failed: {str(e)}")
    
    def add_documents(self, documents: List[Dict[str, Any]]):
        """
        Add new documents to existing vector store.
        
        Args:
            documents: List of documents to add
        """
        try:
            if not self._is_initialized:
                self.initialize_with_documents(documents)
                return
            
            docs = [
                Document(
                    page_content=doc.get("content", ""),
                    metadata=doc.get("metadata", {})
                )
                for doc in documents
            ]
            
            self.vectorstore.add_documents(docs)
            logger.info(f"Added {len(documents)} documents to vector store")
            
        except Exception as e:
            logger.error(f"Failed to add documents: {str(e)}")
            raise RAGError(f"Document addition failed: {str(e)}")
    
    def retrieve(
        self,
        query: str,
        k: Optional[int] = None,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[str]:
        """
        Retrieve relevant context for a query.
        
        Args:
            query: Search query
            k: Number of results (defaults to settings)
            filter_metadata: Optional metadata filter
            
        Returns:
            List of relevant context strings
        """
        if not self._is_initialized or self.vectorstore is None:
            logger.warning("Vector store not initialized, returning empty context")
            return []
        
        try:
            k = k or settings.TOP_K_RESULTS
            
            # Perform similarity search
            docs = self.vectorstore.similarity_search(
                query,
                k=k,
                filter=filter_metadata
            )
            
            # Extract content
            contexts = [doc.page_content for doc in docs]
            
            logger.info(f"Retrieved {len(contexts)} relevant contexts")
            return contexts
            
        except Exception as e:
            logger.error(f"Retrieval failed: {str(e)}")
            raise RetrievalError(f"Context retrieval failed: {str(e)}")
    
    def retrieve_with_scores(
        self,
        query: str,
        k: Optional[int] = None,
        score_threshold: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve context with similarity scores.
        
        Args:
            query: Search query
            k: Number of results
            score_threshold: Minimum similarity score
            
        Returns:
            List of dicts with 'content' and 'score'
        """
        if not self._is_initialized or self.vectorstore is None:
            logger.warning("Vector store not initialized")
            return []
        
        try:
            k = k or settings.TOP_K_RESULTS
            threshold = score_threshold or settings.SIMILARITY_THRESHOLD
            
            # Search with scores
            docs_with_scores = self.vectorstore.similarity_search_with_score(
                query,
                k=k
            )
            
            # Filter by threshold and format
            results = [
                {
                    "content": doc.page_content,
                    "score": float(score),
                    "metadata": doc.metadata
                }
                for doc, score in docs_with_scores
                if score >= threshold
            ]
            
            logger.info(f"Retrieved {len(results)} contexts above threshold {threshold}")
            return results
            
        except Exception as e:
            logger.error(f"Scored retrieval failed: {str(e)}")
            raise RetrievalError(f"Scored retrieval failed: {str(e)}")
    
    def clear(self):
        """Clear the vector store."""
        self.vectorstore = None
        self._is_initialized = False
        logger.info("Vector store cleared")


# Singleton instance
_rag_retriever: Optional[RAGRetriever] = None


def get_rag_retriever() -> RAGRetriever:
    """Get or create the singleton RAG retriever instance."""
    global _rag_retriever
    if _rag_retriever is None:
        _rag_retriever = RAGRetriever()
    return _rag_retriever
