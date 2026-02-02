#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""
Test suite for DweepBot open-core architecture.

This test verifies that:
1. Community features work correctly
2. Pro features are properly gated
3. License system functions as expected
4. Error messages are helpful
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
    
    # Test 3: Pro features blocked
    try:
        lm.has_feature('multi_agent')
        assert False, "Should raise LicenseError"
    except LicenseError as e:
        assert 'DweepBot Pro' in str(e), "Error should mention Pro edition"
        assert 'dweepbot.com/pro' in str(e), "Error should include upgrade URL"
        print("  ✅ Pro features properly gated")
    
    # Test 4: Available features
    features = lm.get_available_features()
    assert 'core_agent' in features, "Core agent should be in available features"
    assert 'multi_agent' not in features, "Multi-agent should not be available"
    print("  ✅ Available features list correct")
    
    print("✅ License Manager tests passed\n")


def test_pro_module_imports():
    """Test Pro module import behavior."""
    print("Testing Pro Module Imports...")
    from dweepbot.license import LicenseError
    
    # Test 1: Can import pro module (lazy loading)
    try:
        from dweepbot import pro
        print("  ✅ Pro module imports (lazy loading)")
    except Exception as e:
        print(f"  ❌ Pro module import failed: {e}")
        return False
    
    # Test 2: Accessing Pro class raises LicenseError
    try:
        from dweepbot.pro import MultiAgentOrchestrator
        print("  ❌ Should have raised LicenseError")
        return False
    except LicenseError:
        print("  ✅ Pro class access properly blocked")
    
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


def test_error_messages():
    """Test that error messages are helpful."""
    print("Testing Error Messages...")
    from dweepbot.license import get_license_manager, LicenseError
    
    lm = get_license_manager()
    
    try:
        lm.has_feature('multi_agent')
    except LicenseError as e:
        error_msg = str(e)
        
        # Check for key elements
        assert 'multi_agent' in error_msg, "Should mention the feature"
        assert 'DweepBot Pro' in error_msg, "Should mention Pro edition"
        assert '$49/month' in error_msg or 'Pricing' in error_msg, "Should mention pricing"
        assert 'dweepbot.com/pro' in error_msg, "Should include upgrade URL"
        assert 'sales@dweepbot.com' in error_msg, "Should include contact email"
        
        print("  ✅ Error message includes feature name")
        print("  ✅ Error message includes Pro edition mention")
        print("  ✅ Error message includes pricing info")
        print("  ✅ Error message includes upgrade URL")
        print("  ✅ Error message includes contact email")
    
    print("✅ Error message tests passed\n")


def test_community_functionality():
    """Test that Community edition core features are accessible."""
    print("Testing Community Edition Functionality...")
    
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
    
    print("✅ Community functionality tests passed\n")


def run_all_tests():
    """Run all tests."""
    print("=" * 70)
    print("DweepBot Open-Core Architecture Tests")
    print("=" * 70)
    print()
    
    tests = [
        test_license_manager,
        test_pro_module_imports,
        test_license_singleton,
        test_error_messages,
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
