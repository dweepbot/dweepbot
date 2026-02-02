# SPDX-License-Identifier: MIT
"""
DweepBot - Production-Grade Autonomous AI Agent Framework

DweepBot is available in two editions:

1. Community Edition (MIT License - Open Source):
   - Core PLAN→ACT→OBSERVE→REFLECT autonomous loop
   - Basic file I/O, HTTP, and code execution tools
   - CLI interface and cost tracking
   - Perfect for individual developers and learning

2. Pro Edition (Commercial License):
   - Multi-agent orchestration
   - Vector store & advanced memory systems
   - Task scheduler & automation
   - Web dashboard & command center
   - Priority support
   - Visit https://dweepbot.com/pro for pricing

For enterprise features, custom deployments, and white-label solutions,
contact sales@dweepbot.com
"""

__version__ = '1.0.0'

# Export license manager for users who want to check features
from .license import LicenseManager, get_license_manager, LicenseError

# Community Edition exports (always available)
# These remain at top-level for backward compatibility
__all__ = [
    '__version__',
    'LicenseManager',
    'get_license_manager', 
    'LicenseError',
]

# Pro features available via dweepbot.pro.*
# Will raise LicenseError if accessed without valid license
