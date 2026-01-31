"""
File operation tools for reading, writing, and managing files in the workspace.

All file operations are sandboxed to the configured workspace directory.
"""

from pathlib import Path
from typing import Optional
import os
import asyncio

from .base import (
    BaseTool,
    ToolMetadata,
    ToolParameter,
    ToolResult,
    ToolCategory,
    ToolExecutionContext
)


class ReadFileTool(BaseTool):
    """Read contents of a file from the workspace."""
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._workspace = Path(context.workspace_path)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="read_file",
            description="Read the contents of a text file from the workspace",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file relative to workspace",
                    required=True
                )
            ],
            returns="File contents as string",
            requires_filesystem=True,
            examples=[
                "read_file(file_path='data.txt')",
                "read_file(file_path='output/results.json')"
            ]
        )
    
    async def execute(self, file_path: str) -> ToolResult:
        """Read file contents."""
        try:
            # Resolve path within workspace (security check)
            full_path = (self._workspace / file_path).resolve()
            
            # Ensure path is within workspace
            if not str(full_path).startswith(str(self._workspace)):
                return ToolResult(
                    success=False,
                    error=f"Access denied: {file_path} is outside workspace",
                    execution_time_seconds=0.0
                )
            
            # Check if file exists
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path}",
                    execution_time_seconds=0.0
                )
            
            # Check file size
            file_size_mb = full_path.stat().st_size / (1024 * 1024)
            if file_size_mb > self._context.max_file_size_mb:
                return ToolResult(
                    success=False,
                    error=f"File too large: {file_size_mb:.2f}MB (max: {self._context.max_file_size_mb}MB)",
                    execution_time_seconds=0.0
                )
            
            # Read file
            content = await asyncio.to_thread(full_path.read_text, encoding='utf-8')
            
            return ToolResult(
                success=True,
                output=content,
                execution_time_seconds=0.0,
                metadata={
                    "file_path": file_path,
                    "file_size_bytes": full_path.stat().st_size,
                    "lines": len(content.splitlines())
                }
            )
        
        except UnicodeDecodeError:
            return ToolResult(
                success=False,
                error=f"File is not a valid text file: {file_path}",
                execution_time_seconds=0.0
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error reading file: {str(e)}",
                execution_time_seconds=0.0
            )


class WriteFileTool(BaseTool):
    """Write or overwrite a file in the workspace."""
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._workspace = Path(context.workspace_path)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="write_file",
            description="Write content to a file in the workspace (creates directories if needed)",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to the file relative to workspace",
                    required=True
                ),
                ToolParameter(
                    name="content",
                    type="string",
                    description="Content to write to the file",
                    required=True
                ),
                ToolParameter(
                    name="append",
                    type="bool",
                    description="Append to file instead of overwriting",
                    required=False,
                    default=False
                )
            ],
            returns="Confirmation message with file path",
            requires_filesystem=True,
            examples=[
                "write_file(file_path='output.txt', content='Hello, world!')",
                "write_file(file_path='logs/app.log', content='Error message', append=True)"
            ]
        )
    
    async def execute(
        self,
        file_path: str,
        content: str,
        append: bool = False
    ) -> ToolResult:
        """Write content to file."""
        try:
            # Resolve path within workspace
            full_path = (self._workspace / file_path).resolve()
            
            # Ensure path is within workspace
            if not str(full_path).startswith(str(self._workspace)):
                return ToolResult(
                    success=False,
                    error=f"Access denied: {file_path} is outside workspace",
                    execution_time_seconds=0.0
                )
            
            # Check content size
            content_size_mb = len(content.encode('utf-8')) / (1024 * 1024)
            if content_size_mb > self._context.max_file_size_mb:
                return ToolResult(
                    success=False,
                    error=f"Content too large: {content_size_mb:.2f}MB (max: {self._context.max_file_size_mb}MB)",
                    execution_time_seconds=0.0
                )
            
            # Create parent directories if needed
            full_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Write file
            mode = 'a' if append else 'w'
            await asyncio.to_thread(full_path.write_text, content, encoding='utf-8')
            
            action = "Appended to" if append else "Wrote"
            
            return ToolResult(
                success=True,
                output=f"{action} {file_path} ({len(content)} characters)",
                execution_time_seconds=0.0,
                metadata={
                    "file_path": file_path,
                    "bytes_written": len(content.encode('utf-8')),
                    "lines": len(content.splitlines()),
                    "appended": append
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error writing file: {str(e)}",
                execution_time_seconds=0.0
            )


class ListDirectoryTool(BaseTool):
    """List files and directories in the workspace."""
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._workspace = Path(context.workspace_path)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="list_directory",
            description="List all files and subdirectories in a directory",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="directory",
                    type="string",
                    description="Directory path relative to workspace (default: root)",
                    required=False,
                    default="."
                ),
                ToolParameter(
                    name="recursive",
                    type="bool",
                    description="List files recursively",
                    required=False,
                    default=False
                )
            ],
            returns="List of file paths",
            requires_filesystem=True,
            examples=[
                "list_directory()",
                "list_directory(directory='output', recursive=True)"
            ]
        )
    
    async def execute(
        self,
        directory: str = ".",
        recursive: bool = False
    ) -> ToolResult:
        """List directory contents."""
        try:
            # Resolve path within workspace
            full_path = (self._workspace / directory).resolve()
            
            # Ensure path is within workspace
            if not str(full_path).startswith(str(self._workspace)):
                return ToolResult(
                    success=False,
                    error=f"Access denied: {directory} is outside workspace",
                    execution_time_seconds=0.0
                )
            
            # Check if directory exists
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"Directory not found: {directory}",
                    execution_time_seconds=0.0
                )
            
            if not full_path.is_dir():
                return ToolResult(
                    success=False,
                    error=f"Not a directory: {directory}",
                    execution_time_seconds=0.0
                )
            
            # List files
            if recursive:
                files = []
                for root, dirs, filenames in os.walk(full_path):
                    for filename in filenames:
                        file_path = Path(root) / filename
                        rel_path = file_path.relative_to(self._workspace)
                        files.append(str(rel_path))
            else:
                files = [
                    str(item.relative_to(self._workspace))
                    for item in full_path.iterdir()
                ]
            
            files.sort()
            
            return ToolResult(
                success=True,
                output=files,
                execution_time_seconds=0.0,
                metadata={
                    "directory": directory,
                    "file_count": len(files),
                    "recursive": recursive
                }
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error listing directory: {str(e)}",
                execution_time_seconds=0.0
            )


class DeleteFileTool(BaseTool):
    """Delete a file from the workspace (dangerous operation)."""
    
    def __init__(self, context: ToolExecutionContext):
        self._context = context
        self._workspace = Path(context.workspace_path)
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="delete_file",
            description="Delete a file from the workspace (DANGEROUS - cannot be undone)",
            category=ToolCategory.FILE,
            parameters=[
                ToolParameter(
                    name="file_path",
                    type="string",
                    description="Path to file to delete",
                    required=True
                )
            ],
            returns="Confirmation message",
            is_dangerous=True,
            requires_filesystem=True,
            examples=["delete_file(file_path='temp.txt')"]
        )
    
    async def execute(self, file_path: str) -> ToolResult:
        """Delete a file."""
        try:
            # Resolve path within workspace
            full_path = (self._workspace / file_path).resolve()
            
            # Ensure path is within workspace
            if not str(full_path).startswith(str(self._workspace)):
                return ToolResult(
                    success=False,
                    error=f"Access denied: {file_path} is outside workspace",
                    execution_time_seconds=0.0
                )
            
            # Check if file exists
            if not full_path.exists():
                return ToolResult(
                    success=False,
                    error=f"File not found: {file_path}",
                    execution_time_seconds=0.0
                )
            
            if not full_path.is_file():
                return ToolResult(
                    success=False,
                    error=f"Not a file: {file_path}",
                    execution_time_seconds=0.0
                )
            
            # Delete file
            await asyncio.to_thread(full_path.unlink)
            
            return ToolResult(
                success=True,
                output=f"Deleted {file_path}",
                execution_time_seconds=0.0,
                metadata={"file_path": file_path}
            )
        
        except Exception as e:
            return ToolResult(
                success=False,
                error=f"Error deleting file: {str(e)}",
                execution_time_seconds=0.0
            )
