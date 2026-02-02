# DweepBot Pro Deployment Guide

This guide covers deploying DweepBot Pro features in production environments.

## Prerequisites

- Valid DweepBot Pro license key
- Python 3.10+
- Docker (optional, for containerized deployment)
- Node.js 18+ (for dashboard)

## License Activation

### Step 1: Obtain License Key

Purchase a DweepBot Pro license at https://dweepbot.com/pro

You will receive:
- License key (UUID format)
- License tier (Pro, Team, or Enterprise)
- Support contact information

### Step 2: Configure License

Set your license key as an environment variable:

```bash
export DWEEPBOT_LICENSE='your-license-key-here'
```

Or add to your `.env` file:

```
DWEEPBOT_LICENSE=your-license-key-here
```

### Step 3: Verify License

```bash
python -c "from dweepbot.license import get_license_manager; print(get_license_manager().get_tier())"
```

## Installation

### Standard Installation

```bash
# Install DweepBot with Pro features
pip install "dweepbot[all]"

# Install additional Pro dependencies
pip install chromadb sentence-transformers fastapi uvicorn
```

### Docker Installation

```bash
# Build Pro image
docker-compose -f docker-compose.pro.yml build

# Start services
docker-compose -f docker-compose.pro.yml up -d
```

## Configuration

### Environment Variables

#### Required
```bash
DWEEPBOT_LICENSE=your-license-key          # Pro license key
DEEPSEEK_API_KEY=your-deepseek-key         # DeepSeek API key
```

#### Optional - Pro Features
```bash
# License Server
DWEEPBOT_LICENSE_SERVER=https://license.dweepbot.com/v1/validate

# Multi-Agent Settings
DWEEPBOT_MAX_AGENTS=5                      # Max concurrent agents
DWEEPBOT_AGENT_POOL_SIZE=10                # Agent pool size

# Vector Store
DWEEPBOT_VECTOR_STORE=chromadb             # chromadb, pinecone, weaviate
DWEEPBOT_VECTOR_PERSIST_PATH=./chroma_db   # Storage location

# Task Scheduler
DWEEPBOT_SCHEDULER_ENABLED=true            # Enable scheduler
DWEEPBOT_SCHEDULER_MAX_TASKS=50            # Max scheduled tasks

# Dashboard
DWEEPBOT_DASHBOARD_PORT=8000               # API server port
DWEEPBOT_DASHBOARD_HOST=0.0.0.0            # Bind address
DWEEPBOT_DASHBOARD_UI_PORT=3000            # UI dev server port
```

#### Optional - Production Settings
```bash
# Rate Limiting
DWEEPBOT_RATE_LIMIT_ENABLED=true
DWEEPBOT_RATE_LIMIT_REQUESTS=100           # Requests per minute

# Telemetry (can be disabled)
DWEEPBOT_TELEMETRY_ENABLED=true            # Anonymous usage stats
DWEEPBOT_TELEMETRY_ENDPOINT=https://telemetry.dweepbot.com

# Logging
DWEEPBOT_LOG_LEVEL=INFO                    # DEBUG, INFO, WARNING, ERROR
DWEEPBOT_LOG_FILE=./logs/dweepbot.log      # Log file path
```

## Deploying Pro Features

### 1. Multi-Agent Orchestration

```python
from dweepbot.pro import MultiAgentOrchestrator

# Initialize orchestrator
orchestrator = MultiAgentOrchestrator(max_agents=5)

# Run distributed task
result = await orchestrator.run_distributed_task(
    task="Research and compare 10 AI frameworks",
    subtasks=[
        "Research frameworks 1-5",
        "Research frameworks 6-10",
        "Create comparison table",
        "Generate summary report"
    ]
)
```

### 2. Task Scheduler

```python
from dweepbot.pro import TaskScheduler

# Initialize scheduler
scheduler = TaskScheduler()

# Schedule daily report
task_id = scheduler.schedule_task(
    task="Generate daily analytics report",
    schedule="0 9 * * *",  # Every day at 9 AM
    notification_webhook="https://hooks.slack.com/your-webhook",
    max_cost_usd=2.0
)
```

### 3. Dashboard Deployment

#### Development Mode

```bash
# Terminal 1: Start API server
cd /path/to/dweepbot
python api_server.py

# Terminal 2: Start dashboard UI
cd dashboard
npm install
npm run dev
```

#### Production Mode

```bash
# Build dashboard
cd dashboard
npm run build

# Serve with API backend
python api_server.py --serve-static ./dashboard/dist
```

Or use nginx to serve the static dashboard:

```nginx
server {
    listen 80;
    server_name dashboard.yourdomain.com;

    # Dashboard UI
    location / {
        root /path/to/dweepbot/dashboard/dist;
        try_files $uri $uri/ /index.html;
    }

    # API Backend
    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }

    # WebSocket
    location /ws {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

### 4. Advanced Memory with Vector Store

```python
from dweepbot.pro import AdvancedMemory

# Initialize vector store
memory = AdvancedMemory(
    vector_store='chromadb',
    collection_name='production'
)

# Add memories
await memory.add_memory(
    "User prefers Python for backend development",
    metadata={"category": "preferences", "user": "john"}
)

# Semantic search
results = await memory.semantic_search(
    "What programming languages does the user like?",
    top_k=5
)
```

## Docker Compose Configuration

### docker-compose.pro.yml

```yaml
version: '3.8'

services:
  dweepbot-api:
    build: .
    environment:
      - DWEEPBOT_LICENSE=${DWEEPBOT_LICENSE}
      - DEEPSEEK_API_KEY=${DEEPSEEK_API_KEY}
      - DWEEPBOT_VECTOR_STORE=chromadb
      - DWEEPBOT_SCHEDULER_ENABLED=true
    ports:
      - "8000:8000"
    volumes:
      - ./workspace:/app/workspace
      - ./chroma_db:/app/chroma_db
      - ./logs:/app/logs
    command: python api_server.py --host 0.0.0.0 --port 8000

  dweepbot-dashboard:
    build: ./dashboard
    ports:
      - "3000:3000"
    depends_on:
      - dweepbot-api
    environment:
      - VITE_API_URL=http://dweepbot-api:8000

  chromadb:
    image: chromadb/chroma:latest
    ports:
      - "8001:8000"
    volumes:
      - ./chroma_data:/chroma/chroma
```

## Security Best Practices

### 1. License Key Security

- Never commit license keys to version control
- Use environment variables or secrets management
- Rotate keys if compromised
- Use different keys for dev/staging/production

### 2. API Security

```python
# Enable authentication for production
DWEEPBOT_API_AUTH_ENABLED=true
DWEEPBOT_API_SECRET_KEY=your-secret-key
```

### 3. Network Security

- Use HTTPS in production
- Enable CORS only for trusted origins
- Use firewall rules to restrict access
- Enable rate limiting

### 4. Data Security

- Encrypt vector store at rest
- Use secure WebSocket connections (WSS)
- Enable audit logging for compliance
- Regular security updates

## Monitoring & Observability

### Health Checks

```bash
# API health
curl http://localhost:8000/health

# License status
curl http://localhost:8000/license/status
```

### Metrics

DweepBot Pro provides metrics endpoints:

- `/metrics/agents` - Active agent statistics
- `/metrics/costs` - Cost tracking and budgets
- `/metrics/system` - System resource usage

### Logs

Structured logging with configurable levels:

```python
import logging
logging.getLogger('dweepbot').setLevel(logging.INFO)
```

## Troubleshooting

### License Issues

**Problem**: `LicenseError: Pro feature requires license`

**Solutions**:
1. Verify DWEEPBOT_LICENSE is set
2. Check license key validity at https://dweepbot.com/license/verify
3. Ensure license tier includes the feature
4. Contact support@dweepbot.com if issues persist

### Connection Issues

**Problem**: Dashboard can't connect to API

**Solutions**:
1. Verify API server is running: `curl http://localhost:8000/health`
2. Check CORS settings in api_server.py
3. Verify firewall rules allow connections
4. Check WebSocket connection in browser console

### Performance Issues

**Problem**: Slow multi-agent execution

**Solutions**:
1. Increase DWEEPBOT_MAX_AGENTS
2. Optimize subtask distribution
3. Use caching for repeated queries
4. Monitor resource usage with `/metrics/system`

## Support

### Community Support (Open Source)
- GitHub Issues: https://github.com/dweepbot/dweepbot/issues
- Documentation: https://docs.dweepbot.dev

### Pro Support
- Email: support@dweepbot.com
- Priority ticket portal: https://support.dweepbot.com
- Response time: < 24 hours (business days)

### Enterprise Support
- Dedicated Slack channel
- Phone support
- Custom SLA available
- Contact: enterprise@dweepbot.com

## Upgrade Path

### From Community to Pro

1. Purchase Pro license at https://dweepbot.com/pro
2. Set DWEEPBOT_LICENSE environment variable
3. Restart your application
4. Pro features are immediately available

No code changes required - the same codebase supports both editions.

### License Tiers

- **Pro**: $49/month - Individual/small team
- **Team**: $199/month - Growing teams (5-20 developers)
- **Enterprise**: Custom pricing - Large organizations

## Additional Resources

- Pro Documentation: https://docs.dweepbot.dev/pro
- Video Tutorials: https://www.youtube.com/dweepbot
- Example Deployments: https://github.com/dweepbot/examples
- Community Discord: https://discord.gg/dweepbot

---

© 2026 DweepBot Inc. All rights reserved.
