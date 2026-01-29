"""
HTTP client tools for making web requests.

Provides GET and POST methods with:
- Timeout enforcement
- Size limits
- Error handling
- Header customization
"""

import aiohttp
import asyncio
from typing import Optional, Dict, Any
import json

from .base import (
    BaseTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolCategory,
    ToolExecutionContext
)


class HTTPGetTool(BaseTool):
    """Make HTTP GET requests."""
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._timeout = getattr(context, 'network_timeout', 30)
        self._max_size_mb = getattr(context, 'max_http_response_size_mb', 5)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="http_get",
            description="Make an HTTP GET request to fetch data from a URL",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL to fetch",
                    required=True
                ),
                ToolParameter(
                    name="headers",
                    type="dict",
                    description="Optional HTTP headers",
                    required=False,
                    default={}
                )
            ],
            returns="Response body as text",
            requires_network=True,
            examples=[
                "http_get(url='https://api.example.com/data')",
                "http_get(url='https://example.com', headers={'User-Agent': 'DweepBot'})"
            ]
        )
    
    async def execute(
        self,
        url: str,
        headers: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Fetch URL via HTTP GET."""
        
        if headers is None:
            headers = {}
        
        # Add default User-Agent if not provided
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'DweepBot/0.1.0 (Autonomous Agent)'
        
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.get(url, headers=headers) as response:
                    # Check response size
                    content_length = response.headers.get('Content-Length')
                    if content_length:
                        size_mb = int(content_length) / (1024 * 1024)
                        if size_mb > self._max_size_mb:
                            return ToolResult(
                                success=False,
                                error=f"Response too large: {size_mb:.2f}MB (max: {self._max_size_mb}MB)",
                                execution_time_seconds=0.0
                            )
                    
                    # Read response
                    text = await response.text()
                    
                    # Check actual size
                    actual_size_mb = len(text.encode('utf-8')) / (1024 * 1024)
                    if actual_size_mb > self._max_size_mb:
                        return ToolResult(
                            success=False,
                            error=f"Response too large: {actual_size_mb:.2f}MB (max: {self._max_size_mb}MB)",
                            execution_time_seconds=0.0
                        )
                    
                    return ToolResult(
                        success=True,
                        output=text,
                        execution_time_seconds=0.0,
                        metadata={
                            "url": url,
                            "status_code": response.status,
                            "content_type": response.headers.get('Content-Type', 'unknown'),
                            "size_bytes": len(text.encode('utf-8'))
                        }
                    )
        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Request timed out after {self._timeout} seconds",
                execution_time_seconds=self._timeout
            )
        
        except aiohttp.ClientError as e:
            return ToolResult(
                success=False,
                error=f"HTTP error: {str(e)}",
                execution_time_seconds=0.0
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Request failed: {str(e)}",
                execution_time_seconds=0.0
            )


class HTTPPostTool(BaseTool):
    """Make HTTP POST requests."""
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._timeout = getattr(context, 'network_timeout', 30)
        self._max_size_mb = getattr(context, 'max_http_response_size_mb', 5)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="http_post",
            description="Make an HTTP POST request to send data to a URL",
            category=ToolCategory.WEB,
            parameters=[
                ToolParameter(
                    name="url",
                    type="string",
                    description="URL to post to",
                    required=True
                ),
                ToolParameter(
                    name="data",
                    type="dict",
                    description="Data to send (will be JSON encoded)",
                    required=False,
                    default={}
                ),
                ToolParameter(
                    name="headers",
                    type="dict",
                    description="Optional HTTP headers",
                    required=False,
                    default={}
                )
            ],
            returns="Response body as text",
            requires_network=True,
            examples=[
                "http_post(url='https://api.example.com/submit', data={'key': 'value'})",
                "http_post(url='https://webhook.site/xxx', data={'event': 'test'})"
            ]
        )
    
    async def execute(
        self,
        url: str,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> ToolResult:
        """Send HTTP POST request."""
        
        if data is None:
            data = {}
        
        if headers is None:
            headers = {}
        
        # Add default headers
        if 'User-Agent' not in headers:
            headers['User-Agent'] = 'DweepBot/0.1.0 (Autonomous Agent)'
        
        if 'Content-Type' not in headers:
            headers['Content-Type'] = 'application/json'
        
        try:
            timeout = aiohttp.ClientTimeout(total=self._timeout)
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                async with session.post(
                    url,
                    json=data,
                    headers=headers
                ) as response:
                    text = await response.text()
                    
                    # Check size
                    actual_size_mb = len(text.encode('utf-8')) / (1024 * 1024)
                    if actual_size_mb > self._max_size_mb:
                        return ToolResult(
                            success=False,
                            error=f"Response too large: {actual_size_mb:.2f}MB",
                            execution_time_seconds=0.0
                        )
                    
                    return ToolResult(
                        success=True,
                        output=text,
                        execution_time_seconds=0.0,
                        metadata={
                            "url": url,
                            "status_code": response.status,
                            "content_type": response.headers.get('Content-Type', 'unknown'),
                            "size_bytes": len(text.encode('utf-8'))
                        }
                    )
        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Request timed out after {self._timeout} seconds",
                execution_time_seconds=self._timeout
            )
        
        except aiohttp.ClientError as e:
            return ToolResult(
                success=False,
                error=f"HTTP error: {str(e)}",
                execution_time_seconds=0.0
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Request failed: {str(e)}",
                execution_time_seconds=0.0
            )
