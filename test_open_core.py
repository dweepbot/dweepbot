#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Test suite for DweepBot open-source features.

This test verifies that:
1. All features work correctly
2. License system exists for backward compatibility
3. Pro features are now freely accessible
"""

import sys
import os

# Add src to path for testing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

def test_license_manager():
    """Test license manager basic functionality."""
    print("Testing License Manager...")
    from dweepbot.license import LicenseManager, LicenseError, FeatureTier
    
    # Test 1: Create without license
    lm = LicenseManager()
    assert lm.get_tier() == FeatureTier.COMMUNITY, "Should default to Community tier"
    print("  ✅ Defaults to Community tier")
    
    # Test 2: Community features available
    assert lm.has_feature('core_agent'), "Core agent should be available"
    assert lm.has_feature('file_io'), "File I/O should be available"
    print("  ✅ Community features accessible")
    
    # Test 3: Pro features now also accessible (no license required)
    assert lm.has_feature('multi_agent'), "Multi-agent should now be available"
    assert lm.has_feature('vector_store'), "Vector store should now be available"
    assert lm.has_feature('dashboard'), "Dashboard should now be available"
    print("  ✅ Pro features now accessible without license")
    
    # Test 4: Available features includes everything
    features = lm.get_available_features()
    assert 'core_agent' in features, "Core agent should be in available features"
    assert 'multi_agent' in features, "Multi-agent should now be available"
    assert 'vector_store' in features, "Vector store should now be available"
    print("  ✅ All features are in available features list")
    
    print("✅ License Manager tests passed\n")


def test_pro_module_imports():
    """Test Pro module import behavior."""
    print("Testing Pro Module Imports...")
    
    # Test 1: Can import pro module
    try:
        from dweepbot import pro
        print("  ✅ Pro module imports")
    except Exception as e:
        print(f"  ❌ Pro module import failed: {e}")
        return False
    
    # Test 2: Can now access Pro classes without license
    try:
        from dweepbot.pro import MultiAgentOrchestrator
        print("  ✅ Pro classes now accessible without license")
    except Exception as e:
        print(f"  ❌ Pro class access failed: {e}")
        return False
    
    print("✅ Pro module import tests passed\n")


def test_license_singleton():
    """Test that license manager is a singleton."""
    print("Testing License Manager Singleton...")
    from dweepbot.license import get_license_manager
    
    lm1 = get_license_manager()
    lm2 = get_license_manager()
    
    assert lm1 is lm2, "Should return same instance"
    print("  ✅ Singleton pattern works correctly")
    
    print("✅ Singleton tests passed\n")


def test_all_features_available():
    """Test that all features are now available."""
    print("Testing All Features Available...")
    from dweepbot.license import get_license_manager
    
    lm = get_license_manager()
    
    # Test all pro features
    pro_features = ['multi_agent', 'vector_store', 'dashboard', 'task_scheduler', 'advanced_memory']
    for feature in pro_features:
        assert lm.has_feature(feature), f"{feature} should be available"
        print(f"  ✅ {feature} is accessible")
    
    # Test enterprise features
    enterprise_features = ['audit_logs', 'compliance_tools', 'white_label']
    for feature in enterprise_features:
        assert lm.has_feature(feature), f"{feature} should be available"
        print(f"  ✅ {feature} is accessible")
    
    print("✅ All features available tests passed\n")


def test_community_functionality():
    """Test that core features are accessible."""
    print("Testing Core Functionality...")
    
    # Test imports work
    try:
        from dweepbot import LicenseManager, get_license_manager, LicenseError
        print("  ✅ Core imports work")
    except Exception as e:
        print(f"  ❌ Import failed: {e}")
        return False
    
    # Test license manager works
    lm = get_license_manager()
    tier = lm.get_tier()
    print(f"  ✅ License tier: {tier}")
    
    # Test feature checking
    features = lm.get_available_features()
    print(f"  ✅ Available features: {len(features)} features")
    
    print("✅ Core functionality tests passed\n")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("DweepBot Open Source Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_license_manager,
        test_pro_module_imports,
        test_license_singleton,
        test_all_features_available,
        test_community_functionality,
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            passed += 1
        except Exception as e:
            print(f"❌ Test failed: {test_func.__name__}")
            print(f"   Error: {e}")
            failed += 1
            import traceback
            traceback.print_exc()
            print()
    
    print("=" * 70)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 70)
    
    return failed == 0


if __name__ == '__main__':
    success = run_all_tests()
    sys.exit(0 if success else 1)
