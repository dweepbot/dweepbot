"""
Autonomous Agent Planner - Creates and manages task execution plans
"""
import json
import re
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import asdict
from enum import Enum

from ..core.types import Plan, PlanStep, Message, TaskStatus, Context
from ..llm.client import DeepSeekClient
from ..utils.logger import get_logger

logger = get_logger(__name__)


class PlanningStrategy(Enum):
    """Different planning strategies for different task types"""
    STEP_BY_STEP = "step_by_step"      # Linear, deterministic tasks
    EXPLORATORY = "exploratory"        # Creative, open-ended tasks
    DEBUGGING = "debugging"            # Problem-solving tasks
    RESEARCH = "research"              # Information gathering tasks
    OPTIMIZATION = "optimization"      # Performance improvement tasks


class Planner:
    """
    Creates execution plans using LLM reasoning.
    Implements task decomposition and strategic planning.
    """
    
    # Planning prompts for different strategies
    PLANNING_PROMPTS = {
        PlanningStrategy.STEP_BY_STEP: """You are an expert task planner specializing in systematic, step-by-step execution.

Given a user's goal, create a detailed, sequential execution plan. Each step should be:
1. Concrete and actionable
2. Dependent only on previous steps
3. With clear success criteria

Available tools: {tools}

Output ONLY valid JSON in this exact format:
{{
  "goal": "The user's goal",
  "strategy": "step_by_step",
  "difficulty_estimate": "easy|medium|hard",
  "estimated_steps": number,
  "steps": [
    {{
      "id": "step_1",
      "description": "What to do in this step",
      "action_type": "tool_call|reasoning|clarification",
      "tool_name": "tool_name or null",
      "arguments": {{}},
      "dependencies": ["previous_step_id"],
      "expected_outcome": "What we expect to achieve",
      "success_criteria": ["specific criteria"],
      "time_estimate_minutes": number
    }}
  ],
  "requires_clarification": false,
  "clarification_questions": []
}}

User's goal: {goal}

Current context: {context}
""",
        
        PlanningStrategy.EXPLORATORY: """You are an expert creative planner specializing in exploratory tasks.

Given a user's goal, create a flexible, adaptive plan that allows for exploration and iteration.
Focus on learning, experimentation, and refinement.

Available tools: {tools}

Output ONLY valid JSON in this exact format:
{{
  "goal": "The user's goal",
  "strategy": "exploratory",
  "exploration_areas": ["area1", "area2"],
  "checkpoints": [
    {{
      "checkpoint": "Review initial findings",
      "criteria": ["gathered enough data"]
    }}
  ],
  "steps": [
    {{
      "id": "explore_1",
      "description": "Explore initial approach",
      "action_type": "tool_call|reasoning",
      "tool_name": "tool_name or null",
      "arguments": {{}},
      "expected_outcome": "Initial findings",
      "is_iterative": true
    }}
  ],
  "max_iterations": 3
}}

User's goal: {goal}

Current context: {context}
""",
        
        PlanningStrategy.DEBUGGING: """You are an expert debugging planner specializing in problem-solving.

Given a user's goal, create a systematic debugging plan that isolates issues, tests hypotheses,
and implements fixes methodically.

Available tools: {tools}

Output ONLY valid JSON in this exact format:
{{
  "goal": "The user's goal",
  "strategy": "debugging",
  "hypotheses": ["possible issue 1", "possible issue 2"],
  "steps": [
    {{
      "id": "diagnose_1",
      "description": "Isolate the issue",
      "action_type": "tool_call|reasoning",
      "tool_name": "tool_name or null",
      "arguments": {{}},
      "test_hypothesis": "which hypothesis this tests",
      "expected_outcome": "Confirmation or refutation",
      "fallback_action": "what to do if this fails"
    }}
  ],
  "requires_clarification": false,
  "clarification_questions": []
}}

User's goal: {goal}

Current context: {context}
"""
    }
    
    DEFAULT_PLANNING_PROMPT = """You are an expert task planner. Given a user's goal, create a detailed execution plan.

Analyze the task and choose the most appropriate approach. Consider complexity, resources needed, and potential risks.

Available tools: {tools}

Output ONLY valid JSON in this exact format:
{{
  "goal": "The user's goal",
  "strategy": "step_by_step|exploratory|debugging|research|optimization",
  "complexity_analysis": {{
    "difficulty": "easy|medium|hard",
    "estimated_time_minutes": number,
    "risk_level": "low|medium|high",
    "resource_intensive": true|false
  }},
  "steps": [
    {{
      "id": "unique_step_id",
      "description": "What to do in this step",
      "action_type": "tool_call|reasoning|clarification",
      "tool_name": "tool_name or null",
      "arguments": {{}},
      "dependencies": [],
      "expected_outcome": "What we expect to achieve",
      "success_criteria": ["criterion1", "criterion2"],
      "failure_handling": "retry|replan|ask_for_help"
    }}
  ],
  "requires_clarification": false,
  "clarification_questions": [],
  "validation_checks": ["check1", "check2"]
}}

User's goal: {goal}

Current context: {context}
"""
    
    REPLAN_PROMPT = """You are reviewing and updating an execution plan based on new observations.

Current situation:
- Original goal: {goal}
- Progress: {completed_steps}/{total_steps} steps completed
- Current step: {current_step}

Observations from execution:
{observations}

Status analysis:
{status_analysis}

Plan review criteria:
1. Are we making progress toward the goal?
2. Do new observations suggest a different approach?
3. Are there new opportunities or risks?
4. Should we adjust, continue, or abandon?

Output ONLY valid JSON:
{{
  "decision": "continue|adjust|complete|fail|ask_for_help",
  "reason": "Detailed explanation of decision",
  "confidence": 0.0-1.0,
  "learnings": ["key learning 1", "key learning 2"],
  "updated_plan": {{
    "goal": "Updated goal if needed",
    "steps": [...],
    "strategy_change": "new_strategy or null"
  }},
  "recommendations": ["suggestion 1", "suggestion 2"]
}}
"""
    
    def __init__(
        self,
        llm_client: DeepSeekClient,
        tools_metadata: List[Dict[str, Any]],
        default_strategy: PlanningStrategy = PlanningStrategy.STEP_BY_STEP
    ):
        self.llm = llm_client
        self.tools_metadata = tools_metadata
        self.default_strategy = default_strategy
        
        # Cache for tool lookups
        self._tool_cache = {tool['function']['name']: tool for tool in tools_metadata}
        
        # Planning history
        self.plan_history: List[Dict[str, Any]] = []
    
    async def create_plan(
        self,
        goal: str,
        context: Optional[Context] = None,
        strategy: Optional[PlanningStrategy] = None,
        previous_attempts: List[Dict] = None
    ) -> Plan:
        """Create initial execution plan with strategy selection"""
        
        logger.info(f"Creating plan for goal: {goal[:100]}...")
        
        # Determine strategy
        planning_strategy = strategy or self._determine_strategy(goal)
        logger.debug(f"Using planning strategy: {planning_strategy.value}")
        
        # Prepare tools description
        tools_desc = self._format_tools_description()
        
        # Prepare context
        context_desc = self._format_context(context, previous_attempts)
        
        # Select appropriate prompt
        if planning_strategy in self.PLANNING_PROMPTS:
            prompt = self.PLANNING_PROMPTS[planning_strategy].format(
                tools=tools_desc,
                goal=goal,
                context=context_desc
            )
        else:
            prompt = self.DEFAULT_PLANNING_PROMPT.format(
                tools=tools_desc,
                goal=goal,
                context=context_desc
            )
        
        messages = [
            Message(
                role="system",
                content="You are an expert task planner with strong analytical skills."
            ),
            Message(role="user", content=prompt)
        ]
        
        try:
            # Get plan from LLM
            response = await self.llm.create_completion(
                messages=messages,
                temperature=0.2,  # Low temperature for consistent planning
                max_tokens=4096,
                response_format={"type": "json_object"}
            )
            
            content = response["choices"][0]["message"]["content"]
            plan_data = self._extract_and_validate_json(content, "plan")
            
            # Validate plan structure
            validation_errors = self._validate_plan_structure(plan_data)
            if validation_errors:
                logger.warning(f"Plan validation errors: {validation_errors}")
                # Try to fix common issues
                plan_data = self._fix_plan_issues(plan_data, validation_errors)
            
            # Validate tool usage
            tool_validation = self._validate_tool_usage(plan_data.get("steps", []))
            if tool_validation["errors"]:
                logger.warning(f"Tool validation issues: {tool_validation['errors']}")
                # Update plan with valid tool usage
                plan_data = self._fix_tool_issues(plan_data, tool_validation)
            
            # Check if clarification needed
            if plan_data.get("requires_clarification", False):
                clarification_questions = plan_data.get("clarification_questions", [])
                logger.info(f"Plan requires clarification: {clarification_questions}")
                
                clarification_step = PlanStep(
                    id="clarification",
                    description="Get clarification from user",
                    action_type="clarification",
                    expected_outcome="User provides needed information",
                    metadata={"questions": clarification_questions}
                )
                
                return Plan(
                    goal=goal,
                    steps=[clarification_step],
                    status=TaskStatus.PENDING,
                    strategy=planning_strategy.value,
                    metadata=plan_data.get("complexity_analysis", {})
                )
            
            # Create plan steps
            steps = []
            for step_data in plan_data.get("steps", []):
                step = PlanStep(
                    id=step_data.get("id", f"step_{len(steps) + 1}"),
                    description=step_data["description"],
                    action_type=step_data.get("action_type", "reasoning"),
                    tool_name=step_data.get("tool_name"),
                    arguments=step_data.get("arguments", {}),
                    expected_outcome=step_data.get("expected_outcome", ""),
                    dependencies=step_data.get("dependencies", []),
                    metadata={
                        "success_criteria": step_data.get("success_criteria", []),
                        "failure_handling": step_data.get("failure_handling", "replan"),
                        "time_estimate": step_data.get("time_estimate_minutes")
                    }
                )
                steps.append(step)
            
            plan = Plan(
                goal=plan_data.get("goal", goal),
                steps=steps,
                status=TaskStatus.PLANNING,
                strategy=plan_data.get("strategy", planning_strategy.value),
                metadata={
                    "complexity_analysis": plan_data.get("complexity_analysis", {}),
                    "validation_checks": plan_data.get("validation_checks", []),
                    "original_plan_data": plan_data  # Store for reference
                }
            )
            
            # Record in history
            self.plan_history.append({
                "timestamp": datetime.now().isoformat(),
                "goal": goal,
                "strategy": planning_strategy.value,
                "step_count": len(steps),
                "plan_id": str(hash(goal))[:8]
            })
            
            logger.info(f"Created plan with {len(steps)} steps using {planning_strategy.value} strategy")
            return plan
        
        except Exception as e:
            logger.error(f"Planning failed: {e}", exc_info=True)
            # Comprehensive fallback
            return self._create_fallback_plan(goal, e)
    
    async def replan(
        self,
        plan: Plan,
        observations: List[str],
        execution_stats: Optional[Dict[str, Any]] = None
    ) -> Plan:
        """Update plan based on observations and execution statistics"""
        
        logger.info(f"Replanning based on {len(observations)} observations")
        
        # Analyze execution status
        status_analysis = self._analyze_execution_status(plan, observations, execution_stats)
        
        # Prepare replan prompt
        prompt = self.REPLAN_PROMPT.format(
            goal=plan.goal,
            completed_steps=plan.current_step,
            total_steps=len(plan.steps),
            current_step=plan.steps[plan.current_step].description if plan.current_step < len(plan.steps) else "None",
            observations="\n".join(f"- {obs}" for obs in observations[-10:]),  # Last 10 observations
            status_analysis=status_analysis
        )
        
        messages = [
            Message(role="system", content="You are an expert at adapting plans based on execution feedback."),
            Message(role="user", content=prompt)
        ]
        
        try:
            response = await self.llm.create_completion(
                messages=messages,
                temperature=0.3,
                max_tokens=2048,
                response_format={"type": "json_object"}
            )
            
            content = response["choices"][0]["message"]["content"]
            replan_data = self._extract_and_validate_json(content, "replan")
            
            decision = replan_data.get("decision", "continue")
            confidence = replan_data.get("confidence", 0.5)
            
            logger.info(f"Replanning decision: {decision} (confidence: {confidence:.2f})")
            
            if decision == "complete":
                plan.status = TaskStatus.COMPLETED
                plan.metadata["completion_reason"] = replan_data.get("reason")
                logger.info("Plan marked as complete")
            
            elif decision == "fail":
                plan.status = TaskStatus.FAILED
                plan.metadata["failure_reason"] = replan_data.get("reason")
                logger.warning(f"Plan failed: {replan_data.get('reason')}")
            
            elif decision == "ask_for_help":
                # Add clarification step
                help_step = PlanStep(
                    id=f"clarify_{plan.current_step}",
                    description="Request additional information or clarification",
                    action_type="clarification",
                    expected_outcome="Get needed information to proceed",
                    metadata={"questions": replan_data.get("recommendations", [])}
                )
                
                # Insert after current step
                plan.steps.insert(plan.current_step + 1, help_step)
                logger.info("Added clarification step")
            
            elif decision == "adjust":
                updated_plan_data = replan_data.get("updated_plan", {})
                
                if updated_plan_data:
                    # Create new steps from updated plan
                    updated_steps = []
                    for step_data in updated_plan_data.get("steps", []):
                        step = PlanStep(
                            id=step_data.get("id", f"adjusted_{len(updated_steps) + 1}"),
                            description=step_data.get("description", "Adjusted step"),
                            action_type=step_data.get("action_type", "reasoning"),
                            tool_name=step_data.get("tool_name"),
                            arguments=step_data.get("arguments", {}),
                            expected_outcome=step_data.get("expected_outcome", ""),
                            metadata={
                                "adjustment_reason": replan_data.get("reason", ""),
                                "original_step": plan.current_step if plan.current_step < len(plan.steps) else None
                            }
                        )
                        updated_steps.append(step)
                    
                    # Replace remaining steps with adjusted ones
                    completed_steps = plan.steps[:plan.current_step]
                    plan.steps = completed_steps + updated_steps
                    
                    # Update strategy if changed
                    if updated_plan_data.get("strategy_change"):
                        plan.strategy = updated_plan_data["strategy_change"]
                    
                    logger.info(f"Plan adjusted: {replan_data.get('reason')}")
                    
                    # Record adjustment
                    plan.metadata.setdefault("adjustments", []).append({
                        "step": plan.current_step,
                        "reason": replan_data.get("reason"),
                        "confidence": confidence,
                        "learnings": replan_data.get("learnings", [])
                    })
            
            else:  # continue
                logger.info("Continuing with current plan")
                # Record learning even when continuing
                plan.metadata.setdefault("learnings", []).extend(replan_data.get("learnings", []))
            
            return plan
        
        except Exception as e:
            logger.error(f"Replanning failed: {e}", exc_info=True)
            # Default to conservative continue
            return plan
    
    def _determine_strategy(self, goal: str) -> PlanningStrategy:
        """Determine appropriate planning strategy based on goal"""
        goal_lower = goal.lower()
        
        # Keyword-based strategy selection
        if any(word in goal_lower for word in ["debug", "fix", "error", "issue", "problem"]):
            return PlanningStrategy.DEBUGGING
        
        if any(word in goal_lower for word in ["explore", "research", "find", "investigate", "analyze"]):
            return PlanningStrategy.RESEARCH
        
        if any(word in goal_lower for word in ["optimize", "improve", "speed up", "efficient"]):
            return PlanningStrategy.OPTIMIZATION
        
        if any(word in goal_lower for word in ["creative", "design", "brainstorm", "ideas"]):
            return PlanningStrategy.EXPLORATORY
        
        return self.default_strategy
    
    def _format_tools_description(self) -> str:
        """Format tools metadata for prompts"""
        tools_desc = []
        for tool in self.tools_metadata:
            func = tool['function']
            tools_desc.append(f"- {func['name']}: {func['description']}")
            
            # Include parameter information
            params = func.get('parameters', {}).get('properties', {})
            if params:
                param_desc = []
                for param_name, param_info in params.items():
                    param_desc.append(f"  {param_name}: {param_info.get('description', '')}")
                if param_desc:
                    tools_desc.append("  Parameters:")
                    tools_desc.extend(param_desc)
            
            tools_desc.append("")  # Empty line between tools
        
        return "\n".join(tools_desc)
    
    def _format_context(self, context: Optional[Context], previous_attempts: Optional[List[Dict]]) -> str:
        """Format context information for prompts"""
        context_parts = []
        
        if context:
            context_parts.append(f"Workspace: {context.workspace_path}")
            context_parts.append(f"Limits: {json.dumps(context.limits, indent=2)}")
        
        if previous_attempts:
            context_parts.append("Previous attempts:")
            for i, attempt in enumerate(previous_attempts[-3:]):  # Last 3 attempts
                context_parts.append(f"  Attempt {i+1}: {attempt.get('result', 'unknown')}")
        
        return "\n".join(context_parts) if context_parts else "No specific context provided"
    
    def _extract_and_validate_json(self, text: str, context: str = "json") -> Dict[str, Any]:
        """Extract and validate JSON from LLM response"""
        # Try multiple extraction strategies
        json_text = self._extract_json(text)
        
        try:
            data = json.loads(json_text)
            
            # Basic validation
            if not isinstance(data, dict):
                raise ValueError(f"{context}: Expected object, got {type(data)}")
            
            return data
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse {context} JSON: {e}")
            logger.debug(f"Raw text: {text[:500]}")
            
            # Try to recover by finding any JSON-like structure
            recovered = self._recover_json(text)
            if recovered:
                logger.warning(f"Recovered partial {context} data")
                return recovered
            
            raise ValueError(f"Invalid {context} format: {e}")
    
    def _extract_json(self, text: str) -> str:
        """Extract JSON from text using multiple strategies"""
        # Strategy 1: Code blocks
        json_patterns = [
            r'```json\s*(.*?)\s*```',
            r'```\s*(.*?)\s*```',
            r'{\s*".*?}\s*',
        ]
        
        for pattern in json_patterns:
            matches = re.findall(pattern, text, re.DOTALL)
            if matches:
                # Take the longest match (most likely the JSON)
                return max(matches, key=len).strip()
        
        # Strategy 2: Find something that looks like JSON
        lines = text.strip().split('\n')
        json_lines = []
        in_json = False
        
        for line in lines:
            stripped = line.strip()
            if stripped.startswith('{'):
                in_json = True
            if in_json:
                json_lines.append(stripped)
            if stripped.endswith('}'):
                break
        
        if json_lines:
            return '\n'.join(json_lines)
        
        # Strategy 3: Return original text (let json.loads handle it)
        return text.strip()
    
    def _recover_json(self, text: str) -> Dict[str, Any]:
        """Attempt to recover JSON from malformed text"""
        try:
            # Try to fix common JSON issues
            fixed = text
            
            # Fix trailing commas
            fixed = re.sub(r',\s*}', '}', fixed)
            fixed = re.sub(r',\s*]', ']', fixed)
            
            # Fix missing quotes on keys
            fixed = re.sub(r'(\{|\s|,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1"\2":', fixed)
            
            # Fix single quotes
            fixed = fixed.replace("'", '"')
            
            return json.loads(fixed)
        except:
            return {}
    
    def _validate_plan_structure(self, plan_data: Dict[str, Any]) -> List[str]:
        """Validate plan structure and return errors"""
        errors = []
        
        if not plan_data.get("goal"):
            errors.append("Missing 'goal' field")
        
        steps = plan_data.get("steps", [])
        if not isinstance(steps, list):
            errors.append("'steps' must be a list")
        elif not steps:
            errors.append("Plan has no steps")
        else:
            for i, step in enumerate(steps):
                if not isinstance(step, dict):
                    errors.append(f"Step {i}: Must be an object")
                    continue
                
                if not step.get("description"):
                    errors.append(f"Step {i}: Missing 'description'")
                
                action_type = step.get("action_type", "reasoning")
                if action_type not in ["tool_call", "reasoning", "clarification"]:
                    errors.append(f"Step {i}: Invalid action_type '{action_type}'")
                
                if action_type == "tool_call" and not step.get("tool_name"):
                    errors.append(f"Step {i}: Tool call missing 'tool_name'")
        
        return errors
    
    def _validate_tool_usage(self, steps: List[Dict]) -> Dict[str, Any]:
        """Validate tool usage in steps"""
        errors = []
        warnings = []
        valid_steps = []
        
        for step in steps:
            if step.get("action_type") == "tool_call":
                tool_name = step.get("tool_name")
                
                if not tool_name:
                    errors.append(f"Step '{step.get('description', 'unknown')}': Missing tool name")
                    continue
                
                if tool_name not in self._tool_cache:
                    errors.append(f"Step '{step.get('description')}': Unknown tool '{tool_name}'")
                    continue
                
                # Validate tool arguments
                tool_metadata = self._tool_cache[tool_name]
                tool_params = tool_metadata['function'].get('parameters', {}).get('properties', {})
                step_args = step.get("arguments", {})
                
                # Check required parameters
                required_params = tool_metadata['function'].get('parameters', {}).get('required', [])
                for param in required_params:
                    if param not in step_args:
                        errors.append(f"Tool '{tool_name}': Missing required parameter '{param}'")
                
                # Check unknown parameters
                for param in step_args:
                    if param not in tool_params:
                        warnings.append(f"Tool '{tool_name}': Unknown parameter '{param}'")
                
                valid_steps.append(step)
            else:
                valid_steps.append(step)
        
        return {
            "errors": errors,
            "warnings": warnings,
            "valid_steps": valid_steps
        }
    
    def _fix_plan_issues(self, plan_data: Dict[str, Any], errors: List[str]) -> Dict[str, Any]:
        """Attempt to fix common plan issues"""
        fixed = plan_data.copy()
        
        # Ensure steps is a list
        if not isinstance(fixed.get("steps"), list):
            fixed["steps"] = []
        
        # Add missing IDs to steps
        for i, step in enumerate(fixed["steps"]):
            if not step.get("id"):
                step["id"] = f"step_{i + 1}"
        
        return fixed
    
    def _fix_tool_issues(self, plan_data: Dict[str, Any], validation: Dict[str, Any]) -> Dict[str, Any]:
        """Fix tool usage issues in plan"""
        if validation["errors"]:
            # Convert tool calls with errors to reasoning steps
            steps = []
            for step in plan_data.get("steps", []):
                if step.get("action_type") == "tool_call":
                    tool_name = step.get("tool_name")
                    if tool_name and tool_name not in self._tool_cache:
                        # Convert to reasoning step
                        step["action_type"] = "reasoning"
                        step["tool_name"] = None
                        step["arguments"] = {}
                        step["description"] = f"Reason about: {step.get('description', 'task')}"
                steps.append(step)
            
            plan_data["steps"] = steps
        
        return plan_data
    
    def _analyze_execution_status(
        self,
        plan: Plan,
        observations: List[str],
        execution_stats: Optional[Dict[str, Any]]
    ) -> str:
        """Analyze execution status for replanning"""
        analysis = []
        
        # Progress analysis
        progress = (plan.current_step / len(plan.steps)) * 100 if plan.steps else 0
        analysis.append(f"Progress: {progress:.1f}% ({plan.current_step}/{len(plan.steps)} steps)")
        
        # Observation analysis
        if observations:
            success_count = sum(1 for obs in observations if "succeeded" in obs.lower() or "success" in obs.lower())
            error_count = sum(1 for obs in observations if "failed" in obs.lower() or "error" in obs.lower())
            
            analysis.append(f"Observations: {success_count} successful, {error_count} errors")
            
            if error_count > success_count:
                analysis.append("Warning: More errors than successes")
        
        # Execution stats analysis
        if execution_stats:
            if execution_stats.get("total_cost", 0) > 0:
                analysis.append(f"Cost: ${execution_stats['total_cost']:.4f}")
            if execution_stats.get("total_tool_calls", 0) > 0:
                analysis.append(f"Tool calls: {execution_stats['total_tool_calls']}")
        
        # Strategy effectiveness
        if plan.current_step > 0:
            avg_success = plan.current_step / len(plan.steps) if plan.steps else 1.0
            analysis.append(f"Strategy effectiveness: {avg_success:.0%}")
        
        return "\n".join(f"- {item}" for item in analysis)
    
    def _create_fallback_plan(self, goal: str, error: Exception) -> Plan:
        """Create a fallback plan when planning fails"""
        logger.warning(f"Creating fallback plan due to: {error}")
        
        # Simple three-step fallback plan
        steps = [
            PlanStep(
                id="fallback_1",
                description=f"Analyze and understand the task: {goal}",
                action_type="reasoning",
                expected_outcome="Clear understanding of requirements"
            ),
            PlanStep(
                id="fallback_2",
                description="Execute the main task with available tools",
                action_type="tool_call",
                expected_outcome="Task completion attempt"
            ),
            PlanStep(
                id="fallback_3",
                description="Review and validate results",
                action_type="reasoning",
                expected_outcome="Verified completion or identified issues"
            )
        ]
        
        return Plan(
            goal=goal,
            steps=steps,
            status=TaskStatus.PLANNING,
            strategy="fallback",
            metadata={
                "fallback_reason": str(error),
                "complexity_analysis": {
                    "difficulty": "unknown",
                    "risk_level": "high"
                }
            }
        )
    
    def get_planning_stats(self) -> Dict[str, Any]:
        """Get planner statistics"""
        return {
            "total_plans_created": len(self.plan_history),
            "strategies_used": {},
            "average_steps_per_plan": 0,
            "recent_plans": self.plan_history[-5:] if self.plan_history else []
        }
