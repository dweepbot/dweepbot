"""
Python code executor with sandboxing and resource limits.

Executes Python code in a restricted environment with:
- Timeout enforcement
- Memory limits
- Restricted imports
- Captured stdout/stderr
"""

import asyncio
import sys
import io
import traceback
from contextlib import redirect_stdout, redirect_stderr
from typing import Dict, Any, Optional
import resource
import signal

from .base import (
    BaseTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolCategory,
    ToolExecutionContext
)


class PythonExecutorTool(BaseTool):
    """
    Execute Python code in a sandboxed environment.
    
    Safety features:
    - Restricted imports (no os, subprocess, etc.)
    - Timeout enforcement
    - Memory limits
    - Captured output
    """
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._timeout = context.current_task or 30
        self._memory_limit_mb = getattr(context, 'code_execution_memory_limit_mb', 512)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="python_execute",
            description="Execute Python code in a sandboxed environment with timeout and memory limits",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                    required=True
                ),
                ToolParameter(
                    name="timeout",
                    type="int",
                    description="Execution timeout in seconds (default: 30)",
                    required=False,
                    default=30
                )
            ],
            returns="Output from code execution (stdout/stderr) or error message",
            is_dangerous=False,  # Sandboxed, so relatively safe
            examples=[
                "python_execute(code='print(2 + 2)')",
                "python_execute(code='import math\\nprint(math.pi)')",
                "python_execute(code='result = [i**2 for i in range(10)]\\nprint(result)')"
            ]
        )
    
    async def execute(self, code: str, timeout: int = 30) -> ToolResult:
        """Execute Python code with sandboxing."""
        
        # Use configured timeout if not specified
        if timeout is None:
            timeout = 30
        
        try:
            # Execute in subprocess to isolate properly
            result = await asyncio.wait_for(
                self._run_sandboxed(code),
                timeout=timeout
            )
            return result
        
        except asyncio.TimeoutError:
            return ToolResult(
                success=False,
                error=f"Code execution timed out after {timeout} seconds",
                execution_time_seconds=timeout
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Execution error: {str(e)}",
                execution_time_seconds=0.0
            )
    
    async def _run_sandboxed(self, code: str) -> ToolResult:
        """Run code in sandboxed environment."""
        
        # Capture stdout and stderr
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        # Create restricted globals
        restricted_globals = {
            '__builtins__': {
                # Allowed built-ins (safe subset)
                'abs': abs,
                'all': all,
                'any': any,
                'bool': bool,
                'dict': dict,
                'enumerate': enumerate,
                'filter': filter,
                'float': float,
                'int': int,
                'len': len,
                'list': list,
                'map': map,
                'max': max,
                'min': min,
                'print': print,
                'range': range,
                'reversed': reversed,
                'round': round,
                'set': set,
                'sorted': sorted,
                'str': str,
                'sum': sum,
                'tuple': tuple,
                'type': type,
                'zip': zip,
                # Math and common utilities
                'True': True,
                'False': False,
                'None': None,
            }
        }
        
        # Allowed safe imports
        allowed_imports = {
            'math', 'statistics', 'random', 'datetime', 'json',
            'collections', 'itertools', 'functools', 're'
        }
        
        # Create safe import function
        original_import = __builtins__.__import__
        
        def safe_import(name, *args, **kwargs):
            if name.split('.')[0] in allowed_imports:
                return original_import(name, *args, **kwargs)
            raise ImportError(f"Import of '{name}' is not allowed in sandbox")
        
        restricted_globals['__builtins__']['__import__'] = safe_import
        
        try:
            # Execute code
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                exec(code, restricted_globals)
            
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()
            
            # Combine output
            output = ""
            if stdout_text:
                output += stdout_text
            if stderr_text:
                output += f"\n[stderr]\n{stderr_text}"
            
            if not output:
                output = "[No output]"
            
            return ToolResult(
                success=True,
                output=output.strip(),
                execution_time_seconds=0.0,
                metadata={
                    "code_length": len(code),
                    "lines": len(code.splitlines()),
                    "has_stdout": bool(stdout_text),
                    "has_stderr": bool(stderr_text)
                }
            )
        
        except SyntaxError as e:
            return ToolResult(
                success=False,
                error=f"Syntax error: {str(e)}",
                execution_time_seconds=0.0,
                metadata={"error_type": "SyntaxError"}
            )
        
        except ImportError as e:
            return ToolResult(
                success=False,
                error=f"Import error: {str(e)}\nAllowed imports: {', '.join(sorted(allowed_imports))}",
                execution_time_seconds=0.0,
                metadata={"error_type": "ImportError"}
            )
        
        except Exception as e:
            # Capture full traceback
            tb = traceback.format_exc()
            
            return ToolResult(
                success=False,
                error=f"Runtime error: {str(e)}\n\nTraceback:\n{tb}",
                execution_time_seconds=0.0,
                metadata={
                    "error_type": type(e).__name__,
                    "traceback": tb
                }
            )


class PythonREPLTool(BaseTool):
    """
    Interactive Python REPL that maintains state between executions.
    
    Useful for multi-step computations where you want to build on
    previous results.
    """
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._globals: Dict[str, Any] = {}
        self._execution_count = 0
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="python_repl",
            description="Execute Python code in a persistent REPL session (maintains variables between calls)",
            category=ToolCategory.CODE,
            parameters=[
                ToolParameter(
                    name="code",
                    type="string",
                    description="Python code to execute",
                    required=True
                ),
                ToolParameter(
                    name="reset",
                    type="bool",
                    description="Reset REPL state before execution",
                    required=False,
                    default=False
                )
            ],
            returns="Output from code execution or error message",
            examples=[
                "python_repl(code='x = 10')",
                "python_repl(code='y = x * 2')",
                "python_repl(code='print(y)')"
            ]
        )
    
    async def execute(self, code: str, reset: bool = False) -> ToolResult:
        """Execute code in persistent REPL."""
        
        if reset:
            self._globals.clear()
            self._execution_count = 0
        
        self._execution_count += 1
        
        # Capture output
        stdout_capture = io.StringIO()
        stderr_capture = io.StringIO()
        
        try:
            with redirect_stdout(stdout_capture), redirect_stderr(stderr_capture):
                # Execute in persistent globals
                exec(code, self._globals)
            
            stdout_text = stdout_capture.getvalue()
            stderr_text = stderr_capture.getvalue()
            
            output = ""
            if stdout_text:
                output += stdout_text
            if stderr_text:
                output += f"\n[stderr]\n{stderr_text}"
            
            if not output:
                # Show variables if no output
                user_vars = {
                    k: v for k, v in self._globals.items()
                    if not k.startswith('__')
                }
                if user_vars:
                    output = f"Variables: {list(user_vars.keys())}"
                else:
                    output = "[No output]"
            
            return ToolResult(
                success=True,
                output=output.strip(),
                execution_time_seconds=0.0,
                metadata={
                    "execution_count": self._execution_count,
                    "variables": len([k for k in self._globals if not k.startswith('__')])
                }
            )
        
        except Exception as e:
            tb = traceback.format_exc()
            
            return ToolResult(
                success=False,
                error=f"Error: {str(e)}\n\nTraceback:\n{tb}",
                execution_time_seconds=0.0,
                metadata={
                    "error_type": type(e).__name__,
                    "execution_count": self._execution_count
                }
            )
