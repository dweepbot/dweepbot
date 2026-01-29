"""
Task planning engine for breaking down complex tasks into executable subgoals.
"""

import json
from typing import List, Optional
from ..utils.deepseek_client import DeepSeekClient, DeepSeekAPIError
from ..utils.logger import get_logger
from .schemas import Subgoal, TaskPlan

logger = get_logger(__name__)


PLANNING_SYSTEM_PROMPT = """You are an expert task planner. Break down complex tasks into clear, executable subgoals.

Rules:
1. Create 3-10 subgoals (more complex tasks need more subgoals)
2. Each subgoal must be specific and measurable
3. Identify required tools for each subgoal
4. Specify dependencies (which subgoals must complete first)
5. Define validation criteria (how to verify success)

Available tools:
- web_search: Search the internet for information
- python_executor: Execute Python code in a sandbox
- file_ops: Read, write, create files
- http_client: Make HTTP requests
- shell_executor: Run shell commands (limited)
- rag_query: Query vector database for context
- notification: Send notifications

Output ONLY valid JSON with this structure:
{
  "subgoals": [
    {
      "id": "step_1",
      "description": "Clear description of what to do",
      "required_tools": ["tool_name"],
      "dependencies": [],
      "validation_criteria": "How to verify this succeeded",
      "estimated_cost": 0.05
    }
  ]
}"""


class TaskPlanner:
    """
    Plans task execution by breaking tasks into subgoals.
    
    Uses DeepSeek to analyze tasks and create structured plans.
    Validates plans for feasibility and cost.
    """
    
    def __init__(
        self,
        deepseek_client: DeepSeekClient,
        max_subgoals: int = 20,
        max_estimated_cost: float = 10.0,
    ):
        """
        Initialize task planner.
        
        Args:
            deepseek_client: DeepSeek API client
            max_subgoals: Maximum subgoals allowed in a plan
            max_estimated_cost: Maximum estimated cost for a plan
        """
        self.client = deepseek_client
        self.max_subgoals = max_subgoals
        self.max_estimated_cost = max_estimated_cost
    
    async def create_plan(
        self,
        task: str,
        context: Optional[str] = None,
    ) -> TaskPlan:
        """
        Create an execution plan for a task.
        
        Args:
            task: The task to plan
            context: Optional additional context
        
        Returns:
            TaskPlan with ordered subgoals
        
        Raises:
            DeepSeekAPIError: If planning fails
            ValueError: If plan is invalid
        """
        logger.info("Creating plan for task", task=task[:100])
        
        # Build prompt
        user_prompt = f"Task: {task}"
        if context:
            user_prompt += f"\n\nAdditional Context:\n{context}"
        
        # Get plan from DeepSeek
        try:
            response = await self.client.complete(
                messages=[
                    {"role": "system", "content": PLANNING_SYSTEM_PROMPT},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=0.3,  # Lower temperature for more focused planning
                max_tokens=2000,
            )
            
            # Extract content
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
            else:
                raise DeepSeekAPIError("No content in planning response")
            
            # Parse JSON
            plan_data = self._extract_json(content)
            
            # Validate and convert to Pydantic models
            subgoals = [
                Subgoal(
                    id=sg["id"],
                    description=sg["description"],
                    required_tools=sg.get("required_tools", []),
                    dependencies=sg.get("dependencies", []),
                    validation_criteria=sg.get("validation_criteria", "Check if step completed"),
                    estimated_cost=float(sg.get("estimated_cost", 0.1)),
                )
                for sg in plan_data.get("subgoals", [])
            ]
            
            # Validate plan
            self._validate_plan(subgoals)
            
            # Calculate total estimated cost
            total_cost = sum(sg.estimated_cost for sg in subgoals)
            
            plan = TaskPlan(
                task_description=task,
                subgoals=subgoals,
                estimated_total_cost=total_cost,
            )
            
            logger.info(
                "Plan created successfully",
                subgoals_count=len(subgoals),
                estimated_cost=total_cost,
            )
            
            return plan
            
        except Exception as e:
            logger.error("Planning failed", error=str(e))
            # Fallback: create a single subgoal
            return self._create_fallback_plan(task)
    
    def _extract_json(self, content: str) -> dict:
        """
        Extract JSON from response content.
        
        Handles cases where JSON is wrapped in markdown code blocks.
        """
        content = content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError as e:
            logger.error("Failed to parse JSON", content=content[:200], error=str(e))
            raise ValueError(f"Invalid JSON in plan: {e}")
    
    def _validate_plan(self, subgoals: List[Subgoal]) -> None:
        """
        Validate a plan for feasibility.
        
        Checks:
        - Not too many subgoals
        - Valid dependency graph (no cycles)
        - Cost within limits
        
        Raises:
            ValueError: If plan is invalid
        """
        if not subgoals:
            raise ValueError("Plan must have at least one subgoal")
        
        if len(subgoals) > self.max_subgoals:
            raise ValueError(f"Too many subgoals: {len(subgoals)} > {self.max_subgoals}")
        
        # Check for duplicate IDs
        ids = [sg.id for sg in subgoals]
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate subgoal IDs found")
        
        # Check dependencies exist
        id_set = set(ids)
        for sg in subgoals:
            for dep in sg.dependencies:
                if dep not in id_set:
                    raise ValueError(f"Subgoal {sg.id} depends on non-existent {dep}")
        
        # Check for dependency cycles (simple check)
        if self._has_cycle(subgoals):
            raise ValueError("Circular dependencies detected in plan")
        
        # Check total cost
        total_cost = sum(sg.estimated_cost for sg in subgoals)
        if total_cost > self.max_estimated_cost:
            raise ValueError(f"Plan too expensive: ${total_cost:.2f} > ${self.max_estimated_cost:.2f}")
    
    def _has_cycle(self, subgoals: List[Subgoal]) -> bool:
        """Check if dependency graph has cycles using DFS."""
        adj = {sg.id: sg.dependencies for sg in subgoals}
        visited = set()
        rec_stack = set()
        
        def dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)
            
            for neighbor in adj.get(node, []):
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True
            
            rec_stack.remove(node)
            return False
        
        for sg in subgoals:
            if sg.id not in visited:
                if dfs(sg.id):
                    return True
        
        return False
    
    def _create_fallback_plan(self, task: str) -> TaskPlan:
        """
        Create a simple fallback plan when AI planning fails.
        
        Just creates a single subgoal for the entire task.
        """
        logger.warning("Using fallback plan", task=task[:100])
        
        subgoal = Subgoal(
            id="fallback_1",
            description=task,
            required_tools=["python_executor", "file_ops"],
            dependencies=[],
            validation_criteria="Task completed successfully",
            estimated_cost=0.5,
        )
        
        return TaskPlan(
            task_description=task,
            subgoals=[subgoal],
            estimated_total_cost=0.5,
        )
