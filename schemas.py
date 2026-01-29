"""
Memory-related Pydantic models.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A single memory entry."""
    id: str = Field(..., description="Unique identifier")
    content: str = Field(..., description="Memory content")
    category: str = Field(default="general", description="Memory category")
    metadata: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    importance: float = Field(default=0.5, ge=0.0, le=1.0, description="Memory importance")


class VectorDocument(BaseModel):
    """A document stored in vector database."""
    id: str = Field(..., description="Document ID")
    text: str = Field(..., description="Document text")
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source: str = Field(default="unknown", description="Document source")
    created_at: datetime = Field(default_factory=datetime.utcnow)


class QueryResult(BaseModel):
    """Result from a vector similarity search."""
    document_id: str
    text: str
    score: float = Field(..., ge=0.0, le=1.0, description="Similarity score")
    metadata: Dict[str, Any] = Field(default_factory=dict)
