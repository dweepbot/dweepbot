"""
RAG query tool for searching vector database.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseTool, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RAGQueryInput(BaseModel):
    """Input schema for RAG query."""
    query: str = Field(..., description="Query text")
    top_k: int = Field(default=5, ge=1, le=20, description="Number of results")
    collection: str = Field(default="default", description="Collection name")


class RAGQueryTool(BaseTool):
    """
    Query vector database for relevant context.
    
    Uses ChromaDB for semantic search over stored documents.
    """
    
    name = "rag_query"
    description = "Search vector database for relevant information"
    input_schema = RAGQueryInput
    
    def __init__(self, vector_store: Optional[Any] = None):
        """
        Initialize RAG query tool.
        
        Args:
            vector_store: Optional VectorMemory instance
        """
        super().__init__()
        self.vector_store = vector_store
    
    async def _execute(
        self,
        query: str,
        top_k: int = 5,
        collection: str = "default",
    ) -> Dict[str, Any]:
        """
        Query vector database.
        
        Args:
            query: Search query
            top_k: Number of results to return
            collection: Collection to search
        
        Returns:
            Dict with search results
        """
        if not self.vector_store:
            raise ToolError("Vector store not configured")
        
        logger.info("Querying vector store", query=query[:100], top_k=top_k)
        
        try:
            # Query vector store
            results = await self.vector_store.query(
                query_text=query,
                top_k=top_k,
                collection=collection,
            )
            
            logger.info("RAG query complete", results_count=len(results))
            
            return {
                "query": query,
                "results": results,
                "count": len(results),
            }
            
        except Exception as e:
            logger.error("RAG query failed", error=str(e))
            raise ToolError(f"Vector search failed: {str(e)}")
