"""
DweepBot CLI - Command-line interface for the autonomous agent.

Provides interactive and single-task modes with real-time updates.
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.live import Live
from rich import print as rprint
from pathlib import Path
import os
import asyncio
import sys

app = typer.Typer(
    name="dweepbot",
    help="🦈 DweepBot - Autonomous AI Agent (Clawdbot autonomy at DeepSeek prices)"
)
console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="Task to execute"),
    max_cost: float = typer.Option(5.0, "--max-cost", help="Maximum cost in USD"),
    max_iterations: int = typer.Option(50, "--max-iter", help="Maximum iterations"),
    enable_web_search: bool = typer.Option(False, "--web", help="Enable web search"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Execute a task with the autonomous agent."""
    
    # Check for API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        console.print("[red]❌ DEEPSEEK_API_KEY not set![/red]")
        console.print("\nSet your API key:")
        console.print("  export DEEPSEEK_API_KEY='your-key-here'")
        console.print("\nOr run: dweepbot setup")
        raise typer.Exit(1)
    
    # Run async task
    try:
        asyncio.run(_run_agent_task(
            task=task,
            api_key=api_key,
            max_cost=max_cost,
            max_iterations=max_iterations,
            enable_web_search=enable_web_search,
            verbose=verbose
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Task interrupted by user[/yellow]")
        raise typer.Exit(0)


async def _run_agent_task(
    task: str,
    api_key: str,
    max_cost: float,
    max_iterations: int,
    enable_web_search: bool,
    verbose: bool
):
    """Internal async task runner."""
    from dweepbot import (
        AgentConfig,
        AutonomousAgent,
        DeepSeekClient,
        create_registry_with_default_tools,
        ToolExecutionContext
    )
    
    # Create configuration
    config = AgentConfig(
        deepseek_api_key=api_key,
        max_cost_usd=max_cost,
        max_iterations=max_iterations,
        enable_web_search=enable_web_search,
        enable_code_execution=True
    )
    
    # Initialize components
    console.print("\n[cyan]🦈 Initializing DweepBot...[/cyan]")
    
    async with DeepSeekClient(
        api_key=config.deepseek_api_key,
        model=config.deepseek_model
    ) as llm_client:
        
        # Create tool registry
        context = ToolExecutionContext(
            workspace_path=str(config.workspace_path),
            max_file_size_mb=config.max_file_size_mb,
            network_timeout=config.network_timeout,
            current_task=task
        )
        
        tools = create_registry_with_default_tools(context)
        
        # Create agent
        agent = AutonomousAgent(config, llm_client, tools)
        
        # Display task
        console.print(Panel.fit(
            f"[bold white]{task}[/bold white]",
            title="[bold cyan]Task[/bold cyan]",
            border_style="cyan"
        ))
        
        console.print()
        
        # Track state
        current_phase = None
        steps_completed = 0
        
        # Run agent and display updates
        try:
            async for update in agent.run(task):
                
                # Phase changes
                if update.type == "phase_change":
                    current_phase = update.phase.value if update.phase else "unknown"
                    console.print(f"\n[bold yellow]▶ {update.message}[/bold yellow]")
                
                # Planning complete
                elif update.type == "planning_complete":
                    subgoals = update.data.get("subgoals", [])
                    console.print(f"\n[green]✓[/green] Created plan with [bold]{len(subgoals)}[/bold] steps:")
                    for i, sg in enumerate(subgoals, 1):
                        console.print(f"  {i}. {sg}")
                
                # Subgoal start
                elif update.type == "subgoal_start":
                    steps_completed += 1
                    console.print(f"\n[cyan]→[/cyan] [bold]{update.message}[/bold]")
                
                # Tool execution
                elif update.type == "tool_execution":
                    tool = update.data.get("tool", "")
                    if verbose:
                        params = update.data.get("params", {})
                        console.print(f"  [dim]Using {tool} with {params}[/dim]")
                    else:
                        console.print(f"  [dim]Using {tool}...[/dim]")
                
                # Tool result
                elif update.type == "tool_result":
                    tool = update.data.get("tool", "")
                    success = update.data.get("success", False)
                    
                    if success:
                        console.print(f"  [green]✓[/green] {tool} completed")
                        if verbose and update.data.get("output"):
                            output = str(update.data["output"])[:200]
                            console.print(f"    [dim]{output}[/dim]")
                    else:
                        error = update.data.get("error", "Unknown error")
                        console.print(f"  [red]✗[/red] {tool} failed: {error}")
                
                # Cost updates
                elif update.type == "cost_update":
                    if verbose:
                        cost = update.data.get("total_cost", 0)
                        tokens = update.data.get("tokens_used", 0)
                        console.print(f"  [dim]💰 Cost: ${cost:.4f} | Tokens: {tokens:,}[/dim]")
                
                # Observation
                elif update.type == "observation":
                    if verbose:
                        obs = update.data.get("observation", "")
                        console.print(f"  [dim]👁️  {obs}[/dim]")
                
                # Plan adjustment
                elif update.type == "plan_adjustment":
                    new_steps = update.data.get("new_steps", [])
                    console.print(f"\n[yellow]⚡ Plan adjusted:[/yellow]")
                    for step in new_steps:
                        console.print(f"  + {step}")
                
                # Completion
                elif update.type == "completion":
                    console.print(f"\n[bold green]{'='*60}[/bold green]")
                    console.print("[bold green]✓ Task completed successfully![/bold green]")
                    console.print(f"[bold green]{'='*60}[/bold green]\n")
                    
                    # Display summary
                    data = update.data
                    
                    table = Table(show_header=False, box=None)
                    table.add_column("Metric", style="cyan")
                    table.add_column("Value", style="white")
                    
                    table.add_row("Steps completed", str(data.get("steps_completed", 0)))
                    table.add_row("Total cost", f"${data.get('total_cost', 0):.4f}")
                    table.add_row("Total time", f"{data.get('total_time', 0):.1f}s")
                    
                    console.print(table)
                    
                    # Display final output
                    if data.get("final_output"):
                        console.print(f"\n[bold white]Result:[/bold white]")
                        console.print(Panel(
                            data["final_output"],
                            border_style="green"
                        ))
                
                # Error
                elif update.type == "error":
                    error_msg = update.data.get("error", update.message)
                    console.print(f"\n[bold red]❌ Error: {error_msg}[/bold red]")
                    
                    if update.data.get("cost"):
                        console.print(f"[dim]Cost incurred: ${update.data['cost']:.4f}[/dim]")
        
        except Exception as e:
            console.print(f"\n[bold red]❌ Unexpected error: {str(e)}[/bold red]")
            raise typer.Exit(1)


@app.command()
def setup():
    """Setup wizard for configuring DweepBot."""
    
    console.print("[cyan]🔧 DweepBot Setup Wizard[/cyan]\n")
    
    # Check if .env already exists
    env_file = Path(".env")
    if env_file.exists():
        console.print("[yellow]⚠️  .env file already exists[/yellow]")
        overwrite = typer.confirm("Overwrite?")
        if not overwrite:
            console.print("[dim]Setup cancelled[/dim]")
            raise typer.Exit(0)
    
    # Get API key
    console.print("[bold]DeepSeek API Key[/bold]")
    console.print("Get your key from: https://platform.deepseek.com/api_keys\n")
    
    api_key = typer.prompt("Enter your DeepSeek API key", hide_input=True)
    
    if not api_key:
        console.print("[red]❌ API key is required[/red]")
        raise typer.Exit(1)
    
    # Get optional configuration
    console.print("\n[bold]Optional Configuration[/bold]")
    console.print("[dim]Press Enter to use defaults[/dim]\n")
    
    max_cost = typer.prompt("Max cost per task (USD)", default="5.00")
    max_iterations = typer.prompt("Max iterations per task", default="50")
    enable_web = typer.confirm("Enable web search?", default=False)
    
    # Create .env file
    env_content = f"""# DweepBot Configuration
DWEEPBOT_DEEPSEEK_API_KEY={api_key}
DWEEPBOT_MAX_COST_USD={max_cost}
DWEEPBOT_MAX_ITERATIONS={max_iterations}
DWEEPBOT_ENABLE_WEB_SEARCH={str(enable_web).lower()}
DWEEPBOT_ENABLE_CODE_EXECUTION=true
"""
    
    env_file.write_text(env_content)
    
    console.print(f"\n[green]✓ Configuration saved to .env[/green]")
    console.print("\nYou can now run:")
    console.print("[cyan]  dweepbot run \"Your task here\"[/cyan]")


@app.command()
def version():
    """Show DweepBot version information."""
    from dweepbot import __version__
    
    console.print(f"\n[cyan]🦈 DweepBot v{__version__}[/cyan]")
    console.print("[dim]Production-grade autonomous AI agent framework[/dim]")
    console.print("[dim]Clawdbot autonomy at DeepSeek prices[/dim]\n")


@app.command()
def info():
    """Show system information and available tools."""
    
    console.print("\n[cyan]🦈 DweepBot System Information[/cyan]\n")
    
    # Check API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if api_key:
        console.print("[green]✓[/green] API key configured")
    else:
        console.print("[red]✗[/red] API key not set")
        console.print("  Run: dweepbot setup")
    
    # Check workspace
    workspace = Path("./workspace")
    if workspace.exists():
        console.print(f"[green]✓[/green] Workspace: {workspace.absolute()}")
    else:
        console.print(f"[yellow]![/yellow] Workspace will be created: {workspace.absolute()}")
    
    # Show available tools
    console.print("\n[bold]Available Tools:[/bold]")
    
    tools_info = [
        ("read_file", "Read file contents", "Always"),
        ("write_file", "Write to files", "Always"),
        ("list_directory", "List directory contents", "Always"),
        ("python_execute", "Execute Python code", "Always"),
        ("http_get", "HTTP GET requests", "Always"),
        ("http_post", "HTTP POST requests", "Always"),
        ("web_search", "Web search (DuckDuckGo)", "With [web] extra"),
    ]
    
    table = Table(show_header=True)
    table.add_column("Tool", style="cyan")
    table.add_column("Description", style="white")
    table.add_column("Availability", style="dim")
    
    for name, desc, avail in tools_info:
        table.add_row(name, desc, avail)
    
    console.print(table)
    
    console.print("\n[dim]To enable all tools: pip install 'dweepbot[all]'[/dim]\n")


if __name__ == "__main__":
    app()
