"""
Web search tool using DuckDuckGo API.
"""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from .base import BaseTool, ToolError
from ..utils.logger import get_logger

logger = get_logger(__name__)


class WebSearchInput(BaseModel):
    """Input schema for web search."""
    query: str = Field(..., description="Search query")
    max_results: int = Field(default=5, ge=1, le=20, description="Maximum results to return")
    region: str = Field(default="us-en", description="Search region")


class WebSearchTool(BaseTool):
    """
    Search the web using DuckDuckGo.
    
    Features:
    - Rate-limited searches
    - Result parsing and ranking
    - Safe search enabled
    """
    
    name = "web_search"
    description = "Search the internet for information using DuckDuckGo"
    input_schema = WebSearchInput
    
    def __init__(self, rate_limit_delay: float = 1.0):
        """
        Initialize web search tool.
        
        Args:
            rate_limit_delay: Delay between searches in seconds
        """
        super().__init__()
        self.rate_limit_delay = rate_limit_delay
        self._last_search_time: Optional[float] = None
    
    async def _execute(self, query: str, max_results: int = 5, region: str = "us-en") -> Dict[str, Any]:
        """
        Execute web search.
        
        Args:
            query: Search query
            max_results: Maximum number of results
            region: Search region
        
        Returns:
            Dict with search results
        """
        logger.info("Searching web", query=query, max_results=max_results)
        
        try:
            # Rate limiting
            import time
            if self._last_search_time:
                elapsed = time.time() - self._last_search_time
                if elapsed < self.rate_limit_delay:
                    await asyncio.sleep(self.rate_limit_delay - elapsed)
            
            # Import here to make it optional
            try:
                from duckduckgo_search import DDGS
            except ImportError:
                raise ToolError(
                    "duckduckgo-search not installed. Install with: pip install duckduckgo-search"
                )
            
            # Perform search
            with DDGS() as ddgs:
                results = list(ddgs.text(
                    keywords=query,
                    region=region,
                    safesearch="moderate",
                    max_results=max_results,
                ))
            
            self._last_search_time = time.time()
            
            # Format results
            formatted_results = [
                {
                    "title": r.get("title", ""),
                    "url": r.get("link", ""),
                    "snippet": r.get("body", ""),
                }
                for r in results
            ]
            
            logger.info("Search complete", results_count=len(formatted_results))
            
            return {
                "query": query,
                "results": formatted_results,
                "count": len(formatted_results),
            }
            
        except Exception as e:
            logger.error("Search failed", error=str(e))
            raise ToolError(f"Web search failed: {str(e)}")


# Make sure to import asyncio at the top of the file
import asyncio
