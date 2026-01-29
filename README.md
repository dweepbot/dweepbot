<p align="center">
  <img src="path/to/your/animated-shark-logo.gif" alt="DweepBot Pro Logo" width="200">
</p>

<h1 align="center">🦈 DweepBot Pro – Autonomous AI Agent Framework</h1>

<p align="center">
  <a href="https://github.com/dweepbot/dweepbot/stargazers"><img src="https://img.shields.io/github/stars/dweepbot/dweepbot?style=social" alt="GitHub Stars"></a>
  <a href="https://github.com/dweepbot/dweepbot/network/members"><img src="https://img.shields.io/github/forks/dweepbot/dweepbot?style=social" alt="GitHub Forks"></a>
  <a href="https://github.com/dweepbot/dweepbot/actions"><img src="https://img.shields.io/github/actions/workflow/status/dweepbot/dweepbot/tests.yml?branch=main" alt="Build Status"></a>
  <a href="https://github.com/dweepbot/dweepbot/blob/main/LICENSE"><img src="https://img.shields.io/github/license/dweepbot/dweepbot" alt="MIT License"></a>
  <a href="https://pypi.org/project/dweepbot/"><img src="https://img.shields.io/pypi/v/dweepbot" alt="PyPI Version"></a>
</p>

<p align="center">
  DweepBot Pro is a production-grade, open-source AI agent framework that gives you Claude/GPT‑4–level autonomy at DeepSeek prices. Batteries included. Extensible. Fun to hack on.
</p>

<p align="center">
  👉 Like this project? <a href="https://github.com/dweepbot/dweepbot">Star the repo</a> to support development!
</p>

## 🎥 Demo

![DweepBot Pro Demo](path/to/your/demo.gif)  
*(Pro tip: Record a quick screen capture of DweepBot handling a task like "Analyze this CSV and generate a report" – use tools like Kap on macOS for GIFs.)*

🦈 DweepBot Pro working through a multi-step task: PLAN → ACT → OBSERVE → REFLECT. Writing code, running tools, fixing errors, and shipping.

## 💡 What Is DweepBot Pro?

DweepBot Pro is an autonomous AI agent framework built for real workloads, not toy demos.  
It combines:

- 🧭 A PLAN → ACT → OBSERVE → REFLECT loop for autonomous planning
- 💰 DeepSeek‑V3 for 50–60× lower LLM costs than GPT‑4/Claude agents
- 🧩 Batteries-included tools (web search, secure code exec, file ops, notifications)
- 🧠 Multi-level memory + RAG so it doesn’t forget what it just did
- 🎨 A simple, hackable architecture that fits in your head

Target users: agencies, indie hackers, and dev teams that want serious agents without serious cloud bills.

## ⚡ Quick Start

### 1. Requirements
- Python 3.10+
- macOS 10.15+, Linux, or WSL (Windows via WSL recommended)
- DeepSeek API key (free tier available)
- Optional deps: For full features, install `rich` (TUI), `duckduckgo-search` (web), `PyPDF2` & `python-docx` (docs), `chromadb` (RAG)

### 2. Install
```bash
# Clone the repo
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot

# Install with all features (RAG, web, docs)
pip install -e ".[all]"

# Or minimal core
pip install -e .

export DEEPSEEK_API_KEY="your_api_key_here"

# Interactive TUI
dweepbot

# Or run a single autonomous task
dweepbot --task "Create a Python script to analyze CSV files"


import asyncio
from pathlib import Path

from dweepbot.core.agent import AutonomousAgent
from dweepbot.core.types import Context
from dweepbot.llm.client import DeepSeekClient
from dweepbot.tools.base import ToolRegistry
from dweepbot.memory.manager import MemoryManager

async def main():
    workspace = Path("./my_workspace")
    api_key = "your_api_key"
    llm = DeepSeekClient(api_key)
    tools = ToolRegistry()
    memory = MemoryManager(workspace)

    # Register core tools
    from dweepbot.tools.core import ReadFileTool, WriteFileTool
    tools.register(ReadFileTool(workspace))
    tools.register(WriteFileTool(workspace))

    context = Context(
        task_id="example",
        workspace_path=str(workspace),
    )

    agent = AutonomousAgent(llm, tools, memory, context)
    async for update in agent.run("Create a README.md file"):
        if update["type"] == "text":
            print(update["content"], end="")
        elif update["type"] == "complete":
            print(f"\n\nDone! Cost: ${update['content']['total_cost']:.4f}")

asyncio.run(main())
🧠 Key Features

🧭 Autonomous Planning
PLAN → ACT → OBSERVE → REFLECT loop for multi-step tasks, with dynamic subgoal creation and recovery when tools fail.
💰 DeepSeek‑V3 Powered (50–60× Cheaper)
Designed around DeepSeek‑V3 to deliver Claude/GPT‑4–class reasoning at a tiny fraction of the cost, with prompt caching and smart model selection.
🧩 Batteries-Included Tools
Comes with web search, secure sandboxed code execution, file operations, notifications, and more — plus a clean plugin system.
🧠 Multi-Level Memory + RAG
Working memory for the current task, session memory for recent history, and long-term memory with RAG over your code and docs.
🛠️ Plugin-Friendly Architecture
Drop in new tools as plugins with Pydantic validation, sandboxing, and optional rollback for stateful operations.
🎨 Developer-First DX
Rich TUI, streaming updates, structured logs, type hints everywhere, and a clean Python API.

🔬 How It Compares
🦈 vs Other Agent Frameworks





































































FeatureAutoGPTLangChainOpen InterpreterClawdbot (Claude)🦈 DweepBot ProAutonomy loopBasic, brittleDIY graphsMostly REPL/code execProprietaryPLAN–ACT–OBSERVE–REFLECTMemoryAd hoc / vectorPluggableSession-onlyContext window onlyMulti-level + RAGCost (LLM)GPT‑4/GPT‑4.1GPT‑4/Claude/etc.GPT-4/Claude/etc.Claude stackDeepSeek‑V3 (50–60× cheaper)Built-in toolsLimitedBYO toolsCode + FSProprietary toolsetWeb, code exec, FS, notifyExtensibilityMediumHigh, complexLow–mediumLimited, closedHigh, simple plugin systemHostingSelf-host onlySelf-host / SaaSLocalSaaS onlySelf-host, OSS, future SaaSComplexityHighHighLow–mediumHidden internalsOpinionated, understandable
TL;DR: Simpler than LangChain, more powerful than Open Interpreter, more reliable than AutoGPT, cheaper and more open than Clawdbot-style agents.
🚀 Roadmap

 Add browser automation tool (e.g., Playwright integration)
 Multi-agent support for complex workflows
 Web UI dashboard for monitoring runs
 More plugins: GitHub integration, email handling
 Core autonomy loop stable

Suggestions? Open an issue!
🧩 Plugin System (Custom Tools)
Create custom tools in a few lines:
from dweepbot.tools.base import ToolPlugin, ToolMetadata, ToolResult, ToolResultStatus

class MyCustomTool(ToolPlugin):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="What this tool does",
            parameters={
                "type": "object",
                "properties": {
                    "arg1": {
                        "type": "string",
                        "description": "First argument",
                    }
                },
                "required": ["arg1"],
            },
            category="custom",
        )

    async def execute(self, arg1: str, **kwargs) -> ToolResult:
        try:
            result = do_something(arg1)
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=result,
            )
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.FAILURE,
                error=str(e),
            )

# Register your tool
tools.register(MyCustomTool())
🤝 Contributing
We love contributions – from bug fixes to big features.

Fork the repo
Create a feature branch: git checkout -b feature/my-awesome-thing
Install dev deps: pip install -e ".[dev]"
Run tests: pytest (and ideally pytest --cov=src/dweepbot)
Format: black . and ruff check .
Open a PR with a clear description and screenshots/logs where helpful

Check out CONTRIBUTING.md for more details and ideas on where to start.
💡 Good first issues: Labeled for beginners – add a new tool plugin (e.g., a simple SaaS integration) or improve the docs.
📜 License
DweepBot Pro is released under the MIT License.
You’re free to use it in commercial projects, build SaaS products, and extend it as you like — just keep the copyright and license notice.
See LICENSE for the full text.
