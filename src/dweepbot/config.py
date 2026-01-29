"""
Production configuration system with environment variable support and validation.
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, validator, field_validator
from pathlib import Path
from typing import Optional, List
import os


class AgentConfig(BaseSettings):
    """
    Main configuration for DweepBot autonomous agent.
    
    All settings can be overridden via environment variables with DWEEPBOT_ prefix.
    Example: DWEEPBOT_MAX_COST_USD=10.0
    """
    
    # DeepSeek API Configuration
    deepseek_api_key: str = Field(
        ...,
        description="DeepSeek API key (required)"
    )
    deepseek_base_url: str = Field(
        default="https://api.deepseek.com",
        description="DeepSeek API base URL"
    )
    deepseek_model: str = Field(
        default="deepseek-chat",
        description="DeepSeek model to use"
    )
    deepseek_timeout: int = Field(
        default=60,
        description="API request timeout in seconds",
        ge=10,
        le=300
    )
    
    # Agent Execution Limits
    max_iterations: int = Field(
        default=50,
        description="Maximum execution steps before termination",
        ge=1,
        le=200
    )
    max_cost_usd: float = Field(
        default=5.00,
        description="Maximum cost in USD before termination",
        ge=0.01,
        le=100.0
    )
    max_time_seconds: int = Field(
        default=3600,
        description="Maximum runtime in seconds (1 hour default)",
        ge=60,
        le=86400
    )
    max_tool_calls_per_step: int = Field(
        default=5,
        description="Maximum tool executions per planning step",
        ge=1,
        le=20
    )
    
    # Tool Configurations
    enable_web_search: bool = Field(
        default=False,
        description="Enable web search via DuckDuckGo"
    )
    enable_code_execution: bool = Field(
        default=True,
        description="Enable Python code execution in sandbox"
    )
    enable_shell_execution: bool = Field(
        default=False,
        description="Enable limited shell command execution"
    )
    code_execution_timeout: int = Field(
        default=30,
        description="Timeout for code execution in seconds",
        ge=5,
        le=300
    )
    code_execution_memory_limit_mb: int = Field(
        default=512,
        description="Memory limit for code execution in MB",
        ge=128,
        le=4096
    )
    
    # Workspace & File System
    workspace_path: Path = Field(
        default=Path("./workspace"),
        description="Sandboxed workspace directory for file operations"
    )
    max_file_size_mb: int = Field(
        default=10,
        description="Maximum file size for read/write operations",
        ge=1,
        le=100
    )
    allowed_file_extensions: List[str] = Field(
        default=[".txt", ".md", ".py", ".json", ".csv", ".html", ".xml"],
        description="Allowed file extensions for operations"
    )
    
    # Memory Configuration
    max_working_memory: int = Field(
        default=20,
        description="Number of recent observations to keep in working memory",
        ge=5,
        le=100
    )
    enable_vector_store: bool = Field(
        default=False,
        description="Enable ChromaDB vector store for RAG"
    )
    vector_store_path: Optional[Path] = Field(
        default=None,
        description="Path to ChromaDB persistence directory"
    )
    embedding_model: str = Field(
        default="all-MiniLM-L6-v2",
        description="Sentence transformer model for embeddings"
    )
    
    # Observability & Logging
    log_level: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    enable_cost_tracking: bool = Field(
        default=True,
        description="Track and report costs per operation"
    )
    enable_telemetry: bool = Field(
        default=False,
        description="Send anonymous usage telemetry"
    )
    state_save_interval: int = Field(
        default=5,
        description="Save agent state every N steps for crash recovery",
        ge=1,
        le=50
    )
    
    # Safety & Security
    require_confirmation_for_dangerous_ops: bool = Field(
        default=True,
        description="Require user confirmation for file deletion, shell commands"
    )
    network_timeout: int = Field(
        default=30,
        description="Network request timeout in seconds",
        ge=5,
        le=120
    )
    max_http_response_size_mb: int = Field(
        default=5,
        description="Maximum HTTP response size to process",
        ge=1,
        le=50
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DWEEPBOT_",
        case_sensitive=False,
        extra="ignore"
    )
    
    @field_validator("workspace_path")
    @classmethod
    def validate_workspace_path(cls, v: Path) -> Path:
        """Ensure workspace directory exists and is writable."""
        workspace = Path(v)
        if not workspace.exists():
            workspace.mkdir(parents=True, exist_ok=True)
        if not workspace.is_dir():
            raise ValueError(f"Workspace path {workspace} is not a directory")
        return workspace.absolute()
    
    @field_validator("vector_store_path")
    @classmethod
    def validate_vector_store_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Create vector store directory if enabled."""
        if v is None:
            return None
        store_path = Path(v)
        if not store_path.exists():
            store_path.mkdir(parents=True, exist_ok=True)
        return store_path.absolute()
    
    def get_cost_per_token(self, input_token: bool = True) -> float:
        """
        Get DeepSeek pricing per token.
        
        DeepSeek-V3 pricing (as of Jan 2025):
        - Input: $0.27 per 1M tokens
        - Output: $1.10 per 1M tokens
        """
        if input_token:
            return 0.27 / 1_000_000
        else:
            return 1.10 / 1_000_000
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate total cost for a request."""
        input_cost = input_tokens * self.get_cost_per_token(input_token=True)
        output_cost = output_tokens * self.get_cost_per_token(input_token=False)
        return input_cost + output_cost


class ToolConfig(BaseSettings):
    """Configuration specific to tool execution."""
    
    # Web Search
    web_search_max_results: int = Field(default=10, ge=1, le=50)
    web_search_region: str = Field(default="us-en")
    web_search_safe_mode: bool = Field(default=True)
    
    # HTTP Client
    http_user_agent: str = Field(
        default="DweepBot/0.1.0 (Autonomous Agent; +https://github.com/dweepbot/dweepbot)"
    )
    http_max_redirects: int = Field(default=5, ge=0, le=10)
    http_verify_ssl: bool = Field(default=True)
    
    # Shell Execution (when enabled)
    allowed_shell_commands: List[str] = Field(
        default=["ls", "cat", "grep", "find", "head", "tail", "wc"],
        description="Whitelist of allowed shell commands"
    )
    shell_working_directory: Optional[Path] = Field(default=None)
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="DWEEPBOT_TOOL_",
        case_sensitive=False
    )


def load_config(env_file: Optional[Path] = None) -> AgentConfig:
    """
    Load configuration from environment and .env file.
    
    Args:
        env_file: Optional path to .env file (defaults to .env in current directory)
    
    Returns:
        Validated AgentConfig instance
    
    Raises:
        ValidationError: If configuration is invalid or API key is missing
    """
    if env_file and env_file.exists():
        return AgentConfig(_env_file=str(env_file))
    return AgentConfig()


def create_default_env_file(path: Path = Path(".env")) -> None:
    """Create a template .env file with all available configuration options."""
    
    template = """# DweepBot Configuration
# Copy this to .env and fill in your values

# Required: DeepSeek API Key
DWEEPBOT_DEEPSEEK_API_KEY=your-api-key-here

# Agent Limits
DWEEPBOT_MAX_ITERATIONS=50
DWEEPBOT_MAX_COST_USD=5.00
DWEEPBOT_MAX_TIME_SECONDS=3600

# Tool Enablement
DWEEPBOT_ENABLE_WEB_SEARCH=false
DWEEPBOT_ENABLE_CODE_EXECUTION=true
DWEEPBOT_ENABLE_SHELL_EXECUTION=false

# Code Execution
DWEEPBOT_CODE_EXECUTION_TIMEOUT=30
DWEEPBOT_CODE_EXECUTION_MEMORY_LIMIT_MB=512

# Workspace
DWEEPBOT_WORKSPACE_PATH=./workspace
DWEEPBOT_MAX_FILE_SIZE_MB=10

# Memory & RAG
DWEEPBOT_MAX_WORKING_MEMORY=20
DWEEPBOT_ENABLE_VECTOR_STORE=false
# DWEEPBOT_VECTOR_STORE_PATH=./vector_db

# Logging
DWEEPBOT_LOG_LEVEL=INFO
DWEEPBOT_ENABLE_COST_TRACKING=true
"""
    
    path.write_text(template)
    print(f"Created template configuration at {path}")
