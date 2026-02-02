# SPDX-License-Identifier: MIT
"""
License management for DweepBot open-core architecture.

This module handles feature gating between Community Edition (open-source)
and Pro Edition (commercial) features.
"""

import os
import logging
from typing import Optional, Set
from enum import Enum

logger = logging.getLogger(__name__)


class LicenseError(Exception):
    """Raised when a pro feature is accessed without a valid license."""
    pass


class FeatureTier(str, Enum):
    """Feature tiers in DweepBot."""
    COMMUNITY = "community"  # Free, open-source features
    PRO = "pro"              # Commercial features
    ENTERPRISE = "enterprise"  # Enterprise-only features


class LicenseManager:
    """
    Manages license validation and feature gating.
    
    Community Edition (MIT License):
    - Core PLAN→ACT→OBSERVE→REFLECT loop
    - Basic file I/O tools
    - HTTP client
    - Python code execution
    - CLI interface
    
    Pro Edition (Commercial License):
    - Multi-agent coordination
    - Vector store (ChromaDB)
    - Task scheduler
    - Web dashboard backend API
    - Advanced memory systems
    
    Enterprise Edition:
    - Custom deployments
    - White-label solutions
    - Audit logs & compliance
    - Priority support
    """
    
    # Features that require commercial license
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
            license_key: License key for Pro/Enterprise features.
                        Can also be set via DWEEPBOT_LICENSE env var.
        """
        self.license_key = license_key or os.getenv('DWEEPBOT_LICENSE')
        self.license_server_url = os.getenv(
            'DWEEPBOT_LICENSE_SERVER',
            'https://license.dweepbot.com/v1/validate'
        )
        self._validated = False
        self._tier = FeatureTier.COMMUNITY
        
        if self.license_key:
            logger.info("License key detected, will validate on first pro feature access")
    
    def has_feature(self, feature: str) -> bool:
        """
        Check if a feature is available with current license.
        
        Args:
            feature: Feature identifier (e.g., 'multi_agent', 'vector_store')
            
        Returns:
            True if feature is available, False otherwise
            
        Raises:
            LicenseError: If feature requires license and none is valid
        """
        # Community features always available
        if feature not in self.PRO_FEATURES and feature not in self.ENTERPRISE_FEATURES:
            return True
        
        # Pro features require license
        if feature in self.PRO_FEATURES:
            if not self._validate_commercial_license():
                raise LicenseError(
                    f"\n{'='*70}\n"
                    f"🔒 DweepBot Pro Feature Required\n"
                    f"{'='*70}\n\n"
                    f"The '{feature}' feature requires a DweepBot Pro license.\n\n"
                    f"DweepBot Pro includes:\n"
                    f"  • Multi-agent orchestration\n"
                    f"  • Vector store & advanced memory\n"
                    f"  • Task scheduler & automation\n"
                    f"  • Web dashboard & command center\n"
                    f"  • Priority support\n\n"
                    f"Pricing starts at $49/month.\n\n"
                    f"👉 Get your license at: https://dweepbot.com/pro\n"
                    f"📧 Questions? Contact: sales@dweepbot.com\n\n"
                    f"To activate your license, set the DWEEPBOT_LICENSE environment variable:\n"
                    f"  export DWEEPBOT_LICENSE='your-license-key'\n\n"
                    f"{'='*70}\n"
                )
            return True
        
        # Enterprise features require enterprise license
        if feature in self.ENTERPRISE_FEATURES:
            if self._tier != FeatureTier.ENTERPRISE:
                raise LicenseError(
                    f"\n{'='*70}\n"
                    f"🏢 DweepBot Enterprise Feature Required\n"
                    f"{'='*70}\n\n"
                    f"The '{feature}' feature requires a DweepBot Enterprise license.\n\n"
                    f"Enterprise includes:\n"
                    f"  • All Pro features\n"
                    f"  • Audit logs & compliance tools\n"
                    f"  • White-label deployment\n"
                    f"  • Custom integrations\n"
                    f"  • SLA with priority support\n\n"
                    f"👉 Contact us: sales@dweepbot.com\n"
                    f"📞 Schedule demo: https://dweepbot.com/enterprise\n\n"
                    f"{'='*70}\n"
                )
            return True
        
        return False
    
    def _validate_commercial_license(self) -> bool:
        """
        Validate commercial license key.
        
        In production, this would:
        1. Send license key to license server
        2. Verify signature and expiration
        3. Check usage limits
        4. Cache validation result
        
        Returns:
            True if license is valid, False otherwise
        """
        if not self.license_key:
            logger.warning("Pro feature access attempted without license key")
            return False
        
        # Placeholder for actual license validation
        # In production, this would call the license server API
        logger.info(
            f"Validating license with server: {self.license_server_url}"
        )
        
        # TODO: Implement actual license server validation
        # For now, just log the check
        logger.warning(
            "License validation not yet implemented. "
            "Pro features will be unavailable until license server is configured."
        )
        
        return False
    
    def get_tier(self) -> FeatureTier:
        """Get current license tier."""
        return self._tier
    
    def get_available_features(self) -> Set[str]:
        """Get set of all available features for current license."""
        features = set()
        
        # Community features (always available)
        features.update([
            'core_agent',
            'file_io',
            'http_client',
            'python_execution',
            'cli',
            'basic_tools',
        ])
        
        # Pro features
        if self._tier in [FeatureTier.PRO, FeatureTier.ENTERPRISE]:
            features.update(self.PRO_FEATURES)
        
        # Enterprise features
        if self._tier == FeatureTier.ENTERPRISE:
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
    Decorator to gate functions that require pro features.
    
    Usage:
        @require_pro_feature('multi_agent')
        def start_multi_agent_task():
            ...
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            license_mgr = get_license_manager()
            if not license_mgr.has_feature(feature):
                # has_feature raises LicenseError if not available
                pass
            return func(*args, **kwargs)
        return wrapper
    return decorator
