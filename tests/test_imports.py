"""Basic import tests to verify package structure."""
import pytest

def test_import_package():
    """Test that the main package can be imported."""
    import dweepbot
    assert dweepbot.__version__ == "1.0.0"

def test_import_cli():
    """Test that CLI module exists."""
    from dweepbot import cli
    assert cli is not None

def test_import_deepseek():
    """Test that DeepSeek module exists."""
    from dweepbot import deepseek
    assert deepseek is not None

if __name__ == "__main__":
    pytest.main([__file__])
