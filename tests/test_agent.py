"""
Integration tests for DweepBot autonomous agent.

Tests complete workflows end-to-end.
"""

import pytest
import asyncio
from pathlib import Path
import os

from dweepbot import (
    AgentConfig,
    AutonomousAgent,
    DeepSeekClient,
    create_registry_with_default_tools,
    ToolExecutionContext
)


@pytest.fixture
def config():
    """Create test configuration."""
    return AgentConfig(
        deepseek_api_key=os.getenv("DEEPSEEK_API_KEY", "test-key"),
        max_cost_usd=1.0,
        max_iterations=10,
        workspace_path=Path("./test_workspace"),
        enable_code_execution=True,
        enable_web_search=False
    )


@pytest.fixture
async def agent_components(config):
    """Create agent components for testing."""
    llm_client = DeepSeekClient(
        api_key=config.deepseek_api_key,
        model=config.deepseek_model
    )
    
    context = ToolExecutionContext(
        workspace_path=str(config.workspace_path),
        max_file_size_mb=config.max_file_size_mb,
        network_timeout=config.network_timeout
    )
    
    tools = create_registry_with_default_tools(context)
    
    yield llm_client, tools
    
    await llm_client.close()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set"
)
async def test_simple_file_task(agent_components, config):
    """Test a simple file writing task."""
    llm_client, tools = agent_components
    
    agent = AutonomousAgent(config, llm_client, tools)
    
    task = "Create a file called 'test.txt' with the content 'Hello, DweepBot!'"
    
    updates = []
    async for update in agent.run(task):
        updates.append(update)
    
    # Check that task completed
    completion_updates = [u for u in updates if u.type == "completion"]
    assert len(completion_updates) > 0
    
    final_update = completion_updates[0]
    assert final_update.data.get("success") is True
    
    # Check cost tracking
    assert agent.state.total_cost_usd > 0
    assert agent.state.total_cost_usd < config.max_cost_usd
    
    # Check file was created
    test_file = config.workspace_path / "test.txt"
    assert test_file.exists()
    assert "Hello, DweepBot!" in test_file.read_text()


@pytest.mark.asyncio
@pytest.mark.skipif(
    not os.getenv("DEEPSEEK_API_KEY"),
    reason="DEEPSEEK_API_KEY not set"
)
async def test_multi_step_task(agent_components, config):
    """Test a task requiring multiple steps."""
    llm_client, tools = agent_components
    
    agent = AutonomousAgent(config, llm_client, tools)
    
    task = """
    1. Create a Python script that calculates the first 10 Fibonacci numbers
    2. Save it to 'fibonacci.py'
    3. List all files in the workspace
    """
    
    updates = []
    async for update in agent.run(task):
        updates.append(update)
    
    # Check completion
    completion_updates = [u for u in updates if u.type == "completion"]
    assert len(completion_updates) > 0
    
    # Check that multiple steps were executed
    step_results = agent.state.step_results
    assert len(step_results) >= 2
    
    # Check file exists
    fib_file = config.workspace_path / "fibonacci.py"
    assert fib_file.exists()
    
    # Check file contains Fibonacci logic
    content = fib_file.read_text()
    assert "fibonacci" in content.lower() or "fib" in content.lower()


@pytest.mark.asyncio
async def test_tool_execution():
    """Test individual tool execution."""
    from dweepbot.tools.file_ops import WriteFileTool
    from dweepbot.tools.base import ToolExecutionContext
    
    context = ToolExecutionContext(
        workspace_path="./test_workspace",
        max_file_size_mb=10
    )
    
    tool = WriteFileTool(context)
    
    result = await tool.execute(
        file_path="test_tool.txt",
        content="Tool test content"
    )
    
    assert result.success is True
    assert "test_tool.txt" in str(result.output)
    
    # Cleanup
    Path("./test_workspace/test_tool.txt").unlink(missing_ok=True)


@pytest.mark.asyncio
async def test_python_executor():
    """Test Python code execution."""
    from dweepbot.tools.python_executor import PythonExecutorTool
    from dweepbot.tools.base import ToolExecutionContext
    
    context = ToolExecutionContext(
        workspace_path="./test_workspace"
    )
    
    tool = PythonExecutorTool(context)
    
    # Test successful execution
    result = await tool.execute(code="print(2 + 2)")
    assert result.success is True
    assert "4" in str(result.output)
    
    # Test error handling
    result = await tool.execute(code="1 / 0")
    assert result.success is False
    assert "ZeroDivisionError" in str(result.error)
    
    # Test restricted imports
    result = await tool.execute(code="import os")
    assert result.success is False
    assert "not allowed" in str(result.error).lower()


@pytest.mark.asyncio
async def test_cost_tracking(agent_components, config):
    """Test that cost tracking works correctly."""
    llm_client, tools = agent_components
    
    agent = AutonomousAgent(config, llm_client, tools)
    
    task = "Write 'test' to a file called 'cost_test.txt'"
    
    async for update in agent.run(task):
        if update.type == "cost_update":
            cost = update.data.get("total_cost", 0)
            assert cost >= 0
            assert cost < config.max_cost_usd
    
    # Final cost should be tracked
    assert agent.state.total_cost_usd > 0
    assert agent.state.total_tokens_used > 0


@pytest.mark.asyncio
async def test_error_recovery(agent_components, config):
    """Test that agent handles errors gracefully."""
    llm_client, tools = agent_components
    
    agent = AutonomousAgent(config, llm_client, tools)
    
    # Task that will likely cause some tool failures
    task = "Read a file that doesn't exist called 'nonexistent.txt'"
    
    updates = []
    async for update in agent.run(task):
        updates.append(update)
    
    # Agent should not crash
    # Check for error handling
    error_updates = [u for u in updates if u.type == "error"]
    
    # Some errors are expected for nonexistent file
    # But agent should complete (even if task "fails")
    completion_updates = [u for u in updates if u.type in ["completion", "error"]]
    assert len(completion_updates) > 0


def test_config_validation():
    """Test configuration validation."""
    # Valid config
    config = AgentConfig(
        deepseek_api_key="test-key",
        max_cost_usd=5.0,
        max_iterations=50
    )
    assert config.max_cost_usd == 5.0
    
    # Invalid config (negative cost)
    with pytest.raises(Exception):
        AgentConfig(
            deepseek_api_key="test-key",
            max_cost_usd=-1.0
        )


@pytest.mark.asyncio
async def test_state_serialization(agent_components, config):
    """Test that agent state can be serialized."""
    llm_client, tools = agent_components
    
    agent = AutonomousAgent(config, llm_client, tools)
    
    # Get state snapshot
    state_dict = agent.get_state_snapshot()
    
    assert isinstance(state_dict, dict)
    assert "task_id" in state_dict
    assert "current_phase" in state_dict
    assert "total_cost_usd" in state_dict
    
    # Should be JSON serializable
    import json
    json_str = json.dumps(state_dict, default=str)
    assert len(json_str) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
