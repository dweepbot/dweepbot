"""
Core Pydantic schemas for DweepBot agent system.

All data structures used across the agent lifecycle with full validation.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union
from pydantic import BaseModel, Field, field_validator


class AgentPhase(str, Enum):
    """Agent execution phases."""
    IDLE = "idle"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    REFLECTING = "reflecting"
    COMPLETED = "completed"
    FAILED = "failed"


class ToolCallStatus(str, Enum):
    """Status of a tool execution."""
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    TIMEOUT = "timeout"


class Subgoal(BaseModel):
    """A single subgoal in the task plan."""
    id: str = Field(..., description="Unique identifier for this subgoal")
    description: str = Field(..., description="Clear description of what needs to be done")
    required_tools: List[str] = Field(default_factory=list, description="Tools needed")
    dependencies: List[str] = Field(default_factory=list, description="IDs of subgoals that must complete first")
    validation_criteria: str = Field(..., description="How to verify this subgoal succeeded")
    estimated_cost: float = Field(default=0.0, description="Estimated cost in USD")
    completed: bool = Field(default=False)
    
    @field_validator("required_tools")
    @classmethod
    def validate_tools(cls, v: List[str]) -> List[str]:
        """Ensure tool names are non-empty."""
        return [t.strip() for t in v if t.strip()]


class ToolCall(BaseModel):
    """A single tool invocation with inputs and results."""
    tool_name: str = Field(..., description="Name of the tool to call")
    inputs: Dict[str, Any] = Field(default_factory=dict, description="Tool input parameters")
    output: Optional[Any] = Field(default=None, description="Tool execution result")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    status: ToolCallStatus = Field(default=ToolCallStatus.PENDING)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    duration_seconds: float = 0.0
    cost_usd: float = 0.0
    
    def mark_running(self) -> None:
        """Mark tool as running."""
        self.status = ToolCallStatus.RUNNING
        self.started_at = datetime.utcnow()
    
    def mark_success(self, output: Any, duration: float, cost: float = 0.0) -> None:
        """Mark tool as successfully completed."""
        self.status = ToolCallStatus.SUCCESS
        self.output = output
        self.completed_at = datetime.utcnow()
        self.duration_seconds = duration
        self.cost_usd = cost
    
    def mark_failed(self, error: str, duration: float) -> None:
        """Mark tool as failed."""
        self.status = ToolCallStatus.FAILED
        self.error = error
        self.completed_at = datetime.utcnow()
        self.duration_seconds = duration


class StepResult(BaseModel):
    """Result of a single agent step (plan/execute/observe/reflect)."""
    phase: AgentPhase
    subgoal_id: Optional[str] = None
    tool_calls: List[ToolCall] = Field(default_factory=list)
    observation: str = Field(default="", description="What was observed")
    reflection: str = Field(default="", description="Agent's reflection on the step")
    next_action: str = Field(default="", description="Planned next action")
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    cost_usd: float = Field(default=0.0)
    tokens_used: int = Field(default=0)


class AgentError(BaseModel):
    """An error that occurred during agent execution."""
    error_type: str = Field(..., description="Type/category of error")
    message: str = Field(..., description="Error message")
    phase: AgentPhase = Field(..., description="Phase where error occurred")
    tool_name: Optional[str] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    recoverable: bool = Field(default=True, description="Can agent recover from this?")
    stack_trace: Optional[str] = None


class CostBreakdown(BaseModel):
    """Detailed cost tracking for an agent run."""
    total_cost_usd: float = 0.0
    llm_cost_usd: float = 0.0
    tool_cost_usd: float = 0.0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tool_calls_count: int = 0
    cost_by_phase: Dict[str, float] = Field(default_factory=dict)
    cost_by_tool: Dict[str, float] = Field(default_factory=dict)


class AgentUpdate(BaseModel):
    """Real-time update from agent (for streaming)."""
    update_type: Literal["planning", "executing", "observing", "reflecting", "completed", "error"]
    message: str
    phase: AgentPhase
    progress: float = Field(default=0.0, ge=0.0, le=1.0, description="Progress 0.0-1.0")
    current_subgoal: Optional[Subgoal] = None
    tool_call: Optional[ToolCall] = None
    cost_so_far: float = 0.0
    timestamp: datetime = Field(default_factory=datetime.utcnow)


class TaskPlan(BaseModel):
    """Complete plan for executing a task."""
    task_description: str = Field(..., description="Original task")
    subgoals: List[Subgoal] = Field(..., description="Ordered list of subgoals")
    estimated_total_cost: float = Field(default=0.0)
    estimated_duration_seconds: float = Field(default=0.0)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    
    @field_validator("subgoals")
    @classmethod
    def validate_subgoals(cls, v: List[Subgoal]) -> List[Subgoal]:
        """Ensure at least one subgoal exists."""
        if not v:
            raise ValueError("Task plan must have at least one subgoal")
        return v
    
    def get_next_subgoal(self) -> Optional[Subgoal]:
        """Get the next incomplete subgoal with satisfied dependencies."""
        completed_ids = {s.id for s in self.subgoals if s.completed}
        
        for subgoal in self.subgoals:
            if subgoal.completed:
                continue
            
            # Check if all dependencies are completed
            deps_satisfied = all(dep in completed_ids for dep in subgoal.dependencies)
            if deps_satisfied:
                return subgoal
        
        return None


class ExecutionContext(BaseModel):
    """Context passed between agent phases."""
    task: str
    plan: Optional[TaskPlan] = None
    completed_steps: List[StepResult] = Field(default_factory=list)
    current_phase: AgentPhase = AgentPhase.IDLE
    errors: List[AgentError] = Field(default_factory=list)
    start_time: datetime = Field(default_factory=datetime.utcnow)
    total_cost: float = 0.0
    total_tokens: int = 0
    iteration_count: int = 0
    
    def add_step(self, step: StepResult) -> None:
        """Add a completed step to history."""
        self.completed_steps.append(step)
        self.total_cost += step.cost_usd
        self.total_tokens += step.tokens_used
        self.iteration_count += 1
    
    def add_error(self, error: AgentError) -> None:
        """Record an error."""
        self.errors.append(error)
    
    def get_recent_steps(self, n: int = 5) -> List[StepResult]:
        """Get the N most recent steps."""
        return self.completed_steps[-n:] if self.completed_steps else []
