# SPDX-License-Identifier: MIT
"""
DweepBot Pro Features

Advanced features including:
- Multi-agent orchestration
- Vector store integration (ChromaDB)
- Task scheduler & automation
- Web dashboard backend API
- Advanced memory systems
- Team collaboration

All features are now open source under MIT License.
"""

from ..license import get_license_manager, LicenseError

# Check for license on import (no longer enforces restrictions)
_license_mgr = get_license_manager()

__all__ = [
    'MultiAgentOrchestrator',
    'TaskScheduler',
    'DashboardAPI',
    'AdvancedMemory',
]

# Lazy imports
def __getattr__(name):
    """Lazy loading of pro modules."""
    if name == 'MultiAgentOrchestrator':
        from .multi_agent import MultiAgentOrchestrator
        return MultiAgentOrchestrator
    elif name == 'TaskScheduler':
        from .task_scheduler import TaskScheduler
        return TaskScheduler
    elif name == 'DashboardAPI':
        from .dashboard_api import DashboardAPI
        return DashboardAPI
    elif name == 'AdvancedMemory':
        from .advanced_memory import AdvancedMemory
        return AdvancedMemory
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
