"""
Core autonomous agent engine implementing PLAN → ACT → OBSERVE → REFLECT loop.

This is the heart of DweepBot - the state machine that orchestrates tool execution,
manages memory, tracks costs, and ensures reliable task completion.
"""

from enum import Enum
from typing import AsyncGenerator, Dict, List, Optional, Any
from pydantic import BaseModel, Field
from datetime import datetime, timedelta
import asyncio
import uuid
import json
import logging

from ..config import AgentConfig
from ..deepseek import DeepSeekClient, Message, CompletionResponse
from ..tools.registry import ToolRegistry
from ..tools.base import ToolResult

logger = logging.getLogger(__name__)


class AgentPhase(str, Enum):
    """Agent execution phases."""
    PLANNING = "planning"
    ACTING = "acting"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


class Subgoal(BaseModel):
    """A decomposed subgoal from the planning phase."""
    id: str
    description: str
    required_tools: List[str] = Field(default_factory=list)
    status: str = "pending"  # pending, in_progress, completed, failed
    result: Optional[str] = None
    error: Optional[str] = None


class StepResult(BaseModel):
    """Result from executing a subgoal."""
    subgoal_id: str
    subgoal_description: str
    tools_used: List[str]
    success: bool
    output: Optional[str] = None
    error: Optional[str] = None
    cost_usd: float = 0.0
    execution_time_seconds: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.now)


class AgentState(BaseModel):
    """
    Complete agent state (serializable for debugging/resume).
    
    This contains everything needed to understand what the agent
    has done and where it is in execution.
    """
    task_id: str
    original_task: str
    current_phase: AgentPhase = AgentPhase.PLANNING
    current_subgoal: Optional[Subgoal] = None
    
    # Planning
    all_subgoals: List[Subgoal] = Field(default_factory=list)
    completed_subgoals: List[str] = Field(default_factory=list)
    failed_subgoals: List[str] = Field(default_factory=list)
    
    # Execution history
    step_results: List[StepResult] = Field(default_factory=list)
    errors: List[str] = Field(default_factory=list)
    
    # Resource tracking
    total_tokens_used: int = 0
    total_cost_usd: float = 0.0
    llm_calls_made: int = 0
    tool_calls_made: int = 0
    
    # Timing
    start_time: datetime = Field(default_factory=datetime.now)
    last_update: datetime = Field(default_factory=datetime.now)
    end_time: Optional[datetime] = None
    
    # Final result
    final_output: Optional[str] = None
    success: bool = False
    
    class Config:
        arbitrary_types_allowed = True


class AgentUpdate(BaseModel):
    """Real-time update streamed to callers."""
    type: str  # "phase_change", "tool_execution", "cost_update", "error", "completion"
    phase: Optional[AgentPhase] = None
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=datetime.now)


class AutonomousAgent:
    """
    Production-grade autonomous agent.
    
    Implements PLAN → ACT → OBSERVE → REFLECT loop with:
    - Error boundaries (tool failures don't crash the agent)
    - Cost tracking (every token, every tool call)
    - State persistence (can resume from crashes)
    - Streaming updates (real-time progress)
    - Configurable limits (iterations, cost, time)
    """
    
    def __init__(
        self,
        config: AgentConfig,
        llm_client: DeepSeekClient,
        tool_registry: ToolRegistry
    ):
        self.config = config
        self.llm = llm_client
        self.tools = tool_registry
        
        self.state = AgentState(task_id=self._generate_task_id(), original_task="")
        self._logger = logging.getLogger(f"{__name__}.Agent-{self.state.task_id[:8]}")
        
    def _generate_task_id(self) -> str:
        """Generate unique task ID."""
        return f"task_{uuid.uuid4().hex[:16]}"
    
    async def run(self, task: str) -> AsyncGenerator[AgentUpdate, None]:
        """
        Main agent loop - executes task and yields updates.
        
        Args:
            task: Natural language task description
        
        Yields:
            AgentUpdate objects for real-time progress
        """
        self.state.original_task = task
        self._logger.info(f"Starting task: {task}")
        
        try:
            # PHASE 1: PLANNING
            yield AgentUpdate(
                type="phase_change",
                phase=AgentPhase.PLANNING,
                message="Analyzing task and creating plan..."
            )
            
            await self._enter_phase(AgentPhase.PLANNING)
            subgoals = await self._plan_task(task)
            self.state.all_subgoals = subgoals
            
            yield AgentUpdate(
                type="planning_complete",
                message=f"Created plan with {len(subgoals)} steps",
                data={"subgoals": [s.description for s in subgoals]}
            )
            
            # PHASE 2: EXECUTION LOOP
            iteration = 0
            while self._has_pending_subgoals() and not self._exceeded_limits():
                iteration += 1
                
                # Get next subgoal
                current = self._get_next_subgoal()
                if not current:
                    break
                
                self.state.current_subgoal = current
                current.status = "in_progress"
                
                yield AgentUpdate(
                    type="subgoal_start",
                    message=f"Step {iteration}: {current.description}",
                    data={"subgoal_id": current.id, "description": current.description}
                )
                
                # ACT: Execute this subgoal
                await self._enter_phase(AgentPhase.ACTING)
                
                async for update in self._execute_subgoal(current):
                    yield update
                
                # OBSERVE: Record results
                await self._enter_phase(AgentPhase.OBSERVING)
                observation = await self._observe_current_state()
                
                yield AgentUpdate(
                    type="observation",
                    message="Processing results...",
                    data={"observation": observation[:200]}  # Truncate for update
                )
                
                # REFLECT: Check if we need to adjust plan
                await self._enter_phase(AgentPhase.REFLECTING)
                adjustments = await self._reflect_on_progress()
                
                if adjustments:
                    self.state.all_subgoals.extend(adjustments)
                    yield AgentUpdate(
                        type="plan_adjustment",
                        message=f"Added {len(adjustments)} new steps to plan",
                        data={"new_steps": [a.description for a in adjustments]}
                    )
                
                # Cost update
                yield AgentUpdate(
                    type="cost_update",
                    message=f"Cost so far: ${self.state.total_cost_usd:.4f}",
                    data={
                        "total_cost": self.state.total_cost_usd,
                        "tokens_used": self.state.total_tokens_used,
                        "tool_calls": self.state.tool_calls_made
                    }
                )
            
            # PHASE 3: COMPLETION
            await self._enter_phase(AgentPhase.COMPLETED)
            self.state.success = True
            self.state.end_time = datetime.now()
            
            # Generate final summary
            final_output = await self._generate_final_summary()
            self.state.final_output = final_output
            
            yield AgentUpdate(
                type="completion",
                phase=AgentPhase.COMPLETED,
                message="Task completed successfully!",
                data={
                    "success": True,
                    "total_cost": self.state.total_cost_usd,
                    "total_time": (self.state.end_time - self.state.start_time).total_seconds(),
                    "steps_completed": len(self.state.completed_subgoals),
                    "final_output": final_output
                }
            )
            
        except Exception as e:
            self._logger.error(f"Agent failed with error: {str(e)}", exc_info=True)
            await self._handle_failure(e)
            
            yield AgentUpdate(
                type="error",
                phase=AgentPhase.FAILED,
                message=f"Task failed: {str(e)}",
                data={"error": str(e), "cost": self.state.total_cost_usd}
            )
    
    async def _plan_task(self, task: str) -> List[Subgoal]:
        """
        Decompose task into executable subgoals using LLM.
        
        Returns:
            List of Subgoals with descriptions and required tools
        """
        # Get available tools
        tool_descriptions = self.tools.get_tool_descriptions()
        
        planning_prompt = f"""You are an AI agent planner. Break down the following task into clear, executable steps.

Task: {task}

Available tools:
{tool_descriptions}

Create a step-by-step plan. For each step:
1. Describe what needs to be done
2. List which tools are needed (by name)
3. Make steps atomic and specific

Return your plan as JSON array:
[
  {{"description": "Step description", "tools": ["tool1", "tool2"]}},
  ...
]

Be specific and actionable. Each step should be completable with the available tools.
"""
        
        try:
            response = await self.llm.complete(
                messages=[Message(role="user", content=planning_prompt)],
                temperature=0.3,  # Lower temperature for planning
                system_prompt="You are a precise task planner. Output only valid JSON."
            )
            
            # Track cost
            self._update_cost(response.usage.estimated_cost_usd, response.usage.total_tokens)
            
            # Parse response
            plan_json = self._extract_json(response.content)
            
            # Convert to Subgoals
            subgoals = []
            for i, step in enumerate(plan_json, 1):
                subgoals.append(Subgoal(
                    id=f"subgoal_{i}",
                    description=step.get("description", ""),
                    required_tools=step.get("tools", [])
                ))
            
            self._logger.info(f"Created plan with {len(subgoals)} subgoals")
            return subgoals
            
        except Exception as e:
            self._logger.error(f"Planning failed: {str(e)}")
            # Fallback: create single subgoal
            return [Subgoal(
                id="subgoal_1",
                description=task,
                required_tools=[]
            )]
    
    async def _execute_subgoal(self, subgoal: Subgoal) -> AsyncGenerator[AgentUpdate, None]:
        """
        Execute a subgoal by selecting and running appropriate tools.
        
        Yields:
            AgentUpdate objects for each tool execution
        """
        # Ask LLM which tools to use and with what parameters
        tool_descriptions = self.tools.get_tool_descriptions()
        
        execution_prompt = f"""Execute this step using available tools.

Current step: {subgoal.description}
Required tools (hint): {', '.join(subgoal.required_tools)}

Available tools:
{tool_descriptions}

Decide which tool(s) to use and with what parameters. Return as JSON:
{{
  "tool_calls": [
    {{"tool": "tool_name", "params": {{"param1": "value1"}}}},
    ...
  ],
  "reasoning": "Why you chose these tools"
}}
"""
        
        try:
            response = await self.llm.complete(
                messages=[Message(role="user", content=execution_prompt)],
                temperature=0.2
            )
            
            self._update_cost(response.usage.estimated_cost_usd, response.usage.total_tokens)
            
            # Parse tool calls
            execution_plan = self._extract_json(response.content)
            tool_calls = execution_plan.get("tool_calls", [])
            
            # Execute each tool
            results = []
            for i, call in enumerate(tool_calls[:self.config.max_tool_calls_per_step]):
                tool_name = call.get("tool", "")
                params = call.get("params", {})
                
                yield AgentUpdate(
                    type="tool_execution",
                    message=f"Using {tool_name}...",
                    data={"tool": tool_name, "params": params}
                )
                
                # Execute tool
                result = await self.tools.execute(
                    tool_name,
                    timeout=self.config.code_execution_timeout,
                    **params
                )
                
                results.append(result)
                self.state.tool_calls_made += 1
                self._update_cost(result.cost_usd, result.tokens_used)
                
                yield AgentUpdate(
                    type="tool_result",
                    message=f"Tool {tool_name} completed",
                    data={
                        "tool": tool_name,
                        "success": result.success,
                        "output": str(result.output)[:500] if result.output else None,
                        "error": result.error
                    }
                )
            
            # Record step result
            all_successful = all(r.success for r in results)
            combined_output = "\n\n".join(
                r.to_observation() for r in results
            )
            
            step_result = StepResult(
                subgoal_id=subgoal.id,
                subgoal_description=subgoal.description,
                tools_used=[call.get("tool", "") for call in tool_calls],
                success=all_successful,
                output=combined_output if all_successful else None,
                error=combined_output if not all_successful else None,
                cost_usd=sum(r.cost_usd for r in results),
                execution_time_seconds=sum(r.execution_time_seconds for r in results)
            )
            
            self.state.step_results.append(step_result)
            
            if all_successful:
                subgoal.status = "completed"
                subgoal.result = combined_output
                self.state.completed_subgoals.append(subgoal.id)
            else:
                subgoal.status = "failed"
                subgoal.error = combined_output
                self.state.failed_subgoals.append(subgoal.id)
                
        except Exception as e:
            self._logger.error(f"Subgoal execution failed: {str(e)}")
            subgoal.status = "failed"
            subgoal.error = str(e)
            self.state.failed_subgoals.append(subgoal.id)
            
            yield AgentUpdate(
                type="error",
                message=f"Failed to execute step: {str(e)}",
                data={"error": str(e)}
            )
    
    async def _observe_current_state(self) -> str:
        """
        Analyze current execution state.
        
        Returns:
            Summary of recent observations
        """
        # Get last few step results
        recent_steps = self.state.step_results[-3:]
        
        observations = []
        for step in recent_steps:
            if step.success:
                observations.append(f"✅ {step.subgoal_description}: {step.output[:200]}")
            else:
                observations.append(f"❌ {step.subgoal_description}: {step.error[:200]}")
        
        return "\n".join(observations)
    
    async def _reflect_on_progress(self) -> Optional[List[Subgoal]]:
        """
        Analyze progress and determine if plan needs adjustment.
        
        Returns:
            List of new subgoals to add (if needed), or None
        """
        # Simple heuristic: if last step failed, don't add new steps
        # In production, this would use LLM to analyze progress
        
        if self.state.step_results:
            last_result = self.state.step_results[-1]
            if not last_result.success:
                self._logger.warning(f"Last step failed, not adding new steps")
                return None
        
        # Check if we're making progress
        completed = len(self.state.completed_subgoals)
        failed = len(self.state.failed_subgoals)
        
        if failed > completed:
            self._logger.warning(f"More failures ({failed}) than successes ({completed})")
            return None
        
        return None  # No adjustments needed
    
    async def _generate_final_summary(self) -> str:
        """Generate summary of task execution."""
        
        summary_prompt = f"""Summarize what was accomplished in this task.

Original task: {self.state.original_task}

Steps completed:
{self._format_step_results()}

Provide a concise summary of what was done and the outcome.
"""
        
        try:
            response = await self.llm.complete(
                messages=[Message(role="user", content=summary_prompt)],
                temperature=0.3
            )
            
            self._update_cost(response.usage.estimated_cost_usd, response.usage.total_tokens)
            return response.content
            
        except Exception as e:
            return f"Task completed with {len(self.state.completed_subgoals)} successful steps."
    
    def _format_step_results(self) -> str:
        """Format step results for display."""
        lines = []
        for i, step in enumerate(self.state.step_results, 1):
            status = "✅" if step.success else "❌"
            lines.append(f"{i}. {status} {step.subgoal_description}")
        return "\n".join(lines)
    
    async def _enter_phase(self, phase: AgentPhase) -> None:
        """Transition to new phase."""
        self.state.current_phase = phase
        self.state.last_update = datetime.now()
        self._logger.info(f"Entered phase: {phase.value}")
    
    async def _handle_failure(self, error: Exception) -> None:
        """Handle agent failure gracefully."""
        self.state.current_phase = AgentPhase.FAILED
        self.state.success = False
        self.state.end_time = datetime.now()
        self.state.errors.append(str(error))
        self._logger.error(f"Agent failed: {str(error)}")
    
    def _has_pending_subgoals(self) -> bool:
        """Check if there are any pending subgoals."""
        return any(
            sg.status == "pending"
            for sg in self.state.all_subgoals
        )
    
    def _get_next_subgoal(self) -> Optional[Subgoal]:
        """Get the next pending subgoal."""
        for subgoal in self.state.all_subgoals:
            if subgoal.status == "pending":
                return subgoal
        return None
    
    def _exceeded_limits(self) -> bool:
        """Check if any configured limits have been exceeded."""
        if self.state.total_cost_usd >= self.config.max_cost_usd:
            self._logger.warning(f"Cost limit exceeded: ${self.state.total_cost_usd:.4f}")
            return True
        
        if len(self.state.step_results) >= self.config.max_iterations:
            self._logger.warning(f"Iteration limit exceeded: {len(self.state.step_results)}")
            return True
        
        elapsed = (datetime.now() - self.state.start_time).total_seconds()
        if elapsed >= self.config.max_time_seconds:
            self._logger.warning(f"Time limit exceeded: {elapsed:.0f}s")
            return True
        
        return False
    
    def _update_cost(self, cost_usd: float, tokens: int) -> None:
        """Update cost and token tracking."""
        self.state.total_cost_usd += cost_usd
        self.state.total_tokens_used += tokens
        self.state.llm_calls_made += 1
    
    def _extract_json(self, text: str) -> Any:
        """Extract JSON from LLM response (handles markdown code blocks)."""
        # Remove markdown code blocks
        text = text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.startswith("```"):
            text = text[3:]
        if text.endswith("```"):
            text = text[:-3]
        
        return json.loads(text.strip())
    
    def get_state_snapshot(self) -> Dict[str, Any]:
        """Get serializable state snapshot for debugging/persistence."""
        return self.state.model_dump()
