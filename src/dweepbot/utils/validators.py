"""
Input validation utilities for DweepBot.
"""

from typing import Any, Dict
from pydantic import BaseModel, Field, ValidationError, field_validator


class TaskInput(BaseModel):
    """Validated task input."""
    task: str = Field(..., min_length=3, max_length=5000)
    
    @field_validator("task")
    @classmethod
    def validate_task_content(cls, v: str) -> str:
        """Ensure task is meaningful."""
        stripped = v.strip()
        if not stripped:
            raise ValueError("Task cannot be empty")
        if len(stripped) < 3:
            raise ValueError("Task must be at least 3 characters")
        return stripped


class ToolInput(BaseModel):
    """Base validator for tool inputs."""
    pass


def validate_task(task: str) -> str:
    """
    Validate a task string.
    
    Args:
        task: The task to validate
    
    Returns:
        Validated and cleaned task string
    
    Raises:
        ValueError: If task is invalid
    """
    try:
        validated = TaskInput(task=task)
        return validated.task
    except ValidationError as e:
        errors = "; ".join([f"{err['loc'][0]}: {err['msg']}" for err in e.errors()])
        raise ValueError(f"Invalid task: {errors}")


def validate_tool_input(tool_name: str, inputs: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate tool inputs against expected schema.
    
    Args:
        tool_name: Name of the tool
        inputs: Input parameters
    
    Returns:
        Validated inputs
    
    Raises:
        ValueError: If inputs are invalid
    """
    # Basic validation - tools should define their own schemas
    if not isinstance(inputs, dict):
        raise ValueError(f"Tool inputs must be a dictionary, got {type(inputs)}")
    
    return inputs
