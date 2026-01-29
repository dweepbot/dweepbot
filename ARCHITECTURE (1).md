# DweepBot Architecture

## System Overview

DweepBot is a production-grade autonomous agent framework built on the PLAN → ACT → OBSERVE → REFLECT paradigm. This document describes the system architecture, key components, and design decisions.

## Core Components

### 1. Autonomous Agent (`core/agent.py`)

The agent is the central orchestrator implementing the agentic loop:

```
┌────────────┐
│    PLAN    │  Break task into subgoals
└──────┬─────┘
       │
       ▼
┌────────────┐
│    ACT     │  Execute tools for current subgoal
└──────┬─────┘
       │
       ▼
┌────────────┐
│  OBSERVE   │  Record results and update state
└──────┬─────┘
       │
       ▼
┌────────────┐
│  REFLECT   │  Analyze progress, adjust plan if needed
└──────┬─────┘
       │
       └─────► Repeat until task complete or limits exceeded
```

#### Key Features:

- **State Persistence**: Full agent state is serializable for debugging/resume
- **Error Boundaries**: Tool failures don't crash the agent
- **Cost Tracking**: Tracks tokens and cost per operation
- **Streaming Updates**: Real-time progress via AsyncGenerator
- **Configurable Limits**: Max iterations, cost, time

#### State Management:

```python
class AgentState(BaseModel):
    task_id: str
    original_task: str
    current_phase: AgentPhase
    all_subgoals: List[Subgoal]
    completed_subgoals: List[str]
    step_results: List[StepResult]
    total_cost_usd: float
    total_tokens_used: int
    # ... more fields
```

### 2. Tool System (`tools/`)

Plugin-based architecture for extensibility:

#### Base Tool Class

```python
class BaseTool(ABC):
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Tool description, parameters, category"""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """Tool implementation"""
        pass
```

#### Tool Registry

Manages all available tools:

- Dynamic registration
- Tool discovery by name/category
- Execution with timeouts and resource limits
- Statistics tracking
- Parallel execution support

#### Built-in Tools

| Category | Tools | Features |
|----------|-------|----------|
| File I/O | read_file, write_file, list_directory, delete_file | Workspace sandboxing, size limits |
| Code Execution | python_execute, python_repl | Restricted imports, memory limits, timeout |
| Web | http_get, http_post, web_search | Response size limits, timeout |

### 3. LLM Client (`deepseek.py`)

Production-ready DeepSeek API client:

- **Async/await**: Non-blocking I/O
- **Streaming**: Token-by-token responses
- **Cost Calculation**: Automatic per-request cost tracking
- **Retry Logic**: Exponential backoff for rate limits
- **Connection Pooling**: Efficient HTTP connections

```python
async with DeepSeekClient(api_key="...") as client:
    response = await client.complete(messages=[...])
    print(f"Cost: ${response.usage.estimated_cost_usd:.4f}")
```

### 4. Memory System (`memory/`)

Two-tier memory architecture:

#### Working Memory (Short-term)

- Rolling window of recent observations
- Used for immediate context in OBSERVE/REFLECT
- Configurable size (default: 20 observations)
- Automatic pruning of old observations

#### Long-term Memory (Optional)

- Persistent storage for future retrieval
- Vector similarity search (when RAG enabled)
- Queryable during planning phase

### 5. Configuration (`config.py`)

Type-safe configuration with Pydantic:

- Environment variable support (`DWEEPBOT_*` prefix)
- `.env` file loading
- Validation with clear error messages
- Sensible defaults

## Data Flow

### Task Execution Flow

```
User Task
    │
    ▼
Agent.run()
    │
    ├─► Planning Phase
    │   ├─► LLM: Break into subgoals
    │   └─► Store subgoals in state
    │
    ├─► Execution Loop (for each subgoal)
    │   │
    │   ├─► Acting Phase
    │   │   ├─► LLM: Select tools
    │   │   └─► Execute tools via registry
    │   │
    │   ├─► Observing Phase
    │   │   └─► Store results in memory
    │   │
    │   └─► Reflecting Phase
    │       └─► LLM: Analyze progress
    │
    └─► Completion
        └─► Generate final summary
```

### Tool Execution Flow

```
Agent
    │
    ▼
ToolRegistry.execute(tool_name, **params)
    │
    ├─► Validate inputs
    ├─► Apply timeout
    ├─► Execute tool
    ├─► Track statistics
    └─► Return ToolResult
```

## Design Principles

### 1. Production-First

All code assumes production usage:

- Comprehensive error handling
- Resource limits (time, memory, cost)
- Observable via logging and metrics
- Serializable state for debugging

### 2. Cost Consciousness

DeepSeek-V3 pricing makes aggressive LLM usage viable:

- Track every token
- Report cost per operation
- Configurable cost limits
- Optimize prompt engineering

### 3. Developer Experience

Easy to use and extend:

- Type hints everywhere
- Clear abstractions
- Async/await for performance
- Minimal dependencies for core

### 4. Safety

Multiple safety layers:

- Sandboxed code execution (restricted imports)
- Workspace boundaries (no file access outside)
- Dangerous operations require confirmation
- Network timeouts and size limits

## Performance Characteristics

### Latency

- **Cold start**: 1-2s (import + initialization)
- **Planning**: 2-5s per task (depends on complexity)
- **Tool execution**: Varies by tool
  - File I/O: <100ms
  - Code execution: <30s (timeout)
  - HTTP requests: <30s (timeout)

### Cost

Typical task costs (as of Jan 2025):

- **Simple task** (1-2 steps): $0.001-0.01
- **Medium task** (3-5 steps): $0.01-0.05
- **Complex task** (10+ steps): $0.05-0.20

### Memory

- **Agent overhead**: ~50MB
- **Working memory**: ~1KB per observation
- **Long-term storage**: Depends on vector DB

## Extensibility Points

### Adding New Tools

```python
from dweepbot.tools.base import BaseTool, ToolMetadata, ToolResult

class MyTool(BaseTool):
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="my_tool",
            description="...",
            category=ToolCategory.SYSTEM,
            parameters=[...],
            returns="..."
        )
    
    async def execute(self, **kwargs) -> ToolResult:
        # Implementation
        return ToolResult(success=True, output="...")

# Register
tools.register(MyTool(context))
```

### Custom Memory Backends

Implement `MemoryManager` interface for custom storage:

```python
class CustomMemory(MemoryManager):
    async def store_observation(self, ...):
        # Store in your DB
        pass
    
    def get_relevant_memories(self, query: str):
        # Query your DB
        pass
```

### Alternative LLM Providers

Create client matching `DeepSeekClient` interface:

```python
class OpenAIClient:
    async def complete(
        self,
        messages: List[Message],
        ...
    ) -> CompletionResponse:
        # Call OpenAI API
        pass
```

## Testing Strategy

### Unit Tests

- Mock LLM responses
- Test individual tools in isolation
- Validate configuration
- Test state serialization

### Integration Tests

- End-to-end task execution
- Real API calls (with API key)
- Cost tracking validation
- Error recovery

### Performance Tests

- Measure latency
- Track memory usage
- Benchmark tool execution

## Future Enhancements

### Near-term (1-2 months)

1. **Vector Store Integration**: ChromaDB for RAG
2. **Web Browser Automation**: Playwright integration
3. **More Tools**: Database, PDF processing, etc.
4. **Dashboard**: Web UI for monitoring

### Long-term (3-6 months)

1. **Multi-agent**: Multiple agents collaborating
2. **Scheduling**: Cron-like task scheduling
3. **Enterprise Features**: Audit logs, SSO, etc.
4. **Model Agnostic**: Support multiple LLM providers

## Security Considerations

### Sandboxing

- Python code execution: Restricted builtins, no dangerous imports
- File operations: Confined to workspace directory
- Shell commands: Allowlist only (when enabled)

### Network

- All requests have timeouts
- Response size limits
- SSL verification enabled by default

### API Keys

- Never logged or persisted
- Environment variable only
- No defaults or fallbacks

## Deployment

### Single Machine

```bash
# Install
pip install dweepbot

# Configure
export DEEPSEEK_API_KEY=xxx

# Run
dweepbot run "Task description"
```

### Docker (Coming Soon)

```dockerfile
FROM python:3.10-slim
RUN pip install dweepbot[all]
ENV DEEPSEEK_API_KEY=xxx
CMD ["dweepbot", "run", "..."]
```

### Kubernetes (Coming Soon)

Helm chart for scalable deployment with:
- StatefulSets for agent persistence
- ConfigMaps for configuration
- Secrets for API keys
- Horizontal pod autoscaling

## Monitoring

### Metrics to Track

- Task completion rate
- Average cost per task
- Tool success/failure rates
- Average execution time
- Error types and frequencies

### Logging

Structured JSON logs with:
- Task IDs for tracing
- Phase information
- Tool execution details
- Cost and token usage
- Errors and warnings

### Alerting

Set up alerts for:
- High failure rates
- Cost exceeding budgets
- Long-running tasks
- Repeated errors

---

For implementation details, see the source code in `src/dweepbot/`.
