"""
Base classes for the tool system.

All tools must inherit from BaseTool and implement the execute method.
"""

from typing import Any, Dict, Optional, List
from pydantic import BaseModel, Field
from enum import Enum
from datetime import datetime
import time
from abc import ABC, abstractmethod


class ToolCategory(str, Enum):
    """Tool categories for organization and filtering."""
    WEB = "web"
    CODE = "code"
    FILE = "file"
    SYSTEM = "system"
    RESEARCH = "research"
    COMMUNICATION = "communication"
    DATA = "data"


class ToolParameter(BaseModel):
    """Schema for a tool parameter."""
    name: str
    type: str  # "string", "int", "float", "bool", "list", "dict"
    description: str
    required: bool = True
    default: Optional[Any] = None
    
    class Config:
        frozen = True


class ToolMetadata(BaseModel):
    """
    Metadata describing a tool's capabilities and requirements.
    
    Used for:
    - Tool discovery and selection
    - Input validation
    - Documentation generation
    - Safety checks
    """
    name: str = Field(..., description="Unique tool identifier")
    description: str = Field(..., description="What the tool does")
    category: ToolCategory = Field(..., description="Tool category")
    parameters: List[ToolParameter] = Field(
        default_factory=list,
        description="Input parameters"
    )
    returns: str = Field(..., description="Description of return value")
    
    # Safety and resource flags
    is_dangerous: bool = Field(
        default=False,
        description="Requires confirmation (file deletion, shell commands)"
    )
    requires_network: bool = Field(
        default=False,
        description="Makes network requests"
    )
    requires_filesystem: bool = Field(
        default=False,
        description="Reads or writes files"
    )
    estimated_cost_usd: float = Field(
        default=0.0,
        description="Estimated cost per execution"
    )
    
    # Examples for documentation
    examples: List[str] = Field(
        default_factory=list,
        description="Example usage strings"
    )
    
    class Config:
        frozen = True


class ToolResult(BaseModel):
    """
    Result from tool execution with metadata.
    
    Always contains success status and timing information.
    May contain output data or error details.
    """
    success: bool = Field(..., description="Whether execution succeeded")
    output: Optional[Any] = Field(
        default=None,
        description="Tool output data"
    )
    error: Optional[str] = Field(
        default=None,
        description="Error message if failed"
    )
    execution_time_seconds: float = Field(
        ...,
        description="Time taken to execute"
    )
    timestamp: datetime = Field(
        default_factory=datetime.now,
        description="When the tool was executed"
    )
    
    # Resource usage
    tokens_used: int = Field(
        default=0,
        description="LLM tokens consumed (if applicable)"
    )
    cost_usd: float = Field(
        default=0.0,
        description="Estimated cost in USD"
    )
    
    # Additional metadata
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Tool-specific metadata"
    )
    
    def to_observation(self) -> str:
        """Convert to human-readable observation for agent."""
        if self.success:
            return f"✅ Success: {self.output}"
        else:
            return f"❌ Error: {self.error}"


class BaseTool(ABC):
    """
    Abstract base class for all tools.
    
    To create a new tool:
    1. Inherit from BaseTool
    2. Implement the metadata property
    3. Implement the execute method
    4. Optionally override validate_inputs for custom validation
    
    Example:
        class MyTool(BaseTool):
            @property
            def metadata(self) -> ToolMetadata:
                return ToolMetadata(
                    name="my_tool",
                    description="Does something useful",
                    category=ToolCategory.SYSTEM,
                    parameters=[
                        ToolParameter(
                            name="input",
                            type="string",
                            description="Input text",
                            required=True
                        )
                    ],
                    returns="Processed output"
                )
            
            async def execute(self, input: str) -> ToolResult:
                # Implementation here
                return ToolResult(
                    success=True,
                    output=f"Processed: {input}",
                    execution_time_seconds=0.1
                )
    """
    
    @property
    @abstractmethod
    def metadata(self) -> ToolMetadata:
        """Return tool metadata for discovery and validation."""
        pass
    
    @abstractmethod
    async def execute(self, **kwargs) -> ToolResult:
        """
        Execute the tool with given parameters.
        
        Args:
            **kwargs: Parameters matching the tool's metadata
        
        Returns:
            ToolResult with success status and output/error
        """
        pass
    
    def validate_inputs(self, **kwargs) -> tuple[bool, Optional[str]]:
        """
        Validate input parameters against metadata.
        
        Args:
            **kwargs: Input parameters to validate
        
        Returns:
            Tuple of (is_valid, error_message)
        """
        # Check required parameters
        required_params = {
            p.name for p in self.metadata.parameters if p.required
        }
        
        provided_params = set(kwargs.keys())
        missing_params = required_params - provided_params
        
        if missing_params:
            return False, f"Missing required parameters: {', '.join(missing_params)}"
        
        # Check parameter types
        for param in self.metadata.parameters:
            if param.name in kwargs:
                value = kwargs[param.name]
                expected_type = param.type
                
                # Type checking
                type_map = {
                    "string": str,
                    "int": int,
                    "float": (int, float),
                    "bool": bool,
                    "list": list,
                    "dict": dict
                }
                
                if expected_type in type_map:
                    expected = type_map[expected_type]
                    if not isinstance(value, expected):
                        return False, f"Parameter '{param.name}' must be {expected_type}, got {type(value).__name__}"
        
        return True, None
    
    async def safe_execute(self, **kwargs) -> ToolResult:
        """
        Execute with validation and timing.
        
        This is the method that should be called externally.
        It wraps execute() with validation and error handling.
        """
        start_time = time.time()
        
        # Validate inputs
        is_valid, error_msg = self.validate_inputs(**kwargs)
        if not is_valid:
            return ToolResult(
                success=False,
                error=f"Validation failed: {error_msg}",
                execution_time_seconds=time.time() - start_time
            )
        
        # Execute with error handling
        try:
            result = await self.execute(**kwargs)
            
            # Ensure execution time is set
            if result.execution_time_seconds == 0:
                result.execution_time_seconds = time.time() - start_time
            
            return result
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_seconds=time.time() - start_time
            )
    
    def to_llm_description(self) -> str:
        """
        Generate a description for the LLM to understand the tool.
        
        Returns:
            Formatted string describing the tool
        """
        params_desc = []
        for param in self.metadata.parameters:
            required = "required" if param.required else "optional"
            params_desc.append(
                f"  - {param.name} ({param.type}, {required}): {param.description}"
            )
        
        params_str = "\n".join(params_desc) if params_desc else "  None"
        
        return f"""Tool: {self.metadata.name}
Category: {self.metadata.category.value}
Description: {self.metadata.description}
Parameters:
{params_str}
Returns: {self.metadata.returns}
Dangerous: {self.metadata.is_dangerous}
"""


class ToolExecutionContext(BaseModel):
    """
    Context for tool execution.
    
    Provides tools with access to:
    - Configuration
    - Workspace paths
    - Current task context
    """
    workspace_path: str
    max_file_size_mb: int = 10
    network_timeout: int = 30
    current_task: Optional[str] = None
    task_id: Optional[str] = None
    
    class Config:
        arbitrary_types_allowed = True
