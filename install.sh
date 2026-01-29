#!/bin/bash
# DweepBot Pro - Quick Setup Script

set -e

echo "🦈 DweepBot Pro - Installation & Setup"
echo "========================================"
echo ""

# Check Python version
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: Python 3 is required but not installed"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✓ Python $PYTHON_VERSION detected"

# Check if in virtual environment
if [[ -z "${VIRTUAL_ENV}" ]]; then
    echo ""
    echo "⚠️  Warning: Not in a virtual environment"
    echo "It's recommended to create one:"
    echo ""
    echo "  python3 -m venv venv"
    echo "  source venv/bin/activate  # On Windows: venv\\Scripts\\activate"
    echo ""
    read -p "Continue anyway? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Install options
echo ""
echo "Select installation type:"
echo "  1) Core only (minimal dependencies)"
echo "  2) All features (recommended)"
echo "  3) Development (includes testing tools)"
echo ""
read -p "Choice (1-3): " choice

case $choice in
    1)
        echo "Installing core dependencies..."
        pip install -e .
        ;;
    2)
        echo "Installing all features..."
        pip install -e ".[all]"
        ;;
    3)
        echo "Installing with development tools..."
        pip install -e ".[all,dev]"
        ;;
    *)
        echo "Invalid choice. Defaulting to core installation."
        pip install -e .
        ;;
esac

echo ""
echo "✓ Installation complete!"
echo ""

# Setup wizard
read -p "Run setup wizard to configure API key? (y/n) " -n 1 -r
echo
if [[ $REPLY =~ ^[Yy]$ ]]; then
    python3 -m dweepbot.cli setup
fi

echo ""
echo "🎉 DweepBot is ready!"
echo ""
echo "Quick start:"
echo "  dweepbot info                    # Check system status"
echo "  dweepbot run \"Your task here\"    # Execute a task"
echo ""
echo "Documentation:"
echo "  README.md            - User guide"
echo "  docs/ARCHITECTURE.md - System design"
echo "  examples/            - Example scripts"
echo ""
echo "Happy coding! 🦈"
