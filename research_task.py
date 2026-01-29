"""
Research task example - demonstrates multi-step workflow with web search.

This example shows how DweepBot handles complex research tasks.
"""

import asyncio
from pathlib import Path
from dweepbot.core.agent import AutonomousAgent
from dweepbot.config import AgentConfig
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

console = Console()


async def main():
    """Run a research task."""
    
    # Configure the agent with web search enabled
    config = AgentConfig(
        deepseek_api_key="your_api_key_here",
        max_iterations=30,
        max_cost_usd=2.0,
        enable_web_search=True,  # Enable web search
        workspace_path=Path("./workspace"),
    )
    
    # Create the agent
    agent = AutonomousAgent(config)
    
    # Complex research task
    task = """
    Research the following topics and create a comprehensive report:
    
    1. What are the key differences between LangGraph and LangChain?
    2. What are the main use cases for each framework?
    3. Which one is better for building autonomous agents?
    
    Write a 500-word comparison and save it to langchain_vs_langgraph.md
    Include sections for: Overview, Key Differences, Use Cases, and Recommendation.
    """
    
    console.print("[bold blue]🔬 Research Task[/bold blue]")
    console.print(task)
    console.print()
    
    # Track progress
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        research_task = progress.add_task("[cyan]Researching...", total=None)
        
        total_cost = 0.0
        
        async for update in agent.run(task):
            # Update progress
            if update.update_type == "planning":
                progress.update(research_task, description=f"[yellow]📋 {update.message}")
            elif update.update_type == "executing":
                progress.update(research_task, description=f"[cyan]⚙️  {update.message}")
                if update.tool_call:
                    console.print(f"  Using: {update.tool_call.tool_name}")
            elif update.update_type == "observing":
                progress.update(research_task, description=f"[magenta]👁️  Observing results")
            elif update.update_type == "reflecting":
                progress.update(research_task, description=f"[blue]🤔 Reflecting...")
            elif update.update_type == "completed":
                progress.update(research_task, description="[green]✅ Complete!")
                total_cost = update.cost_so_far
            elif update.update_type == "error":
                progress.update(research_task, description=f"[red]❌ Error")
                console.print(f"[red]Error:[/red] {update.message}")
    
    console.print()
    console.print("[bold green]✅ Research complete![/bold green]")
    console.print(f"[dim]Total cost: ${total_cost:.4f}[/dim]")
    console.print(f"[dim]Savings vs GPT-4: ~${total_cost * 50:.2f}[/dim]")
    
    # Show the result
    output_file = Path("./workspace/langchain_vs_langgraph.md")
    if output_file.exists():
        console.print()
        console.print("[bold]📄 Generated Report:[/bold]")
        console.print(output_file.read_text())


if __name__ == "__main__":
    asyncio.run(main())
