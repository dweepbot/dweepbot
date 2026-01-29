import typer
from rich.console import Console
from rich.markdown import Markdown
from pathlib import Path
import os

app = typer.Typer()
console = Console()

@app.command()
def run(
    task: str = typer.Argument(None, help="Task to execute"),
    interactive: bool = typer.Option(False, "-i", "--interactive"),
):
    """Run DweepBot AI agent"""
    from dweepbot.deepseek import DeepSeekAgent
    
    # Check for API key
    api_key = os.getenv("DEEPSEEK_API_KEY")
    if not api_key:
        console.print("[red]❌ DEEPSEEK_API_KEY not set![/red]")
        console.print("Run: export DEEPSEEK_API_KEY='your-key'")
        console.print("Or: dweepbot setup")
        return
    
    agent = DeepSeekAgent(api_key)
    
    if interactive or not task:
        # Interactive mode
        console.print("[cyan]🦞 DweepBot Interactive Mode[/cyan]")
        console.print("Type your message or /quit to exit\n")
        
        while True:
            try:
                user_input = input("You: ").strip()
                
                if not user_input:
                    continue
                    
                if user_input.lower() in ['/quit', '/exit']:
                    console.print("[yellow]👋 Goodbye![/yellow]")
                    break
                
                if user_input == '/reset':
                    agent.reset()
                    console.print("[green]🔄 Chat reset[/green]")
                    continue
                
                console.print("\n[bold cyan]DweepBot:[/bold cyan] ", end="")
                
                for chunk in agent.chat(user_input):
                    console.print(chunk, end="", markup=False)
                
                console.print("\n")
                
            except KeyboardInterrupt:
                console.print("\n[yellow]👋 Goodbye![/yellow]")
                break
    else:
        # Single task mode
        console.print(f"[cyan]🦞 Executing:[/cyan] {task}\n")
        console.print("[bold cyan]DweepBot:[/bold cyan] ", end="")
        
        for chunk in agent.chat(task):
            console.print(chunk, end="", markup=False)
        
        console.print("\n")

@app.command()
def setup():
    """Setup wizard"""
    console.print("[cyan]🔧 DweepBot Setup[/cyan]\n")
    
    api_key = input("Enter your DeepSeek API key: ").strip()
    
    if api_key:
        # Save to .env file
        env_file = Path.home() / ".dweepbot_env"
        env_file.write_text(f"DEEPSEEK_API_KEY={api_key}\n")
        
        console.print(f"\n[green]✅ API key saved to {env_file}[/green]")
        console.print("\nAdd to your shell profile:")
        console.print(f"[yellow]source {env_file}[/yellow]")
        console.print("\nOr run:")
        console.print(f"[yellow]export DEEPSEEK_API_KEY='{api_key}'[/yellow]")
    else:
        console.print("[red]❌ No API key provided[/red]")

@app.command()
def chat():
    """Start interactive chat"""
    run(interactive=True)

if __name__ == '__main__':
    app()
