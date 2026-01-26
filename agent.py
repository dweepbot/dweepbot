"""
Main Autonomous Agent - Implements the PLAN → ACT → OBSERVE → REFLECT loop
"""
import asyncio
import time
import json
import hashlib
import uuid
from typing import Optional, List, AsyncGenerator, Dict, Any, Callable, Union
from datetime import datetime, timedelta
from dataclasses import asdict
from enum import Enum
import csv
from pathlib import Path

from ..core.types import (
    Plan, PlanStep, Message, Context, AgentState,
    TaskStatus, ToolResult, ToolResultStatus,
    ExecutionResult, AgentPhase
)
from ..core.planner import Planner, PlanningStrategy
from ..llm.client import DeepSeekClient
from ..tools.base import ToolRegistry, ToolMetadata
from ..memory.manager import MemoryManager
from ..utils.logger import get_logger
from ..utils.metrics import MetricsCollector

logger = get_logger(__name__)


class AgentMode(Enum):
    """Different modes the agent can operate in"""
    AUTONOMOUS = "autonomous"      # Full PLAN-ACT-OBSERVE loop
    ASSISTANT = "assistant"        # Chat with tool usage
    DEBUG = "debug"               # Debugging mode with verbose output
    VALIDATE = "validate"         # Planning validation only
    BITE_SIZED = "bite_sized"     # Quick, minimal planning for simple tasks


class AutonomousAgent:
    """
    Advanced autonomous agent that can plan, execute, observe, and reflect.
    
    Core loop:
    1. PLAN: Break down task into steps with strategy selection
    2. ACT: Execute tools or reason with monitoring
    3. OBSERVE: Process results and learn
    4. REFLECT: Update plan, adjust strategy, or request help
    
    Features:
    - Multiple planning strategies
    - Real-time monitoring
    - Checkpoint and resume
    - Tool usage optimization
    - Learning from past executions
    - Cost and resource management
    """
    
    def __init__(
        self,
        llm_client: DeepSeekClient,
        tool_registry: ToolRegistry,
        memory_manager: MemoryManager,
        context: Context,
        mode: AgentMode = AgentMode.AUTONOMOUS,
        callbacks: Optional[Dict[str, Callable]] = None,
        config: Optional[Dict[str, Any]] = None
    ):
        self.llm = llm_client
        self.tools = tool_registry
        self.memory = memory_manager
        self.context = context
        self.mode = mode
        self.callbacks = callbacks or {}
        self.config = config or {}
        
        # Set default config values
        self.config.setdefault("tool_cache_size", 100)
        self.config.setdefault("reasoning_temperature", 0.7)
        self.config.setdefault("planning_temperature", 0.3)
        self.config.setdefault("max_consecutive_errors", 3)
        self.config.setdefault("observation_history_size", 10)
        self.config.setdefault("enable_llm_caching", True)
        
        # Initialize planner with learning from memory
        # We'll initialize this properly when we have a task
        self.planner: Optional[Planner] = None
        
        # Agent state
        self.state = AgentState(context=context)
        self.state.agent_id = str(uuid.uuid4())[:8]
        
        # Execution tracking
        self.metrics = MetricsCollector(f"agent_{self.state.agent_id}")
        self.start_time = time.time()  # Use time.time() for consistency
        self.last_checkpoint = None
        self.last_activity = self.start_time
        
        # Caches for optimization
        self.tool_cache: Dict[str, Dict] = {}
        self.llm_cache: Dict[str, Dict] = {}
        
        # System prompt (will be created when needed)
        self.system_prompt: Optional[str] = None
        
        # Register event callbacks
        self._register_default_callbacks()
        
        logger.info(f"Agent initialized: {self.state.agent_id}, mode: {mode.value}")
    
    def _create_system_prompt(self, task: Optional[str] = None) -> str:
        """Create comprehensive system prompt with context"""
        tools_desc = self._create_tools_description()
        
        # Get memory insights safely
        try:
            memory_stats = self.memory.get_stats()
            successful_tasks = memory_stats.get("successful_tasks", 0)
        except Exception as e:
            logger.warning(f"Failed to get memory stats: {e}")
            successful_tasks = 0
        
        # Get common patterns from memory
        try:
            patterns = self.memory.get_common_patterns() or []
        except Exception as e:
            logger.warning(f"Failed to get memory patterns: {e}")
            patterns = []
        
        # Task-specific context if available
        task_context = ""
        if task:
            # Find similar tasks for context
            try:
                similar_tasks = self.memory.find_similar_tasks(task)
                if similar_tasks:
                    task_context = "\n## RELEVANT PAST TASKS:\n" + "\n".join([
                        f"- {t.get('goal', 'Unknown')[:50]}... (success: {t.get('success', False)})"
                        for t in similar_tasks[:2]
                    ])
            except Exception as e:
                logger.debug(f"Could not find similar tasks: {e}")
        
        prompt = f"""# 🦈 DweepBot Pro - Autonomous AI Agent
## Agent ID: {self.state.agent_id}
## Mode: {self.mode.value}

## CAPABILITIES:
You have access to {len(self.tools.list_tools())} tools:
{tools_desc}

## WORKSPACE:
- Path: {self.context.workspace_path}
- Memory: {successful_tasks} successful tasks in history

{task_context}

## OPERATING PRINCIPLES:
1. **Autonomy**: Take initiative, don't ask for permission to use tools
2. **Efficiency**: Minimize steps, cost, and time
3. **Adaptability**: Learn from observations and adjust plans
4. **Safety**: Respect limits and handle errors gracefully
5. **Transparency**: Log actions and reasoning clearly

## LIMITS (HARD CONSTRAINTS):
- Max iterations: {self.context.limits['max_iterations']}
- Max cost: ${self.context.limits['max_cost']:.4f}
- Max tool calls: {self.context.limits['max_tool_calls']}
- Max time: {self.context.limits.get('max_time_seconds', 3600)}s

## LEARNING FROM HISTORY:
Common successful patterns:
{chr(10).join(f'- {p}' for p in patterns[:3]) if patterns else '- No patterns yet'}

## INSTRUCTIONS:
- Break down complex tasks into clear, actionable steps
- Use tools proactively when they can help
- If stuck, try a different approach or ask for clarification
- Always validate results before proceeding
- Log observations for future learning

You are now ready to assist. Begin by analyzing the task and creating a plan."""
        
        return prompt
    
    def _create_tools_description(self) -> str:
        """Create detailed tools description for system prompt"""
        tools_desc = []
        all_tools = self.tools.get_metadata()
        
        # Group tools by category if available
        categories = {}
        for tool_meta in all_tools:
            category = getattr(tool_meta, 'category', 'general')
            categories.setdefault(category, []).append(tool_meta)
        
        for category, cat_tools in categories.items():
            tools_desc.append(f"\n### {category.upper()}:")
            for tool_meta in cat_tools:
                tools_desc.append(f"**{tool_meta.name}**")
                tools_desc.append(f"  - {tool_meta.description}")
                
                # Include common usage patterns from memory
                try:
                    usage_patterns = self.memory.get_tool_patterns(tool_meta.name)
                    if usage_patterns:
                        tools_desc.append(f"  - Common uses: {', '.join(usage_patterns[:2])}")
                except Exception:
                    pass  # Skip if we can't get patterns
                
                tools_desc.append("")
        
        return "\n".join(tools_desc)
    
    def _determine_planning_strategy(self, task: str) -> PlanningStrategy:
        """Determine planning strategy based on task and mode"""
        if self.mode == AgentMode.BITE_SIZED:
            return PlanningStrategy.STEP_BY_STEP
        
        if self.mode == AgentMode.DEBUG or self.mode == AgentMode.VALIDATE:
            return PlanningStrategy.DEBUGGING
        
        task_lower = task.lower()
        
        # Keyword-based strategy selection
        if any(word in task_lower for word in ["debug", "fix", "error", "issue", "problem"]):
            return PlanningStrategy.DEBUGGING
        
        if any(word in task_lower for word in ["explore", "research", "find", "investigate", "analyze"]):
            return PlanningStrategy.RESEARCH
        
        if any(word in task_lower for word in ["optimize", "improve", "speed up", "efficient"]):
            return PlanningStrategy.OPTIMIZATION
        
        if any(word in task_lower for word in ["creative", "design", "brainstorm", "ideas"]):
            return PlanningStrategy.EXPLORATORY
        
        # For bite-sized mode or simple tasks, use step-by-step
        if self.mode == AgentMode.BITE_SIZED or len(task) < 100:
            return PlanningStrategy.STEP_BY_STEP
        
        return PlanningStrategy.STEP_BY_STEP
    
    def _register_default_callbacks(self):
        """Register default event callbacks"""
        default_callbacks = {
            "on_phase_change": self._on_phase_change,
            "on_tool_call": self._on_tool_call,
            "on_observation": self._on_observation,
            "on_limit_warning": self._on_limit_warning,
            "on_error": self._on_error,
            "on_checkpoint": self._on_checkpoint,
            "on_replan": self._on_replan,
            "on_complete": self._on_complete,
        }
        
        for name, callback in default_callbacks.items():
            if name not in self.callbacks:
                self.callbacks[name] = callback
    
    async def run(
        self,
        task: str,
        stream: bool = True,
        max_iterations: Optional[int] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run autonomous agent on a task with full planning loop.
        
        Args:
            task: The task description
            stream: Whether to stream updates
            max_iterations: Override context iterations limit
        
        Yields:
            Progress updates, results, and status
        
        Example:
            ```python
            agent = AutonomousAgent(...)
            async for update in agent.run("Write a hello world program"):
                print(update)
            ```
        """
        
        logger.info(f"Starting {self.mode.value} run for task: {task[:100]}...")
        
        # Update limits if provided
        if max_iterations:
            self.context.limits["max_iterations"] = max_iterations
        
        # Initialize agent state
        self.state.phase = AgentPhase.INITIALIZING
        self._trigger_callback("on_phase_change", self.state.phase)
        
        # Store task in memory
        self.memory.add_message(Message(role="user", content=task))
        self.state.task = task
        
        # Create system prompt with task context
        self.system_prompt = self._create_system_prompt(task)
        
        # Initialize planner with similar tasks
        similar_tasks = []
        try:
            similar_tasks = self.memory.find_similar_tasks(task)
            logger.debug(f"Found {len(similar_tasks)} similar tasks in memory")
        except Exception as e:
            logger.warning(f"Failed to find similar tasks: {e}")
        
        self.planner = Planner(
            llm_client=self.llm,
            tools_metadata=self.tools.get_openai_tools(),
            default_strategy=self._determine_planning_strategy(task)
        )
        
        # Yield initialization status
        if stream:
            yield await self._create_update("init", {
                "task": task,
                "agent_id": self.state.agent_id,
                "mode": self.mode.value,
                "limits": self.context.limits,
                "similar_tasks_count": len(similar_tasks)
            })
        
        try:
            # Handle different modes
            if self.mode == AgentMode.ASSISTANT:
                # Assistant mode: chat with tools, no planning
                async for update in self._run_assistant_mode(task, stream):
                    yield update
                return
            
            elif self.mode == AgentMode.BITE_SIZED:
                # Bite-sized mode: quick execution
                async for update in self._run_bite_sized_mode(task, stream):
                    yield update
                return
            
            # AUTONOMOUS, DEBUG, VALIDATE modes use full planning
            
            # PHASE 1: Planning
            self.state.phase = AgentPhase.PLANNING
            self._trigger_callback("on_phase_change", self.state.phase)
            
            if stream:
                yield await self._create_update("planning", {"status": "Creating execution plan..."})
            
            # Create plan
            previous_attempts = [t.get("attempts", []) for t in similar_tasks[:2]] if similar_tasks else []
            
            plan = await self.planner.create_plan(
                goal=task,
                context=self.context,
                previous_attempts=previous_attempts
            )
            self.state.plan = plan
            
            if stream:
                yield await self._create_update("plan_created", {
                    "plan": plan.dict(),
                    "strategy": plan.strategy,
                    "step_count": len(plan.steps)
                })
            
            # PHASE 2: Main execution loop
            execution_start = time.time()
            
            while not self._should_stop_execution():
                self.state.phase = AgentPhase.EXECUTING
                self._trigger_callback("on_phase_change", self.state.phase)
                
                # Check limits
                limit_check = self._check_all_limits()
                if limit_check["should_stop"]:
                    if stream:
                        yield await self._create_update("limit_reached", {
                            "reason": limit_check["reason"],
                            "limits": self._get_current_limits()
                        })
                    break
                
                # Emit any warnings
                if limit_check.get("warnings"):
                    for warning in limit_check["warnings"]:
                        if stream:
                            yield await self._create_update("warning", {"message": warning})
                
                # Get next step
                step = plan.get_current_step()
                if not step:
                    logger.info("No more steps in plan")
                    break
                
                # Log step start
                step_start = time.time()
                logger.info(f"Executing step {plan.current_step + 1}/{len(plan.steps)}: {step.description}")
                
                if stream:
                    yield await self._create_update("step_start", {
                        "step_number": plan.current_step + 1,
                        "total_steps": len(plan.steps),
                        "step": step.dict()
                    })
                
                # Execute step
                try:
                    execution_result = await self._execute_step(step, plan)
                    
                    # Track metrics
                    self.metrics.record_step(
                        step_id=step.id,
                        duration=time.time() - step_start,
                        success=execution_result.success,
                        tool_used=step.tool_name
                    )
                    
                    # Update state
                    self.state.iteration += 1
                    self.state.total_cost += execution_result.cost
                    self.last_activity = time.time()
                    
                    if execution_result.tool_used:
                        self.state.total_tool_calls += 1
                    
                    # Add observation
                    observation = self._create_observation(step, execution_result)
                    self.state.add_observation(observation)
                    self._trigger_callback("on_observation", observation)
                    
                    # Yield result
                    if stream:
                        yield await self._create_update("step_result", {
                            "step": step.dict(),
                            "result": execution_result.dict(),
                            "observation": observation
                        })
                    
                    # Handle step result
                    if not execution_result.success:
                        self.state.consecutive_errors += 1
                        
                        # Check if too many consecutive errors
                        if self.state.consecutive_errors >= self.config["max_consecutive_errors"]:
                            logger.warning("Too many consecutive errors, triggering replan")
                            self.state.phase = AgentPhase.REPLANNING
                            break
                    else:
                        self.state.consecutive_errors = 0
                    
                    # Check if step indicates replanning needed
                    if execution_result.needs_replan:
                        logger.info("Step indicates replanning needed")
                        self.state.phase = AgentPhase.REPLANNING
                        break
                    
                    # Mark step as complete
                    step.status = TaskStatus.COMPLETED if execution_result.success else TaskStatus.FAILED
                    step.result = execution_result
                    
                    # Check if plan is complete
                    if plan.is_complete():
                        self.state.phase = AgentPhase.COMPLETED
                        break
                    
                    # Move to next step
                    plan.advance()
                    
                    # Periodically checkpoint
                    if self.state.iteration % 5 == 0:
                        await self._create_checkpoint()
                
                except Exception as e:
                    logger.error(f"Step execution failed: {e}", exc_info=True)
                    self.state.add_error(str(e))
                    self._trigger_callback("on_error", str(e))
                    
                    if stream:
                        yield await self._create_update("step_error", {
                            "step": step.dict(),
                            "error": str(e)
                        })
                    
                    self.state.consecutive_errors += 1
                
                # PHASE 3: Reflection and replanning (if needed)
                if self._should_replan(plan):
                    await self._handle_replanning(plan, stream)
                    if self.state.phase == AgentPhase.REPLANNING:
                        continue  # New plan, restart loop
            
            # PHASE 4: Completion
            execution_time = time.time() - execution_start
            
            if plan.is_complete() or self.state.phase == AgentPhase.COMPLETED:
                await self._handle_completion(task, plan, execution_time, stream)
            
            else:
                await self._handle_stopped(execution_time, stream)
        
        except Exception as e:
            await self._handle_failure(e, stream)
        
        finally:
            # Final metrics and cleanup
            await self._finalize_execution(stream)
    
    async def _run_assistant_mode(self, task: str, stream: bool) -> AsyncGenerator[Dict[str, Any], None]:
        """Run in assistant mode (chat with tools, no planning)"""
        yield await self._create_update("assistant_mode", {
            "status": "Running in assistant mode",
            "task": task
        })
        
        # Add system message
        self.state.add_message(Message(role="system", content=self.system_prompt))
        
        # Process task as a chat message
        async for update in self._process_chat_message(task, stream):
            yield update
    
    async def _run_bite_sized_mode(self, task: str, stream: bool) -> AsyncGenerator[Dict[str, Any], None]:
        """Run in bite-sized mode (quick execution for simple tasks)"""
        yield await self._create_update("bite_sized_mode", {
            "status": "Running in bite-sized mode",
            "task": task
        })
        
        # Create a simple one-step plan
        plan = Plan(
            goal=task,
            steps=[
                PlanStep(
                    id="bite_sized_step",
                    description=f"Complete task: {task}",
                    action_type="tool_call",
                    tool_name=self._select_appropriate_tool(task),
                    arguments={"task": task},
                    expected_outcome="Task completed quickly"
                )
            ],
            strategy="bite_sized"
        )
        
        self.state.plan = plan
        
        # Execute the single step
        step = plan.steps[0]
        execution_result = await self._execute_tool_step(step)
        
        yield await self._create_update("bite_sized_result", {
            "success": execution_result.success,
            "output": execution_result.output,
            "error": execution_result.error
        })
    
    def _select_appropriate_tool(self, task: str) -> str:
        """Select the most appropriate tool for a simple task"""
        task_lower = task.lower()
        
        # Simple heuristic for tool selection
        if any(word in task_lower for word in ["write", "create", "file"]):
            for tool_name in ["write_file", "create_file", "file_write"]:
                if tool_name in self.tools.list_tools():
                    return tool_name
        
        if any(word in task_lower for word in ["read", "open", "file"]):
            for tool_name in ["read_file", "file_read", "open_file"]:
                if tool_name in self.tools.list_tools():
                    return tool_name
        
        # Default to first available tool
        available_tools = self.tools.list_tools()
        return available_tools[0] if available_tools else ""
    
    async def _process_chat_message(
        self,
        message: str,
        stream: bool
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Process a chat message with tool usage"""
        # Add user message
        self.state.add_message(Message(role="user", content=message))
        
        # Get response from LLM with tool support
        messages = self.state.get_recent_messages(10)  # Get last 10 messages
        tools = self.tools.get_openai_tools()
        
        try:
            response = await self.llm.create_completion(
                messages=messages,
                tools=tools,
                temperature=0.7,
                max_tokens=2048
            )
            
            message_content = response["choices"][0]["message"]
            
            # Add assistant response to state
            self.state.add_message(Message(
                role="assistant",
                content=message_content.get("content", "")
            ))
            
            # Yield the response
            if stream:
                if message_content.get("content"):
                    yield await self._create_update("assistant_response", {
                        "content": message_content["content"]
                    })
            
            # Handle tool calls if any
            if message_content.get("tool_calls"):
                for tool_call in message_content["tool_calls"]:
                    tool_name = tool_call["function"]["name"]
                    tool_args = json.loads(tool_call["function"]["arguments"])
                    
                    yield await self._create_update("tool_call", {
                        "tool": tool_name,
                        "arguments": tool_args
                    })
                    
                    # Execute tool
                    result = await self.tools.execute(tool_name, tool_args)
                    
                    # Add tool result to conversation
                    tool_result_msg = Message(
                        role="tool",
                        content=result.output if result.success else f"Error: {result.error}",
                        tool_call_id=tool_call.get("id")
                    )
                    self.state.add_message(tool_result_msg)
                    
                    yield await self._create_update("tool_result", {
                        "tool": tool_name,
                        "success": result.success,
                        "output": result.output,
                        "error": result.error
                    })
                    
                    # Continue conversation with tool result
                    # (In a full implementation, you might want to get another LLM response here)
        
        except Exception as e:
            logger.error(f"Chat processing failed: {e}")
            yield await self._create_update("chat_error", {"error": str(e)})
    
    async def _execute_step(self, step: PlanStep, plan: Plan) -> ExecutionResult:
        """Execute a single plan step"""
        logger.debug(f"Executing step: {step.description}")
        
        try:
            if step.action_type == "tool_call":
                return await self._execute_tool_step(step)
            elif step.action_type == "reasoning":
                return await self._execute_reasoning_step(step, plan)
            elif step.action_type == "clarification":
                result = await self._execute_clarification_step(step)
                # Check if clarification indicates replanning needed
                if result.metadata.get("needs_replan"):
                    result.needs_replan = True
                return result
            else:
                return ExecutionResult(
                    success=False,
                    error=f"Unknown action type: {step.action_type}"
                )
        except Exception as e:
            logger.error(f"Step execution error: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error=f"Execution error: {str(e)}",
                tool_used=step.tool_name if step.action_type == "tool_call" else None
            )
    
    async def _execute_tool_step(self, step: PlanStep) -> ExecutionResult:
        """Execute a tool call step with caching"""
        if not step.tool_name:
            return ExecutionResult(
                success=False,
                error="Tool step missing tool name"
            )
        
        # Create cache key using hashed arguments
        args_str = json.dumps(step.arguments, sort_keys=True)
        cache_key = f"{step.tool_name}:{self._hash_string(args_str)}"
        
        # Check cache
        if cache_key in self.tool_cache:
            cached_result = self.tool_cache[cache_key]
            cache_age = time.time() - cached_result.get("timestamp", 0)
            cache_ttl = self.context.limits.get("tool_cache_ttl", 300)  # 5 minutes default
            
            if cache_age < cache_ttl:
                logger.debug(f"Using cached tool result for {step.tool_name}")
                return ExecutionResult(
                    success=True,
                    output=cached_result["result"],
                    tool_used=step.tool_name,
                    cost=0,  # Cached results don't incur cost
                    cached=True,
                    metadata={"cache_hit": True, "cache_age": cache_age}
                )
        
        # Trigger callback
        self._trigger_callback("on_tool_call", {
            "tool": step.tool_name,
            "arguments": step.arguments,
            "step": step.description
        })
        
        try:
            # Execute tool
            tool_result = await self.tools.execute(step.tool_name, step.arguments)
            
            # Cache successful results
            if tool_result.status == ToolResultStatus.SUCCESS:
                self.tool_cache[cache_key] = {
                    "result": tool_result.output,
                    "timestamp": time.time()
                }
                
                # Manage cache size with configurable limit
                max_cache_size = self.context.limits.get("max_cache_size", self.config["tool_cache_size"])
                if len(self.tool_cache) > max_cache_size:
                    # Remove oldest entries (20% of cache)
                    sorted_keys = sorted(
                        self.tool_cache.keys(),
                        key=lambda k: self.tool_cache[k]["timestamp"]
                    )
                    remove_count = max(1, int(len(self.tool_cache) * 0.2))
                    for key in sorted_keys[:remove_count]:
                        del self.tool_cache[key]
            
            return ExecutionResult(
                success=tool_result.status == ToolResultStatus.SUCCESS,
                output=tool_result.output,
                error=tool_result.error,
                tool_used=step.tool_name,
                cost=tool_result.cost or 0,
                metadata={
                    "tool_result": tool_result.dict(),
                    "cache_hit": False,
                    "cached": tool_result.status == ToolResultStatus.SUCCESS
                }
            )
        
        except Exception as e:
            logger.error(f"Tool execution failed: {e}", exc_info=True)
            return ExecutionResult(
                success=False,
                error=f"Tool execution error: {str(e)}",
                tool_used=step.tool_name
            )
    
    def _hash_string(self, text: str) -> str:
        """Create a hash of a string for cache keys"""
        return hashlib.md5(text.encode()).hexdigest()[:12]
    
    async def _execute_reasoning_step(self, step: PlanStep, plan: Plan) -> ExecutionResult:
        """Execute a reasoning step using LLM with optional caching"""
        # Build context for reasoning
        messages = [
            Message(role="system", content=self.system_prompt),
            Message(role="user", content=f"Task: {plan.goal}"),
            Message(role="user", content=f"Current step to reason about: {step.description}")
        ]
        
        # Add recent observations for context
        if self.state.observations:
            messages.append(Message(
                role="system",
                content=f"Recent observations:\n" + "\n".join(f"- {obs}" for obs in self.state.observations[-3:])
            ))
        
        # Create cache key for LLM call
        cache_key = None
        if self.config["enable_llm_caching"]:
            messages_str = json.dumps([m.dict() for m in messages], sort_keys=True)
            cache_key = f"reasoning:{self._hash_string(messages_str)}:{self.config['reasoning_temperature']}"
            
            if cache_key in self.llm_cache:
                cached = self.llm_cache[cache_key]
                logger.debug("Using cached LLM reasoning result")
                return ExecutionResult(
                    success=True,
                    output=cached["content"],
                    cost=0,  # Cached, no cost
                    cached=True,
                    metadata=cached.get("metadata", {})
                )
        
        try:
            # Get reasoning from LLM
            response = await self.llm.create_completion(
                messages=messages,
                temperature=self.config["reasoning_temperature"],
                max_tokens=1024
            )
            
            content = response["choices"][0]["message"]["content"]
            
            # Track cost
            usage = response.get("usage", {})
            cost = self.llm.calculate_cost(
                input_tokens=usage.get("prompt_tokens", 0),
                output_tokens=usage.get("completion_tokens", 0)
            )
            
            # Cache the result
            if cache_key and self.config["enable_llm_caching"]:
                self.llm_cache[cache_key] = {
                    "content": content,
                    "timestamp": time.time(),
                    "metadata": {"tokens": usage}
                }
                
                # Manage LLM cache size
                if len(self.llm_cache) > 50:  # Smaller cache for LLM responses
                    sorted_keys = sorted(
                        self.llm_cache.keys(),
                        key=lambda k: self.llm_cache[k]["timestamp"]
                    )
                    for key in sorted_keys[:10]:
                        del self.llm_cache[key]
            
            # Store reasoning in memory
            self.memory.add_message(Message(
                role="assistant",
                content=f"Reasoning for '{step.description}': {content}"
            ))
            
            return ExecutionResult(
                success=True,
                output=content,
                cost=cost,
                metadata={
                    "reasoning": content,
                    "tokens": usage,
                    "cache_hit": cache_key in self.llm_cache if cache_key else False
                }
            )
        
        except Exception as e:
            logger.error(f"Reasoning step failed: {e}")
            return ExecutionResult(
                success=False,
                error=f"Reasoning error: {str(e)}"
            )
    
    async def _execute_clarification_step(self, step: PlanStep) -> ExecutionResult:
        """Handle clarification needed from user"""
        # In autonomous mode, try to infer from memory or continue with best guess
        if self.mode == AgentMode.AUTONOMOUS:
            # Try to infer from similar tasks in memory
            similar_tasks = self.memory.find_similar_tasks(step.description)
            if similar_tasks:
                logger.info(f"Inferred clarification from {len(similar_tasks)} similar tasks")
                # Use the most common approach from similar tasks
                return ExecutionResult(
                    success=True,
                    output=f"Inferred approach from similar tasks",
                    metadata={"clarification_inferred": True}
                )
        
        # If we can't infer, mark as needing replan
        clarification_need = step.metadata.get("questions", ["Need clarification to proceed"])
        
        return ExecutionResult(
            success=False,
            output="Clarification needed",
            error=f"Awaiting user input: {clarification_need}",
            needs_replan=True,
            metadata={
                "clarification_needed": clarification_need,
                "suggested_action": "request_user_input"
            }
        )
    
    async def _handle_replanning(self, plan: Plan, stream: bool):
        """Handle replanning logic"""
        self.state.phase = AgentPhase.REPLANNING
        self._trigger_callback("on_phase_change", self.state.phase)
        self._trigger_callback("on_replan", {
            "current_step": plan.current_step,
            "observations": self.state.observations[-5:],
            "errors": self.state.consecutive_errors
        })
        
        if stream:
            yield await self._create_update("replanning", {
                "reason": "Observations suggest plan adjustment needed",
                "observations": self.state.observations[-5:],
                "consecutive_errors": self.state.consecutive_errors
            })
        
        try:
            execution_stats = {
                "iterations": self.state.iteration,
                "total_cost": self.state.total_cost,
                "total_tool_calls": self.state.total_tool_calls,
                "observations": self.state.observations,
                "errors": self.state.get_errors()
            }
            
            new_plan = await self.planner.replan(
                plan,
                self.state.observations,
                execution_stats
            )
            
            if new_plan and new_plan != plan:
                # Archive old observations before clearing
                self._archive_observations(plan)
                
                # Update plan
                plan = new_plan
                self.state.plan = plan
                
                # Keep only recent observations for context
                self.state.observations = self.state.observations[
                    -self.config["observation_history_size"]:
                ] if self.state.observations else []
                
                if stream:
                    yield await self._create_update("plan_updated", {
                        "plan": plan.dict(),
                        "reason": "Plan adjusted based on observations",
                        "observations_archived": True
                    })
            
            self.state.phase = AgentPhase.EXECUTING
            
        except Exception as e:
            logger.error(f"Replanning failed: {e}")
            self.state.add_error(f"Replanning failed: {e}")
            # Continue with current plan
    
    def _archive_observations(self, plan: Plan):
        """Archive observations to memory before clearing"""
        if self.state.observations:
            try:
                self.memory.add_observations(
                    task_id=plan.goal,
                    observations=self.state.observations,
                    step=plan.current_step
                )
                logger.debug(f"Archived {len(self.state.observations)} observations to memory")
            except Exception as e:
                logger.warning(f"Failed to archive observations: {e}")
    
    async def _handle_completion(self, task: str, plan: Plan, execution_time: float, stream: bool):
        """Handle task completion"""
        self.state.phase = AgentPhase.COMPLETED
        self._trigger_callback("on_phase_change", self.state.phase)
        self._trigger_callback("on_complete", {
            "task": task,
            "execution_time": execution_time,
            "iterations": self.state.iteration
        })
        
        # Learn from success
        try:
            self.memory.learn_from_success(task, plan.dict())
        except Exception as e:
            logger.warning(f"Failed to learn from success: {e}")
        
        if stream:
            yield await self._create_update("completed", {
                "success": True,
                "execution_time": execution_time,
                "summary": self._create_execution_summary(plan)
            })
    
    async def _handle_stopped(self, execution_time: float, stream: bool):
        """Handle stopped execution"""
        self.state.phase = AgentPhase.STOPPED
        self._trigger_callback("on_phase_change", self.state.phase)
        
        if stream:
            yield await self._create_update("stopped", {
                "success": False,
                "execution_time": execution_time,
                "reason": "Execution stopped before completion",
                "errors": self.state.get_errors(),
                "limits": self._get_current_limits()
            })
    
    async def _handle_failure(self, error: Exception, stream: bool):
        """Handle execution failure"""
        logger.error(f"Agent execution failed: {error}", exc_info=True)
        self.state.phase = AgentPhase.FAILED
        self._trigger_callback("on_phase_change", self.state.phase)
        self._trigger_callback("on_error", str(error))
        
        if stream:
            yield await self._create_update("failed", {
                "error": str(error),
                "errors": self.state.get_errors(),
                "phase": self.state.phase.value
            })
    
    async def _finalize_execution(self, stream: bool):
        """Finalize execution with metrics and cleanup"""
        self.metrics.record_session(
            success=self.state.phase == AgentPhase.COMPLETED,
            duration=time.time() - self.start_time
        )
        
        # Export metrics if configured
        if self.config.get("export_metrics"):
            await self._export_metrics()
        
        if stream:
            yield await self._create_update("metrics", self.metrics.get_summary())
    
    async def _export_metrics(self):
        """Export metrics to file"""
        try:
            metrics_data = self.metrics.get_summary()
            export_path = Path(self.context.workspace_path) / "metrics"
            export_path.mkdir(exist_ok=True)
            
            # Export as JSON
            json_path = export_path / f"metrics_{self.state.agent_id}.json"
            with open(json_path, 'w') as f:
                json.dump(metrics_data, f, indent=2)
            
            # Export as CSV (flattened)
            csv_path = export_path / f"metrics_{self.state.agent_id}.csv"
            self._export_metrics_to_csv(metrics_data, csv_path)
            
            logger.info(f"Metrics exported to {json_path} and {csv_path}")
        except Exception as e:
            logger.warning(f"Failed to export metrics: {e}")
    
    def _export_metrics_to_csv(self, metrics_data: Dict[str, Any], filepath: Path):
        """Export metrics to CSV format"""
        # Flatten metrics data
        rows = []
        
        # Session metrics
        session = metrics_data.get("session", {})
        rows.append(["category", "metric", "value"])
        rows.append(["session", "duration", session.get("duration")])
        rows.append(["session", "success", session.get("success")])
        rows.append(["session", "start_time", session.get("start_time")])
        
        # Step metrics
        for step in metrics_data.get("steps", []):
            rows.append(["step", "id", step.get("id")])
            rows.append(["step", "duration", step.get("duration")])
            rows.append(["step", "success", step.get("success")])
            rows.append(["step", "tool_used", step.get("tool_used")])
        
        # Write CSV
        with open(filepath, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
    
    def _create_observation(self, step: PlanStep, result: ExecutionResult) -> str:
        """Create an observation from step execution result"""
        if result.success:
            if result.tool_used:
                return f"Tool '{result.tool_used}' succeeded: {result.output[:100]}..."
            else:
                return f"Reasoning completed: {result.output[:100]}..."
        else:
            if result.tool_used:
                return f"Tool '{result.tool_used}' failed: {result.error}"
            else:
                return f"Reasoning failed: {result.error}"
    
    def _should_stop_execution(self) -> bool:
        """Determine if execution should stop"""
        if self.state.phase in [AgentPhase.COMPLETED, AgentPhase.FAILED, AgentPhase.STOPPED]:
            return True
        
        if self.state.iteration >= self.context.limits["max_iterations"]:
            return True
        
        elapsed = time.time() - self.start_time
        max_time = self.context.limits.get("max_time_seconds", 3600)
        if elapsed > max_time:
            return True
        
        return False
    
    def _should_replan(self, plan: Plan) -> bool:
        """Determine if replanning is needed"""
        # Replan if we have observations suggesting issues
        if len(self.state.observations) >= 5:
            # Check last few observations for failures
            recent_failures = sum(1 for obs in self.state.observations[-3:] if "failed" in obs.lower())
            if recent_failures >= 2:
                return True
        
        # Replan if we've made no progress for several steps
        if self.state.iteration > 10 and plan.current_step < 3:
            return True
        
        # Replan if we're approaching limits
        max_iterations = self.context.limits["max_iterations"]
        if max_iterations > 0 and self.state.iteration >= max_iterations * 0.8:
            return True
        
        return False
    
    def _check_all_limits(self) -> Dict[str, Any]:
        """Check all execution limits with proper division safety"""
        limits = self.context.limits
        should_stop = False
        reason = ""
        warnings = []
        
        # Check iteration limit
        max_iterations = limits["max_iterations"]
        if max_iterations > 0 and self.state.iteration >= max_iterations:
            should_stop = True
            reason = f"Reached max iterations ({self.state.iteration}/{max_iterations})"
        
        # Check cost limit
        max_cost = limits["max_cost"]
        if max_cost > 0 and self.state.total_cost >= max_cost:
            should_stop = True
            reason = f"Reached max cost (${self.state.total_cost:.4f}/${max_cost})"
        
        # Check tool call limit
        max_tool_calls = limits["max_tool_calls"]
        if max_tool_calls > 0 and self.state.total_tool_calls >= max_tool_calls:
            should_stop = True
            reason = f"Reached max tool calls ({self.state.total_tool_calls}/{max_tool_calls})"
        
        # Check time limit
        elapsed = time.time() - self.start_time
        max_time = limits.get("max_time_seconds", 3600)
        if max_time > 0 and elapsed >= max_time:
            should_stop = True
            reason = f"Reached time limit ({elapsed:.1f}s/{max_time}s)"
        
        # Generate warnings (avoid division by zero)
        if not should_stop:
            if max_iterations > 0 and self.state.iteration >= max_iterations * 0.9:
                warnings.append(f"Approaching iteration limit: {self.state.iteration}/{max_iterations}")
            
            if max_cost > 0 and self.state.total_cost >= max_cost * 0.9:
                warnings.append(f"Approaching cost limit: ${self.state.total_cost:.4f}/${max_cost}")
            
            if max_tool_calls > 0 and self.state.total_tool_calls >= max_tool_calls * 0.9:
                warnings.append(f"Approaching tool call limit: {self.state.total_tool_calls}/{max_tool_calls}")
            
            if max_time > 0 and elapsed >= max_time * 0.9:
                warnings.append(f"Approaching time limit: {elapsed:.1f}s/{max_time}s")
        
        return {
            "should_stop": should_stop,
            "reason": reason,
            "warnings": warnings
        }
    
    def _get_current_limits(self) -> Dict[str, Any]:
        """Get current limit usage with safe division"""
        limits = self.context.limits
        elapsed = time.time() - self.start_time
        
        def safe_percent(current, maximum):
            if maximum <= 0:
                return 0
            return (current / maximum) * 100
        
        return {
            "iterations": {
                "current": self.state.iteration,
                "max": limits["max_iterations"],
                "percent": safe_percent(self.state.iteration, limits["max_iterations"])
            },
            "cost": {
                "current": self.state.total_cost,
                "max": limits["max_cost"],
                "percent": safe_percent(self.state.total_cost, limits["max_cost"])
            },
            "tool_calls": {
                "current": self.state.total_tool_calls,
                "max": limits["max_tool_calls"],
                "percent": safe_percent(self.state.total_tool_calls, limits["max_tool_calls"])
            },
            "time": {
                "current": elapsed,
                "max": limits.get("max_time_seconds", 3600),
                "percent": safe_percent(elapsed, limits.get("max_time_seconds", 3600))
            }
        }
    
    async def _create_checkpoint(self):
        """Create a checkpoint of agent state"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.state.agent_id,
            "phase": self.state.phase.value,
            "iteration": self.state.iteration,
            "plan": self.state.plan.dict() if self.state.plan else None,
            "observations": self.state.observations[-self.config["observation_history_size"]:],
            "limits": self._get_current_limits(),
            "metrics": self.metrics.get_summary()
        }
        
        self.last_checkpoint = checkpoint
        self._trigger_callback("on_checkpoint", checkpoint)
        
        # Save to memory
        try:
            self.memory.save_checkpoint(checkpoint)
            logger.debug(f"Checkpoint created at iteration {self.state.iteration}")
        except Exception as e:
            logger.warning(f"Failed to save checkpoint to memory: {e}")
    
    def _create_execution_summary(self, plan: Plan) -> Dict[str, Any]:
        """Create execution summary"""
        total_steps = len(plan.steps)
        completed_steps = sum(1 for step in plan.steps if step.status == TaskStatus.COMPLETED)
        
        summary = {
            "goal": plan.goal,
            "strategy": plan.strategy,
            "steps": {
                "total": total_steps,
                "completed": completed_steps,
                "success_rate": (completed_steps / total_steps * 100) if total_steps > 0 else 0
            },
            "execution": {
                "iterations": self.state.iteration,
                "total_cost": self.state.total_cost,
                "total_tool_calls": self.state.total_tool_calls,
                "duration": time.time() - self.start_time
            },
            "performance": self.metrics.get_summary(),
            "learnings": self.state.observations[-5:] if self.state.observations else []
        }
        
        return summary
    
    async def _create_update(self, update_type: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Create a standardized update message"""
        return {
            "type": update_type,
            "timestamp": datetime.now().isoformat(),
            "agent_id": self.state.agent_id,
            "phase": self.state.phase.value,
            "iteration": self.state.iteration,
            "data": data
        }
    
    def _trigger_callback(self, callback_name: str, *args, **kwargs):
        """Trigger a registered callback"""
        callback = self.callbacks.get(callback_name)
        if callback:
            try:
                callback(*args, **kwargs)
            except Exception as e:
                logger.error(f"Callback '{callback_name}' failed: {e}")
    
    # Unit test helper methods
    def _test_check_limits(self, test_state: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Test method for limit checking (for unit tests)
        
        Example:
            result = agent._test_check_limits({
                "iteration": 95,
                "total_cost": 9.5,
                "total_tool_calls": 45
            })
        """
        if test_state:
            # Save original state
            original_state = {
                "iteration": self.state.iteration,
                "total_cost": self.state.total_cost,
                "total_tool_calls": self.state.total_tool_calls
            }
            
            # Set test state
            self.state.iteration = test_state.get("iteration", self.state.iteration)
            self.state.total_cost = test_state.get("total_cost", self.state.total_cost)
            self.state.total_tool_calls = test_state.get("total_tool_calls", self.state.total_tool_calls)
            
            # Run check
            result = self._check_all_limits()
            
            # Restore original state
            self.state.iteration = original_state["iteration"]
            self.state.total_cost = original_state["total_cost"]
            self.state.total_tool_calls = original_state["total_tool_calls"]
            
            return result
        else:
            return self._check_all_limits()
    
    # Callback implementations
    def _on_phase_change(self, phase: AgentPhase):
        logger.info(f"Agent phase changed to: {phase.value}")
    
    def _on_tool_call(self, tool_info: Dict[str, Any]):
        logger.info(f"Tool called: {tool_info['tool']} with args: {tool_info['arguments']}")
    
    def _on_observation(self, observation: str):
        logger.debug(f"Observation: {observation}")
    
    def _on_limit_warning(self, warnings: List[str]):
        for warning in warnings:
            logger.warning(f"Limit warning: {warning}")
    
    def _on_error(self, error: str):
        logger.error(f"Agent error: {error}")
    
    def _on_checkpoint(self, checkpoint: Dict[str, Any]):
        logger.debug(f"Checkpoint saved: iteration {checkpoint['iteration']}")
    
    def _on_replan(self, replan_info: Dict[str, Any]):
        logger.info(f"Replanning triggered: {replan_info}")
    
    def _on_complete(self, completion_info: Dict[str, Any]):
        logger.info(f"Task completed: {completion_info['task'][:50]}...")
    
    # Public methods for interaction
    
    async def continue_with_clarification(
        self,
        clarification: str,
        question: Optional[str] = None
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Continue execution after providing clarification"""
        if not self.state.plan:
            yield await self._create_update("error", {
                "error": "No active plan to continue"
            })
            return
        
        # Add clarification to memory
        self.memory.add_message(Message(
            role="user",
            content=f"Clarification: {clarification}" + (f"\nQuestion was: {question}" if question else "")
        ))
        
        # Update the current step that needed clarification
        if self.state.plan and self.state.plan.current_step < len(self.state.plan.steps):
            step = self.state.plan.steps[self.state.plan.current_step]
            if step.action_type == "clarification":
                # Convert to reasoning step with the clarification
                step.action_type = "reasoning"
                step.description = f"Process clarification: {clarification}"
                step.status = TaskStatus.PENDING
        
        # Continue execution
        async for update in self.run(
            task=self.state.plan.goal,
            stream=True,
            max_iterations=self.context.limits["max_iterations"] - self.state.iteration
        ):
            yield update
    
    async def pause(self):
        """Pause agent execution"""
        if self.state.phase not in [AgentPhase.COMPLETED, AgentPhase.FAILED, AgentPhase.STOPPED]:
            self.state.phase = AgentPhase.STOPPED
            self._trigger_callback("on_phase_change", self.state.phase)
            logger.info("Agent paused")
    
    async def resume(self) -> AsyncGenerator[Dict[str, Any], None]:
        """Resume paused agent execution"""
        if self.state.phase == AgentPhase.STOPPED and self.state.plan:
            logger.info("Resuming agent execution")
            async for update in self.run(
                task=self.state.plan.goal,
                stream=True,
                max_iterations=self.context.limits["max_iterations"] - self.state.iteration
            ):
                yield update
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "agent_id": self.state.agent_id,
            "phase": self.state.phase.value,
            "mode": self.mode.value,
            "task": self.state.task,
            "iteration": self.state.iteration,
            "limits": self._get_current_limits(),
            "plan_progress": {
                "current_step": self.state.plan.current_step if self.state.plan else 0,
                "total_steps": len(self.state.plan.steps) if self.state.plan else 0,
                "goal": self.state.plan.goal if self.state.plan else None
            } if self.state.plan else None,
            "errors": self.state.get_errors(),
            "observations_count": len(self.state.observations),
            "cache_sizes": {
                "tool_cache": len(self.tool_cache),
                "llm_cache": len(self.llm_cache)
            }
        }
    
    def save_state(self, filepath: str):
        """Save full agent state to file"""
        state = {
            "agent_id": self.state.agent_id,
            "context": asdict(self.context),
            "state": self.state.dict(),
            "mode": self.mode.value,
            "system_prompt": self.system_prompt,
            "config": self.config,
            "last_checkpoint": self.last_checkpoint,
            "metrics": self.metrics.get_summary(),
            "saved_at": datetime.now().isoformat()
        }
        
        # Convert enums to strings
        state["state"]["phase"] = state["state"]["phase"].value
        
        with open(filepath, 'w') as f:
            json.dump(state, f, indent=2)
        
        logger.info(f"Agent state saved to {filepath}")
    
    @classmethod
    async def load_state(
        cls,
        filepath: str,
        llm_client: DeepSeekClient,
        tool_registry: ToolRegistry,
        memory_manager: MemoryManager
    ) -> 'AutonomousAgent':
        """Load agent state from file"""
        with open(filepath, 'r') as f:
            state = json.load(f)
        
        # Recreate context
        context = Context(**state["context"])
        
        # Create agent
        agent = cls(
            llm_client=llm_client,
            tool_registry=tool_registry,
            memory_manager=memory_manager,
            context=context,
            mode=AgentMode(state["mode"]),
            config=state.get("config", {})
        )
        
        # Restore state
        agent.state = AgentState.from_dict(state["state"])
        agent.system_prompt = state["system_prompt"]
        agent.last_checkpoint = state.get("last_checkpoint")
        
        # Restore plan if it exists
        if state["state"].get("plan"):
            # Import here to avoid circular imports
            from ..core.types import Plan, TaskStatus
            
            plan_data = state["state"]["plan"]
            # Convert status strings back to enums
            if "status" in plan_data:
                plan_data["status"] = TaskStatus(plan_data["status"])
            
            # Convert step statuses
            if "steps" in plan_data:
                for step in plan_data["steps"]:
                    if "status" in step:
                        step["status"] = TaskStatus(step["status"])
            
            agent.state.plan = Plan.from_dict(plan_data)
        
        logger.info(f"Agent state loaded from {filepath}")
        return agent


class AgentManager:
    """
    Manages multiple agents for complex workflows.
    Handles agent creation, coordination, and resource management.
    
    Features:
    - Multi-agent coordination and delegation
    - Shared memory between agents
    - Resource pooling
    - Task prioritization
    """
    
    def __init__(self, workspace_root: str, llm_client: DeepSeekClient, tool_registry: ToolRegistry):
        self.workspace_root = workspace_root
        self.llm_client = llm_client
        self.tool_registry = tool_registry
        self.agents: Dict[str, AutonomousAgent] = {}
        self.sessions: Dict[str, Dict] = {}
        self.shared_memory = {}
        self.logger = get_logger(__name__ + ".AgentManager")
        
        # Create shared workspace
        self.shared_workspace = Path(workspace_root) / "shared"
        self.shared_workspace.mkdir(parents=True, exist_ok=True)
    
    async def create_agent(
        self,
        task: str,
        session_id: Optional[str] = None,
        mode: AgentMode = AgentMode.AUTONOMOUS,
        **kwargs
    ) -> AutonomousAgent:
        """Create a new agent for a task"""
        # Create unique agent ID
        agent_id = f"agent_{len(self.agents) + 1}_{int(time.time())}"
        
        # Create workspace for agent
        workspace_path = str(self.shared_workspace / agent_id)
        Path(workspace_path).mkdir(parents=True, exist_ok=True)
        
        # Create memory manager with shared access
        memory_manager = MemoryManager(workspace_path)
        
        # Share memory between agents in same session
        if session_id and session_id in self.sessions:
            shared_session_data = self.sessions[session_id].get("shared_data", {})
            memory_manager.import_data(shared_session_data)
        
        # Create context with defaults
        default_limits = {
            "max_iterations": 100,
            "max_cost": 10.0,
            "max_tool_calls": 50,
            "max_time_seconds": 1800,
            "max_cache_size": 100,
            "tool_cache_ttl": 300
        }
        default_limits.update(kwargs.get("limits", {}))
        
        context = Context(
            task_id=agent_id,
            workspace_path=workspace_path,
            limits=default_limits
        )
        
        # Create agent with configuration
        config = kwargs.get("config", {})
        config.setdefault("export_metrics", True)
        
        agent = AutonomousAgent(
            llm_client=self.llm_client,
            tool_registry=self.tool_registry,
            memory_manager=memory_manager,
            context=context,
            mode=mode,
            config=config
        )
        
        # Register agent
        self.agents[agent_id] = agent
        
        # Add to session if specified
        if session_id:
            if session_id not in self.sessions:
                self.sessions[session_id] = {
                    "agents": [],
                    "created": datetime.now().isoformat(),
                    "tasks": [],
                    "shared_data": {}
                }
            self.sessions[session_id]["agents"].append(agent_id)
            self.sessions[session_id]["tasks"].append(task)
            
            # Store agent's initial state in shared data
            self.sessions[session_id]["shared_data"][agent_id] = {
                "task": task,
                "created": datetime.now().isoformat(),
                "mode": mode.value
            }
        
        self.logger.info(f"Created agent {agent_id} for task: {task[:50]}...")
        return agent
    
    async def delegate_task(
        self,
        task: str,
        parent_agent_id: str,
        subtask_description: str
    ) -> AutonomousAgent:
        """Delegate a subtask to a new agent"""
        parent_agent = self.agents.get(parent_agent_id)
        if not parent_agent:
            raise ValueError(f"Parent agent {parent_agent_id} not found")
        
        # Create new agent with context from parent
        child_agent = await self.create_agent(
            task=subtask_description,
            session_id=f"delegated_from_{parent_agent_id}",
            mode=AgentMode.AUTONOMOUS,
            limits=parent_agent.context.limits.copy(),
            config={"export_metrics": True}
        )
        
        # Share parent's memory with child
        parent_memory = parent_agent.memory.get_export_data()
        child_agent.memory.import_data(parent_memory)
        
        self.logger.info(f"Delegated subtask '{subtask_description}' from {parent_agent_id} to {child_agent.state.agent_id}")
        return child_agent
    
    async def coordinate_agents(
        self,
        session_id: str,
        tasks: List[str],
        coordination_strategy: str = "parallel"
    ) -> Dict[str, Any]:
        """Coordinate multiple agents on related tasks"""
        if coordination_strategy == "parallel":
            return await self._run_agents_in_parallel(session_id, tasks)
        elif coordination_strategy == "sequential":
            return await self._run_agents_in_sequence(session_id, tasks)
        elif coordination_strategy == "hierarchical":
            return await self._run_agents_hierarchically(session_id, tasks)
        else:
            raise ValueError(f"Unknown coordination strategy: {coordination_strategy}")
    
    async def _run_agents_in_parallel(self, session_id: str, tasks: List[str]) -> Dict[str, Any]:
        """Run multiple agents in parallel"""
        agents = []
        for task in tasks:
            agent = await self.create_agent(task, session_id)
            agents.append(agent)
        
        # Run all agents concurrently
        tasks_running = [agent.run(task) for agent, task in zip(agents, tasks)]
        results = await asyncio.gather(*tasks_running, return_exceptions=True)
        
        # Aggregate results
        aggregated = {
            "session_id": session_id,
            "strategy": "parallel",
            "results": [],
            "success_count": 0
        }
        
        for agent, result in zip(agents, results):
            if isinstance(result, Exception):
                aggregated["results"].append({
                    "agent_id": agent.state.agent_id,
                    "success": False,
                    "error": str(result)
                })
            else:
                # Collect final result from generator
                final_result = None
                async for update in agent.run(agent.state.task):
                    if update["type"] in ["completed", "stopped", "failed"]:
                        final_result = update
                
                success = final_result and final_result["type"] == "completed"
                if success:
                    aggregated["success_count"] += 1
                
                aggregated["results"].append({
                    "agent_id": agent.state.agent_id,
                    "success": success,
                    "result": final_result
                })
        
        return aggregated
    
    async def _run_agents_in_sequence(self, session_id: str, tasks: List[str]) -> Dict[str, Any]:
        """Run multiple agents sequentially, passing results between them"""
        results = []
        previous_result = None
        
        for i, task in enumerate(tasks):
            agent = await self.create_agent(
                task,
                session_id,
                mode=AgentMode.AUTONOMOUS
            )
            
            # Add previous result as context if available
            if previous_result:
                agent.memory.add_message(Message(
                    role="system",
                    content=f"Previous agent result: {json.dumps(previous_result, indent=2)}"
                ))
            
            # Run agent
            agent_result = None
            async for update in agent.run(task):
                if update["type"] in ["completed", "stopped", "failed"]:
                    agent_result = update
            
            results.append({
                "agent_id": agent.state.agent_id,
                "task": task,
                "result": agent_result,
                "success": agent_result and agent_result["type"] == "completed"
            })
            
            previous_result = agent_result
        
        return {
            "session_id": session_id,
            "strategy": "sequential",
            "results": results,
            "success_count": sum(1 for r in results if r["success"])
        }
    
    async def _run_agents_hierarchically(self, session_id: str, tasks: List[str]) -> Dict[str, Any]:
        """Run agents in a hierarchical structure with delegation"""
        # Create main coordinator agent
        coordinator = await self.create_agent(
            f"Coordinate tasks: {', '.join(tasks)}",
            session_id,
            mode=AgentMode.AUTONOMOUS
        )
        
        # Coordinator creates plan and delegates subtasks
        delegated_results = []
        
        for task in tasks:
            # Delegate to child agent
            child_agent = await self.delegate_task(
                task=task,
                parent_agent_id=coordinator.state.agent_id,
                subtask_description=task
            )
            
            # Run child agent
            child_result = None
            async for update in child_agent.run(task):
                if update["type"] in ["completed", "stopped", "failed"]:
                    child_result = update
            
            delegated_results.append({
                "agent_id": child_agent.state.agent_id,
                "task": task,
                "result": child_result,
                "success": child_result and child_result["type"] == "completed"
            })
        
        # Coordinator aggregates results
        coordinator_result = None
        async for update in coordinator.run(f"Aggregate results from {len(tasks)} subtasks"):
            if update["type"] in ["completed", "stopped", "failed"]:
                coordinator_result = update
        
        return {
            "session_id": session_id,
            "strategy": "hierarchical",
            "coordinator": {
                "agent_id": coordinator.state.agent_id,
                "result": coordinator_result,
                "success": coordinator_result and coordinator_result["type"] == "completed"
            },
            "delegated_agents": delegated_results,
            "success_count": sum(1 for r in delegated_results if r["success"])
        }
    
    def get_agent(self, agent_id: str) -> Optional[AutonomousAgent]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
    
    def get_session_agents(self, session_id: str) -> List[AutonomousAgent]:
        """Get all agents in a session"""
        session = self.sessions.get(session_id, {})
        return [self.agents[aid] for aid in session.get("agents", []) if aid in self.agents]
    
    async def cleanup_old_agents(self, max_age_hours: int = 24):
        """Clean up old agents to free resources"""
        cutoff = datetime.now() - timedelta(hours=max_age_hours)
        
        to_remove = []
        for agent_id, agent in self.agents.items():
            # Check if agent is inactive
            if agent.state.phase in [AgentPhase.COMPLETED, AgentPhase.FAILED, AgentPhase.STOPPED]:
                # Check last activity time
                if hasattr(agent, 'last_activity') and agent.last_activity < cutoff.timestamp():
                    to_remove.append(agent_id)
        
        for agent_id in to_remove:
            # Export agent metrics before cleanup
            agent = self.agents[agent_id]
            if agent.config.get("export_metrics"):
                await agent._export_metrics()
            
            del self.agents[agent_id]
            self.logger.info(f"Cleaned up old agent: {agent_id}")
        
        return len(to_remove)
    
    def get_manager_stats(self) -> Dict[str, Any]:
        """Get manager statistics"""
        active_agents = sum(1 for agent in self.agents.values() 
                          if agent.state.phase not in [AgentPhase.COMPLETED, AgentPhase.FAILED, AgentPhase.STOPPED])
        
        return {
            "total_agents": len(self.agents),
            "active_agents": active_agents,
            "sessions": len(self.sessions),
            "shared_memory_size": len(self.shared_memory)
        }
