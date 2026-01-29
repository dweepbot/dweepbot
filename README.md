# 🦈 DweepBot Pro

**Production-grade autonomous AI agent framework**  
*Clawdbot autonomy at DeepSeek prices*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)

---

## 🎯 What is DweepBot?

DweepBot is an open-source autonomous agent framework built for **real production workloads**. It delivers the same PLAN → ACT → OBSERVE → REFLECT autonomy as expensive alternatives like Clawdbot, but at **50-60× lower cost** by using DeepSeek-V3.

### Key Features

✨ **Full Autonomy**: Real PLAN → ACT → OBSERVE → REFLECT loop, not a chatbot wrapper  
💰 **Cost-Effective**: $0.27/1M input tokens vs GPT-4's $15/1M (55× cheaper)  
🛠️ **Batteries Included**: 8+ production-ready tools out of the box  
🧠 **Memory System**: Working memory + optional RAG for complex tasks  
🔒 **Production-Ready**: Error boundaries, cost tracking, state persistence  
🎨 **Developer-Friendly**: Clean APIs, full type hints, async/await  

---

## 📦 Installation

### Quick Start (Core Features)

```bash
pip install dweepbot
```

### With All Features

```bash
# Web search + RAG + document processing
pip install "dweepbot[all]"

# Or install specific feature sets
pip install "dweepbot[web]"     # Web search
pip install "dweepbot[rag]"     # Vector store
pip install "dweepbot[docs]"    # PDF/Word support
```

### From Source

```bash
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot
pip install -e ".[all]"
```

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

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────┐
│                  Autonomous Agent                    │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   PLAN   │→ │   ACT    │→ │  OBSERVE │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│       ↑                              │               │
│       └──────────  REFLECT  ←────────┘               │
└─────────────────────────────────────────────────────┘
           │                    │
    ┌──────▼──────┐      ┌─────▼──────┐
    │  Tool       │      │   Memory    │
    │  Registry   │      │   Manager   │
    │             │      │             │
    │ - File I/O  │      │ - Working   │
    │ - Code Exec │      │ - Vector DB │
    │ - Web       │      │ - RAG       │
    └─────────────┘      └─────────────┘
```

### Core Components

1. **Autonomous Agent**: State machine orchestrating the PLAN→ACT→OBSERVE→REFLECT loop
2. **Tool Registry**: Plugin system for extensible capabilities
3. **Memory Manager**: Short-term (working) and long-term (RAG) memory
4. **DeepSeek Client**: Async LLM client with cost tracking
5. **Configuration**: Type-safe settings with validation

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

### Phase 1: Core ✅ (Current)
- [x] PLAN→ACT→OBSERVE→REFLECT loop
- [x] Tool system with 8+ tools
- [x] Cost tracking & limits
- [x] Working memory
- [x] Production error handling

### Phase 2: Enhanced Tools (Next 2 weeks)
- [ ] Web browser automation (Playwright)
- [ ] Document processing (PDF/DOCX)
- [ ] Database tools (SQL, MongoDB)
- [ ] API integration templates
- [ ] Notification system (Discord/Slack)

### Phase 3: Advanced Features (Month 2)
- [ ] Vector store integration (ChromaDB)
- [ ] Multi-agent orchestration
- [ ] Task scheduling & cron
- [ ] Web dashboard for monitoring
- [ ] LangSmith integration

### Phase 4: Enterprise (Month 3+)
- [ ] Team collaboration features
- [ ] Audit logs & compliance
- [ ] Custom model support
- [ ] On-premise deployment
- [ ] SLA & support tiers

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

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- DeepSeek for providing cost-effective, high-quality LLMs
- The open-source AI community for inspiration and tools
- Early testers and contributors

---

## 📞 Support

- **Documentation**: [docs.dweepbot.dev](https://docs.dweepbot.dev) (coming soon)
- **Issues**: [GitHub Issues](https://github.com/dweepbot/dweepbot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dweepbot/dweepbot/discussions)
- **Twitter**: [@dweepbot](https://twitter.com/dweepbot)

---

## ⭐ Star History

If you find DweepBot useful, please star the repo! It helps others discover the project.

[![Star History Chart](https://api.star-history.com/svg?repos=dweepbot/dweepbot&type=Date)](https://star-history.com/#dweepbot/dweepbot&Date)

---

**Built with ❤️ by the DweepBot team**

*Making autonomous AI agents accessible to everyone*
DweepBot Pro - Complete File Structure
dweepbot-pro/
├── .env.example
├── .gitignore
├── LICENSE
├── README.md
├── pyproject.toml
├── setup.py
├── requirements.txt
├── requirements-dev.txt
├── Makefile
├── docker-compose.yml
├── Dockerfile
│
├── .github/
│   └── workflows/
│       ├── tests.yml
│       └── publish.yml
│
├── src/
│   └── dweepbot/
│       ├── __init__.py
│       ├── __version__.py
│       ├── cli.py
│       ├── config.py
│       │
│       ├── core/
│       │   ├── __init__.py
│       │   ├── agent.py           # Main AutonomousAgent class
│       │   ├── planner.py         # TaskPlanner
│       │   ├── executor.py        # ToolExecutor
│       │   ├── reflection.py      # ReflectionEngine
│       │   └── schemas.py         # Pydantic models
│       │
│       ├── tools/
│       │   ├── __init__.py
│       │   ├── base.py            # BaseTool abstract class
│       │   ├── registry.py        # ToolRegistry
│       │   ├── web_search.py      # DuckDuckGo search
│       │   ├── python_executor.py # Sandboxed Python
│       │   ├── file_ops.py        # File operations
│       │   ├── shell_executor.py  # Limited shell
│       │   ├── http_client.py     # HTTP requests
│       │   ├── rag_query.py       # Vector DB query
│       │   └── notification.py    # Webhooks
│       │
│       ├── memory/
│       │   ├── __init__.py
│       │   ├── working_memory.py  # Short-term memory
│       │   ├── vector_store.py    # ChromaDB integration
│       │   └── schemas.py         # Memory models
│       │
│       ├── state/
│       │   ├── __init__.py
│       │   ├── agent_state.py     # State management
│       │   └── serialization.py   # State persistence
│       │
│       └── utils/
│           ├── __init__.py
│           ├── cost_tracker.py    # Token/cost tracking
│           ├── logger.py          # Structured logging
│           ├── validators.py      # Input validation
│           └── deepseek_client.py # DeepSeek API client
│
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   ├── __init__.py
│   │   ├── test_agent.py
│   │   ├── test_planner.py
│   │   ├── test_executor.py
│   │   ├── test_tools.py
│   │   ├── test_memory.py
│   │   └── test_cost_tracker.py
│   │
│   └── integration/
│       ├── __init__.py
│       ├── test_full_workflows.py
│       └── test_tool_integration.py
│
├── examples/
│   ├── basic_usage.py
│   ├── research_task.py
│   ├── code_generation.py
│   └── custom_tools.py
│
├── docs/
│   ├── architecture.md
│   ├── api_reference.md
│   ├── tool_development.md
│   └── deployment.md
│
└── workspace/
    └── .gitkeep
