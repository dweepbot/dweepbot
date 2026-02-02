# SPDX-License-Identifier: COMMERCIAL
"""
DweepBot Pro - Commercial Features

This module contains premium features that require a commercial license.
See LICENSE-COMMERCIAL.md for details.

Pro Features:
- Multi-agent orchestration
- Vector store integration (ChromaDB)
- Task scheduler & automation
- Web dashboard backend API
- Advanced memory systems
- Team collaboration

To use Pro features, you need a valid license key.
Get your license at: https://dweepbot.com/pro

Configuration:
    export DWEEPBOT_LICENSE='your-license-key'
"""

from ..license import get_license_manager, LicenseError

# Check for license on import
_license_mgr = get_license_manager()

# We don't raise on import to allow package inspection
# but individual modules will check when used
__all__ = [
    'MultiAgentOrchestrator',
    'TaskScheduler',
    'DashboardAPI',
    'AdvancedMemory',
]

# Lazy imports to avoid loading if not licensed
def __getattr__(name):
    """Lazy loading of pro modules with license check."""
    if name == 'MultiAgentOrchestrator':
        _license_mgr.has_feature('multi_agent')
        from .multi_agent import MultiAgentOrchestrator
        return MultiAgentOrchestrator
    elif name == 'TaskScheduler':
        _license_mgr.has_feature('task_scheduler')
        from .task_scheduler import TaskScheduler
        return TaskScheduler
    elif name == 'DashboardAPI':
        _license_mgr.has_feature('dashboard')
        from .dashboard_api import DashboardAPI
        return DashboardAPI
    elif name == 'AdvancedMemory':
        _license_mgr.has_feature('advanced_memory')
        from .advanced_memory import AdvancedMemory
        return AdvancedMemory
    
    raise AttributeError(f"module '{__name__}' has no attribute '{name}'")
