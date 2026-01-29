"""
Example: Using DweepBot programmatically.

This shows how to use DweepBot from Python code rather than the CLI.
"""

import asyncio
import os
from pathlib import Path

from dweepbot import (
    AgentConfig,
    AutonomousAgent,
    DeepSeekClient,
    create_registry_with_default_tools,
    ToolExecutionContext
)


async def main():
    """Run a simple example task."""
    
    # Check for API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        print("Error: DEEPSEEK_API_KEY environment variable not set")
        print("Get your key from: https://platform.deepseek.com/api_keys")
        return
    
    # Create configuration
    config = AgentConfig(
        deepseek_api_key=api_key,
        max_cost_usd=2.0,
        max_iterations=30,
        enable_code_execution=True,
        enable_web_search=False,  # Set to True if you installed dweepbot[web]
        workspace_path=Path("./example_workspace")
    )
    
    print("🦈 DweepBot Example")
    print("=" * 60)
    
    # Initialize LLM client
    async with DeepSeekClient(
        api_key=config.deepseek_api_key,
        model=config.deepseek_model
    ) as llm_client:
        
        # Create tool registry
        context = ToolExecutionContext(
            workspace_path=str(config.workspace_path),
            max_file_size_mb=config.max_file_size_mb,
            network_timeout=config.network_timeout
        )
        
        tools = create_registry_with_default_tools(context)
        
        print(f"\nRegistered {len(tools.list_tools())} tools:")
        for tool_name in tools.list_tools():
            print(f"  - {tool_name}")
        
        # Create agent
        agent = AutonomousAgent(config, llm_client, tools)
        
        # Define task
        task = """
        Create a simple data analysis script that:
        1. Generates 100 random numbers between 1 and 100
        2. Calculates their mean, median, and standard deviation
        3. Saves the results to a file called 'stats_results.txt'
        """
        
        print(f"\nTask: {task.strip()}")
        print("\n" + "=" * 60)
        print()
        
        # Run agent and display updates
        async for update in agent.run(task):
            
            if update.type == "phase_change":
                print(f"\n▶ {update.message}")
            
            elif update.type == "planning_complete":
                subgoals = update.data.get("subgoals", [])
                print(f"\n✓ Created plan with {len(subgoals)} steps:")
                for i, sg in enumerate(subgoals, 1):
                    print(f"  {i}. {sg}")
            
            elif update.type == "subgoal_start":
                print(f"\n→ {update.message}")
            
            elif update.type == "tool_execution":
                tool = update.data.get("tool", "")
                print(f"  Using {tool}...")
            
            elif update.type == "tool_result":
                tool = update.data.get("tool", "")
                success = update.data.get("success", False)
                
                if success:
                    print(f"  ✓ {tool} completed")
                else:
                    error = update.data.get("error", "Unknown error")
                    print(f"  ✗ {tool} failed: {error}")
            
            elif update.type == "cost_update":
                cost = update.data.get("total_cost", 0)
                tokens = update.data.get("tokens_used", 0)
                print(f"  💰 Cost: ${cost:.4f} | Tokens: {tokens:,}")
            
            elif update.type == "completion":
                print("\n" + "=" * 60)
                print("✓ Task completed successfully!")
                print("=" * 60)
                
                data = update.data
                print(f"\nSteps completed: {data.get('steps_completed', 0)}")
                print(f"Total cost: ${data.get('total_cost', 0):.4f}")
                print(f"Total time: {data.get('total_time', 0):.1f}s")
                
                if data.get("final_output"):
                    print(f"\nResult:\n{data['final_output']}")
            
            elif update.type == "error":
                print(f"\n❌ Error: {update.message}")
        
        # Check workspace
        print(f"\nWorkspace contents:")
        workspace = Path(config.workspace_path)
        if workspace.exists():
            for file in workspace.iterdir():
                if file.is_file():
                    print(f"  - {file.name} ({file.stat().st_size} bytes)")


if __name__ == "__main__":
    # Run the example
    asyncio.run(main())
