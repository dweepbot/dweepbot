# SPDX-License-Identifier: MIT
"""
Feature management for DweepBot.

This module previously handled license gating but now all features are open source.
It's kept for backward compatibility.
"""

import logging
from typing import Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class LicenseError(Exception):
    """Raised when a feature is accessed incorrectly (kept for backward compatibility)."""
    pass


class FeatureTier(str, Enum):
    """Feature tiers in DweepBot."""
    COMMUNITY = "community"  # All features are now community/open source
    PRO = "pro"              # No longer gated - all features available
    ENTERPRISE = "enterprise"  # No longer gated - all features available


class LicenseManager:
    """
    Manages feature access in DweepBot.
    
    All features are now open source and available without restriction:
    - Core PLAN→ACT→OBSERVE→REFLECT loop
    - File I/O tools
    - HTTP client
    - Python code execution
    - CLI interface
    - Multi-agent coordination
    - Vector store (ChromaDB)
    - Task scheduler
    - Web dashboard backend API
    - Advanced memory systems
    """
    
    # All features are now available to everyone
    PRO_FEATURES = {
        'multi_agent',
        'vector_store',
        'dashboard',
        'task_scheduler',
        'advanced_memory',
        'orchestration',
    }
    
    ENTERPRISE_FEATURES = {
        'audit_logs',
        'compliance_tools',
        'white_label',
        'custom_deployment',
        'sla_support',
    }
    
    def __init__(self, license_key: Optional[str] = None):
        """
        Initialize license manager.
        
        Args:
            license_key: No longer required - kept for backward compatibility
        """
        self.license_key = license_key
        self._validated = True  # Always validated now
        self._tier = FeatureTier.COMMUNITY
        
        logger.info("All features are now open source and freely available")
    
    def has_feature(self, feature: str) -> bool:
        """
        Check if a feature is available.
        
        Args:
            feature: Feature identifier (e.g., 'multi_agent', 'vector_store')
            
        Returns:
            True (all features are now available)
        """
        # All features are now available
        return True
    
    def get_tier(self) -> FeatureTier:
        """Get current license tier."""
        return self._tier
    
    def get_available_features(self) -> Set[str]:
        """Get set of all available features."""
        # Return all features
        features = {
            'core_agent',
            'file_io',
            'http_client',
            'python_execution',
            'cli',
            'basic_tools',
        }
        
        # All pro and enterprise features are now available
        features.update(self.PRO_FEATURES)
        features.update(self.ENTERPRISE_FEATURES)
        
        return features


# Global license manager instance
_global_license_manager: Optional[LicenseManager] = None


def get_license_manager() -> LicenseManager:
    """Get or create global license manager instance."""
    global _global_license_manager
    if _global_license_manager is None:
        _global_license_manager = LicenseManager()
    return _global_license_manager


def require_pro_feature(feature: str):
    """
    Decorator for features (kept for backward compatibility).
    
    Usage:
        @require_pro_feature('multi_agent')
        def start_multi_agent_task():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            # All features are now available, no check needed
            return func(*args, **kwargs)
        return wrapper
    return decorator
