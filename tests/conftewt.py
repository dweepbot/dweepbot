"""
Pytest configuration and shared fixtures.
"""

import pytest
import asyncio
from pathlib import Path
from typing import AsyncIterator, Dict, Any
from unittest.mock import AsyncMock, MagicMock

from dweepbot.config import AgentConfig
from dweepbot.utils.cost_tracker import CostTracker
from dweepbot.utils.deepseek_client import DeepSeekClient
from dweepbot.tools.registry import ToolRegistry
from dweepbot.core.planner import TaskPlanner
from dweepbot.core.executor import ToolExecutor


@pytest.fixture
def mock_config() -> AgentConfig:
    """Create a test configuration."""
    return AgentConfig(
        deepseek_api_key="test_key",
        max_iterations=10,
        max_cost_usd=1.0,
        workspace_path=Path("./test_workspace"),
    )


@pytest.fixture
def cost_tracker() -> CostTracker:
    """Create a cost tracker for testing."""
    return CostTracker(max_cost_usd=1.0)


@pytest.fixture
def mock_deepseek_client() -> AsyncMock:
    """Create a mock DeepSeek client."""
    client = AsyncMock(spec=DeepSeekClient)
    
    # Default successful response
    client.complete.return_value = {
        "choices": [
            {
                "message": {
                    "content": '{"subgoals": [{"id": "step_1", "description": "Test step", "required_tools": [], "dependencies": [], "validation_criteria": "Done", "estimated_cost": 0.1}]}'
                }
            }
        ],
        "usage": {
            "prompt_tokens": 100,
            "completion_tokens": 50,
        }
    }
    
    return client


@pytest.fixture
def tool_registry() -> ToolRegistry:
    """Create a tool registry for testing."""
    registry = ToolRegistry()
    
    # Register mock tools
    from dweepbot.tools.file_ops import FileOperationsTool
    from dweepbot.tools.python_executor import PythonExecutorTool
    
    registry.register(FileOperationsTool())
    registry.register(PythonExecutorTool())
    
    return registry


@pytest.fixture
async def task_planner(mock_deepseek_client: AsyncMock) -> TaskPlanner:
    """Create a task planner for testing."""
    return TaskPlanner(deepseek_client=mock_deepseek_client)


@pytest.fixture
def tool_executor(tool_registry: ToolRegistry, cost_tracker: CostTracker) -> ToolExecutor:
    """Create a tool executor for testing."""
    return ToolExecutor(
        tool_registry=tool_registry,
        cost_tracker=cost_tracker,
    )


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for async tests."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def workspace_dir(tmp_path: Path) -> Path:
    """Create a temporary workspace directory."""
    workspace = tmp_path / "workspace"
    workspace.mkdir()
    return workspace


@pytest.fixture(autouse=True)
def cleanup_workspace(workspace_dir: Path):
    """Cleanup workspace after each test."""
    yield
    # Cleanup logic if needed
    pass


# Markers for test categorization
def pytest_configure(config):
    """Configure custom pytest markers."""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow-running"
    )
    config.addinivalue_line(
        "markers", "requires_api: mark test as requiring API access"
    )
