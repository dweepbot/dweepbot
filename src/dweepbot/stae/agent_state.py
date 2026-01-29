"""
Agent state management with transitions and persistence.
"""

from datetime import datetime
from pathlib import Path
from typing import Optional
from ..core.schemas import AgentPhase, ExecutionContext, StepResult, AgentError, TaskPlan
from ..utils.logger import get_logger

logger = get_logger(__name__)


class AgentStateManager:
    """
    Manages agent state throughout execution.
    
    Features:
    - State transitions
    - State validation
    - State snapshots for debugging
    - Cost tracking integration
    """
    
    def __init__(self, task: str, workspace_path: Optional[Path] = None):
        """
        Initialize state manager.
        
        Args:
            task: The task being executed
            workspace_path: Optional path for state snapshots
        """
        self.context = ExecutionContext(task=task)
        self.workspace_path = workspace_path or Path("./workspace")
        self.workspace_path.mkdir(parents=True, exist_ok=True)
    
    def transition_to(self, new_phase: AgentPhase) -> None:
        """
        Transition to a new phase.
        
        Args:
            new_phase: The phase to transition to
        """
        old_phase = self.context.current_phase
        self.context.current_phase = new_phase
        
        logger.info("Phase transition", from_phase=old_phase, to_phase=new_phase)
    
    def set_plan(self, plan: TaskPlan) -> None:
        """Set the task plan."""
        self.context.plan = plan
        logger.info("Plan set", subgoals_count=len(plan.subgoals))
    
    def add_step_result(self, step: StepResult) -> None:
        """
        Add a completed step to the history.
        
        Args:
            step: The completed step
        """
        self.context.add_step(step)
        logger.info(
            "Step recorded",
            phase=step.phase,
            cost=step.cost_usd,
            total_cost=self.context.total_cost,
        )
    
    def add_error(self, error: AgentError) -> None:
        """
        Record an error.
        
        Args:
            error: The error that occurred
        """
        self.context.add_error(error)
        logger.error(
            "Error recorded",
            error_type=error.error_type,
            phase=error.phase,
            recoverable=error.recoverable,
        )
    
    def get_current_phase(self) -> AgentPhase:
        """Get current execution phase."""
        return self.context.current_phase
    
    def get_total_cost(self) -> float:
        """Get total cost so far."""
        return self.context.total_cost
    
    def get_iteration_count(self) -> int:
        """Get number of iterations."""
        return self.context.iteration_count
    
    def get_recent_steps(self, n: int = 5) -> list[StepResult]:
        """Get N most recent steps."""
        return self.context.get_recent_steps(n)
    
    def has_errors(self) -> bool:
        """Check if any errors occurred."""
        return len(self.context.errors) > 0
    
    def get_unrecoverable_errors(self) -> list[AgentError]:
        """Get list of unrecoverable errors."""
        return [e for e in self.context.errors if not e.recoverable]
    
    def snapshot(self, filename: Optional[str] = None) -> Path:
        """
        Create a state snapshot for debugging.
        
        Args:
            filename: Optional custom filename
        
        Returns:
            Path to snapshot file
        """
        if not filename:
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"agent_state_{timestamp}.json"
        
        snapshot_path = self.workspace_path / filename
        
        # Use serialization module
        from .serialization import serialize_state
        serialize_state(self.context, snapshot_path)
        
        logger.info("State snapshot created", path=str(snapshot_path))
        return snapshot_path
    
    def get_summary(self) -> dict:
        """
        Get a summary of current state.
        
        Returns:
            Dictionary with state summary
        """
        duration = (datetime.utcnow() - self.context.start_time).total_seconds()
        
        completed_subgoals = 0
        if self.context.plan:
            completed_subgoals = sum(
                1 for sg in self.context.plan.subgoals if sg.completed
            )
        
        return {
            "task": self.context.task,
            "current_phase": self.context.current_phase.value,
            "iterations": self.context.iteration_count,
            "total_cost_usd": round(self.context.total_cost, 4),
            "duration_seconds": round(duration, 2),
            "steps_completed": len(self.context.completed_steps),
            "errors_count": len(self.context.errors),
            "unrecoverable_errors": len(self.get_unrecoverable_errors()),
            "subgoals_completed": completed_subgoals,
            "subgoals_total": len(self.context.plan.subgoals) if self.context.plan else 0,
        }
