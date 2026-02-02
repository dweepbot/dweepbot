# 🦈 DweepBot - Autonomous AI Agent Framework

**Production-grade autonomous AI agents at DeepSeek prices**

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 What is DweepBot?

DweepBot is an **open-source autonomous agent framework** built for real production workloads. It delivers full PLAN → ACT → OBSERVE → REFLECT autonomy at **50-60× lower cost** by using DeepSeek-V3.

### ✨ Features

✨ **Full Autonomy**: Real PLAN → ACT → OBSERVE → REFLECT loop, not a chatbot wrapper  
💰 **Cost-Effective**: $0.27/1M input tokens vs GPT-4's $15/1M (55× cheaper)  
🛠️ **Comprehensive Tools**: File I/O, HTTP client, Python execution  
🧠 **Advanced Memory**: Working memory with vector store support (ChromaDB)  
🔒 **Production-Ready**: Error boundaries, cost tracking, state persistence  
🎨 **Developer-Friendly**: Clean APIs, full type hints, async/await  
🚀 **Multi-Agent Support**: Coordinate multiple agents on complex tasks  
⏰ **Task Scheduler**: Cron-style automation and recurring tasks  
📊 **Web Dashboard**: Real-time monitoring and control center

---

## 📦 Installation

### Quick Start

```bash
pip install dweepbot
```

### With All Features

```bash
# Web search + RAG + document processing + advanced features
pip install "dweepbot[all]"

# Or install specific feature sets
pip install "dweepbot[web]"     # Web search
pip install "dweepbot[rag]"     # Vector store
pip install "dweepbot[docs]"    # PDF/Word support
pip install "dweepbot[pro]"     # Multi-agent, scheduler, dashboard
```

### From Source

```bash
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot
pip install -e ".[all]"
```

### Optional: Start the Dashboard

```bash
# Install Pro dependencies (for dashboard and advanced features)
pip install "dweepbot[pro]"

# Start the dashboard
cd dashboard && npm install && npm run dev
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete setup instructions.

---

## 🚀 Quick Start

### 1. Get Your API Key

Get a free DeepSeek API key from [platform.deepseek.com](https://platform.deepseek.com/api_keys)

### 2. Configure

```bash
# Run the setup wizard
dweepbot setup

# Or manually set environment variable
export DEEPSEEK_API_KEY='your-api-key-here'
```

### 3. Run Your First Task

```bash
# CLI mode
dweepbot run "Create a Python script that calculates the first 20 prime numbers and save it to primes.py"

# Interactive mode
dweepbot chat
```

---

## 💻 Usage

### Command Line Interface

```bash
# Execute a task
dweepbot run "Your task here"

# With options
dweepbot run "Research and compare Python vs Rust" \
  --max-cost 2.0 \
  --max-iter 100 \
  --web \
  --verbose

# Show available tools and system info
dweepbot info

# Check version
dweepbot version
```

### Python API

```python
import asyncio
from dweepbot import (
    AgentConfig,
    AutonomousAgent,
    DeepSeekClient,
    create_registry_with_default_tools,
    ToolExecutionContext
)

async def main():
    # Configuration
    config = AgentConfig(
        deepseek_api_key="your-key",
        max_cost_usd=5.0,
        max_iterations=50,
        enable_code_execution=True
    )
    
    # Initialize components
    async with DeepSeekClient(api_key=config.deepseek_api_key) as llm:
        context = ToolExecutionContext(
            workspace_path="./workspace"
        )
        tools = create_registry_with_default_tools(context)
        
        # Create and run agent
        agent = AutonomousAgent(config, llm, tools)
        
        async for update in agent.run("Your task here"):
            print(f"{update.type}: {update.message}")

asyncio.run(main())
```

---

## 🛠️ Available Tools

| Tool | Description | Category |
|------|-------------|----------|
| `read_file` | Read file contents | File I/O |
| `write_file` | Create or modify files | File I/O |
| `list_directory` | List directory contents | File I/O |
| `delete_file` | Delete files (dangerous) | File I/O |
| `python_execute` | Run Python code in sandbox | Code Execution |
| `python_repl` | Interactive Python session | Code Execution |
| `http_get` | Make HTTP GET requests | Web |
| `http_post` | Make HTTP POST requests | Web |
| `web_search` | DuckDuckGo search (requires `[web]`) | Web |

### Creating Custom Tools

```python
from dweepbot.tools.base import BaseTool, ToolMetadata, ToolResult, ToolCategory

class MyCustomTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="Does something useful",
            category=ToolCategory.SYSTEM,
            parameters=[...],
            returns="Result description"
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        # Your implementation here
        return ToolResult(
            success=True,
            output="Done!",
            execution_time_seconds=0.1
        )

# Register with agent
tools.register(MyCustomTool(context))
```

---

## 📊 Cost Comparison

| Model | Input Cost | Output Cost | DweepBot Savings |
|-------|-----------|-------------|------------------|
| **DeepSeek-V3** | $0.27/1M | $1.10/1M | **Baseline** |
| GPT-4 Turbo | $10/1M | $30/1M | **55× cheaper** |
| Claude 3.5 Sonnet | $3/1M | $15/1M | **11× cheaper** |
| Gemini 1.5 Pro | $1.25/1M | $5/1M | **4× cheaper** |

**Real Example**: A complex research task (5 steps, 50K tokens):
- GPT-4: ~$1.50
- Claude: ~$0.75
- **DweepBot**: ~$0.03 💰

---

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│              Autonomous Agent                        │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   PLAN   │→ │   ACT    │→ │  OBSERVE │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│       ↑                              │               │
│       └──────────  REFLECT  ←────────┘               │
└─────────────────────────────────────────────────────┘
           │                    │
    ┌──────▼──────┐      ┌─────▼──────┐
    │  Tool       │      │   Memory    │
    │  Registry   │      │             │
    │             │      │ - Working   │
    │ - File I/O  │      │ - Vector DB │
    │ - Code Exec │      │ - Semantic  │
    │ - HTTP      │      │   Search    │
    │ - Multi-    │      │             │
    │   Agent     │      │             │
    └─────────────┘      └─────────────┘
```

### Multi-Agent Orchestration

```
┌──────────────────────────────────────────────────────────┐
│         Multi-Agent Orchestration                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐               │
│  │ Agent 1  │  │ Agent 2  │  │ Agent 3  │               │
│  └──────────┘  └──────────┘  └──────────┘               │
│       ↓              ↓              ↓                     │
│  ┌────────────────────────────────────────┐              │
│  │       Task Scheduler & Queue           │              │
│  └────────────────────────────────────────┘              │
└──────────────────────────────────────────────────────────┘
           │                    │
    ┌──────▼──────┐      ┌─────▼──────────────┐
    │  Advanced   │      │  Web Dashboard 📊   │
    │  Memory     │      │                     │
    │             │      │ - Real-time UI      │
    │ - Vector DB │      │ - Agent Control     │
    │ - Semantic  │      │ - Analytics         │
    │   Search    │      │ - Multi-agent View  │
    └─────────────┘      └─────────────────────┘
```

---

## 🔧 Configuration

All configuration via environment variables (prefix: `DWEEPBOT_`):

```bash
# Required
DWEEPBOT_DEEPSEEK_API_KEY=your-key

# Agent Limits
DWEEPBOT_MAX_ITERATIONS=50
DWEEPBOT_MAX_COST_USD=5.00
DWEEPBOT_MAX_TIME_SECONDS=3600

# Tool Control
DWEEPBOT_ENABLE_WEB_SEARCH=false
DWEEPBOT_ENABLE_CODE_EXECUTION=true
DWEEPBOT_ENABLE_SHELL_EXECUTION=false

# Code Execution
DWEEPBOT_CODE_EXECUTION_TIMEOUT=30
DWEEPBOT_CODE_EXECUTION_MEMORY_LIMIT_MB=512

# Workspace
DWEEPBOT_WORKSPACE_PATH=./workspace
DWEEPBOT_MAX_FILE_SIZE_MB=10

# Memory
DWEEPBOT_MAX_WORKING_MEMORY=20
DWEEPBOT_ENABLE_VECTOR_STORE=false
```

Or use `.env` file (auto-loaded):

```bash
dweepbot setup  # Creates .env with guided prompts
```

---

## 📈 Example Tasks

### Data Analysis

```bash
dweepbot run "Analyze this CSV file: sales_data.csv. Calculate total revenue, average transaction value, and create a summary report in markdown."
```

### Web Scraping

```bash
dweepbot run "Search for Python async best practices, fetch the top 3 articles, and create a summary document with key takeaways." --web
```

### Code Generation

```bash
dweepbot run "Create a FastAPI REST API with CRUD endpoints for a 'books' resource. Include data validation with Pydantic."
```

### Multi-Step Research

```bash
dweepbot run "Research the top 5 AI agent frameworks, compare their features, and create a comparison table saved as comparison.md" --web --max-cost 1.0
```

---

## 🧪 Testing

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# With coverage
pytest --cov=dweepbot --cov-report=html

# Integration tests (requires API key)
export DEEPSEEK_API_KEY=your-key
pytest tests/integration/
```

---

## 🛣️ Roadmap

**Current - v1.0** ✅
- [x] PLAN→ACT→OBSERVE→REFLECT loop
- [x] Tool system with core tools (File I/O, HTTP, Python exec)
- [x] Cost tracking & limits
- [x] Working memory
- [x] Production error handling
- [x] Multi-agent orchestration
- [x] Vector store (ChromaDB integration)
- [x] Task scheduler with cron support
- [x] Web dashboard & command center
- [x] Advanced memory systems
- [x] MIT License

**Next - v1.1** (Q1 2026)
- [ ] Enhanced documentation
- [ ] More example projects
- [ ] Performance optimizations
- [ ] Additional tools
- [ ] Improved error messages
- [ ] Pinecone & Weaviate vector store support
- [ ] Advanced analytics dashboard
- [ ] Webhook integrations (Slack, Discord, Teams)
- [ ] Database tools (SQL, MongoDB)
- [ ] Browser automation (Playwright integration)

**Future - v2.0** (Q2 2026)
- [ ] Team collaboration features
- [ ] Shared agent workspaces
- [ ] Role-based access control
- [ ] Advanced audit logging
- [ ] Custom compliance reports

---

## 🤝 Contributing

We welcome contributions! See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Setup

```bash
# Clone repo
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot

# Create virtual environment
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows

# Install in dev mode
pip install -e ".[dev,all]"

# Run tests
pytest

# Format code
black src/ tests/
ruff check src/ tests/
```

---

## 📄 License

DweepBot is released under the **MIT License**.

All code in this repository is open source and free to use, modify, and distribute.
See [LICENSE](LICENSE) for full details.

---

## 🙏 Acknowledgments

- DeepSeek for providing cost-effective, high-quality LLMs
- The open-source AI community for inspiration and tools
- All contributors to this project

---

## 📞 Support

- **Documentation**: [GitHub Wiki](https://github.com/dweepbot/dweepbot/wiki)
- **Issues**: [GitHub Issues](https://github.com/dweepbot/dweepbot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dweepbot/dweepbot/discussions)

---

## ⭐ Star History

If you find DweepBot useful, please star the repo! It helps others discover the project.

[![Star History Chart](https://api.star-history.com/svg?repos=dweepbot/dweepbot&type=Date)](https://star-history.com/#dweepbot/dweepbot&Date)

---

**Built with ❤️ by the DweepBot team**

*Making autonomous AI agents accessible to everyone*
