# Installation Guide

This guide will help you install and set up DweepBot Pro on your system.

## Table of Contents

- [Requirements](#requirements)
- [Installation Methods](#installation-methods)
- [Configuration](#configuration)
- [Verification](#verification)
- [Troubleshooting](#troubleshooting)

## Requirements

### System Requirements
- **Operating System**: macOS 10.15+, Linux, or Windows (via WSL recommended)
- **Python**: 3.10 or higher
- **Memory**: 4GB RAM minimum (8GB+ recommended for RAG features)
- **Storage**: 500MB for core installation, additional space for models and databases

### API Keys
You'll need at least one of these:
- **DeepSeek API Key** (recommended - lowest cost)
- OpenAI API Key (optional alternative)
- Anthropic API Key (optional alternative)

Get a DeepSeek API key: https://platform.deepseek.com/

## Installation Methods

### Method 1: Install from PyPI (Recommended)

```bash
# Install core package
pip install dweepbot

# Or install with all features
pip install dweepbot[all]

# Or install specific features
pip install dweepbot[rag,web,ui]
```

### Method 2: Install from Source

```bash
# Clone the repository
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot

# Create virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install in development mode
pip install -e .

# Or with all features
pip install -e ".[all]"
```

### Method 3: Using Docker

```bash
# Clone the repository
git clone https://github.com/dweepbot/dweepbot.git
cd dweepbot

# Copy environment file
cp .env.example .env
# Edit .env with your API keys

# Build and run
docker-compose up
```

## Feature Installation Options

DweepBot Pro offers several optional feature sets:

### Core Features (Always Installed)
- Basic agent functionality
- LLM integration
- Simple tools

### Optional Features

#### RAG & Memory (`[rag]`)
```bash
pip install dweepbot[rag]
```
Includes:
- ChromaDB for vector storage
- Sentence transformers for embeddings
- Enhanced memory capabilities

#### Web Capabilities (`[web]`)
```bash
pip install dweepbot[web]
```
Includes:
- Web search (DuckDuckGo)
- Web scraping (BeautifulSoup)
- HTTP requests library

#### Document Processing (`[docs]`)
```bash
pip install dweepbot[docs]
```
Includes:
- PDF reading/writing
- Word document processing
- PowerPoint processing

#### Enhanced UI (`[ui]`)
```bash
pip install dweepbot[ui]
```
Includes:
- Rich terminal UI
- Interactive prompts
- Better console output

#### Notifications (`[notifications]`)
```bash
pip install dweepbot[notifications]
```
Includes:
- Slack integration
- Discord integration

#### Development Tools (`[dev]`)
```bash
pip install dweepbot[dev]
```
Includes:
- Testing frameworks
- Linting tools
- Type checkers

#### Everything (`[all]`)
```bash
pip install dweepbot[all]
```
Installs all optional features.

## Configuration

### 1. Environment Variables

Copy the example environment file:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```bash
# Minimum required
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Optional
OPENAI_API_KEY=your_openai_api_key_here
ANTHROPIC_API_KEY=your_anthropic_api_key_here
```

### 2. Basic Configuration

The default configuration works for most use cases. You can customize:

```bash
# In .env file
DEFAULT_MODEL=deepseek-chat
MAX_ITERATIONS=10
ENABLE_RAG=true
ENABLE_WEB_SEARCH=true
ENABLE_CODE_EXEC=true  # Use with caution
```

### 3. Advanced Configuration

For advanced users, you can configure:
- Custom prompts directory
- Workflow definitions
- Memory settings
- Rate limiting
- Security options

See `.env.example` for all available options.

## Verification

### Test Your Installation

```bash
# Check version
python -c "import dweepbot; print(dweepbot.__version__)"

# Run a simple test
python -c "from dweepbot import Agent; print('Installation successful!')"
```

### Run the CLI

```bash
# Using the command line tool
dweepbot

# Or run as module
python -m cli
```

### Run Example

```bash
# From the repository
python examples/simple_task.py
```

## Platform-Specific Notes

### macOS
```bash
# Install with Homebrew Python (recommended)
brew install python@3.11
pip3 install dweepbot[all]
```

### Linux (Ubuntu/Debian)
```bash
# Install Python 3.11
sudo apt update
sudo apt install python3.11 python3.11-venv python3-pip

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install DweepBot
pip install dweepbot[all]
```

### Windows (WSL Recommended)
```bash
# Install WSL2 and Ubuntu
wsl --install

# Then follow Linux instructions above
```

### Windows (Native - Not Recommended)
```bash
# Install Python from python.org
# Use PowerShell or Command Prompt

python -m pip install dweepbot[all]
```

## Troubleshooting

### Common Issues

#### 1. Import Error: No module named 'dweepbot'
```bash
# Make sure you're in the correct virtual environment
# And the package is installed
pip list | grep dweepbot
```

#### 2. API Key Not Found
```bash
# Verify .env file exists and has correct keys
cat .env | grep API_KEY

# Make sure .env is in the working directory
```

#### 3. ChromaDB Issues (RAG)
```bash
# Reinstall ChromaDB
pip uninstall chromadb
pip install chromadb --no-cache-dir
```

#### 4. Permission Errors (Linux/macOS)
```bash
# Use virtual environment (recommended)
python -m venv venv
source venv/bin/activate
pip install dweepbot[all]

# Or install for user only
pip install --user dweepbot[all]
```

#### 5. SSL Certificate Errors
```bash
# Update certificates (macOS)
/Applications/Python\ 3.11/Install\ Certificates.command

# Or install certifi
pip install --upgrade certifi
```

### Getting Help

If you encounter issues:

1. Check the [documentation](https://github.com/dweepbot/dweepbot/tree/main/docs)
2. Search [existing issues](https://github.com/dweepbot/dweepbot/issues)
3. Create a [new issue](https://github.com/dweepbot/dweepbot/issues/new)
4. Join our community discussions

## Next Steps

After installation:

1. Read the [Quick Start Guide](README.md#quick-start)
2. Explore [Examples](examples/)
3. Review [Documentation](docs/)
4. Try some [Workflows](workflows/)

## Updating

To update to the latest version:

```bash
# From PyPI
pip install --upgrade dweepbot

# From source
cd dweepbot
git pull
pip install -e ".[all]"
```

## Uninstallation

To remove DweepBot Pro:

```bash
pip uninstall dweepbot

# Also remove virtual environment if used
deactivate
rm -rf venv
```

---

For more information, see the [main README](README.md) or visit our [GitHub repository](https://github.com/dweepbot/dweepbot).
