# dweepbot/core/model_router.py
from enum import Enum, auto
from typing import Optional, Dict, Any
import os

class TaskType(Enum):
    CODE_GENERATION = auto()
    CODE_REVIEW = auto()
    DEBUGGING = auto()
    REFACTORING = auto()
    LONG_CONTEXT = auto()
    REASONING = auto()
    CREATIVE = auto()
    QUICK_ANSWER = auto()

class ModelRouter:
    """
    Routes tasks to optimal model based on type and constraints.
    
    Kimi K2.5: Coding, long context (2M tokens)
    DeepSeek-V3: Reasoning, cost-efficiency
    Claude 3.5: Creative tasks, nuance
    """
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.clients = {}
        self._init_clients()
    
    def _init_clients(self):
        """Initialize available model clients."""
        from dweepbot.utils.kimi_client import KimiClient
        from dweepbot.utils.deepseek_client import DeepSeekClient
        
        # Always available
        if os.getenv("MOONSHOT_API_KEY"):
            self.clients["kimi"] = KimiClient()
        
        if os.getenv("DEEPSEEK_API_KEY"):
            self.clients["deepseek"] = DeepSeekClient()
        
        # Optional
        if os.getenv("ANTHROPIC_API_KEY"):
            from dweepbot.utils.anthropic_client import AnthropicClient
            self.clients["claude"] = AnthropicClient()
    
    def classify_task(self, task: str) -> TaskType:
        """Auto-classify task from description."""
        task_lower = task.lower()
        
        code_keywords = [
            "code", "function", "class", "implement", "refactor",
            "debug", "fix", "optimize", "write", "script",
            "api", "endpoint", "database", "query"
        ]
        
        if any(kw in task_lower for kw in code_keywords):
            if "debug" in task_lower or "fix" in task_lower:
                return TaskType.DEBUGGING
            elif "refactor" in task_lower:
                return TaskType.REFACTORING
            elif "review" in task_lower:
                return TaskType.CODE_REVIEW
            else:
                return TaskType.CODE_GENERATION
        
        if len(task) > 50000:
            return TaskType.LONG_CONTEXT
        
        if any(kw in task_lower for kw in ["explain", "analyze", "compare"]):
            return TaskType.REASONING
        
        return TaskType.QUICK_ANSWER
    
    def route(self, task: str, task_type: Optional[TaskType] = None) -> str:
        """
        Select best model for task.
        
        Priority:
        1. Coding tasks → Kimi (superior performance)
        2. Long context → Kimi (2M tokens)
        3. Cost-sensitive → DeepSeek (cheapest)
        4. Creative → Claude (if available)
        """
        
        if not task_type:
            task_type = self.classify_task(task)
        
        # Kimi for coding and long context
        if task_type in [
            TaskType.CODE_GENERATION,
            TaskType.CODE_REVIEW,
            TaskType.DEBUGGING,
            TaskType.REFACTORING,
            TaskType.LONG_CONTEXT
        ]:
            if "kimi" in self.clients:
                return "kimi"
        
        # DeepSeek for reasoning and cost efficiency
        if "deepseek" in self.clients:
            return "deepseek"
        
        # Fallback
        if self.clients:
            return list(self.clients.keys())[0]
        
        raise ValueError("No model clients configured")
    
    async def execute(
        self,
        task: str,
        context: Optional[str] = None,
        model: Optional[str] = None,
    ) -> str:
        """Execute task with routed model."""
        
        selected_model = model or self.route(task)
        client = self.clients.get(selected_model)
        
        if not client:
            raise ValueError(f"Model {selected_model} not available")
        
        if selected_model == "kimi":
            return await client.generate_code(task, context=context)
        else:
            # Generic completion for other models
            messages = [{"role": "user", "content": task}]
            chunks = []
            async for chunk in client.complete(messages):
                chunks.append(chunk)
            return "".join(chunks)
