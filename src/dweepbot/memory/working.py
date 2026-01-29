"""
Working memory system for short-term observation storage.

Maintains a rolling window of recent agent actions and observations
for use in the OBSERVE and REFLECT phases.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from collections import deque


class Observation(BaseModel):
    """A single observation from agent execution."""
    id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    phase: str  # "planning", "acting", "observing", "reflecting"
    subgoal_id: Optional[str] = None
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def to_text(self) -> str:
        """Convert to human-readable text."""
        return f"[{self.phase}] {self.content}"


class WorkingMemory:
    """
    Rolling context window of recent observations.
    
    Used by the agent during OBSERVE and REFLECT phases to:
    - Remember what it just did
    - Avoid repeating failed actions
    - Maintain context across steps
    """
    
    def __init__(self, max_observations: int = 20):
        self.max_observations = max_observations
        self._observations: deque[Observation] = deque(maxlen=max_observations)
        self._observation_counter = 0
    
    def add_observation(
        self,
        phase: str,
        content: str,
        subgoal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Observation:
        """
        Add a new observation to working memory.
        
        Args:
            phase: Current agent phase
            content: Observation content
            subgoal_id: Associated subgoal (if any)
            metadata: Additional metadata
        
        Returns:
            Created Observation object
        """
        self._observation_counter += 1
        
        obs = Observation(
            id=f"obs_{self._observation_counter}",
            phase=phase,
            content=content,
            subgoal_id=subgoal_id,
            metadata=metadata or {}
        )
        
        self._observations.append(obs)
        return obs
    
    def get_recent(self, count: Optional[int] = None) -> List[Observation]:
        """
        Get recent observations.
        
        Args:
            count: Number of observations to return (None = all)
        
        Returns:
            List of recent Observation objects
        """
        if count is None:
            return list(self._observations)
        
        # Get last N observations
        return list(self._observations)[-count:]
    
    def get_by_phase(self, phase: str) -> List[Observation]:
        """Get all observations for a specific phase."""
        return [obs for obs in self._observations if obs.phase == phase]
    
    def get_by_subgoal(self, subgoal_id: str) -> List[Observation]:
        """Get all observations for a specific subgoal."""
        return [
            obs for obs in self._observations
            if obs.subgoal_id == subgoal_id
        ]
    
    def to_context_string(self, max_observations: Optional[int] = None) -> str:
        """
        Format recent observations as context string for LLM.
        
        Args:
            max_observations: Maximum observations to include
        
        Returns:
            Formatted string of observations
        """
        observations = self.get_recent(max_observations)
        
        if not observations:
            return "No previous observations."
        
        lines = ["Recent observations:"]
        for obs in observations:
            lines.append(f"- {obs.to_text()}")
        
        return "\n".join(lines)
    
    def clear(self) -> None:
        """Clear all observations."""
        self._observations.clear()
        self._observation_counter = 0
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics about working memory."""
        phase_counts = {}
        for obs in self._observations:
            phase_counts[obs.phase] = phase_counts.get(obs.phase, 0) + 1
        
        return {
            "total_observations": len(self._observations),
            "max_capacity": self.max_observations,
            "utilization_pct": (len(self._observations) / self.max_observations) * 100,
            "by_phase": phase_counts,
            "oldest_observation": self._observations[0].timestamp if self._observations else None,
            "newest_observation": self._observations[-1].timestamp if self._observations else None
        }


class MemoryManager:
    """
    Manages both short-term (working) and long-term memory.
    
    Short-term: Recent observations for immediate context
    Long-term: Persistent storage for future retrieval (RAG)
    """
    
    def __init__(
        self,
        max_working_memory: int = 20,
        enable_long_term: bool = False
    ):
        self.working_memory = WorkingMemory(max_observations=max_working_memory)
        self.enable_long_term = enable_long_term
        self._long_term_store: List[Observation] = []
    
    async def store_observation(
        self,
        phase: str,
        content: str,
        subgoal_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Observation:
        """
        Store an observation in both working and long-term memory.
        
        Args:
            phase: Current agent phase
            content: Observation content
            subgoal_id: Associated subgoal
            metadata: Additional metadata
        
        Returns:
            Created Observation object
        """
        # Add to working memory
        obs = self.working_memory.add_observation(
            phase=phase,
            content=content,
            subgoal_id=subgoal_id,
            metadata=metadata
        )
        
        # Store in long-term if enabled
        if self.enable_long_term:
            self._long_term_store.append(obs)
        
        return obs
    
    def get_context_for_llm(self, max_recent: int = 10) -> str:
        """
        Get formatted context string for LLM prompts.
        
        Args:
            max_recent: Maximum recent observations to include
        
        Returns:
            Formatted context string
        """
        return self.working_memory.to_context_string(max_recent)
    
    def get_relevant_memories(
        self,
        query: str,
        max_results: int = 5
    ) -> List[Observation]:
        """
        Retrieve relevant memories based on query.
        
        Currently uses simple string matching.
        In production, this would use vector similarity.
        
        Args:
            query: Search query
            max_results: Maximum results to return
        
        Returns:
            List of relevant Observation objects
        """
        query_lower = query.lower()
        
        # Score observations by relevance
        scored = []
        for obs in self._long_term_store:
            content_lower = obs.content.lower()
            
            # Simple scoring: count matching words
            words = query_lower.split()
            score = sum(1 for word in words if word in content_lower)
            
            if score > 0:
                scored.append((score, obs))
        
        # Sort by score and return top results
        scored.sort(reverse=True, key=lambda x: x[0])
        return [obs for _, obs in scored[:max_results]]
    
    def clear_all(self) -> None:
        """Clear all memory (both working and long-term)."""
        self.working_memory.clear()
        self._long_term_store.clear()
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get memory usage statistics."""
        stats = {
            "working_memory": self.working_memory.get_summary(),
            "long_term_enabled": self.enable_long_term,
            "long_term_count": len(self._long_term_store) if self.enable_long_term else 0
        }
        
        return stats
