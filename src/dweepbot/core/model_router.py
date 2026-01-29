"""
Multi-model router for intelligent LLM selection.

Routes tasks to optimal model based on task type, cost, and capabilities:
- Kimi K2.5: Coding tasks, large context needs
- DeepSeek-V3: Cost-sensitive reasoning, general tasks
- Claude 3.5: Creative writing, nuanced understanding

Features:
- Auto-detection of task type from keywords
- Cost estimation before execution
- Fallback chain if primary model fails
- Async support throughout
"""

from enum import Enum
from typing import Any, Dict, List, Optional, Tuple
from pydantic import BaseModel, Field
import re

from ..utils.logger import get_logger

logger = get_logger(__name__)


class ModelType(str, Enum):
    """Available model types."""
    KIMI = "kimi"
    DEEPSEEK = "deepseek"
    CLAUDE = "claude"


class TaskType(str, Enum):
    """Task classification types."""
    CODING = "coding"
    REASONING = "reasoning"
    CREATIVE = "creative"
    ANALYSIS = "analysis"
    GENERAL = "general"


class ModelCapabilities(BaseModel):
    """Model capabilities and costs."""
    name: str
    provider: str
    context_window: int
    input_cost_per_1m: float  # USD
    output_cost_per_1m: float  # USD
    strengths: List[str]
    max_output_tokens: int = 4000


# Model configurations
MODEL_CONFIGS = {
    ModelType.KIMI: ModelCapabilities(
        name="moonshot-v1-128k",
        provider="Moonshot AI",
        context_window=2_000_000,  # 2M tokens
        input_cost_per_1m=0.15,
        output_cost_per_1m=0.60,
        strengths=["coding", "large_context", "analysis"],
        max_output_tokens=8000,
    ),
    ModelType.DEEPSEEK: ModelCapabilities(
        name="deepseek-chat",
        provider="DeepSeek",
        context_window=128_000,
        input_cost_per_1m=0.27,
        output_cost_per_1m=1.10,
        strengths=["reasoning", "cost_effective", "general"],
        max_output_tokens=4000,
    ),
    ModelType.CLAUDE: ModelCapabilities(
        name="claude-3-5-sonnet-20241022",
        provider="Anthropic",
        context_window=200_000,
        input_cost_per_1m=3.00,
        output_cost_per_1m=15.00,
        strengths=["creative", "nuanced", "complex_reasoning"],
        max_output_tokens=8000,
    ),
}

# Task detection patterns
TASK_PATTERNS = {
    TaskType.CODING: [
        r'\b(write|create|build|implement|code|program|function|class|script)\b.*\b(python|javascript|java|code|api|function)\b',
        r'\b(debug|fix|refactor|optimize)\b.*\bcode\b',
        r'\b(algorithm|data structure|regex)\b',
        r'```\w+',  # Code blocks
    ],
    TaskType.CREATIVE: [
        r'\b(write|create|compose|generate)\b.*\b(story|poem|article|essay|blog|creative|narrative)\b',
        r'\b(brainstorm|imagine|invent)\b',
        r'\b(marketing|copywriting|slogan)\b',
    ],
    TaskType.ANALYSIS: [
        r'\b(analyze|examine|review|evaluate|assess|compare)\b',
        r'\b(summarize|explain|interpret)\b.*\b(data|document|text|code|codebase)\b',
        r'\b(find|search|extract)\b.*\b(information|pattern|insights)\b',
    ],
    TaskType.REASONING: [
        r'\b(solve|calculate|reason|deduce|infer)\b',
        r'\b(why|how|explain|justify)\b',
        r'\b(logic|proof|theorem)\b',
    ],
}


class ModelRouter:
    """
    Intelligent router for selecting optimal LLM based on task.
    
    Features:
    - Auto-detects task type from prompt analysis
    - Estimates cost before execution
    - Provides fallback chain if primary model fails
    - Supports async operations
    
    Example:
        ```python
        router = ModelRouter(
            kimi_client=kimi,
            deepseek_client=deepseek,
            claude_client=claude,
        )
        
        model, cost_estimate = await router.select_model(
            task="Write a Python function to parse JSON",
            estimated_tokens=1000,
        )
        ```
    """
    
    def __init__(
        self,
        kimi_client: Optional[Any] = None,
        deepseek_client: Optional[Any] = None,
        claude_client: Optional[Any] = None,
        default_model: ModelType = ModelType.DEEPSEEK,
    ):
        """
        Initialize model router.
        
        Args:
            kimi_client: Kimi K2.5 client instance
            deepseek_client: DeepSeek-V3 client instance
            claude_client: Claude 3.5 client instance
            default_model: Default model if no specific match
        """
        self.clients = {
            ModelType.KIMI: kimi_client,
            ModelType.DEEPSEEK: deepseek_client,
            ModelType.CLAUDE: claude_client,
        }
        self.default_model = default_model
        
        # Filter out None clients
        self.available_models = [
            model for model, client in self.clients.items() 
            if client is not None
        ]
        
        if not self.available_models:
            raise ValueError("At least one model client must be provided")
        
        logger.info(
            "Model router initialized",
            available_models=[m.value for m in self.available_models],
            default=default_model.value,
        )
    
    def detect_task_type(self, task: str) -> TaskType:
        """
        Detect task type from prompt analysis.
        
        Args:
            task: Task description
        
        Returns:
            Detected TaskType
        """
        task_lower = task.lower()
        
        # Check each pattern
        scores = {task_type: 0 for task_type in TaskType}
        
        for task_type, patterns in TASK_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, task_lower, re.IGNORECASE):
                    scores[task_type] += 1
        
        # Get highest scoring type
        if max(scores.values()) > 0:
            detected = max(scores, key=scores.get)
            logger.debug(
                "Task type detected",
                task=task[:100],
                type=detected.value,
                scores=scores,
            )
            return detected
        
        logger.debug("No specific task type detected, using GENERAL")
        return TaskType.GENERAL
    
    def select_model_for_task(
        self,
        task_type: TaskType,
        estimated_tokens: int = 1000,
        prefer_cost_effective: bool = True,
    ) -> Tuple[ModelType, ModelCapabilities]:
        """
        Select optimal model for a task type.
        
        Args:
            task_type: Type of task
            estimated_tokens: Estimated token count
            prefer_cost_effective: Prefer cheaper models when possible
        
        Returns:
            Tuple of (ModelType, ModelCapabilities)
        """
        # Define model preferences by task type
        preferences = {
            TaskType.CODING: [ModelType.KIMI, ModelType.DEEPSEEK, ModelType.CLAUDE],
            TaskType.CREATIVE: [ModelType.CLAUDE, ModelType.DEEPSEEK, ModelType.KIMI],
            TaskType.ANALYSIS: [ModelType.KIMI, ModelType.CLAUDE, ModelType.DEEPSEEK],
            TaskType.REASONING: [ModelType.DEEPSEEK, ModelType.CLAUDE, ModelType.KIMI],
            TaskType.GENERAL: [ModelType.DEEPSEEK, ModelType.KIMI, ModelType.CLAUDE],
        }
        
        # Get preference order for this task
        preference_order = preferences.get(task_type, [ModelType.DEEPSEEK])
        
        # Filter to available models
        available_preferences = [
            m for m in preference_order if m in self.available_models
        ]
        
        if not available_preferences:
            # Fallback to any available model
            selected = self.available_models[0]
        elif prefer_cost_effective and task_type == TaskType.GENERAL:
            # For general tasks, prefer DeepSeek for cost
            if ModelType.DEEPSEEK in available_preferences:
                selected = ModelType.DEEPSEEK
            else:
                selected = available_preferences[0]
        else:
            # Use first preference
            selected = available_preferences[0]
        
        config = MODEL_CONFIGS[selected]
        
        logger.info(
            "Model selected",
            model=selected.value,
            task_type=task_type.value,
            provider=config.provider,
        )
        
        return selected, config
    
    def estimate_cost(
        self,
        model_type: ModelType,
        input_tokens: int,
        output_tokens: int = 1000,
    ) -> float:
        """
        Estimate cost for a model execution.
        
        Args:
            model_type: Model to use
            input_tokens: Estimated input tokens
            output_tokens: Estimated output tokens
        
        Returns:
            Estimated cost in USD
        """
        config = MODEL_CONFIGS[model_type]
        
        input_cost = (input_tokens / 1_000_000) * config.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * config.output_cost_per_1m
        
        total_cost = input_cost + output_cost
        
        logger.debug(
            "Cost estimated",
            model=model_type.value,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=total_cost,
        )
        
        return total_cost
    
    async def route(
        self,
        task: str,
        estimated_input_tokens: int = 1000,
        estimated_output_tokens: int = 1000,
        force_model: Optional[ModelType] = None,
    ) -> Tuple[Any, ModelType, float]:
        """
        Route a task to the optimal model client.
        
        Args:
            task: Task description
            estimated_input_tokens: Estimated input token count
            estimated_output_tokens: Estimated output token count
            force_model: Force a specific model (overrides auto-detection)
        
        Returns:
            Tuple of (client, model_type, estimated_cost)
        """
        if force_model:
            if force_model not in self.available_models:
                raise ValueError(f"Model {force_model} not available")
            model_type = force_model
        else:
            # Auto-detect task type
            task_type = self.detect_task_type(task)
            
            # Select model
            model_type, _ = self.select_model_for_task(
                task_type=task_type,
                estimated_tokens=estimated_input_tokens,
            )
        
        # Get client
        client = self.clients[model_type]
        
        # Estimate cost
        cost = self.estimate_cost(
            model_type=model_type,
            input_tokens=estimated_input_tokens,
            output_tokens=estimated_output_tokens,
        )
        
        logger.info(
            "Task routed",
            model=model_type.value,
            estimated_cost=f"${cost:.4f}",
        )
        
        return client, model_type, cost
    
    def get_fallback_chain(
        self,
        primary_model: ModelType,
    ) -> List[ModelType]:
        """
        Get fallback chain if primary model fails.
        
        Args:
            primary_model: Primary model that failed
        
        Returns:
            List of fallback models in priority order
        """
        # Define fallback preferences
        fallback_map = {
            ModelType.KIMI: [ModelType.DEEPSEEK, ModelType.CLAUDE],
            ModelType.DEEPSEEK: [ModelType.KIMI, ModelType.CLAUDE],
            ModelType.CLAUDE: [ModelType.DEEPSEEK, ModelType.KIMI],
        }
        
        fallbacks = fallback_map.get(primary_model, [])
        
        # Filter to available models
        available_fallbacks = [
            m for m in fallbacks if m in self.available_models
        ]
        
        logger.info(
            "Fallback chain created",
            primary=primary_model.value,
            fallbacks=[m.value for m in available_fallbacks],
        )
        
        return available_fallbacks
    
    def get_model_info(self, model_type: ModelType) -> Dict[str, Any]:
        """Get detailed information about a model."""
        config = MODEL_CONFIGS[model_type]
        return {
            "type": model_type.value,
            "name": config.name,
            "provider": config.provider,
            "context_window": config.context_window,
            "costs": {
                "input_per_1m": config.input_cost_per_1m,
                "output_per_1m": config.output_cost_per_1m,
            },
            "strengths": config.strengths,
            "available": model_type in self.available_models,
        }
    
    def get_all_models_info(self) -> Dict[str, Any]:
        """Get information about all models."""
        return {
            model.value: self.get_model_info(model)
            for model in ModelType
        }
