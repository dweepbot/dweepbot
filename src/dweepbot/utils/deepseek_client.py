"""
DeepSeek API client with retry logic, rate limiting, and streaming support.
"""

import asyncio
import httpx
from typing import Any, AsyncIterator, Dict, List, Optional
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
)

from ..utils.cost_tracker import CostTracker
from ..utils.logger import get_logger

logger = get_logger(__name__)


class DeepSeekAPIError(Exception):
    """DeepSeek API error."""
    pass


class RateLimitError(DeepSeekAPIError):
    """Rate limit exceeded."""
    pass


class DeepSeekClient:
    """
    Async client for DeepSeek API with production features.
    
    Features:
    - Automatic retries with exponential backoff
    - Rate limiting
    - Cost tracking integration
    - Streaming support
    - Error handling
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "deepseek-chat",
        base_url: str = "https://api.deepseek.com/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
        cost_tracker: Optional[CostTracker] = None,
    ):
        """
        Initialize DeepSeek client.
        
        Args:
            api_key: DeepSeek API key
            model: Model name (default: deepseek-chat)
            base_url: API base URL
            timeout: Request timeout in seconds
            max_retries: Maximum retry attempts
            cost_tracker: Optional cost tracker instance
        """
        self.api_key = api_key
        self.model = model
        self.base_url = base_url
        self.timeout = timeout
        self.max_retries = max_retries
        self.cost_tracker = cost_tracker
        
        self._client = httpx.AsyncClient(
            base_url=base_url,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
    
    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((httpx.HTTPError, RateLimitError)),
    )
    async def complete(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a chat completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            temperature: Sampling temperature (0.0-2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional API parameters
        
        Returns:
            API response dict with 'choices', 'usage', etc.
        
        Raises:
            DeepSeekAPIError: If API request fails
            RateLimitError: If rate limit exceeded
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": stream,
            **kwargs,
        }
        
        try:
            response = await self._client.post("/chat/completions", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Track costs if tracker is available
            if self.cost_tracker and "usage" in data:
                usage = data["usage"]
                self.cost_tracker.record_llm_call(
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    cache_read_tokens=usage.get("prompt_cache_hit_tokens", 0),
                )
            
            return data
            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                logger.warning("Rate limit exceeded, retrying...")
                raise RateLimitError("DeepSeek API rate limit exceeded")
            elif e.response.status_code >= 500:
                logger.error(f"DeepSeek API server error: {e}")
                raise DeepSeekAPIError(f"Server error: {e}")
            else:
                logger.error(f"DeepSeek API error: {e}")
                raise DeepSeekAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            logger.error(f"DeepSeek API request failed: {e}")
            raise DeepSeekAPIError(f"Request failed: {e}")
    
    async def complete_streaming(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Create a streaming chat completion.
        
        Args:
            messages: List of message dicts
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional API parameters
        
        Yields:
            Text chunks as they arrive
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens,
            "stream": True,
            **kwargs,
        }
        
        try:
            async with self._client.stream("POST", "/chat/completions", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]  # Remove "data: " prefix
                        
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            if "choices" in data and len(data["choices"]) > 0:
                                delta = data["choices"][0].get("delta", {})
                                content = delta.get("content", "")
                                if content:
                                    yield content
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPStatusError as e:
            if e.response.status_code == 429:
                raise RateLimitError("DeepSeek API rate limit exceeded")
            raise DeepSeekAPIError(f"API error: {e}")
        except httpx.RequestError as e:
            raise DeepSeekAPIError(f"Request failed: {e}")
    
    async def generate_text(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
    ) -> str:
        """
        Simple text generation helper.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated text
        """
        messages = []
        
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        
        messages.append({"role": "user", "content": prompt})
        
        response = await self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        
        if "choices" in response and len(response["choices"]) > 0:
            return response["choices"][0]["message"]["content"]
        
        raise DeepSeekAPIError("No content in response")
