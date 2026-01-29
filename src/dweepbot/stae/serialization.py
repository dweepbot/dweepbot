"""
State serialization for debugging and persistence.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict
from ..core.schemas import ExecutionContext
from ..utils.logger import get_logger

logger = get_logger(__name__)


def serialize_state(context: ExecutionContext, filepath: Path) -> None:
    """
    Serialize agent state to JSON file.
    
    Args:
        context: The execution context to serialize
        filepath: Path to save the JSON file
    """
    try:
        # Convert to dict using Pydantic
        state_dict = context.model_dump(mode="json")
        
        # Write to file
        with open(filepath, "w") as f:
            json.dump(state_dict, f, indent=2, default=str)
        
        logger.info("State serialized", path=str(filepath))
        
    except Exception as e:
        logger.error("State serialization failed", error=str(e))
        raise


def deserialize_state(filepath: Path) -> ExecutionContext:
    """
    Deserialize agent state from JSON file.
    
    Args:
        filepath: Path to the JSON file
    
    Returns:
        Reconstructed ExecutionContext
    """
    try:
        with open(filepath, "r") as f:
            state_dict = json.load(f)
        
        # Reconstruct using Pydantic
        context = ExecutionContext(**state_dict)
        
        logger.info("State deserialized", path=str(filepath))
        return context
        
    except Exception as e:
        logger.error("State deserialization failed", error=str(e))
        raise


def create_debug_snapshot(
    context: ExecutionContext,
    error: Exception,
    filepath: Path,
) -> None:
    """
    Create a detailed debug snapshot when an error occurs.
    
    Args:
        context: Current execution context
        error: The exception that occurred
        filepath: Path to save the snapshot
    """
    snapshot = {
        "timestamp": datetime.utcnow().isoformat(),
        "error": {
            "type": type(error).__name__,
            "message": str(error),
        },
        "state": context.model_dump(mode="json"),
    }
    
    with open(filepath, "w") as f:
        json.dump(snapshot, f, indent=2, default=str)
    
    logger.info("Debug snapshot created", path=str(filepath))
