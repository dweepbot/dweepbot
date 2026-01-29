"""
Production DeepSeek API client with async support, cost tracking, and error handling.
"""

import asyncio
import aiohttp
import json
import time
from typing import AsyncGenerator, Dict, List, Optional, Any, Union
from dataclasses import dataclass
from datetime import datetime
from pydantic import BaseModel


class Message(BaseModel):
    """Chat message structure."""
    role: str  # "user", "assistant", or "system"
    content: str


class CompletionUsage(BaseModel):
    """Token usage and cost information."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


class CompletionResponse(BaseModel):
    """Complete API response with metadata."""
    content: str
    usage: CompletionUsage
    model: str
    finish_reason: str
    response_time_seconds: float


@dataclass
class StreamChunk:
    """Individual chunk from streaming response."""
    content: str
    is_final: bool = False
    usage: Optional[CompletionUsage] = None


class DeepSeekClient:
    """
    Production-grade DeepSeek API client.
    
    Features:
    - Async/await support for non-blocking I/O
    - Streaming responses
    - Automatic cost calculation
    - Retry logic with exponential backoff
    - Request/response logging
    - Context window management
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.deepseek.com",
        model: str = "deepseek-chat",
        timeout: int = 60,
        max_retries: int = 3
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self.max_retries = max_retries
        
        # Cost tracking (DeepSeek-V3 pricing)
        self.input_cost_per_token = 0.27 / 1_000_000  # $0.27 per 1M tokens
        self.output_cost_per_token = 1.10 / 1_000_000  # $1.10 per 1M tokens
        
        # Session for connection pooling
        self._session: Optional[aiohttp.ClientSession] = None
    
    async def __aenter__(self):
        """Async context manager entry."""
        await self._ensure_session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()
    
    async def _ensure_session(self) -> None:
        """Create aiohttp session if not exists."""
        if self._session is None or self._session.closed:
            self._session = aiohttp.ClientSession(
                timeout=aiohttp.ClientTimeout(total=self.timeout),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                }
            )
    
    async def close(self) -> None:
        """Close the HTTP session."""
        if self._session and not self._session.closed:
            await self._session.close()
    
    def _calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost in USD."""
        input_cost = prompt_tokens * self.input_cost_per_token
        output_cost = completion_tokens * self.output_cost_per_token
        return input_cost + output_cost
    
    async def complete(
        self,
        messages: List[Message],
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        system_prompt: Optional[str] = None
    ) -> Union[CompletionResponse, AsyncGenerator[StreamChunk, None]]:
        """
        Get completion from DeepSeek.
        
        Args:
            messages: Conversation history
            temperature: Sampling temperature (0.0 to 2.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            system_prompt: Optional system message
        
        Returns:
            CompletionResponse or async generator of StreamChunks
        """
        await self._ensure_session()
        
        # Prepare messages
        message_dicts = []
        if system_prompt:
            message_dicts.append({"role": "system", "content": system_prompt})
        message_dicts.extend([{"role": m.role, "content": m.content} for m in messages])
        
        payload = {
            "model": self.model,
            "messages": message_dicts,
            "temperature": temperature,
            "stream": stream
        }
        
        if max_tokens:
            payload["max_tokens"] = max_tokens
        
        if stream:
            return self._stream_completion(payload)
        else:
            return await self._complete_single(payload)
    
    async def _complete_single(self, payload: Dict[str, Any]) -> CompletionResponse:
        """Non-streaming completion with retry logic."""
        start_time = time.time()
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                async with self._session.post(
                    f"{self.base_url}/chat/completions",
                    json=payload
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        elapsed = time.time() - start_time
                        
                        # Extract response
                        choice = data["choices"][0]
                        content = choice["message"]["content"]
                        finish_reason = choice.get("finish_reason", "stop")
                        
                        # Extract usage
                        usage_data = data.get("usage", {})
                        prompt_tokens = usage_data.get("prompt_tokens", 0)
                        completion_tokens = usage_data.get("completion_tokens", 0)
                        total_tokens = usage_data.get("total_tokens", 0)
                        
                        cost = self._calculate_cost(prompt_tokens, completion_tokens)
                        
                        usage = CompletionUsage(
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                            total_tokens=total_tokens,
                            estimated_cost_usd=cost
                        )
                        
                        return CompletionResponse(
                            content=content,
                            usage=usage,
                            model=self.model,
                            finish_reason=finish_reason,
                            response_time_seconds=elapsed
                        )
                    
                    elif response.status == 429:
                        # Rate limit - exponential backoff
                        wait_time = (2 ** attempt) * 1.0
                        await asyncio.sleep(wait_time)
                        continue
                    
                    else:
                        error_text = await response.text()
                        raise Exception(f"API error {response.status}: {error_text}")
            
            except asyncio.TimeoutError:
                last_error = "Request timeout"
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
            
            except Exception as e:
                last_error = str(e)
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                    continue
        
        raise Exception(f"Failed after {self.max_retries} attempts. Last error: {last_error}")
    
    async def _stream_completion(self, payload: Dict[str, Any]) -> AsyncGenerator[StreamChunk, None]:
        """Stream completion chunks."""
        full_content = ""
        
        try:
            async with self._session.post(
                f"{self.base_url}/chat/completions",
                json=payload
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"API error {response.status}: {error_text}")
                
                async for line in response.content:
                    line = line.decode('utf-8').strip()
                    
                    if not line or not line.startswith('data: '):
                        continue
                    
                    data = line[6:]  # Remove 'data: ' prefix
                    
                    if data == '[DONE]':
                        # Final chunk with usage info (estimated)
                        # Note: Streaming doesn't provide exact token counts
                        # We'll estimate based on content length
                        estimated_tokens = len(full_content.split()) * 1.3
                        usage = CompletionUsage(
                            prompt_tokens=0,  # Not available in stream
                            completion_tokens=int(estimated_tokens),
                            total_tokens=int(estimated_tokens),
                            estimated_cost_usd=estimated_tokens * self.output_cost_per_token
                        )
                        yield StreamChunk(content="", is_final=True, usage=usage)
                        break
                    
                    try:
                        chunk_data = json.loads(data)
                        delta = chunk_data['choices'][0]['delta']
                        
                        if 'content' in delta:
                            content = delta['content']
                            full_content += content
                            yield StreamChunk(content=content, is_final=False)
                    
                    except json.JSONDecodeError:
                        continue
        
        except Exception as e:
            raise Exception(f"Streaming error: {str(e)}")
    
    async def chat(
        self,
        message: str,
        history: Optional[List[Message]] = None,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7
    ) -> CompletionResponse:
        """
        Simple chat interface.
        
        Args:
            message: User message
            history: Previous messages
            system_prompt: System message
            temperature: Sampling temperature
        
        Returns:
            CompletionResponse
        """
        messages = history or []
        messages.append(Message(role="user", content=message))
        
        return await self.complete(
            messages=messages,
            temperature=temperature,
            system_prompt=system_prompt,
            stream=False
        )


class ChatHistory:
    """Manages conversation history with context window limits."""
    
    def __init__(self, max_tokens: int = 32000):
        self.messages: List[Message] = []
        self.max_tokens = max_tokens
    
    def add_message(self, role: str, content: str) -> None:
        """Add a message to history."""
        self.messages.append(Message(role=role, content=content))
        self._trim_if_needed()
    
    def _trim_if_needed(self) -> None:
        """Trim old messages if exceeding context window."""
        # Simple token estimation: ~4 chars per token
        total_chars = sum(len(m.content) for m in self.messages)
        estimated_tokens = total_chars / 4
        
        while estimated_tokens > self.max_tokens and len(self.messages) > 1:
            # Remove oldest message (keep system message if first)
            if self.messages[0].role == "system":
                self.messages.pop(1)
            else:
                self.messages.pop(0)
            
            total_chars = sum(len(m.content) for m in self.messages)
            estimated_tokens = total_chars / 4
    
    def get_messages(self) -> List[Message]:
        """Get all messages in history."""
        return self.messages.copy()
    
    def clear(self) -> None:
        """Clear all messages."""
        self.messages.clear()
