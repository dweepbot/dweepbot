"""
Kimi K2.5 client for Moonshot AI API.

Kimi K2.5 is optimized for:
- Coding tasks with 2M token context
- Large codebase analysis
- Long-form technical content

Pricing: $0.15/1M input, $0.60/1M output
"""

from typing import Any, AsyncIterator, Dict, List, Optional
from openai import AsyncOpenAI
import asyncio

from ..utils.cost_tracker import CostTracker
from ..utils.logger import get_logger

logger = get_logger(__name__)


# Kimi K2.5 pricing
KIMI_INPUT_COST_PER_TOKEN = 0.15 / 1_000_000
KIMI_OUTPUT_COST_PER_TOKEN = 0.60 / 1_000_000


class KimiClient:
    """
    Async client for Kimi K2.5 (Moonshot AI).
    
    Features:
    - 2M token context window
    - OpenAI-compatible API
    - Specialized for coding tasks
    - Streaming support
    - Cost tracking integration
    
    Example:
        ```python
        client = KimiClient(api_key="your_key")
        
        # Generate code
        code = await client.generate_code(
            task="Create a binary search function",
            language="python",
        )
        
        # Analyze codebase
        analysis = await client.analyze_codebase(
            files={"main.py": code_content},
            question="What does this function do?",
        )
        ```
    """
    
    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.moonshot.cn/v1",
        model: str = "moonshot-v1-128k",
        timeout: float = 60.0,
        cost_tracker: Optional[CostTracker] = None,
    ):
        """
        Initialize Kimi client.
        
        Args:
            api_key: Moonshot AI API key
            base_url: API base URL
            model: Model name (moonshot-v1-8k, moonshot-v1-32k, moonshot-v1-128k)
            timeout: Request timeout in seconds
            cost_tracker: Optional cost tracker instance
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        self.timeout = timeout
        self.cost_tracker = cost_tracker
        
        # Initialize OpenAI-compatible client
        self._client = AsyncOpenAI(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
        )
        
        logger.info(
            "Kimi client initialized",
            model=model,
            base_url=base_url,
        )
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.close()
    
    async def close(self) -> None:
        """Close the client."""
        await self._client.close()
    
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
            temperature: Sampling temperature (0.0-1.0)
            max_tokens: Maximum tokens to generate
            stream: Whether to stream the response
            **kwargs: Additional API parameters
        
        Returns:
            API response dict with 'choices', 'usage', etc.
        """
        try:
            response = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=stream,
                **kwargs,
            )
            
            if stream:
                # Streaming handled separately
                return response
            
            # Convert to dict
            result = {
                "choices": [
                    {
                        "message": {
                            "role": choice.message.role,
                            "content": choice.message.content,
                        },
                        "finish_reason": choice.finish_reason,
                    }
                    for choice in response.choices
                ],
                "usage": {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                },
            }
            
            # Track costs
            if self.cost_tracker:
                self.cost_tracker.record_llm_call(
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    phase="kimi_completion",
                )
            
            logger.info(
                "Kimi completion",
                tokens=response.usage.total_tokens,
                model=self.model,
            )
            
            return result
            
        except Exception as e:
            logger.error("Kimi API error", error=str(e))
            raise
    
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
        try:
            stream = await self._client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
                **kwargs,
            )
            
            async for chunk in stream:
                if chunk.choices and len(chunk.choices) > 0:
                    delta = chunk.choices[0].delta
                    if delta.content:
                        yield delta.content
                        
        except Exception as e:
            logger.error("Kimi streaming error", error=str(e))
            raise
    
    async def generate_code(
        self,
        task: str,
        language: str = "python",
        context: Optional[str] = None,
        temperature: float = 0.3,
    ) -> str:
        """
        Generate code for a specific task.
        
        Optimized for Kimi's coding strengths.
        
        Args:
            task: Code generation task
            language: Programming language
            context: Optional additional context
            temperature: Lower for more deterministic code
        
        Returns:
            Generated code as string
        """
        system_prompt = f"""You are an expert {language} programmer. 
Generate clean, efficient, well-documented code.
Include type hints, error handling, and docstrings where appropriate."""
        
        user_prompt = f"Task: {task}"
        if context:
            user_prompt += f"\n\nContext:\n{context}"
        
        user_prompt += f"\n\nGenerate {language} code for this task. Return only the code, no explanations."
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = await self.complete(
            messages=messages,
            temperature=temperature,
            max_tokens=4000,
        )
        
        if response["choices"]:
            content = response["choices"][0]["message"]["content"]
            
            # Extract code from markdown if present
            if "```" in content:
                # Find code block
                import re
                code_match = re.search(r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
                if code_match:
                    return code_match.group(1).strip()
            
            return content
        
        return ""
    
    async def analyze_codebase(
        self,
        files: Dict[str, str],
        question: str,
        max_files: int = 50,
    ) -> str:
        """
        Analyze a codebase and answer questions.
        
        Leverages Kimi's 2M token context to analyze large codebases.
        
        Args:
            files: Dict mapping filenames to file contents
            question: Question about the codebase
            max_files: Maximum number of files to include
        
        Returns:
            Analysis result
        """
        # Build context from files
        file_contexts = []
        for filename, content in list(files.items())[:max_files]:
            file_contexts.append(f"# File: {filename}\n```\n{content}\n```\n")
        
        combined_context = "\n".join(file_contexts)
        
        system_prompt = """You are a code analysis expert. 
Analyze the provided codebase and answer questions accurately.
Consider code structure, patterns, dependencies, and potential issues."""
        
        user_prompt = f"""Codebase:

{combined_context}

Question: {question}

Provide a detailed analysis."""
        
        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
        
        response = await self.complete(
            messages=messages,
            temperature=0.5,
            max_tokens=4000,
        )
        
        if response["choices"]:
            return response["choices"][0]["message"]["content"]
        
        return ""
    
    async def explain_code(
        self,
        code: str,
        language: str = "python",
    ) -> str:
        """
        Explain what a piece of code does.
        
        Args:
            code: Code to explain
            language: Programming language
        
        Returns:
            Explanation
        """
        messages = [
            {
                "role": "user",
                "content": f"Explain what this {language} code does:\n\n```{language}\n{code}\n```",
            }
        ]
        
        response = await self.complete(
            messages=messages,
            temperature=0.5,
            max_tokens=2000,
        )
        
        if response["choices"]:
            return response["choices"][0]["message"]["content"]
        
        return ""
    
    async def refactor_code(
        self,
        code: str,
        instructions: str,
        language: str = "python",
    ) -> str:
        """
        Refactor code based on instructions.
        
        Args:
            code: Code to refactor
            instructions: Refactoring instructions
            language: Programming language
        
        Returns:
            Refactored code
        """
        messages = [
            {
                "role": "user",
                "content": f"""Refactor this {language} code according to these instructions:

Instructions: {instructions}

Original code:
```{language}
{code}
```

Return only the refactored code, no explanations.""",
            }
        ]
        
        response = await self.complete(
            messages=messages,
            temperature=0.3,
            max_tokens=4000,
        )
        
        if response["choices"]:
            content = response["choices"][0]["message"]["content"]
            
            # Extract code
            if "```" in content:
                import re
                code_match = re.search(r'```(?:\w+)?\n(.*?)```', content, re.DOTALL)
                if code_match:
                    return code_match.group(1).strip()
            
            return content
        
        return ""
