# SPDX-License-Identifier: MIT
"""
DweepBot Open Source Edition

This package contains the core open-source features of DweepBot,
licensed under MIT.

Community Features (Open Source):
- Core PLAN→ACT→OBSERVE→REFLECT autonomous loop
- Basic file I/O tools
- HTTP client
- Python code execution sandbox
- CLI interface
- Cost tracking
- Working memory

For advanced features like multi-agent orchestration, vector stores,
and the web dashboard, see DweepBot Pro: https://dweepbot.com/pro
"""

__all__ = [
    'AutonomousAgent',
    'AgentConfig',
    'ToolRegistry',
    'BaseTool',
]

# Core exports remain available from dweepbot.oss for clarity
# but we also export from top-level for backward compatibility
