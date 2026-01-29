"""
Tool execution engine with parallel execution, timeouts, and error handling.
"""

import asyncio
from datetime import datetime
from typing import Any, Dict, List, Optional
from ..tools.registry import ToolRegistry
from ..tools.base import BaseTool, ToolError
from ..utils.logger import get_logger
from ..utils.cost_tracker import CostTracker
from .schemas import ToolCall, ToolCallStatus, Subgoal

logger = get_logger(__name__)


class ExecutionError(Exception):
    """Tool execution error."""
    pass


class ToolExecutor:
    """
    Executes tools with sophisticated orchestration.
    
    Features:
    - Parallel execution where safe
    - Dependency resolution
    - Timeout management
    - Input/output validation
    - Cost tracking
    - Error recovery
    """
    
    def __init__(
        self,
        tool_registry: ToolRegistry,
        cost_tracker: Optional[CostTracker] = None,
        default_timeout: float = 30.0,
        max_parallel: int = 3,
    ):
        """
        Initialize tool executor.
        
        Args:
            tool_registry: Registry of available tools
            cost_tracker: Optional cost tracker
            default_timeout: Default timeout per tool (seconds)
            max_parallel: Maximum parallel tool executions
        """
        self.registry = tool_registry
        self.cost_tracker = cost_tracker
        self.default_timeout = default_timeout
        self.max_parallel = max_parallel
    
    async def execute_subgoal(
        self,
        subgoal: Subgoal,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ToolCall]:
        """
        Execute all tools required for a subgoal.
        
        Args:
            subgoal: The subgoal to execute
            context: Optional execution context (previous results, etc.)
        
        Returns:
            List of completed ToolCall objects
        
        Raises:
            ExecutionError: If execution fails critically
        """
        logger.info("Executing subgoal", subgoal_id=subgoal.id, description=subgoal.description[:100])
        
        if not subgoal.required_tools:
            logger.warning("No tools specified for subgoal", subgoal_id=subgoal.id)
            return []
        
        # Create tool calls
        tool_calls = [
            ToolCall(
                tool_name=tool_name,
                inputs=self._prepare_tool_inputs(tool_name, subgoal, context or {}),
            )
            for tool_name in subgoal.required_tools
        ]
        
        # Execute tools (parallel where possible)
        completed_calls = await self._execute_tools(tool_calls)
        
        # Log results
        success_count = sum(1 for tc in completed_calls if tc.status == ToolCallStatus.SUCCESS)
        logger.info(
            "Subgoal execution complete",
            subgoal_id=subgoal.id,
            total=len(completed_calls),
            success=success_count,
            failed=len(completed_calls) - success_count,
        )
        
        return completed_calls
    
    async def execute_tool(
        self,
        tool_name: str,
        inputs: Dict[str, Any],
        timeout: Optional[float] = None,
    ) -> ToolCall:
        """
        Execute a single tool.
        
        Args:
            tool_name: Name of the tool to execute
            inputs: Tool input parameters
            timeout: Optional timeout override
        
        Returns:
            Completed ToolCall object
        """
        tool_call = ToolCall(tool_name=tool_name, inputs=inputs)
        timeout = timeout or self.default_timeout
        
        try:
            # Get tool
            tool = self.registry.get_tool(tool_name)
            if not tool:
                raise ExecutionError(f"Tool not found: {tool_name}")
            
            # Execute with timeout
            tool_call.mark_running()
            start_time = datetime.utcnow()
            
            try:
                result = await asyncio.wait_for(
                    tool.execute(**inputs),
                    timeout=timeout,
                )
                
                duration = (datetime.utcnow() - start_time).total_seconds()
                
                # Record cost if tool has cost
                cost = getattr(tool, 'cost_usd', 0.0)
                if self.cost_tracker and cost > 0:
                    self.cost_tracker.record_tool_call(tool_name, cost)
                
                tool_call.mark_success(result, duration, cost)
                logger.info("Tool executed successfully", tool=tool_name, duration=duration)
                
            except asyncio.TimeoutError:
                duration = (datetime.utcnow() - start_time).total_seconds()
                tool_call.status = ToolCallStatus.TIMEOUT
                tool_call.error = f"Tool execution timed out after {timeout}s"
                tool_call.duration_seconds = duration
                logger.warning("Tool timeout", tool=tool_name, timeout=timeout)
            
        except ToolError as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            tool_call.mark_failed(str(e), duration)
            logger.error("Tool execution failed", tool=tool_name, error=str(e))
        
        except Exception as e:
            duration = (datetime.utcnow() - start_time).total_seconds()
            tool_call.mark_failed(f"Unexpected error: {str(e)}", duration)
            logger.error("Unexpected tool error", tool=tool_name, error=str(e), exc_info=True)
        
        return tool_call
    
    async def _execute_tools(self, tool_calls: List[ToolCall]) -> List[ToolCall]:
        """
        Execute multiple tools, parallelizing where possible.
        
        Args:
            tool_calls: List of tool calls to execute
        
        Returns:
            List of completed tool calls
        """
        if not tool_calls:
            return []
        
        # For now, execute in parallel up to max_parallel
        # More sophisticated dependency resolution could be added
        completed = []
        
        # Split into batches
        for i in range(0, len(tool_calls), self.max_parallel):
            batch = tool_calls[i:i + self.max_parallel]
            
            # Execute batch in parallel
            tasks = [
                self.execute_tool(tc.tool_name, tc.inputs)
                for tc in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Handle results
            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error("Tool execution failed with exception", error=str(result))
                    # Create failed tool call
                    failed_call = ToolCall(
                        tool_name="unknown",
                        inputs={},
                    )
                    failed_call.mark_failed(str(result), 0.0)
                    completed.append(failed_call)
                else:
                    completed.append(result)
        
        return completed
    
    def _prepare_tool_inputs(
        self,
        tool_name: str,
        subgoal: Subgoal,
        context: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Prepare inputs for a tool based on subgoal and context.
        
        This is a smart input preparation that:
        - Extracts relevant context
        - Uses subgoal description as default input
        - Handles tool-specific formatting
        
        Args:
            tool_name: Name of the tool
            subgoal: The subgoal being executed
            context: Execution context
        
        Returns:
            Dictionary of tool inputs
        """
        # Default inputs based on tool type
        if tool_name == "web_search":
            return {
                "query": subgoal.description,
                "max_results": context.get("max_search_results", 5),
            }
        
        elif tool_name == "python_executor":
            # Extract code from description or context
            code = context.get("code", subgoal.description)
            return {
                "code": code,
                "timeout": 30,
            }
        
        elif tool_name == "file_ops":
            return {
                "operation": context.get("file_operation", "read"),
                "path": context.get("file_path", "./workspace/output.txt"),
                "content": context.get("file_content"),
            }
        
        elif tool_name == "http_client":
            return {
                "url": context.get("url", ""),
                "method": context.get("http_method", "GET"),
                "headers": context.get("headers", {}),
            }
        
        elif tool_name == "shell_executor":
            return {
                "command": context.get("command", subgoal.description),
                "timeout": 30,
            }
        
        elif tool_name == "rag_query":
            return {
                "query": subgoal.description,
                "top_k": context.get("top_k", 5),
            }
        
        elif tool_name == "notification":
            return {
                "message": context.get("message", subgoal.description),
                "channel": context.get("notification_channel", "default"),
            }
        
        # Fallback: pass context as-is
        return context.copy()
    
    def validate_tool_availability(self, tool_names: List[str]) -> Dict[str, bool]:
        """
        Check which tools are available.
        
        Args:
            tool_names: List of tool names to check
        
        Returns:
            Dictionary mapping tool names to availability
        """
        return {
            name: self.registry.has_tool(name)
            for name in tool_names
        }
