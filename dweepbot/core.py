"""
Core autonomous agent implementation for Dweepbot
"""
import json
import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator, Union
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
import uuid

from dweepbot.llm.client import DeepSeekClient
from dweepbot.tools.base import ToolRegistry, ToolResult, ToolResultStatus
from dweepbot.memory.manager import MemoryManager
from dweepbot.core.types import Context, Message, Plan, PlanStep, TaskStatus
from dweepbot.core.planner import Planner
from dweepbot.core.executor import Executor


logger = logging.getLogger(__name__)


class AgentState:
    """Track the current state of the agent"""
    
    def __init__(self, context: Context):
        self.iteration: int = 0
        self.total_cost: float = 0.0
        self.total_tool_calls: int = 0
        self.start_time: datetime = datetime.now()
        self.current_plan: Optional[Plan] = None
        self.observations: List[str] = []
        self.context = context
        self._errors: List[str] = []
        self._results: List[Any] = []
    
    def add_observation(self, observation: str):
        """Add an observation from tool execution or reasoning"""
        self.observations.append(observation)
        # Keep only recent observations to avoid memory blowup
        if len(self.observations) > 20:
            self.observations = self.observations[-20:]
    
    def add_error(self, error: str):
        """Add an error that occurred during execution"""
        self._errors.append(error)
        logger.error(f"Agent error: {error}")
    
    def add_result(self, result: Any):
        """Add a successful result"""
        self._results.append(result)
    
    def get_errors(self) -> List[str]:
        """Get all accumulated errors"""
        return self._errors.copy()
    
    def get_results(self) -> List[Any]:
        """Get all accumulated results"""
        return self._results.copy()
    
    def check_limits(self) -> Optional[str]:
        """
        Check if any limits have been exceeded.
        Returns error message if limits exceeded, None otherwise.
        """
        limits = self.context.limits
        
        if self.iteration >= limits.get("max_iterations", 100):
            return f"Exceeded maximum iterations: {self.iteration}/{limits['max_iterations']}"
        
        if self.total_cost >= limits.get("max_cost", 10.0):
            return f"Exceeded maximum cost: ${self.total_cost:.4f}/${limits['max_cost']}"
        
        if self.total_tool_calls >= limits.get("max_tool_calls", 100):
            return f"Exceeded maximum tool calls: {self.total_tool_calls}/{limits['max_tool_calls']}"
        
        # Check execution time limit (if specified)
        execution_time = (datetime.now() - self.start_time).total_seconds()
        if execution_time > limits.get("max_time_seconds", 300):
            return f"Exceeded maximum execution time: {execution_time:.1f}s/{limits['max_time_seconds']}s"
        
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert state to dictionary for serialization"""
        return {
            "iteration": self.iteration,
            "total_cost": self.total_cost,
            "total_tool_calls": self.total_tool_calls,
            "execution_time_seconds": (datetime.now() - self.start_time).total_seconds(),
            "observations_count": len(self.observations),
            "errors_count": len(self._errors),
            "results_count": len(self._results),
            "has_plan": self.current_plan is not None,
            "limits": self.context.limits.copy()
        }


class AgentPhase(Enum):
    """Current phase of agent execution"""
    INITIALIZING = "initializing"
    PLANNING = "planning"
    EXECUTING = "executing"
    OBSERVING = "observing"
    REPLANNING = "replanning"
    COMPLETED = "completed"
    FAILED = "failed"
    STOPPED = "stopped"


class AutonomousAgent:
    """
    Autonomous agent that plans and executes tasks using LLMs and tools.
    
    The agent follows this loop:
    1. Receive task/user request
    2. Plan steps to achieve goal
    3. Execute steps using available tools
    4. Observe results and replan if necessary
    5. Return final result
    """
    
    def __init__(
        self,
        llm: DeepSeekClient,
        tools: ToolRegistry,
        memory: MemoryManager,
        context: Context
    ):
        """
        Initialize autonomous agent.
        
        Args:
            llm: LLM client for planning and reasoning
            tools: Registry of available tools
            memory: Memory manager for context and learning
            context: Execution context with limits and workspace
        """
        self.llm = llm
        self.tools = tools
        self.memory = memory
        self.context = context
        
        # Core components
        self.planner = Planner(llm, tools.get_openai_tools())
        self.executor = Executor(llm, tools)
        
        # State tracking
        self.state = AgentState(context)
        self.phase = AgentPhase.INITIALIZING
        self._stop_requested = False
        
        # Callbacks for monitoring
        self.on_phase_change: Optional[Callable[[AgentPhase], None]] = None
        self.on_observation: Optional[Callable[[str], None]] = None
        self.on_tool_call: Optional[Callable[[str, Dict], None]] = None
        
        logger.info(f"Agent initialized with task_id: {context.task_id}")
    
    def _set_phase(self, phase: AgentPhase):
        """Update agent phase and notify observers"""
        old_phase = self.phase
        self.phase = phase
        logger.debug(f"Agent phase changed: {old_phase.value} -> {phase.value}")
        
        if self.on_phase_change:
            self.on_phase_change(phase)
    
    async def run(self, task: str, stream: bool = False) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Run the agent on a given task.
        
        Args:
            task: The task description
            stream: Whether to stream intermediate results
            
        Yields:
            Status updates and results
        """
        logger.info(f"Starting agent run for task: {task}")
        self._set_phase(AgentPhase.INITIALIZING)
        
        # Add task to memory
        self.memory.add_message(Message(role="user", content=task))
        
        # Check for similar past tasks
        similar_tasks = self.memory.find_similar_tasks(task)
        if similar_tasks:
            logger.info(f"Found {len(similar_tasks)} similar past tasks")
        
        # Create initial plan
        self._set_phase(AgentPhase.PLANNING)
        yield {"phase": "planning", "status": "Creating initial plan..."}
        
        try:
            plan = await self._create_plan(task, similar_tasks)
            self.state.current_plan = plan
        except Exception as e:
            error_msg = f"Failed to create plan: {str(e)}"
            logger.error(error_msg)
            self.state.add_error(error_msg)
            self._set_phase(AgentPhase.FAILED)
            yield {"phase": "failed", "error": error_msg}
            return
        
        yield {"phase": "plan_created", "plan": plan.to_dict()}
        
        # Main execution loop
        while not self._stop_requested:
            self.state.iteration += 1
            
            # Check limits before proceeding
            limit_error = self.state.check_limits()
            if limit_error:
                logger.warning(f"Limit exceeded: {limit_error}")
                self._set_phase(AgentPhase.STOPPED)
                yield {"phase": "stopped", "reason": limit_error}
                break
            
            # Execute current step
            self._set_phase(AgentPhase.EXECUTING)
            
            try:
                result = await self._execute_next_step(plan)
                
                if stream:
                    yield {"phase": "executing", "result": result}
                
                # Add observation
                observation = self._create_observation(result)
                self.state.add_observation(observation)
                
                if self.on_observation:
                    self.on_observation(observation)
                
                # Check if plan is complete
                if plan.is_complete():
                    self._set_phase(AgentPhase.COMPLETED)
                    
                    # Learn from success
                    self.memory.learn_from_success(task, plan.to_dict())
                    
                    final_result = {
                        "phase": "completed",
                        "task": task,
                        "plan": plan.to_dict(),
                        "state": self.state.to_dict(),
                        "results": self.state.get_results(),
                        "errors": self.state.get_errors()
                    }
                    yield final_result
                    break
                
                # Check if replanning is needed
                if result.get("needs_replan", False) or len(self.state.observations) >= 5:
                    self._set_phase(AgentPhase.REPLANNING)
                    yield {"phase": "replanning", "reason": "Adjusting plan based on observations"}
                    
                    new_plan = await self._replan(plan, self.state.observations)
                    if new_plan:
                        plan = new_plan
                        self.state.current_plan = plan
                        self.state.observations = []  # Clear observations after replan
                        yield {"phase": "plan_updated", "plan": plan.to_dict()}
                
                # Move to next step
                plan.advance()
                
            except Exception as e:
                error_msg = f"Error in execution loop: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.state.add_error(error_msg)
                
                # Try to recover by replanning
                try:
                    self._set_phase(AgentPhase.REPLANNING)
                    yield {"phase": "replanning", "reason": "Recovering from error"}
                    
                    new_plan = await self._replan(plan, [f"Error occurred: {str(e)}"])
                    if new_plan:
                        plan = new_plan
                        self.state.current_plan = plan
                        yield {"phase": "plan_updated", "plan": plan.to_dict()}
                    else:
                        self._set_phase(AgentPhase.FAILED)
                        yield {"phase": "failed", "error": "Failed to recover from error"}
                        break
                except Exception as replan_error:
                    self._set_phase(AgentPhase.FAILED)
                    yield {"phase": "failed", "error": f"Critical failure: {str(replan_error)}"}
                    break
        
        logger.info(f"Agent run completed for task: {task}")
    
    async def _create_plan(self, task: str, similar_tasks: List[Dict] = None) -> Plan:
        """Create an execution plan for the given task"""
        try:
            # Incorporate learnings from similar tasks if available
            context_messages = []
            if similar_tasks:
                context_messages.append(
                    Message(
                        role="system",
                        content=f"Previously successful approach for similar task: {similar_tasks[0].get('plan')}"
                    )
                )
            
            # Create plan using planner
            plan = await self.planner.create_plan(task, context_messages)
            
            # Update costs
            llm_stats = self.llm.get_stats()
            self.state.total_cost += llm_stats.get("cost", 0)
            
            logger.info(f"Created plan with {len(plan.steps)} steps")
            return plan
            
        except Exception as e:
            logger.error(f"Failed to create plan: {e}")
            raise
    
    async def _execute_next_step(self, plan: Plan) -> Dict[str, Any]:
        """Execute the next step in the plan"""
        current_step = plan.get_current_step()
        if not current_step:
            return {"status": "no_step", "needs_replan": True}
        
        logger.info(f"Executing step: {current_step.description}")
        
        try:
            # Execute step using executor
            result = await self.executor.execute_step(
                current_step,
                context_messages=self.memory.get_context(),
                workspace_path=self.context.workspace_path
            )
            
            # Update state
            self.state.total_tool_calls += 1
            
            if result.tool_used:
                self.state.total_cost += result.cost or 0
                
                if self.on_tool_call:
                    self.on_tool_call(result.tool_used, result.tool_arguments or {})
            
            # Add result to memory if successful
            if result.success:
                self.state.add_result(result.output)
                
                # Store successful tool usage pattern
                if result.tool_used:
                    self.memory.record_tool_usage(
                        task=plan.goal,
                        tool=result.tool_used,
                        success=True
                    )
            
            return {
                "step": current_step.description,
                "success": result.success,
                "output": result.output,
                "error": result.error,
                "needs_replan": result.needs_replan or False,
                "cost": result.cost or 0
            }
            
        except Exception as e:
            error_msg = f"Failed to execute step: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.state.add_error(error_msg)
            
            return {
                "step": current_step.description,
                "success": False,
                "error": error_msg,
                "needs_replan": True
            }
    
    async def _replan(self, current_plan: Plan, observations: List[str]) -> Optional[Plan]:
        """Replan based on observations"""
        try:
            new_plan = await self.planner.replan(current_plan, observations)
            
            # Update costs
            llm_stats = self.llm.get_stats()
            self.state.total_cost += llm_stats.get("cost", 0)
            
            logger.info(f"Replanned: {len(new_plan.steps)} steps remaining")
            return new_plan
            
        except Exception as e:
            logger.error(f"Failed to replan: {e}")
            return None
    
    def _create_observation(self, execution_result: Dict[str, Any]) -> str:
        """Create an observation string from execution result"""
        step = execution_result.get("step", "unknown")
        success = execution_result.get("success", False)
        output = execution_result.get("output", "")
        error = execution_result.get("error", "")
        
        if success:
            return f"Step '{step}' succeeded: {output[:100]}..."
        else:
            return f"Step '{step}' failed: {error}"
    
    def stop(self):
        """Request the agent to stop execution"""
        logger.info("Stop requested")
        self._stop_requested = True
        self._set_phase(AgentPhase.STOPPED)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status"""
        return {
            "phase": self.phase.value,
            "state": self.state.to_dict(),
            "context": {
                "task_id": self.context.task_id,
                "workspace": self.context.workspace_path,
                "limits": self.context.limits
            },
            "tools_available": len(self.tools.list_tools()),
            "memory_stats": self.memory.get_stats()
        }
    
    def save_checkpoint(self, filepath: str):
        """Save agent state to a checkpoint file"""
        checkpoint = {
            "timestamp": datetime.now().isoformat(),
            "context": {
                "task_id": self.context.task_id,
                "workspace_path": self.context.workspace_path,
                "limits": self.context.limits
            },
            "state": self.state.to_dict(),
            "phase": self.phase.value,
            "current_plan": self.state.current_plan.to_dict() if self.state.current_plan else None,
            "observations": self.state.observations,
            "errors": self.state.get_errors(),
            "results": self.state.get_results()
        }
        
        with open(filepath, 'w') as f:
            json.dump(checkpoint, f, indent=2, default=str)
        
        logger.info(f"Checkpoint saved to {filepath}")
    
    @classmethod
    async def create_from_task(
        cls,
        task: str,
        llm: DeepSeekClient,
        tools: ToolRegistry,
        workspace_dir: Optional[str] = None,
        limits: Optional[Dict[str, Any]] = None
    ) -> 'AutonomousAgent':
        """
        Factory method to create an agent for a specific task.
        
        Args:
            task: The task description
            llm: LLM client
            tools: Tool registry
            workspace_dir: Optional workspace directory
            limits: Optional execution limits
        
        Returns:
            Configured AutonomousAgent instance
        """
        # Create workspace if not provided
        if not workspace_dir:
            workspace_dir = f"./workspace/{uuid.uuid4().hex[:8]}"
        
        Path(workspace_dir).mkdir(parents=True, exist_ok=True)
        
        # Set default limits
        default_limits = {
            "max_iterations": 50,
            "max_cost": 5.0,
            "max_tool_calls": 100,
            "max_time_seconds": 600
        }
        
        if limits:
            default_limits.update(limits)
        
        # Create context
        context = Context(
            task_id=uuid.uuid4().hex[:8],
            workspace_path=workspace_dir,
            limits=default_limits
        )
        
        # Initialize memory manager
        memory = MemoryManager(workspace_dir)
        
        # Create agent
        agent = cls(llm, tools, memory, context)
        
        # Store task in memory
        memory.add_message(Message(role="user", content=task))
        
        return agent


class MultiAgentSession:
    """
    Manages multiple agents working on related tasks.
    Useful for complex workflows that require coordination.
    """
    
    def __init__(self, session_id: str = None):
        self.session_id = session_id or uuid.uuid4().hex[:8]
        self.agents: Dict[str, AutonomousAgent] = {}
        self.shared_memory = {}
        self.logger = logging.getLogger(f"{__name__}.MultiAgentSession.{self.session_id}")
    
    def add_agent(self, agent: AutonomousAgent, name: str = None):
        """Add an agent to the session"""
        agent_name = name or f"agent_{len(self.agents) + 1}"
        self.agents[agent_name] = agent
        self.logger.info(f"Added agent: {agent_name}")
    
    async def run_parallel(self, tasks: Dict[str, str]) -> Dict[str, Any]:
        """Run multiple agents in parallel on different tasks"""
        self.logger.info(f"Running {len(tasks)} agents in parallel")
        
        results = {}
        
        # Run agents concurrently
        agent_tasks = []
        for agent_name, task in tasks.items():
            if agent_name in self.agents:
                agent = self.agents[agent_name]
                task_coro = self._run_agent_with_task(agent, task, agent_name)
                agent_tasks.append(task_coro)
        
        # Wait for all agents to complete
        agent_results = await asyncio.gather(*agent_tasks, return_exceptions=True)
        
        # Collect results
        for agent_name, result in zip(tasks.keys(), agent_results):
            if isinstance(result, Exception):
                results[agent_name] = {"error": str(result)}
            else:
                results[agent_name] = result
        
        return {
            "session_id": self.session_id,
            "results": results,
            "success": all(r.get("phase") == "completed" for r in results.values())
        }
    
    async def _run_agent_with_task(self, agent: AutonomousAgent, task: str, agent_name: str) -> Dict[str, Any]:
        """Run a single agent and collect its results"""
        try:
            results = []
            async for update in agent.run(task):
                results.append(update)
            
            # Get the final result
            final_result = results[-1] if results else {"phase": "empty"}
            final_result["agent_name"] = agent_name
            final_result["all_updates"] = results
            
            return final_result
        except Exception as e:
            self.logger.error(f"Agent {agent_name} failed: {e}")
            return {"phase": "failed", "error": str(e), "agent_name": agent_name}
    
    def get_session_status(self) -> Dict[str, Any]:
        """Get status of all agents in the session"""
        status = {}
        for name, agent in self.agents.items():
            status[name] = agent.get_status()
        
        return {
            "session_id": self.session_id,
            "agent_count": len(self.agents),
            "agents": status,
            "shared_memory": self.shared_memory
        }
