"""
Tool registry for managing and executing tools.

Provides:
- Dynamic tool registration
- Tool discovery by name or category
- Safe execution with timeouts and resource limits
- Parallel tool execution support
"""

from typing import Dict, List, Optional, Any
from .base import BaseTool, ToolResult, ToolCategory, ToolExecutionContext
import asyncio
import logging

logger = logging.getLogger(__name__)


class ToolRegistry:
    """
    Central registry for all available tools.
    
    Responsibilities:
    - Register and manage tools
    - Execute tools with proper error handling
    - Enforce timeouts and resource limits
    - Track tool usage statistics
    """
    
    def __init__(self, context: ToolExecutionContext):
        self._tools: Dict[str, BaseTool] = {}
        self._context = context
        self._execution_stats: Dict[str, Dict[str, Any]] = {}
        self._logger = logging.getLogger(f"{__name__}.ToolRegistry")
    
    def register(self, tool: BaseTool) -> None:
        """
        Register a tool.
        
        Args:
            tool: Tool instance to register
        
        Raises:
            ValueError: If tool with same name already registered
        """
        tool_name = tool.metadata.name
        
        if tool_name in self._tools:
            raise ValueError(f"Tool '{tool_name}' is already registered")
        
        self._tools[tool_name] = tool
        self._execution_stats[tool_name] = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_time_seconds": 0.0,
            "total_cost_usd": 0.0
        }
        
        self._logger.info(f"Registered tool: {tool_name} ({tool.metadata.category.value})")
    
    def unregister(self, tool_name: str) -> None:
        """Remove a tool from the registry."""
        if tool_name in self._tools:
            del self._tools[tool_name]
            del self._execution_stats[tool_name]
            self._logger.info(f"Unregistered tool: {tool_name}")
    
    def get_tool(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name."""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """Get list of all registered tool names."""
        return list(self._tools.keys())
    
    def get_tools_by_category(self, category: ToolCategory) -> List[BaseTool]:
        """
        Get all tools in a specific category.
        
        Args:
            category: Tool category to filter by
        
        Returns:
            List of tools in the category
        """
        return [
            tool for tool in self._tools.values()
            if tool.metadata.category == category
        ]
    
    def get_tool_descriptions(self) -> str:
        """
        Get formatted descriptions of all tools for LLM consumption.
        
        Returns:
            Multi-line string describing all available tools
        """
        descriptions = []
        for tool in self._tools.values():
            descriptions.append(tool.to_llm_description())
        
        return "\n\n".join(descriptions)
    
    async def execute(
        self,
        tool_name: str,
        timeout: Optional[int] = None,
        **kwargs
    ) -> ToolResult:
        """
        Execute a tool with timeout and error handling.
        
        Args:
            tool_name: Name of the tool to execute
            timeout: Maximum execution time in seconds (None = no timeout)
            **kwargs: Tool-specific parameters
        
        Returns:
            ToolResult with execution status and output/error
        """
        tool = self.get_tool(tool_name)
        
        if not tool:
            return ToolResult(
                success=False,
                error=f"Tool '{tool_name}' not found in registry",
                execution_time_seconds=0.0
            )
        
        self._logger.info(f"Executing tool: {tool_name} with params: {kwargs}")
        
        # Update stats
        stats = self._execution_stats[tool_name]
        stats["total_executions"] += 1
        
        try:
            # Execute with timeout if specified
            if timeout:
                result = await asyncio.wait_for(
                    tool.safe_execute(**kwargs),
                    timeout=timeout
                )
            else:
                result = await tool.safe_execute(**kwargs)
            
            # Update stats
            if result.success:
                stats["successful_executions"] += 1
            else:
                stats["failed_executions"] += 1
            
            stats["total_time_seconds"] += result.execution_time_seconds
            stats["total_cost_usd"] += result.cost_usd
            
            self._logger.info(
                f"Tool {tool_name} completed: success={result.success}, "
                f"time={result.execution_time_seconds:.2f}s"
            )
            
            return result
        
        except asyncio.TimeoutError:
            stats["failed_executions"] += 1
            self._logger.warning(f"Tool {tool_name} timed out after {timeout}s")
            
            return ToolResult(
                success=False,
                error=f"Tool execution timed out after {timeout} seconds",
                execution_time_seconds=timeout or 0.0
            )
        
        except Exception as e:
            stats["failed_executions"] += 1
            self._logger.error(f"Tool {tool_name} failed with error: {str(e)}")
            
            return ToolResult(
                success=False,
                error=f"Unexpected error: {str(e)}",
                execution_time_seconds=0.0
            )
    
    async def execute_batch(
        self,
        tool_calls: List[Dict[str, Any]],
        max_parallel: int = 3,
        timeout_per_tool: Optional[int] = None
    ) -> List[ToolResult]:
        """
        Execute multiple tools in parallel (where safe).
        
        Args:
            tool_calls: List of dicts with 'tool_name' and 'params' keys
            max_parallel: Maximum number of parallel executions
            timeout_per_tool: Timeout for each individual tool
        
        Returns:
            List of ToolResults in same order as tool_calls
        """
        semaphore = asyncio.Semaphore(max_parallel)
        
        async def execute_with_semaphore(tool_call: Dict[str, Any]) -> ToolResult:
            async with semaphore:
                tool_name = tool_call.get("tool_name", "")
                params = tool_call.get("params", {})
                return await self.execute(tool_name, timeout_per_tool, **params)
        
        tasks = [execute_with_semaphore(tc) for tc in tool_calls]
        return await asyncio.gather(*tasks)
    
    def get_statistics(self, tool_name: Optional[str] = None) -> Dict[str, Any]:
        """
        Get execution statistics.
        
        Args:
            tool_name: Specific tool to get stats for (None = all tools)
        
        Returns:
            Dictionary of statistics
        """
        if tool_name:
            if tool_name not in self._execution_stats:
                return {}
            return self._execution_stats[tool_name].copy()
        
        # Aggregate stats across all tools
        total_stats = {
            "total_executions": 0,
            "successful_executions": 0,
            "failed_executions": 0,
            "total_time_seconds": 0.0,
            "total_cost_usd": 0.0,
            "tools_registered": len(self._tools),
            "by_tool": self._execution_stats.copy()
        }
        
        for stats in self._execution_stats.values():
            total_stats["total_executions"] += stats["total_executions"]
            total_stats["successful_executions"] += stats["successful_executions"]
            total_stats["failed_executions"] += stats["failed_executions"]
            total_stats["total_time_seconds"] += stats["total_time_seconds"]
            total_stats["total_cost_usd"] += stats["total_cost_usd"]
        
        return total_stats
    
    def reset_statistics(self) -> None:
        """Reset all execution statistics."""
        for stats in self._execution_stats.values():
            stats.update({
                "total_executions": 0,
                "successful_executions": 0,
                "failed_executions": 0,
                "total_time_seconds": 0.0,
                "total_cost_usd": 0.0
            })
        
        self._logger.info("Reset all tool execution statistics")


def create_registry_with_default_tools(context: ToolExecutionContext) -> ToolRegistry:
    """
    Create a registry and register all default tools.
    
    Args:
        context: Execution context for tools
    
    Returns:
        ToolRegistry with all default tools registered
    """
    registry = ToolRegistry(context)
    
    # Import and register default tools
    # This will be expanded as we implement more tools
    try:
        from .file_ops import ReadFileTool, WriteFileTool, ListDirectoryTool
        registry.register(ReadFileTool(context))
        registry.register(WriteFileTool(context))
        registry.register(ListDirectoryTool(context))
    except ImportError:
        logger.warning("File operations tools not available")
    
    try:
        from .python_executor import PythonExecutorTool
        registry.register(PythonExecutorTool(context))
    except ImportError:
        logger.warning("Python executor tool not available")
    
    try:
        from .web_search import WebSearchTool
        registry.register(WebSearchTool(context))
    except ImportError:
        logger.warning("Web search tool not available (install with pip install 'dweepbot[web]')")
    
    try:
        from .http_client import HTTPGetTool, HTTPPostTool
        registry.register(HTTPGetTool(context))
        registry.register(HTTPPostTool(context))
    except ImportError:
        logger.warning("HTTP client tools not available")
    
    return registry
