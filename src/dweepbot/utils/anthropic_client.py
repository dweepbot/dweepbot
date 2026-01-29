"""
Anthropic Claude 3.5 Sonnet client.

Claude 3.5 Sonnet is optimized for:
- Creative writing and storytelling
- Nuanced understanding and complex reasoning
- High-quality analysis and explanations

Pricing: $3/1M input, $15/1M output
"""

from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

from ..utils.cost_tracker import CostTracker
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Claude 3.5 Sonnet pricing
CLAUDE_INPUT_COST_PER_TOKEN = 3.00 / 1_000_000
CLAUDE_OUTPUT_COST_PER_TOKEN = 15.00 / 1_000_000


class AnthropicClient:
    """
    Async client for Claude 3.5 Sonnet.
    
    Features:
    - 200K token context window
    - Superior creative and nuanced tasks
    - Streaming support
    - Cost tracking integration
    - Retry logic with exponential backoff
    
    Example:
        ```python
        client = AnthropicClient(api_key="your_key")
        
        # Creative writing
        story = await client.complete(
            messages=[{"role": "user", "content": "Write a short story about AI"}],
            max_tokens=2000,
        )
        
        # Analysis
        analysis = await client.analyze(
            content="Long document...",
            question="What are the key themes?",
        )
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-3-5-sonnet-20241022",
        base_url: str = "https://api.anthropic.com/v1",
        timeout: float = 60.0,
        max_retries: int = 3,
        cost_tracker: Optional[CostTracker] = None,
    ):
        """
        Initialize Anthropic client.
        
        Args:
            api_key: Anthropic API key
            model: Model name
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
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            timeout=httpx.Timeout(timeout),
        )
        
        logger.info(
            "Anthropic client initialized",
            model=model,
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
    )
    async def complete(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        stream: bool = False,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        Create a message completion.
        
        Args:
            messages: List of message dicts with 'role' and 'content'
            system: Optional system prompt
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional API parameters
        
        Returns:
            API response dict with 'content', 'usage', etc.
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": stream,
            **kwargs,
        }
        
        if system:
            payload["system"] = system
        
        try:
            response = await self._client.post("/messages", json=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # Track costs
            if self.cost_tracker and "usage" in data:
                usage = data["usage"]
                self.cost_tracker.record_llm_call(
                    prompt_tokens=usage.get("input_tokens", 0),
                    completion_tokens=usage.get("output_tokens", 0),
                    phase="claude_completion",
                )
            
            logger.info(
                "Claude completion",
                tokens=data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0),
                model=self.model,
            )
            
            return data
            
        except httpx.HTTPStatusError as e:
            logger.error("Claude API error", status=e.response.status_code, error=str(e))
            raise
        except Exception as e:
            logger.error("Claude request failed", error=str(e))
            raise
    
    async def complete_streaming(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 4000,
        **kwargs,
    ) -> AsyncIterator[str]:
        """
        Create a streaming message completion.
        
        Args:
            messages: List of message dicts
            system: Optional system prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            **kwargs: Additional API parameters
        
        Yields:
            Text chunks as they arrive
        """
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "stream": True,
            **kwargs,
        }
        
        if system:
            payload["system"] = system
        
        try:
            async with self._client.stream("POST", "/messages", json=payload) as response:
                response.raise_for_status()
                
                async for line in response.aiter_lines():
                    if line.startswith("data: "):
                        data_str = line[6:]
                        
                        if data_str.strip() == "[DONE]":
                            break
                        
                        try:
                            import json
                            data = json.loads(data_str)
                            
                            if data.get("type") == "content_block_delta":
                                delta = data.get("delta", {})
                                if delta.get("type") == "text_delta":
                                    yield delta.get("text", "")
                                    
                        except json.JSONDecodeError:
                            continue
                            
        except httpx.HTTPStatusError as e:
            logger.error("Claude streaming error", status=e.response.status_code)
            raise
        except Exception as e:
            logger.error("Claude streaming failed", error=str(e))
            raise
    
    async def analyze(
        self,
        content: str,
        question: str,
        context: Optional[str] = None,
    ) -> str:
        """
        Analyze content and answer a question.
        
        Args:
            content: Content to analyze
            question: Question about the content
            context: Optional additional context
        
        Returns:
            Analysis result
        """
        user_message = f"Content to analyze:\n\n{content}\n\nQuestion: {question}"
        
        if context:
            user_message += f"\n\nAdditional context: {context}"
        
        messages = [{"role": "user", "content": user_message}]
        
        response = await self.complete(
            messages=messages,
            temperature=0.5,
            max_tokens=4000,
        )
        
        if response.get("content"):
            # Extract text from content blocks
            text_blocks = [
                block.get("text", "")
                for block in response["content"]
                if block.get("type") == "text"
            ]
            return "\n".join(text_blocks)
        
        return ""
    
    async def write_creative(
        self,
        prompt: str,
        style: Optional[str] = None,
        max_length: int = 2000,
    ) -> str:
        """
        Generate creative writing.
        
        Args:
            prompt: Creative writing prompt
            style: Optional style guidance
            max_length: Maximum length in tokens
        
        Returns:
            Generated creative content
        """
        system_prompt = "You are a creative writer who produces engaging, original content."
        
        if style:
            system_prompt += f" Write in a {style} style."
        
        messages = [{"role": "user", "content": prompt}]
        
        response = await self.complete(
            messages=messages,
            system=system_prompt,
            temperature=0.9,  # Higher for creativity
            max_tokens=max_length,
        )
        
        if response.get("content"):
            text_blocks = [
                block.get("text", "")
                for block in response["content"]
                if block.get("type") == "text"
            ]
            return "\n".join(text_blocks)
        
        return ""
    
    async def summarize(
        self,
        content: str,
        max_summary_length: int = 500,
    ) -> str:
        """
        Summarize content.
        
        Args:
            content: Content to summarize
            max_summary_length: Maximum summary length in tokens
        
        Returns:
            Summary
        """
        messages = [
            {
                "role": "user",
                "content": f"Summarize the following content concisely:\n\n{content}",
            }
        ]
        
        response = await self.complete(
            messages=messages,
            temperature=0.5,
            max_tokens=max_summary_length,
        )
        
        if response.get("content"):
            text_blocks = [
                block.get("text", "")
                for block in response["content"]
                if block.get("type") == "text"
            ]
            return "\n".join(text_blocks)
        
        return ""
