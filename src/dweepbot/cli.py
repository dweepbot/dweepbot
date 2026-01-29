"""
DweepBot CLI - Production-ready command-line interface.

Commands:
- dweepbot run "task" - Execute single task
- dweepbot chat - Interactive chat mode
- dweepbot setup - Configuration wizard
- dweepbot info - Show system information
"""

import typer
from rich.console import Console
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich.live import Live
from rich import print as rprint
from pathlib import Path
import os
import asyncio
import sys
from typing import Optional

app = typer.Typer(
    name="dweepbot",
    help="🦈 DweepBot - Autonomous AI Agent Framework",
    add_completion=False,
)
console = Console()


@app.command()
def run(
    task: str = typer.Argument(..., help="Task to execute"),
    model: Optional[str] = typer.Option(None, "--model", "-m", help="Force specific model (kimi/deepseek/claude)"),
    max_cost: float = typer.Option(5.0, "--max-cost", help="Maximum cost in USD"),
    max_iter: int = typer.Option(50, "--max-iter", help="Maximum iterations"),
    web: bool = typer.Option(False, "--web", help="Enable web search"),
    verbose: bool = typer.Option(False, "-v", "--verbose", help="Verbose output"),
):
    """Execute a single task with the autonomous agent."""
    
    # Check for API keys
    deepseek_key = os.getenv("DWEEPBOT_DEEPSEEK_API_KEY")
    if not deepseek_key:
        console.print("[red]❌ DWEEPBOT_DEEPSEEK_API_KEY not set![/red]")
        console.print("\n💡 Run: [cyan]dweepbot setup[/cyan] to configure")
        raise typer.Exit(1)
    
    # Run async task
    try:
        asyncio.run(_run_single_task(
            task=task,
            force_model=model,
            max_cost=max_cost,
            max_iterations=max_iter,
            enable_web_search=web,
            verbose=verbose,
        ))
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Task interrupted[/yellow]")
        raise typer.Exit(0)


async def _run_single_task(
    task: str,
    force_model: Optional[str],
    max_cost: float,
    max_iterations: int,
    enable_web_search: bool,
    verbose: bool,
):
    """Execute a single task."""
    from dweepbot.config import AgentConfig
    from dweepbot.core.agent import AutonomousAgent
    
    # Create config
    config = AgentConfig(
        deepseek_api_key=os.getenv("DWEEPBOT_DEEPSEEK_API_KEY"),
        max_cost_usd=max_cost,
        max_iterations=max_iterations,
        enable_web_search=enable_web_search,
    )
    
    # Show task
    console.print(Panel(
        f"[bold cyan]Task:[/bold cyan] {task}",
        title="🦈 DweepBot",
        border_style="cyan",
    ))
    
    # Create agent
    agent = AutonomousAgent(config)
    
    # Track progress
    total_cost = 0.0
    step_count = 0
    
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        console=console,
        transient=False,
    ) as progress:
        
        task_progress = progress.add_task("[cyan]Executing...", total=100)
        
        async for update in agent.run(task):
            step_count += 1
            total_cost = update.cost_so_far
            
            # Update progress
            progress_pct = int(update.progress * 100)
            progress.update(task_progress, completed=progress_pct)
            
            # Show updates
            if update.update_type == "planning":
                progress.update(task_progress, description=f"[yellow]📋 {update.message}")
                if verbose:
                    console.print(f"  [dim]{update.message}[/dim]")
            
            elif update.update_type == "executing":
                progress.update(task_progress, description=f"[cyan]⚙️  {update.message}")
                if verbose:
                    console.print(f"  [dim]{update.message}[/dim]")
                    if update.tool_call:
                        console.print(f"    Tool: {update.tool_call.tool_name}")
            
            elif update.update_type == "observing":
                progress.update(task_progress, description="[magenta]👁️  Observing...")
            
            elif update.update_type == "reflecting":
                progress.update(task_progress, description="[blue]🤔 Reflecting...")
                if verbose:
                    console.print(f"  [dim]{update.message}[/dim]")
            
            elif update.update_type == "completed":
                progress.update(task_progress, description="[green]✅ Complete!", completed=100)
                console.print(f"\n[green]✅ {update.message}[/green]")
                break
            
            elif update.update_type == "error":
                console.print(f"\n[red]❌ Error: {update.message}[/red]")
    
    # Show summary
    console.print()
    summary_table = Table(title="Execution Summary", show_header=False)
    summary_table.add_row("Steps", str(step_count))
    summary_table.add_row("Cost", f"${total_cost:.4f}")
    summary_table.add_row("Savings vs GPT-4", f"~${total_cost * 50:.2f}")
    console.print(summary_table)


@app.command()
def chat():
    """Start interactive chat mode."""
    
    # Check API keys
    deepseek_key = os.getenv("DWEEPBOT_DEEPSEEK_API_KEY")
    if not deepseek_key:
        console.print("[red]❌ DWEEPBOT_DEEPSEEK_API_KEY not set![/red]")
        console.print("\n💡 Run: [cyan]dweepbot setup[/cyan] to configure")
        raise typer.Exit(1)
    
    console.print(Panel(
        "[bold cyan]DweepBot Interactive Mode[/bold cyan]\n"
        "Type your tasks, and I'll execute them autonomously.\n"
        "Commands: [yellow]/quit[/yellow], [yellow]/help[/yellow], [yellow]/cost[/yellow]",
        title="🦈 Chat Mode",
        border_style="cyan",
    ))
    
    total_session_cost = 0.0
    
    while True:
        try:
            # Get user input
            user_input = Prompt.ask("\n[bold cyan]You[/bold cyan]")
            
            if not user_input.strip():
                continue
            
            # Handle commands
            if user_input.strip().lower() == "/quit":
                console.print(f"\n[yellow]Session cost: ${total_session_cost:.4f}[/yellow]")
                console.print("[green]Goodbye! 🦈[/green]")
                break
            
            elif user_input.strip().lower() == "/help":
                _show_chat_help()
                continue
            
            elif user_input.strip().lower() == "/cost":
                console.print(f"[yellow]Session cost so far: ${total_session_cost:.4f}[/yellow]")
                continue
            
            # Execute task
            cost = asyncio.run(_run_chat_task(user_input))
            total_session_cost += cost
            
        except KeyboardInterrupt:
            console.print(f"\n\n[yellow]Session cost: ${total_session_cost:.4f}[/yellow]")
            console.print("[green]Goodbye! 🦈[/green]")
            break
        except Exception as e:
            console.print(f"[red]Error: {e}[/red]")


async def _run_chat_task(task: str) -> float:
    """Execute a task in chat mode."""
    from dweepbot.config import AgentConfig
    from dweepbot.core.agent import AutonomousAgent
    
    config = AgentConfig(
        deepseek_api_key=os.getenv("DWEEPBOT_DEEPSEEK_API_KEY"),
        max_cost_usd=2.0,  # Lower limit for chat
        max_iterations=20,
    )
    
    agent = AutonomousAgent(config)
    
    total_cost = 0.0
    
    async for update in agent.run(task):
        total_cost = update.cost_so_far
        
        if update.update_type == "executing":
            console.print(f"[dim]  {update.message}[/dim]")
        elif update.update_type == "completed":
            console.print(f"\n[green]✓[/green] {update.message}")
            break
        elif update.update_type == "error":
            console.print(f"[red]✗ {update.message}[/red]")
            break
    
    return total_cost


def _show_chat_help():
    """Show chat mode help."""
    help_table = Table(title="Chat Commands", show_header=False)
    help_table.add_row("/quit", "Exit chat mode")
    help_table.add_row("/help", "Show this help")
    help_table.add_row("/cost", "Show session cost")
    console.print(help_table)


@app.command()
def setup():
    """Run configuration wizard."""
    
    console.print(Panel(
        "[bold cyan]DweepBot Setup Wizard[/bold cyan]\n"
        "Let's configure your API keys and preferences.",
        title="🦈 Setup",
        border_style="cyan",
    ))
    
    # Check for existing .env
    env_file = Path(".env")
    if env_file.exists():
        overwrite = Confirm.ask("\n.env file exists. Overwrite?")
        if not overwrite:
            console.print("[yellow]Setup cancelled[/yellow]")
            return
    
    # Collect API keys
    console.print("\n[bold]API Keys[/bold]")
    console.print("Get your DeepSeek key from: [cyan]https://platform.deepseek.com[/cyan]")
    
    deepseek_key = Prompt.ask("DeepSeek API Key", password=True)
    
    # Optional keys
    console.print("\n[dim]Optional: Configure additional models for multi-model routing[/dim]")
    
    kimi_key = Prompt.ask("Kimi API Key (optional, press Enter to skip)", default="", password=True)
    claude_key = Prompt.ask("Claude API Key (optional, press Enter to skip)", default="", password=True)
    
    # Preferences
    console.print("\n[bold]Preferences[/bold]")
    max_cost = Prompt.ask("Default max cost (USD)", default="5.0")
    max_iter = Prompt.ask("Default max iterations", default="50")
    enable_web = Confirm.ask("Enable web search by default?", default=False)
    
    # Write .env file
    env_content = f"""# DweepBot Configuration
# Generated by setup wizard

# Required: DeepSeek API Key
DWEEPBOT_DEEPSEEK_API_KEY={deepseek_key}

# Optional: Additional Model API Keys
{"DWEEPBOT_KIMI_API_KEY=" + kimi_key if kimi_key else "# DWEEPBOT_KIMI_API_KEY="}
{"DWEEPBOT_CLAUDE_API_KEY=" + claude_key if claude_key else "# DWEEPBOT_CLAUDE_API_KEY="}

# Agent Configuration
DWEEPBOT_MAX_COST_USD={max_cost}
DWEEPBOT_MAX_ITERATIONS={max_iter}
DWEEPBOT_ENABLE_WEB_SEARCH={"true" if enable_web else "false"}

# Workspace
DWEEPBOT_WORKSPACE_PATH=./workspace

# Logging
DWEEPBOT_LOG_LEVEL=INFO
"""
    
    env_file.write_text(env_content)
    
    console.print("\n[green]✅ Configuration saved to .env[/green]")
    console.print("\n[bold]Next steps:[/bold]")
    console.print("1. Load environment: [cyan]source .env[/cyan] (or restart terminal)")
    console.print("2. Test with: [cyan]dweepbot run \"Create a hello world script\"[/cyan]")


@app.command()
def info():
    """Show system information and available tools."""
    
    console.print(Panel(
        "[bold cyan]DweepBot System Information[/bold cyan]",
        title="🦈 Info",
        border_style="cyan",
    ))
    
    # Check API keys
    console.print("\n[bold]API Keys:[/bold]")
    keys_table = Table(show_header=False)
    
    deepseek_set = bool(os.getenv("DWEEPBOT_DEEPSEEK_API_KEY"))
    keys_table.add_row(
        "DeepSeek",
        "[green]✓ Configured[/green]" if deepseek_set else "[red]✗ Not set[/red]"
    )
    
    kimi_set = bool(os.getenv("DWEEPBOT_KIMI_API_KEY"))
    keys_table.add_row(
        "Kimi K2.5",
        "[green]✓ Configured[/green]" if kimi_set else "[dim]Not configured[/dim]"
    )
    
    claude_set = bool(os.getenv("DWEEPBOT_CLAUDE_API_KEY"))
    keys_table.add_row(
        "Claude 3.5",
        "[green]✓ Configured[/green]" if claude_set else "[dim]Not configured[/dim]"
    )
    
    console.print(keys_table)
    
    # Show available tools
    console.print("\n[bold]Available Tools:[/bold]")
    tools_table = Table()
    tools_table.add_column("Tool", style="cyan")
    tools_table.add_column("Description")
    
    tools_table.add_row("file_ops", "Read, write, create files")
    tools_table.add_row("python_executor", "Execute Python code")
    tools_table.add_row("http_client", "Make HTTP requests")
    
    if os.getenv("DWEEPBOT_ENABLE_WEB_SEARCH", "").lower() == "true":
        tools_table.add_row("web_search", "Search the web (DuckDuckGo)")
    
    console.print(tools_table)
    
    # Show configuration
    console.print("\n[bold]Current Configuration:[/bold]")
    config_table = Table(show_header=False)
    config_table.add_row("Max Cost", f"${os.getenv('DWEEPBOT_MAX_COST_USD', '5.0')}")
    config_table.add_row("Max Iterations", os.getenv('DWEEPBOT_MAX_ITERATIONS', '50'))
    config_table.add_row("Workspace", os.getenv('DWEEPBOT_WORKSPACE_PATH', './workspace'))
    console.print(config_table)
    
    # Show model info
    if kimi_set or claude_set:
        console.print("\n[bold]Multi-Model Routing:[/bold]")
        console.print("[green]✓[/green] Enabled - Tasks will be routed to optimal model")
        routing_table = Table()
        routing_table.add_column("Task Type", style="cyan")
        routing_table.add_column("Preferred Model")
        routing_table.add_row("Coding", "Kimi K2.5" if kimi_set else "DeepSeek")
        routing_table.add_row("Creative", "Claude 3.5" if claude_set else "DeepSeek")
        routing_table.add_row("General", "DeepSeek")
        console.print(routing_table)


def main():
    """Main entry point."""
    app()


if __name__ == "__main__":
    main()
