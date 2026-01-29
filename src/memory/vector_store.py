"""
Vector store implementation using ChromaDB.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional
from .schemas import VectorDocument, QueryResult
from ..utils.logger import get_logger

logger = get_logger(__name__)


class VectorMemory:
    """
    Vector database for long-term memory using ChromaDB.
    
    Features:
    - Semantic search over documents
    - Persistent storage
    - Multiple collections
    - Automatic embeddings
    """
    
    def __init__(
        self,
        persist_directory: Optional[Path] = None,
        collection_name: str = "default",
    ):
        """
        Initialize vector memory.
        
        Args:
            persist_directory: Directory for persistent storage
            collection_name: Name of the collection to use
        """
        self.persist_directory = persist_directory or Path("./chroma_db")
        self.collection_name = collection_name
        self._client = None
        self._collection = None
        
        try:
            import chromadb
            self._chromadb = chromadb
        except ImportError:
            logger.warning(
                "ChromaDB not installed. Install with: pip install chromadb"
            )
            self._chromadb = None
    
    def _ensure_initialized(self) -> None:
        """Ensure ChromaDB client is initialized."""
        if not self._chromadb:
            raise RuntimeError(
                "ChromaDB not available. Install with: pip install chromadb"
            )
        
        if not self._client:
            self._client = self._chromadb.PersistentClient(
                path=str(self.persist_directory)
            )
            
            # Get or create collection
            self._collection = self._client.get_or_create_collection(
                name=self.collection_name,
                metadata={"description": "DweepBot agent memory"},
            )
            
            logger.info(
                "Vector store initialized",
                collection=self.collection_name,
                persist_dir=str(self.persist_directory),
            )
    
    async def add_document(
        self,
        document: VectorDocument,
    ) -> None:
        """
        Add a document to the vector store.
        
        Args:
            document: Document to add
        """
        self._ensure_initialized()
        
        try:
            self._collection.add(
                ids=[document.id],
                documents=[document.text],
                metadatas=[document.metadata],
            )
            
            logger.info("Document added", doc_id=document.id, text_length=len(document.text))
            
        except Exception as e:
            logger.error("Failed to add document", error=str(e))
            raise
    
    async def add_documents(
        self,
        documents: List[VectorDocument],
    ) -> None:
        """
        Add multiple documents to the vector store.
        
        Args:
            documents: List of documents to add
        """
        self._ensure_initialized()
        
        if not documents:
            return
        
        try:
            self._collection.add(
                ids=[doc.id for doc in documents],
                documents=[doc.text for doc in documents],
                metadatas=[doc.metadata for doc in documents],
            )
            
            logger.info("Documents added", count=len(documents))
            
        except Exception as e:
            logger.error("Failed to add documents", error=str(e))
            raise
    
    async def query(
        self,
        query_text: str,
        top_k: int = 5,
        collection: Optional[str] = None,
    ) -> List[QueryResult]:
        """
        Query the vector store for similar documents.
        
        Args:
            query_text: Text to search for
            top_k: Number of results to return
            collection: Optional collection name override
        
        Returns:
            List of query results
        """
        self._ensure_initialized()
        
        try:
            results = self._collection.query(
                query_texts=[query_text],
                n_results=top_k,
            )
            
            # Format results
            query_results = []
            if results["ids"] and len(results["ids"]) > 0:
                for i, doc_id in enumerate(results["ids"][0]):
                    query_results.append(
                        QueryResult(
                            document_id=doc_id,
                            text=results["documents"][0][i],
                            score=1.0 - results["distances"][0][i],  # Convert distance to score
                            metadata=results["metadatas"][0][i] if results["metadatas"] else {},
                        )
                    )
            
            logger.info("Query complete", results_count=len(query_results))
            return query_results
            
        except Exception as e:
            logger.error("Query failed", error=str(e))
            raise
    
    def get_collection_stats(self) -> Dict[str, Any]:
        """
        Get statistics about the collection.
        
        Returns:
            Dictionary with collection stats
        """
        self._ensure_initialized()
        
        count = self._collection.count()
        
        return {
            "collection_name": self.collection_name,
            "document_count": count,
            "persist_directory": str(self.persist_directory),
        }
    
    def clear(self) -> None:
        """Clear all documents from the collection."""
        self._ensure_initialized()
        
        # Delete and recreate collection
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.create_collection(
            name=self.collection_name,
            metadata={"description": "DweepBot agent memory"},
        )
        
        logger.info("Collection cleared", collection=self.collection_name)
