# 🦈 DweepBot - Autonomous AI Agent Framework

**Production-grade autonomous AI agents at DeepSeek prices**  
*Available in Community (Open Source) and Pro (Commercial) editions*

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![Pro License](https://img.shields.io/badge/Pro-Commercial-blue.svg)](https://dweepbot.com/pro)

---

## 🎯 What is DweepBot?

DweepBot is an **open-core autonomous agent framework** built for real production workloads. It delivers the same PLAN → ACT → OBSERVE → REFLECT autonomy as expensive alternatives, but at **50-60× lower cost** by using DeepSeek-V3.

### 🆓 Community Edition (Open Source - MIT License)

Perfect for individual developers, learning, and non-commercial projects:

✨ **Full Autonomy**: Real PLAN → ACT → OBSERVE → REFLECT loop, not a chatbot wrapper  
💰 **Cost-Effective**: $0.27/1M input tokens vs GPT-4's $15/1M (55× cheaper)  
🛠️ **Core Tools**: File I/O, HTTP client, Python execution  
🧠 **Basic Memory**: Working memory for task context  
🔒 **Production-Ready**: Error boundaries, cost tracking, state persistence  
🎨 **Developer-Friendly**: Clean APIs, full type hints, async/await  

### 💎 DweepBot Pro (Commercial License)

Built for teams and production deployments. **Starting at $49/month**:

🚀 **Multi-Agent Orchestration**: Coordinate multiple agents on complex tasks  
🧠 **Advanced Memory Systems**: Vector store (ChromaDB) with semantic search  
⏰ **Task Scheduler**: Cron-style automation and recurring tasks  
📊 **Web Dashboard**: Real-time monitoring and control center  
🔄 **Enterprise Features**: Audit logs, compliance tools, white-label options  
🎯 **Priority Support**: Email support with < 24hr response time  

[**Get DweepBot Pro →**](https://dweepbot.com/pro)  

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

### Activating Pro Features

If you have a Pro license:

```bash
# Set your license key
export DWEEPBOT_LICENSE='your-license-key'

# Install Pro dependencies
pip install chromadb sentence-transformers fastapi uvicorn

# Start the dashboard (optional)
cd dashboard && npm install && npm run dev
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for complete Pro setup instructions.

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

### Community Edition (Open Source)

```
┌─────────────────────────────────────────────────────┐
│              Autonomous Agent (MIT)                  │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐          │
│  │   PLAN   │→ │   ACT    │→ │  OBSERVE │          │
│  └──────────┘  └──────────┘  └──────────┘          │
│       ↑                              │               │
│       └──────────  REFLECT  ←────────┘               │
└─────────────────────────────────────────────────────┘
           │                    │
    ┌──────▼──────┐      ┌─────▼──────┐
    │  Tool       │      │   Working   │
    │  Registry   │      │   Memory    │
    │             │      │             │
    │ - File I/O  │      │ - Context   │
    │ - Code Exec │      │ - History   │
    │ - HTTP      │      │             │
    └─────────────┘      └─────────────┘
```

### Pro Edition (Commercial)

```
┌──────────────────────────────────────────────────────────┐
│         Multi-Agent Orchestration (Pro) 💎                │
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

## 💎 Feature Comparison

| Feature | Community (Free) | Pro ($49/mo) | Enterprise (Custom) |
|---------|------------------|--------------|---------------------|
| **Core Autonomy** | ✅ PLAN→ACT→OBSERVE→REFLECT | ✅ | ✅ |
| **File I/O Tools** | ✅ | ✅ | ✅ |
| **Python Execution** | ✅ | ✅ | ✅ |
| **HTTP Client** | ✅ | ✅ | ✅ |
| **CLI Interface** | ✅ | ✅ | ✅ |
| **Cost Tracking** | ✅ | ✅ | ✅ |
| **Working Memory** | ✅ | ✅ | ✅ |
| **Multi-Agent Orchestration** | ❌ | ✅ Up to 5 agents | ✅ Unlimited |
| **Vector Store (ChromaDB)** | ❌ | ✅ | ✅ |
| **Semantic Memory Search** | ❌ | ✅ | ✅ |
| **Task Scheduler** | ❌ | ✅ 50 tasks | ✅ Unlimited |
| **Web Dashboard** | ❌ | ✅ | ✅ |
| **Real-time Monitoring** | ❌ | ✅ | ✅ |
| **Audit Logs** | ❌ | ❌ | ✅ |
| **Compliance Tools** | ❌ | ❌ | ✅ |
| **White-Label** | ❌ | ❌ | ✅ |
| **Support** | Community | Email (< 24hr) | Dedicated + SLA |
| **Commercial Use** | ✅ | ✅ | ✅ |

---

## 💰 Pricing

### Community Edition - **FREE** ✨
- Perfect for individual developers and learning
- Full core functionality (PLAN→ACT→OBSERVE→REFLECT)
- All basic tools included
- MIT License - use anywhere
- Community support via GitHub

### Pro Edition - **$49/month** 💎
- Everything in Community, plus:
- Multi-agent orchestration (up to 5 concurrent agents)
- Vector store & advanced memory
- Task scheduler (up to 50 scheduled tasks)
- Web dashboard with real-time monitoring
- Priority email support (< 24 hour response)
- **[Get Pro License →](https://dweepbot.com/pro)**

### Team Edition - **$199/month** 🚀
- Everything in Pro, plus:
- Up to 20 concurrent agents
- Unlimited scheduled tasks
- Team collaboration features
- Shared memory across agents
- Advanced analytics
- **[Contact Sales →](mailto:sales@dweepbot.com)**

### Enterprise Edition - **Custom** 🏢
- Everything in Team, plus:
- Unlimited agents
- Audit logs & compliance tools
- White-label deployment
- Custom integrations
- On-premise installation
- SLA with priority support
- Dedicated account manager
- **[Contact Enterprise Sales →](mailto:enterprise@dweepbot.com)**

---

## 🏗️ Architecture

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

### Community Edition (Open Source)

**Current - v1.0** ✅
- [x] PLAN→ACT→OBSERVE→REFLECT loop
- [x] Tool system with core tools (File I/O, HTTP, Python exec)
- [x] Cost tracking & limits
- [x] Working memory
- [x] Production error handling
- [x] MIT License

**Next - v1.1** (Q1 2026)
- [ ] Enhanced documentation
- [ ] More example projects
- [ ] Performance optimizations
- [ ] Additional basic tools
- [ ] Improved error messages

### Pro Edition (Commercial)

**Available Now** 💎
- [x] Multi-agent orchestration
- [x] Vector store (ChromaDB integration)
- [x] Task scheduler with cron support
- [x] Web dashboard & command center
- [x] Advanced memory systems

**Coming Q1 2026**
- [ ] Pinecone & Weaviate vector store support
- [ ] Advanced analytics dashboard
- [ ] Webhook integrations (Slack, Discord, Teams)
- [ ] Database tools (SQL, MongoDB)
- [ ] Browser automation (Playwright integration)

**Coming Q2 2026**
- [ ] Team collaboration features
- [ ] Shared agent workspaces
- [ ] Role-based access control
- [ ] Advanced audit logging

### Enterprise Edition (Custom)

**Available Now** 🏢
- [x] All Pro features
- [x] White-label deployment
- [x] Custom integrations
- [x] SLA & priority support

**Roadmap** (Custom timeline)
- [ ] Air-gapped deployment options
- [ ] SAML/SSO integration
- [ ] Custom compliance reports
- [ ] Dedicated infrastructure options

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

DweepBot uses an **open-core model**:

- **Community Edition**: MIT License - see [LICENSE](LICENSE)
- **Pro Edition**: Commercial License - see [LICENSE-COMMERCIAL.md](LICENSE-COMMERCIAL.md)

All code in the `src/dweepbot/oss/` directory and files marked with `SPDX-License-Identifier: MIT` 
are open source and free to use under the MIT License.

Code in the `src/dweepbot/pro/` directory and files marked with `SPDX-License-Identifier: COMMERCIAL`
require a commercial license. Get your license at [dweepbot.com/pro](https://dweepbot.com/pro).

---

## 🙏 Acknowledgments

- DeepSeek for providing cost-effective, high-quality LLMs
- The open-source AI community for inspiration and tools
- Our Pro customers for supporting development

---

## 📞 Support

### Community Edition (Open Source)
- **Documentation**: [GitHub Wiki](https://github.com/dweepbot/dweepbot/wiki)
- **Issues**: [GitHub Issues](https://github.com/dweepbot/dweepbot/issues)
- **Discussions**: [GitHub Discussions](https://github.com/dweepbot/dweepbot/discussions)
- **Discord**: [Join our community](https://discord.gg/dweepbot)

### Pro Edition Support
- **Email**: support@dweepbot.com (< 24hr response)
- **Documentation**: [Pro Docs](https://docs.dweepbot.dev/pro)
- **Deployment Guide**: [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md)
- **Status Page**: [status.dweepbot.com](https://status.dweepbot.com)

### Enterprise Support
- **Dedicated Support**: enterprise@dweepbot.com
- **Phone Support**: Available with Enterprise SLA
- **Private Slack**: Dedicated channel for your team
- **Custom Integrations**: We'll build what you need

### Sales & Licensing
- **Pro License**: [dweepbot.com/pro](https://dweepbot.com/pro)
- **Sales Inquiries**: sales@dweepbot.com
- **Custom Quotes**: enterprise@dweepbot.com
- **Partnerships**: partners@dweepbot.com

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
