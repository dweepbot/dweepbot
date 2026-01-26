"""
Plugin system for tools - dynamic loading and execution
"""
import abc
import asyncio
import inspect
import importlib
import pkgutil
import time
import uuid
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Callable, Set, Union, get_type_hints
from enum import Enum
from dataclasses import dataclass, field
from datetime import datetime
from pydantic import BaseModel, ValidationError, Field, validator

from ..core.types import ToolMetadata, ToolResult, ToolResultStatus
from ..utils.logger import get_logger
from ..utils.metrics import MetricsCollector

logger = get_logger(__name__)


class ToolCategory(Enum):
    """Categories for organizing tools"""
    FILE_SYSTEM = "file_system"
    NETWORK = "network"
    DATA_PROCESSING = "data_processing"
    AI_ML = "ai_ml"
    CODE = "code"
    UTILITY = "utility"
    SYSTEM = "system"
    COMMUNICATION = "communication"
    RESEARCH = "research"


class ToolCapability(Enum):
    """Capabilities that tools can have"""
    READ_ONLY = "read_only"            # No modifications
    WRITABLE = "writable"              # Can modify state
    DESTRUCTIVE = "destructive"        # Can delete or permanently change
    NETWORK = "network"                # Makes network calls
    EXPENSIVE = "expensive"            # High cost/resource usage
    FAST = "fast"                      # Low latency
    BATCHABLE = "batchable"            # Can process multiple items
    STREAMING = "streaming"            # Supports streaming output


@dataclass
class ToolExecutionContext:
    """Context for tool execution"""
    execution_id: str
    agent_id: Optional[str] = None
    workspace_path: Optional[str] = None
    user_id: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ToolValidationResult:
    """Result of tool validation"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class ToolPlugin(abc.ABC):
    """Base class for all tool plugins"""
    
    # Class-level configuration
    VERSION: str = "1.0.0"
    MINIMUM_AGENT_VERSION: Optional[str] = None
    REQUIRED_PACKAGES: List[str] = field(default_factory=list)
    
    def __init__(self):
        self.metrics = MetricsCollector(f"tool_{self.metadata.name}")
        self._execution_count = 0
        self._error_count = 0
        self._initialized = False
    
    @property
    @abc.abstractmethod
    def metadata(self) -> ToolMetadata:
        """Tool metadata for LLM"""
        pass
    
    @abc.abstractmethod
    async def execute(
        self, 
        context: ToolExecutionContext,
        **kwargs
    ) -> ToolResult:
        """Execute the tool with execution context"""
        pass
    
    async def initialize(self) -> bool:
        """
        Initialize the tool (load resources, connect, etc.)
        Called once before first execution.
        """
        if self._initialized:
            return True
        
        try:
            # Check for required packages
            for package in self.REQUIRED_PACKAGES:
                try:
                    importlib.import_module(package.split('.')[0])
                except ImportError:
                    logger.warning(f"Tool {self.metadata.name} requires package: {package}")
            
            await self._on_initialize()
            self._initialized = True
            logger.info(f"Tool initialized: {self.metadata.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize tool {self.metadata.name}: {e}")
            return False
    
    async def _on_initialize(self):
        """Override for custom initialization logic"""
        pass
    
    async def validate_input(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext] = None
    ) -> ToolValidationResult:
        """
        Validate tool inputs.
        
        Returns:
            ToolValidationResult with validation status
        """
        errors = []
        warnings = []
        suggestions = []
        
        try:
            # 1. Schema validation
            schema_result = await self._validate_schema(arguments)
            errors.extend(schema_result.errors)
            warnings.extend(schema_result.warnings)
            
            # 2. Security validation
            security_result = await self._validate_security(arguments, context)
            errors.extend(security_result.errors)
            warnings.extend(security_result.warnings)
            
            # 3. Business logic validation
            logic_result = await self._validate_business_logic(arguments, context)
            errors.extend(logic_result.errors)
            warnings.extend(logic_result.warnings)
            suggestions.extend(logic_result.suggestions)
            
            # 4. Resource validation
            resource_result = await self._validate_resources(arguments, context)
            errors.extend(resource_result.errors)
            warnings.extend(resource_result.warnings)
            
            valid = len(errors) == 0
            
            if not valid and len(errors) == 0 and len(warnings) > 0:
                # Only warnings, still valid
                valid = True
            
            return ToolValidationResult(
                valid=valid,
                errors=errors,
                warnings=warnings,
                suggestions=suggestions
            )
            
        except Exception as e:
            logger.error(f"Validation error for {self.metadata.name}: {e}")
            return ToolValidationResult(
                valid=False,
                errors=[f"Validation error: {str(e)}"]
            )
    
    async def _validate_schema(self, arguments: Dict[str, Any]) -> ToolValidationResult:
        """Validate against JSON schema"""
        errors = []
        warnings = []
        
        try:
            params_schema = self.metadata.parameters
            if "properties" in params_schema:
                # Check for unknown parameters
                schema_props = set(params_schema["properties"].keys())
                input_params = set(arguments.keys())
                
                unknown_params = input_params - schema_props
                if unknown_params:
                    warnings.append(f"Unknown parameters: {unknown_params}")
                
                # Check required parameters
                required_params = set(params_schema.get("required", []))
                missing_params = required_params - input_params
                if missing_params:
                    errors.append(f"Missing required parameters: {missing_params}")
                
                # Type checking (basic)
                for key, value in arguments.items():
                    if key in params_schema["properties"]:
                        prop_schema = params_schema["properties"][key]
                        expected_type = prop_schema.get("type")
                        
                        if expected_type:
                            type_valid = self._check_type(value, expected_type)
                            if not type_valid:
                                errors.append(
                                    f"Parameter '{key}' has wrong type. "
                                    f"Expected {expected_type}, got {type(value).__name__}"
                                )
            
            return ToolValidationResult(
                valid=len(errors) == 0,
                errors=errors,
                warnings=warnings
            )
            
        except Exception as e:
            return ToolValidationResult(
                valid=False,
                errors=[f"Schema validation error: {str(e)}"]
            )
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type"""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict
        }
        
        if expected_type not in type_map:
            return True  # Unknown type, skip check
        
        expected = type_map[expected_type]
        if isinstance(expected, tuple):
            return isinstance(value, expected)
        return isinstance(value, expected)
    
    async def _validate_security(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext]
    ) -> ToolValidationResult:
        """Validate security constraints"""
        errors = []
        warnings = []
        
        # Check for potentially dangerous patterns
        dangerous_patterns = [
            ("..", "directory traversal"),
            ("://", "URL in parameter"),
            ("<script>", "HTML injection"),
            ("${", "template injection"),
            ("exec(", "code execution"),
            ("eval(", "code execution"),
            ("system(", "system call"),
            ("subprocess", "subprocess call")
        ]
        
        for key, value in arguments.items():
            if isinstance(value, str):
                value_lower = value.lower()
                for pattern, description in dangerous_patterns:
                    if pattern in value_lower:
                        warnings.append(
                            f"Parameter '{key}' contains potential {description}: {value[:50]}..."
                        )
        
        # Check file paths if tool has file access
        if ToolCapability.WRITABLE.value in (c.value for c in self.metadata.capabilities):
            for key, value in arguments.items():
                if isinstance(value, str) and ("/" in value or "\\" in value):
                    # Check for path traversal
                    if ".." in value:
                        errors.append(
                            f"Parameter '{key}' contains path traversal: {value}"
                        )
        
        return ToolValidationResult(
            valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    async def _validate_business_logic(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext]
    ) -> ToolValidationResult:
        """Validate business logic constraints"""
        # Override in subclasses for tool-specific logic
        return ToolValidationResult(valid=True)
    
    async def _validate_resources(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext]
    ) -> ToolValidationResult:
        """Validate resource constraints"""
        # Override in subclasses for resource validation
        return ToolValidationResult(valid=True)
    
    async def rollback(
        self,
        execution_id: str,
        context: ToolExecutionContext
    ):
        """
        Rollback changes from a specific execution.
        Override for tools that modify state and need rollback.
        """
        logger.info(f"Rollback called for {self.metadata.name} execution {execution_id}")
        # Default implementation does nothing
    
    async def cleanup(self):
        """Cleanup resources when tool is unloaded"""
        try:
            await self._on_cleanup()
            logger.info(f"Tool cleaned up: {self.metadata.name}")
        except Exception as e:
            logger.error(f"Error cleaning up tool {self.metadata.name}: {e}")
    
    async def _on_cleanup(self):
        """Override for custom cleanup logic"""
        pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get tool statistics"""
        return {
            "name": self.metadata.name,
            "version": self.VERSION,
            "execution_count": self._execution_count,
            "error_count": self._error_count,
            "success_rate": (
                ((self._execution_count - self._error_count) / self._execution_count * 100)
                if self._execution_count > 0 else 0
            ),
            "metrics": self.metrics.get_summary()
        }
    
    def _record_execution(self, success: bool, duration: float):
        """Record execution metrics"""
        self._execution_count += 1
        if not success:
            self._error_count += 1
        
        self.metrics.record_execution(
            success=success,
            duration=duration
        )


class AsyncToolPlugin(ToolPlugin):
    """Base class for tools that need async initialization/cleanup"""
    
    async def initialize(self) -> bool:
        """Async initialization"""
        if self._initialized:
            return True
        
        try:
            # Check for required packages asynchronously
            for package in self.REQUIRED_PACKAGES:
                try:
                    importlib.import_module(package.split('.')[0])
                except ImportError as e:
                    logger.warning(f"Missing package {package} for tool {self.metadata.name}: {e}")
                    # Optionally install package here
            
            await self._async_on_initialize()
            self._initialized = True
            logger.info(f"Async tool initialized: {self.metadata.name}")
            return True
        except Exception as e:
            logger.error(f"Failed to initialize async tool {self.metadata.name}: {e}")
            return False
    
    async def _async_on_initialize(self):
        """Async initialization logic"""
        pass
    
    async def cleanup(self):
        """Async cleanup"""
        try:
            await self._async_on_cleanup()
            logger.info(f"Async tool cleaned up: {self.metadata.name}")
        except Exception as e:
            logger.error(f"Error cleaning up async tool {self.metadata.name}: {e}")
    
    async def _async_on_cleanup(self):
        """Async cleanup logic"""
        pass


class ToolRegistry:
    """
    Advanced registry for managing tool plugins.
    Supports dynamic loading, dependency resolution, and lifecycle management.
    """
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        self._tools: Dict[str, ToolPlugin] = {}
        self._tool_dependencies: Dict[str, Set[str]] = {}
        self._execution_history: List[Dict[str, Any]] = []
        self._cache: Dict[str, Dict] = {}
        self._config = config or {}
        self._initialized_tools: Set[str] = set()
        
        # Metrics
        self.metrics = MetricsCollector("tool_registry")
        
        # Cache configuration
        self._cache_config = {
            "max_size": self._config.get("cache_max_size", 1000),
            "ttl": self._config.get("cache_ttl", 300),  # 5 minutes
            "enabled": self._config.get("enable_cache", True)
        }
    
    def register(
        self, 
        tool: ToolPlugin,
        dependencies: Optional[List[str]] = None
    ):
        """Register a tool plugin with optional dependencies"""
        name = tool.metadata.name
        
        if name in self._tools:
            logger.warning(f"Tool {name} already registered, overwriting")
        
        self._tools[name] = tool
        self._tool_dependencies[name] = set(dependencies or [])
        
        # Check for missing dependencies
        missing_deps = self._tool_dependencies[name] - set(self._tools.keys())
        if missing_deps:
            logger.warning(f"Tool {name} has missing dependencies: {missing_deps}")
        
        logger.info(f"Registered tool: {name} (dependencies: {dependencies})")
    
    def unregister(self, name: str, cleanup: bool = True):
        """Unregister a tool with optional cleanup"""
        if name in self._tools:
            if cleanup:
                asyncio.create_task(self._tools[name].cleanup())
            
            # Remove from initialized set
            if name in self._initialized_tools:
                self._initialized_tools.remove(name)
            
            del self._tools[name]
            del self._tool_dependencies[name]
            logger.info(f"Unregistered tool: {name}")
    
    def get_tool(self, name: str) -> Optional[ToolPlugin]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self, category: Optional[str] = None) -> List[str]:
        """List all registered tool names, optionally filtered by category"""
        if category:
            return [
                name for name, tool in self._tools.items()
                if tool.metadata.category == category
            ]
        return list(self._tools.keys())
    
    def get_metadata(self, category: Optional[str] = None) -> List[ToolMetadata]:
        """Get metadata for all tools, optionally filtered by category"""
        if category:
            return [
                tool.metadata for tool in self._tools.values()
                if tool.metadata.category == category
            ]
        return [tool.metadata for tool in self._tools.values()]
    
    def get_openai_tools(self, category: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get tools in OpenAI function calling format"""
        if category:
            tools = [
                tool for tool in self._tools.values()
                if tool.metadata.category == category
            ]
        else:
            tools = self._tools.values()
        
        return [tool.metadata.to_openai_format() for tool in tools]
    
    def get_tools_by_capability(self, capability: str) -> List[str]:
        """Get tools that have a specific capability"""
        return [
            name for name, tool in self._tools.items()
            if capability in [c.value for c in tool.metadata.capabilities]
        ]
    
    async def initialize_tool(self, name: str) -> bool:
        """Initialize a specific tool"""
        tool = self.get_tool(name)
        if not tool:
            logger.error(f"Cannot initialize unknown tool: {name}")
            return False
        
        if name in self._initialized_tools:
            return True
        
        # Initialize dependencies first
        deps = self._tool_dependencies.get(name, set())
        for dep in deps:
            if dep in self._tools and dep not in self._initialized_tools:
                logger.info(f"Initializing dependency {dep} for {name}")
                if not await self.initialize_tool(dep):
                    logger.error(f"Failed to initialize dependency {dep} for {name}")
                    return False
        
        # Initialize the tool
        try:
            success = await tool.initialize()
            if success:
                self._initialized_tools.add(name)
                logger.info(f"Tool initialized successfully: {name}")
            else:
                logger.error(f"Tool initialization failed: {name}")
            
            return success
        except Exception as e:
            logger.error(f"Error initializing tool {name}: {e}")
            return False
    
    async def initialize_all(self) -> Dict[str, bool]:
        """Initialize all registered tools"""
        results = {}
        for name in self._tools:
            results[name] = await self.initialize_tool(name)
        return results
    
    async def execute(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
        validate: bool = True,
        use_cache: bool = True
    ) -> ToolResult:
        """
        Execute a tool with comprehensive validation and caching.
        
        Args:
            name: Tool name
            arguments: Tool arguments
            context: Execution context (agent_id, workspace, etc.)
            validate: Whether to validate inputs
            use_cache: Whether to use result caching
        
        Returns:
            ToolResult with execution outcome
        """
        execution_id = str(uuid.uuid4())
        start_time = time.time()
        
        # Create execution context
        exec_context = ToolExecutionContext(
            execution_id=execution_id,
            **{k: v for k, v in (context or {}).items() 
               if k in ToolExecutionContext.__dataclass_fields__}
        )
        
        tool = self.get_tool(name)
        if not tool:
            return ToolResult(
                status=ToolResultStatus.FAILURE,
                error=f"Tool not found: {name}",
                execution_id=execution_id
            )
        
        # Check cache
        cache_key = None
        if use_cache and self._cache_config["enabled"]:
            cache_key = self._create_cache_key(name, arguments, context)
            cached_result = self._get_from_cache(cache_key)
            if cached_result:
                logger.debug(f"Cache hit for tool {name}")
                return ToolResult(
                    status=ToolResultStatus.SUCCESS,
                    output=cached_result["result"],
                    execution_id=execution_id,
                    execution_time=time.time() - start_time,
                    cached=True,
                    metadata={"cache_hit": True}
                )
        
        # Ensure tool is initialized
        if name not in self._initialized_tools:
            logger.info(f"Auto-initializing tool: {name}")
            if not await self.initialize_tool(name):
                return ToolResult(
                    status=ToolResultStatus.FAILURE,
                    error=f"Tool initialization failed: {name}",
                    execution_id=execution_id,
                    execution_time=time.time() - start_time
                )
        
        # Validate inputs
        validation_result = None
        if validate:
            validation_result = await tool.validate_input(arguments, exec_context)
            if not validation_result.valid:
                logger.warning(f"Tool validation failed: {name}")
                return ToolResult(
                    status=ToolResultStatus.FAILURE,
                    error="Validation failed: " + "; ".join(validation_result.errors),
                    execution_id=execution_id,
                    execution_time=time.time() - start_time,
                    metadata={
                        "validation_errors": validation_result.errors,
                        "validation_warnings": validation_result.warnings
                    }
                )
        
        # Execute
        try:
            result = await tool.execute(exec_context, **arguments)
            result.execution_id = execution_id
            result.execution_time = time.time() - start_time
            
            # Add validation warnings if any
            if validation_result and validation_result.warnings:
                result.metadata = result.metadata or {}
                result.metadata["validation_warnings"] = validation_result.warnings
                result.metadata["validation_suggestions"] = validation_result.suggestions
            
            # Cache successful results
            if (use_cache and self._cache_config["enabled"] and 
                result.status == ToolResultStatus.SUCCESS and
                cache_key):
                self._add_to_cache(cache_key, result.output, context)
            
            # Track execution
            self._record_execution(
                name=name,
                arguments=arguments,
                context=exec_context,
                result=result,
                validation_result=validation_result
            )
            
            # Record tool metrics
            tool._record_execution(
                success=result.status == ToolResultStatus.SUCCESS,
                duration=result.execution_time
            )
            
            # Record registry metrics
            self.metrics.record_operation(
                operation="tool_execution",
                duration=result.execution_time,
                success=result.status == ToolResultStatus.SUCCESS
            )
            
            log_level = logger.info if result.success else logger.warning
            log_level(
                f"Tool executed: {name} -> {result.status} "
                f"({result.execution_time:.3f}s)"
            )
            
            return result
        
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(f"Tool execution failed: {name} - {e}", exc_info=True)
            
            # Record failure
            tool._record_execution(success=False, duration=execution_time)
            self.metrics.record_operation(
                operation="tool_execution",
                duration=execution_time,
                success=False
            )
            
            return ToolResult(
                status=ToolResultStatus.FAILURE,
                error=f"Execution error: {str(e)}",
                execution_id=execution_id,
                execution_time=execution_time
            )
    
    def _create_cache_key(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: Optional[Dict[str, Any]]
    ) -> str:
        """Create a cache key for tool execution"""
        # Create a deterministic string representation
        cache_data = {
            "tool": name,
            "arguments": arguments,
            "context": {k: v for k, v in (context or {}).items() 
                       if k not in ["execution_id", "timestamp"]}
        }
        
        cache_str = json.dumps(cache_data, sort_keys=True)
        return f"tool:{hashlib.md5(cache_str.encode()).hexdigest()}"
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict]:
        """Get result from cache if valid"""
        if cache_key not in self._cache:
            return None
        
        cached = self._cache[cache_key]
        cache_age = time.time() - cached["timestamp"]
        
        if cache_age < self._cache_config["ttl"]:
            return cached
        
        # Cache expired, remove it
        del self._cache[cache_key]
        return None
    
    def _add_to_cache(
        self,
        cache_key: str,
        result: Any,
        context: Optional[Dict[str, Any]]
    ):
        """Add result to cache"""
        # Check cache size
        if len(self._cache) >= self._cache_config["max_size"]:
            # Remove oldest entries (20% of cache)
            sorted_keys = sorted(
                self._cache.keys(),
                key=lambda k: self._cache[k]["timestamp"]
            )
            remove_count = max(1, int(len(self._cache) * 0.2))
            for key in sorted_keys[:remove_count]:
                del self._cache[key]
        
        self._cache[cache_key] = {
            "result": result,
            "timestamp": time.time(),
            "context": context
        }
    
    def clear_cache(self):
        """Clear the tool cache"""
        self._cache.clear()
        logger.info("Tool cache cleared")
    
    def _record_execution(
        self,
        name: str,
        arguments: Dict[str, Any],
        context: ToolExecutionContext,
        result: ToolResult,
        validation_result: Optional[ToolValidationResult]
    ):
        """Record execution in history"""
        self._execution_history.append({
            "execution_id": context.execution_id,
            "tool": name,
            "arguments": arguments,
            "context": {
                "agent_id": context.agent_id,
                "workspace": context.workspace_path,
                "session_id": context.session_id
            },
            "status": result.status,
            "execution_time": result.execution_time,
            "cached": getattr(result, 'cached', False),
            "validation_result": validation_result.dict() if validation_result else None,
            "timestamp": time.time()
        })
        
        # Keep history size manageable
        if len(self._execution_history) > 1000:
            self._execution_history = self._execution_history[-500:]
    
    def load_from_module(
        self,
        module_name: str,
        auto_initialize: bool = False
    ):
        """Load tools from a Python module"""
        try:
            module = importlib.import_module(module_name)
            
            # Find all ToolPlugin subclasses
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if (issubclass(obj, ToolPlugin) and 
                    obj != ToolPlugin and 
                    obj != AsyncToolPlugin):
                    
                    try:
                        # Check for dependencies attribute
                        dependencies = getattr(obj, 'DEPENDENCIES', [])
                        
                        # Instantiate and register
                        tool = obj()
                        self.register(tool, dependencies)
                        
                        logger.info(
                            f"Loaded tool from module {module_name}: {name} "
                            f"(dependencies: {dependencies})"
                        )
                        
                        # Auto-initialize if requested
                        if auto_initialize:
                            asyncio.create_task(self.initialize_tool(tool.metadata.name))
                    
                    except Exception as e:
                        logger.error(f"Failed to instantiate tool {name}: {e}")
        
        except Exception as e:
            logger.error(f"Failed to load module {module_name}: {e}")
    
    def load_from_directory(
        self,
        directory: Path,
        auto_initialize: bool = False
    ):
        """Load tools from a directory of Python files"""
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return
        
        # Add directory to path temporarily
        import sys
        original_sys_path = sys.path.copy()
        sys.path.insert(0, str(directory.parent))
        
        try:
            # Load all .py files
            for file in directory.glob("*.py"):
                if file.name.startswith("_"):
                    continue
                
                module_name = f"{directory.name}.{file.stem}"
                self.load_from_module(module_name, auto_initialize)
            
            # Also load from subdirectories
            for subdir in directory.iterdir():
                if subdir.is_dir() and not subdir.name.startswith("_"):
                    self.load_from_directory(subdir, auto_initialize)
        
        finally:
            # Restore original sys.path
            sys.path = original_sys_path
    
    def load_from_package(
        self,
        package_name: str,
        auto_initialize: bool = False
    ):
        """Load tools from a Python package"""
        try:
            package = importlib.import_module(package_name)
            
            # Find submodules
            for _, module_name, is_pkg in pkgutil.iter_modules(package.__path__):
                full_module_name = f"{package_name}.{module_name}"
                
                if is_pkg:
                    # Recursively load from subpackage
                    self.load_from_package(full_module_name, auto_initialize)
                else:
                    # Load from module
                    self.load_from_module(full_module_name, auto_initialize)
        
        except Exception as e:
            logger.error(f"Failed to load package {package_name}: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get comprehensive execution statistics"""
        if not self._execution_history:
            return {
                "total_executions": 0,
                "by_tool": {},
                "by_status": {},
                "cache_stats": self._get_cache_stats(),
                "registry_metrics": self.metrics.get_summary()
            }
        
        by_tool = {}
        by_status = {}
        total_time = 0.0
        
        for exec_data in self._execution_history:
            tool = exec_data["tool"]
            status = exec_data["status"]
            exec_time = exec_data["execution_time"]
            
            # By tool
            if tool not in by_tool:
                by_tool[tool] = {
                    "count": 0,
                    "total_time": 0.0,
                    "success_count": 0,
                    "error_count": 0,
                    "avg_time": 0.0
                }
            
            by_tool[tool]["count"] += 1
            by_tool[tool]["total_time"] += exec_time
            
            if status == ToolResultStatus.SUCCESS:
                by_tool[tool]["success_count"] += 1
            else:
                by_tool[tool]["error_count"] += 1
            
            # By status
            if status not in by_status:
                by_status[status] = 0
            by_status[status] += 1
            
            total_time += exec_time
        
        # Calculate averages
        for tool_stats in by_tool.values():
            if tool_stats["count"] > 0:
                tool_stats["avg_time"] = tool_stats["total_time"] / tool_stats["count"]
                tool_stats["success_rate"] = (
                    tool_stats["success_count"] / tool_stats["count"] * 100
                )
        
        return {
            "total_executions": len(self._execution_history),
            "total_time": total_time,
            "avg_time": total_time / len(self._execution_history),
            "by_tool": by_tool,
            "by_status": by_status,
            "initialized_tools": list(self._initialized_tools),
            "cache_stats": self._get_cache_stats(),
            "registry_metrics": self.metrics.get_summary()
        }
    
    def _get_cache_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        return {
            "size": len(self._cache),
            "max_size": self._cache_config["max_size"],
            "ttl": self._cache_config["ttl"],
            "enabled": self._cache_config["enabled"]
        }
    
    async def cleanup_all(self):
        """Cleanup all registered tools"""
        for name, tool in self._tools.items():
            try:
                await tool.cleanup()
            except Exception as e:
                logger.error(f"Error cleaning up tool {name}: {e}")
        
        self._initialized_tools.clear()
        logger.info("All tools cleaned up")


# Example tool implementations with enhanced features

class EchoTool(ToolPlugin):
    """Simple echo tool for testing"""
    
    VERSION = "2.0.0"
    REQUIRED_PACKAGES = []
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="echo",
            description="Echo back the input message. Useful for testing and debugging.",
            parameters={
                "type": "object",
                "properties": {
                    "message": {
                        "type": "string",
                        "description": "Message to echo back"
                    },
                    "repeat": {
                        "type": "integer",
                        "description": "Number of times to repeat the message",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 1
                    },
                    "format": {
                        "type": "string",
                        "description": "Output format",
                        "enum": ["plain", "json", "yaml"],
                        "default": "plain"
                    }
                },
                "required": ["message"]
            },
            category=ToolCategory.UTILITY.value,
            capabilities=[ToolCapability.FAST.value],
            version=self.VERSION
        )
    
    async def execute(
        self,
        context: ToolExecutionContext,
        message: str,
        repeat: int = 1,
        format: str = "plain",
        **kwargs
    ) -> ToolResult:
        """Execute echo with formatting"""
        try:
            # Process message
            repeated_message = "\n".join([message] * repeat)
            
            # Format output
            if format == "json":
                output = json.dumps({
                    "message": message,
                    "repeated": repeated_message,
                    "repeat_count": repeat,
                    "execution_id": context.execution_id
                }, indent=2)
            elif format == "yaml":
                import yaml
                output = yaml.dump({
                    "message": message,
                    "repeated": repeated_message,
                    "repeat_count": repeat,
                    "execution_id": context.execution_id
                }, default_flow_style=False)
            else:
                output = repeated_message
            
            return ToolResult(
                status=ToolResultStatus.SUCCESS,
                output=output,
                metadata={
                    "input_length": len(message),
                    "repeat_count": repeat,
                    "format": format
                }
            )
        
        except Exception as e:
            return ToolResult(
                status=ToolResultStatus.FAILURE,
                error=f"Echo failed: {str(e)}"
            )
    
    async def _validate_business_logic(
        self,
        arguments: Dict[str, Any],
        context: Optional[ToolExecutionContext]
    ) -> ToolValidationResult:
        """Add business logic validation"""
        errors = []
        suggestions = []
        
        message = arguments.get("message", "")
        repeat = arguments.get("repeat", 1)
        
        # Check message length
        if len(message) > 1000:
            suggestions.append("Message is very long, consider truncating")
        
        # Check repeat count
        if repeat > 5:
            suggestions.append(f"High repeat count ({repeat}), may produce large output")
        
        return ToolValidationResult(
            valid=True,
            errors=errors,
            suggestions=suggestions
        )


class CalculatorTool(ToolPlugin):
    """Advanced calculator tool with safe evaluation"""
    
    VERSION = "2.1.0"
    REQUIRED_PACKAGES = ["numpy"]
    
    # Safe operations and functions
    SAFE_FUNCTIONS = {
        # Math functions
        "abs": abs,
        "round": round,
        "min": min,
        "max": max,
        "sum": sum,
        "pow": pow,
        
        # Constants
        "pi": 3.141592653589793,
        "e": 2.718281828459045,
        
        # Comparison
        "sqrt": lambda x: x ** 0.5,
        "log": lambda x: __import__('math').log(x) if x > 0 else None,
        "log10": lambda x: __import__('math').log10(x) if x > 0 else None,
        "exp": lambda x: __import__('math').exp(x),
        "sin": lambda x: __import__('math').sin(x),
        "cos": lambda x: __import__('math').cos(x),
        "tan": lambda x: __import__('math').tan(x),
    }
    
    @property
    def metadata(self) -> ToolMetadata:
        return ToolMetadata(
            name="calculator",
            description=(
                "Perform mathematical calculations with support for basic operations, "
                "functions, and constants. Safe evaluation with no external dependencies."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "Mathematical expression (e.g., '2 + 2', 'sqrt(16)', 'sin(pi/2)')"
                    },
                    "precision": {
                        "type": "integer",
                        "description": "Decimal precision for result",
                        "minimum": 0,
                        "maximum": 10,
                        "default": 6
                    },
                    "format": {
                        "type":
