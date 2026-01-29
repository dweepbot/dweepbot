"""
Reflection engine for analyzing step results and planning next actions.
"""

import json
from typing import List, Optional
from ..utils.deepseek_client import DeepSeekClient
from ..utils.logger import get_logger
from .schemas import StepResult, AgentPhase

logger = get_logger(__name__)


REFLECTION_SYSTEM_PROMPT = """You are a reflection engine for an autonomous AI agent. Analyze completed steps and decide what to do next.

Your job:
1. Analyze what just happened (tool results, errors, observations)
2. Determine if the current subgoal is complete
3. Decide the next action

Respond with JSON only:
{
  "subgoal_completed": true/false,
  "next_action": "continue" | "retry" | "skip" | "abort",
  "reasoning": "Brief explanation of decision",
  "adjustments": "Any changes needed to the plan"
}

Guidelines:
- If tools succeeded and validation criteria met → subgoal_completed: true
- If recoverable error → next_action: "retry"
- If unrecoverable error → next_action: "skip" or "abort"
- If making progress → next_action: "continue"
"""


class ReflectionEngine:
    """
    Analyzes agent steps and determines next actions.
    
    Uses LLM to:
    - Evaluate step success/failure
    - Decide if subgoals are complete
    - Plan recovery from errors
    - Adjust execution strategy
    """
    
    def __init__(self, deepseek_client: DeepSeekClient):
        """
        Initialize reflection engine.
        
        Args:
            deepseek_client: DeepSeek API client
        """
        self.client = deepseek_client
    
    async def reflect(
        self,
        current_step: StepResult,
        recent_steps: List[StepResult],
        subgoal_description: str,
        validation_criteria: str,
    ) -> dict:
        """
        Reflect on a completed step and decide next action.
        
        Args:
            current_step: The step that just completed
            recent_steps: Last few steps for context
            subgoal_description: What we're trying to accomplish
            validation_criteria: How to verify success
        
        Returns:
            Dictionary with reflection results
        """
        logger.info("Reflecting on step", phase=current_step.phase)
        
        # Build reflection prompt
        prompt = self._build_reflection_prompt(
            current_step,
            recent_steps,
            subgoal_description,
            validation_criteria,
        )
        
        try:
            response = await self.client.complete(
                messages=[
                    {"role": "system", "content": REFLECTION_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.2,  # Low temperature for consistent decisions
                max_tokens=500,
            )
            
            if "choices" in response and len(response["choices"]) > 0:
                content = response["choices"][0]["message"]["content"]
            else:
                return self._default_reflection()
            
            # Parse JSON
            reflection = self._extract_json(content)
            
            logger.info(
                "Reflection complete",
                subgoal_completed=reflection.get("subgoal_completed"),
                next_action=reflection.get("next_action"),
            )
            
            return reflection
            
        except Exception as e:
            logger.error("Reflection failed", error=str(e))
            return self._default_reflection()
    
    def _build_reflection_prompt(
        self,
        current_step: StepResult,
        recent_steps: List[StepResult],
        subgoal_description: str,
        validation_criteria: str,
    ) -> str:
        """Build the reflection prompt from step data."""
        prompt_parts = [
            f"Current Subgoal: {subgoal_description}",
            f"Validation Criteria: {validation_criteria}",
            "",
            "Current Step:",
            f"- Phase: {current_step.phase}",
            f"- Observation: {current_step.observation}",
        ]
        
        # Add tool results
        if current_step.tool_calls:
            prompt_parts.append("\nTool Results:")
            for tc in current_step.tool_calls:
                status_emoji = "✓" if tc.status.value == "success" else "✗"
                prompt_parts.append(f"  {status_emoji} {tc.tool_name}: {tc.status.value}")
                if tc.error:
                    prompt_parts.append(f"    Error: {tc.error}")
                elif tc.output:
                    output_str = str(tc.output)[:200]
                    prompt_parts.append(f"    Output: {output_str}")
        
        # Add recent context
        if recent_steps:
            prompt_parts.append("\nRecent Steps (for context):")
            for step in recent_steps[-3:]:
                prompt_parts.append(f"- {step.phase}: {step.observation[:100]}")
        
        return "\n".join(prompt_parts)
    
    def _extract_json(self, content: str) -> dict:
        """Extract JSON from response."""
        content = content.strip()
        
        if content.startswith("```json"):
            content = content[7:]
        elif content.startswith("```"):
            content = content[3:]
        
        if content.endswith("```"):
            content = content[:-3]
        
        content = content.strip()
        
        try:
            return json.loads(content)
        except json.JSONDecodeError:
            logger.warning("Failed to parse reflection JSON", content=content[:200])
            return self._default_reflection()
    
    def _default_reflection(self) -> dict:
        """Return default reflection when parsing fails."""
        return {
            "subgoal_completed": False,
            "next_action": "continue",
            "reasoning": "Unable to parse reflection, continuing with caution",
            "adjustments": "None",
        }
