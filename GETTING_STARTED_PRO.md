# Getting Started with DweepBot Pro

Welcome to DweepBot Pro! This guide will help you get up and running with premium features.

## Prerequisites

- Python 3.10 or higher
- Valid DweepBot Pro license key
- DeepSeek API key (or other supported LLM provider)

## Installation

### 1. Install DweepBot

```bash
# Clone or install DweepBot
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot

# Install with all dependencies
pip install -e ".[all]"

# Install Pro dependencies
pip install chromadb sentence-transformers fastapi uvicorn redis
```

### 2. Configure Environment

Copy the example environment file and add your keys:

```bash
cp .env.example .env
```

Edit `.env` and add:

```bash
# Required
DEEPSEEK_API_KEY=your-deepseek-key
DWEEPBOT_LICENSE=your-pro-license-key

# Optional Pro features
DWEEPBOT_MAX_AGENTS=5
DWEEPBOT_VECTOR_STORE=chromadb
DWEEPBOT_SCHEDULER_ENABLED=true
```

### 3. Verify License

```bash
python -c "from dweepbot.license import get_license_manager; lm = get_license_manager(); print(f'License tier: {lm.get_tier()}')"
```

## Using Pro Features

### Multi-Agent Orchestration

```python
import asyncio
from dweepbot.pro import MultiAgentOrchestrator

async def main():
    # Initialize orchestrator
    orchestrator = MultiAgentOrchestrator(max_agents=5)
    
    # Run distributed task
    result = await orchestrator.run_distributed_task(
        task="Research top 10 AI frameworks and create comparison",
        subtasks=[
            "Research frameworks 1-5",
            "Research frameworks 6-10",
            "Create comparison table",
            "Generate summary"
        ]
    )
    
    print(result)

asyncio.run(main())
```

### Task Scheduler

```python
from dweepbot.pro import TaskScheduler

# Initialize scheduler
scheduler = TaskScheduler()

# Schedule daily report
task_id = scheduler.schedule_task(
    task="Generate daily analytics report",
    schedule="0 9 * * *",  # Every day at 9 AM
    notification_webhook="https://hooks.slack.com/your-webhook"
)

print(f"Scheduled task: {task_id}")
```

### Advanced Memory with Vector Store

```python
import asyncio
from dweepbot.pro import AdvancedMemory

async def main():
    # Initialize advanced memory
    memory = AdvancedMemory(
        vector_store='chromadb',
        collection_name='my_project'
    )
    
    # Add memories
    await memory.add_memory(
        "User prefers Python for backend development",
        metadata={"category": "preferences"}
    )
    
    # Semantic search
    results = await memory.semantic_search(
        "What programming languages does the user like?",
        top_k=5
    )
    
    for result in results:
        print(f"Match: {result['content']} (score: {result['score']})")

asyncio.run(main())
```

### Web Dashboard

Start the Pro dashboard and API server:

```bash
# Terminal 1: Start API backend
python api_server.py

# Terminal 2: Start dashboard UI
cd dashboard
npm install
npm run dev
```

Then open http://localhost:3000 in your browser.

## Docker Deployment

For production deployments:

```bash
# Configure environment
cp .env.example .env
# Edit .env with your keys

# Start all services
docker-compose -f docker-compose.pro.yml up -d

# Check logs
docker-compose -f docker-compose.pro.yml logs -f

# Stop services
docker-compose -f docker-compose.pro.yml down
```

## Features Overview

### Included in Pro

✅ Multi-agent orchestration (up to 5 concurrent agents)  
✅ Vector store with ChromaDB  
✅ Semantic memory search  
✅ Task scheduler with cron support  
✅ Web dashboard with real-time monitoring  
✅ Priority email support (< 24hr response)  

### Coming Soon

🔜 Additional vector store backends (Pinecone, Weaviate)  
🔜 Webhook integrations (Slack, Discord, Teams)  
🔜 Advanced analytics dashboard  
🔜 Database tools (SQL, MongoDB)  
🔜 Browser automation (Playwright)  

## Troubleshooting

### License Issues

**Problem**: `LicenseError: Pro feature requires license`

**Solution**:
1. Verify `DWEEPBOT_LICENSE` environment variable is set
2. Check license validity at https://dweepbot.com/license/verify
3. Contact support@dweepbot.com if issues persist

### Dashboard Connection Issues

**Problem**: Dashboard can't connect to API

**Solution**:
1. Verify API is running: `curl http://localhost:8000/health`
2. Check CORS settings in `api_server.py`
3. Verify firewall allows connections on port 8000

### Vector Store Issues

**Problem**: ChromaDB errors or slow performance

**Solution**:
1. Ensure ChromaDB is installed: `pip install chromadb`
2. Check disk space in `chroma_db/` directory
3. Consider using external ChromaDB server for production

## Support

### Pro Support Channels

- **Email**: support@dweepbot.com (< 24hr response)
- **Documentation**: https://docs.dweepbot.dev/pro
- **Status Page**: https://status.dweepbot.com

### Getting Help

When contacting support, please include:

1. Your license tier (Pro/Team/Enterprise)
2. DweepBot version: `python -c "import dweepbot; print(dweepbot.__version__)"`
3. Error messages or logs
4. Steps to reproduce the issue

## Next Steps

- Read the [Deployment Guide](DEPLOYMENT_GUIDE.md) for production setup
- Join our Discord community: https://discord.gg/dweepbot
- Check out example projects: https://github.com/dweepbot/examples
- Watch video tutorials: https://www.youtube.com/dweepbot

## Upgrade Options

### Need More?

- **Team Edition** ($199/mo): Up to 20 agents, team collaboration
- **Enterprise**: Unlimited agents, white-label, custom integrations

Contact sales@dweepbot.com or visit https://dweepbot.com/pricing

---

**Welcome to DweepBot Pro!** 🚀

We're excited to have you. If you have any questions or feedback, don't hesitate to reach out to our support team.

Happy building! 🦈
