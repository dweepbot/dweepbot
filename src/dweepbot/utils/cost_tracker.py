"""
Cost tracking for DeepSeek API calls and tool executions.

Tracks tokens, API calls, and costs with DeepSeek-V3 pricing.
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, List, Optional
import json


# DeepSeek-V3 Pricing (as of Jan 2025)
# Input: $0.27 per million tokens
# Output: $1.10 per million tokens
# Cache hits: $0.07 per million tokens
DEEPSEEK_INPUT_COST_PER_TOKEN = 0.27 / 1_000_000
DEEPSEEK_OUTPUT_COST_PER_TOKEN = 1.10 / 1_000_000
DEEPSEEK_CACHE_COST_PER_TOKEN = 0.07 / 1_000_000


@dataclass
class TokenUsage:
    """Token usage for a single API call."""
    prompt_tokens: int = 0
    completion_tokens: int = 0
    cache_read_tokens: int = 0
    total_tokens: int = 0
    
    def __post_init__(self) -> None:
        if self.total_tokens == 0:
            self.total_tokens = self.prompt_tokens + self.completion_tokens


@dataclass
class CostEntry:
    """A single cost entry."""
    timestamp: datetime
    category: str  # "llm", "tool", "other"
    operation: str  # "deepseek_call", "web_search", etc.
    tokens: TokenUsage
    cost_usd: float
    metadata: Dict[str, any] = field(default_factory=dict)


class CostTracker:
    """
    Tracks costs across agent execution.
    
    Features:
    - Real-time cost accumulation
    - Per-phase cost breakdown
    - Per-tool cost breakdown
    - Token counting
    - Configurable cost limits
    """
    
    def __init__(
        self,
        max_cost_usd: float = 5.0,
        warn_threshold_usd: float = 3.0,
    ):
        """
        Initialize cost tracker.
        
        Args:
            max_cost_usd: Maximum allowed cost before stopping
            warn_threshold_usd: Cost threshold to trigger warnings
        """
        self.max_cost_usd = max_cost_usd
        self.warn_threshold_usd = warn_threshold_usd
        
        self._entries: List[CostEntry] = []
        self._total_cost: float = 0.0
        self._total_tokens: int = 0
        self._phase_costs: Dict[str, float] = {}
        self._tool_costs: Dict[str, float] = {}
        self._start_time = datetime.utcnow()
    
    def record_llm_call(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        cache_read_tokens: int = 0,
        phase: str = "unknown",
        metadata: Optional[Dict] = None,
    ) -> float:
        """
        Record a DeepSeek API call and return its cost.
        
        Args:
            prompt_tokens: Number of prompt tokens
            completion_tokens: Number of completion tokens
            cache_read_tokens: Number of cached tokens read
            phase: Agent phase (planning, execution, etc.)
            metadata: Additional metadata
        
        Returns:
            Cost in USD for this call
        """
        # Calculate cost
        input_cost = prompt_tokens * DEEPSEEK_INPUT_COST_PER_TOKEN
        output_cost = completion_tokens * DEEPSEEK_OUTPUT_COST_PER_TOKEN
        cache_cost = cache_read_tokens * DEEPSEEK_CACHE_COST_PER_TOKEN
        
        total_cost = input_cost + output_cost + cache_cost
        
        # Create token usage
        usage = TokenUsage(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            cache_read_tokens=cache_read_tokens,
            total_tokens=prompt_tokens + completion_tokens,
        )
        
        # Record entry
        entry = CostEntry(
            timestamp=datetime.utcnow(),
            category="llm",
            operation="deepseek_call",
            tokens=usage,
            cost_usd=total_cost,
            metadata=metadata or {},
        )
        
        self._entries.append(entry)
        self._total_cost += total_cost
        self._total_tokens += usage.total_tokens
        
        # Update phase costs
        self._phase_costs[phase] = self._phase_costs.get(phase, 0.0) + total_cost
        
        return total_cost
    
    def record_tool_call(
        self,
        tool_name: str,
        cost_usd: float = 0.0,
        phase: str = "execution",
        metadata: Optional[Dict] = None,
    ) -> None:
        """
        Record a tool execution cost.
        
        Args:
            tool_name: Name of the tool
            cost_usd: Cost of tool execution (most tools are free)
            phase: Agent phase
            metadata: Additional metadata
        """
        entry = CostEntry(
            timestamp=datetime.utcnow(),
            category="tool",
            operation=tool_name,
            tokens=TokenUsage(),
            cost_usd=cost_usd,
            metadata=metadata or {},
        )
        
        self._entries.append(entry)
        self._total_cost += cost_usd
        
        # Update tool costs
        self._tool_costs[tool_name] = self._tool_costs.get(tool_name, 0.0) + cost_usd
        
        # Update phase costs
        self._phase_costs[phase] = self._phase_costs.get(phase, 0.0) + cost_usd
    
    def get_total_cost(self) -> float:
        """Get total cost so far."""
        return self._total_cost
    
    def get_total_tokens(self) -> int:
        """Get total tokens used."""
        return self._total_tokens
    
    def get_phase_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by phase."""
        return self._phase_costs.copy()
    
    def get_tool_breakdown(self) -> Dict[str, float]:
        """Get cost breakdown by tool."""
        return self._tool_costs.copy()
    
    def is_over_budget(self) -> bool:
        """Check if we've exceeded the cost limit."""
        return self._total_cost >= self.max_cost_usd
    
    def should_warn(self) -> bool:
        """Check if we've exceeded the warning threshold."""
        return self._total_cost >= self.warn_threshold_usd
    
    def get_remaining_budget(self) -> float:
        """Get remaining budget."""
        return max(0.0, self.max_cost_usd - self._total_cost)
    
    def get_summary(self) -> Dict:
        """
        Get comprehensive cost summary.
        
        Returns:
            Dictionary with full cost breakdown
        """
        duration = (datetime.utcnow() - self._start_time).total_seconds()
        
        return {
            "total_cost_usd": round(self._total_cost, 4),
            "total_tokens": self._total_tokens,
            "duration_seconds": round(duration, 2),
            "cost_per_second": round(self._total_cost / duration if duration > 0 else 0, 6),
            "budget_remaining_usd": round(self.get_remaining_budget(), 4),
            "budget_used_percent": round((self._total_cost / self.max_cost_usd) * 100, 2),
            "phase_breakdown": {
                phase: round(cost, 4) for phase, cost in self._phase_costs.items()
            },
            "tool_breakdown": {
                tool: round(cost, 4) for tool, cost in self._tool_costs.items()
            },
            "total_api_calls": len([e for e in self._entries if e.category == "llm"]),
            "total_tool_calls": len([e for e in self._entries if e.category == "tool"]),
        }
    
    def export_to_json(self, filepath: str) -> None:
        """Export detailed cost log to JSON file."""
        data = {
            "summary": self.get_summary(),
            "entries": [
                {
                    "timestamp": e.timestamp.isoformat(),
                    "category": e.category,
                    "operation": e.operation,
                    "tokens": {
                        "prompt": e.tokens.prompt_tokens,
                        "completion": e.tokens.completion_tokens,
                        "cache_read": e.tokens.cache_read_tokens,
                        "total": e.tokens.total_tokens,
                    },
                    "cost_usd": round(e.cost_usd, 6),
                    "metadata": e.metadata,
                }
                for e in self._entries
            ],
        }
        
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)
    
    def reset(self) -> None:
        """Reset all cost tracking."""
        self._entries.clear()
        self._total_cost = 0.0
        self._total_tokens = 0
        self._phase_costs.clear()
        self._tool_costs.clear()
        self._start_time = datetime.utcnow()
