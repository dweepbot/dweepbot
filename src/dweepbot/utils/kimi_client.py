# dweepbot/utils/kimi_client.py
import os
from typing import AsyncIterator, Optional, List, Dict
import openai
from dataclasses import dataclass
import asyncio

@dataclass
class KimiConfig:
    api_key: str
    model: str = "kimi-k2.5"  # or "kimi-k1.5" for reasoning
    temperature: float = 0.3
    max_tokens: Optional[int] = None
    api_base: str = "https://api.moonshot.cn/v1"

class KimiClient:
    """
    Kimi K2.5 client for DweepBot.
    Strengths: Coding, long context (2M tokens), fast inference.
    """
    
    # Pricing (estimated, check current rates)
    COST_PER_1M_INPUT = 0.15   # $0.15 per 1M input tokens
    COST_PER_1M_OUTPUT = 0.60  # $0.60 per 1M output tokens
    
    def __init__(self, config: Optional[KimiConfig] = None):
        self.config = config or KimiConfig(
            api_key=os.getenv("MOONSHOT_API_KEY", "")
        )
        self.client = openai.AsyncOpenAI(
            api_key=self.config.api_key,
            base_url=self.config.api_base,
        )
        self.total_cost = 0.0
        self.total_tokens = 0
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        stream: bool = True,
    ) -> AsyncIterator[str]:
        """Stream completion from Kimi."""
        
        try:
            response = await self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                stream=stream,
            )
            
            if stream:
                async for chunk in response:
                    if chunk.choices[0].delta.content:
                        yield chunk.choices[0].delta.content
            else:
                content = response.choices[0].message.content
                yield content
                
        except Exception as e:
            yield f"[Kimi Error: {str(e)}]"
    
    def estimate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate estimated cost for token usage."""
        input_cost = (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT
        output_cost = (output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT
        return input_cost + output_cost
    
    async def analyze_codebase(
        self,
        files: List[Dict[str, str]],
        query: str,
    ) -> str:
        """
        Kimi's killer feature: analyze massive codebases.
        Fits entire repos in 2M token context.
        """
        
        # Build context from files
        context_parts = []
        total_chars = 0
        max_chars = 1_000_000  # Conservative limit
        
        for file in files:
            content = f"### {file['path']}\n```{file['content']}```\n\n"
            if total_chars + len(content) > max_chars:
                break
            context_parts.append(content)
            total_chars += len(content)
        
        context = "".join(context_parts)
        
        messages = [
            {
                "role": "system",
                "content": "You are an expert software engineer. Analyze the provided codebase and answer the user's question concisely."
            },
            {
                "role": "user",
                "content": f"Codebase:\n{context}\n\nQuestion: {query}"
            }
        ]
        
        response_chunks = []
        async for chunk in self.complete(messages, stream=False):
            response_chunks.append(chunk)
        
        return "".join(response_chunks)
    
    async def generate_code(
        self,
        prompt: str,
        language: str = "python",
        context: Optional[str] = None,
    ) -> str:
        """
        Optimized for code generation.
        Uses Kimi's coding strengths.
        """
        
        messages = [
            {
                "role": "system",
                "content": f"You are an expert {language} developer. Write clean, efficient, well-documented code."
            }
        ]
        
        if context:
            messages.append({
                "role": "user",
                "content": f"Context:\n{context}\n\nTask: {prompt}"
            })
        else:
            messages.append({
                "role": "user",
                "content": prompt
            })
        
        response_chunks = []
        async for chunk in self.complete(messages, stream=False):
            response_chunks.append(chunk)
        
        return "".join(response_chunks)
