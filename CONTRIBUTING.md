# Contributing to DweepBot Pro

Thank you for your interest in contributing to DweepBot Pro! 🦈

We welcome contributions from the community. This document provides guidelines and instructions for contributing.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Setup](#development-setup)
- [How to Contribute](#how-to-contribute)
- [Pull Request Process](#pull-request-process)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)

## 🤝 Code of Conduct

This project adheres to a Code of Conduct. By participating, you are expected to:

- Be respectful and inclusive
- Welcome newcomers and help them get started
- Focus on what is best for the community
- Show empathy towards other community members

## 🚀 Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/dweepbot.git
   cd dweepbot
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/dweepbot/dweepbot.git
   ```

## 💻 Development Setup

1. **Create a virtual environment**:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install development dependencies**:
   ```bash
   pip install -e ".[dev]"
   # Or install all features
   pip install -e ".[all]"
   ```

3. **Set up pre-commit hooks** (optional but recommended):
   ```bash
   pre-commit install
   ```

4. **Copy environment file**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## 🔧 How to Contribute

### Reporting Bugs

- **Check existing issues** to avoid duplicates
- **Use the bug report template** when creating a new issue
- **Include**:
  - Clear description of the bug
  - Steps to reproduce
  - Expected vs actual behavior
  - Environment details (OS, Python version, etc.)
  - Relevant logs or screenshots

### Suggesting Features

- **Check existing issues** for similar suggestions
- **Use the feature request template**
- **Describe**:
  - The problem you're trying to solve
  - Your proposed solution
  - Alternative solutions considered
  - Additional context

### Code Contributions

We welcome pull requests for:

- 🐛 Bug fixes
- ✨ New features
- 📝 Documentation improvements
- 🎨 Code quality improvements
- ✅ Test coverage improvements

## 🔄 Pull Request Process

1. **Create a branch** for your work:
   ```bash
   git checkout -b feature/your-feature-name
   # or
   git checkout -b fix/your-bug-fix
   ```

2. **Make your changes**:
   - Write clear, concise code
   - Follow our [coding standards](#coding-standards)
   - Add tests for new functionality
   - Update documentation as needed

3. **Test your changes**:
   ```bash
   # Run tests
   pytest

   # Run linting
   black .
   isort .
   flake8
   mypy .
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add new feature"
   ```
   
   Use conventional commit messages:
   - `feat:` new feature
   - `fix:` bug fix
   - `docs:` documentation changes
   - `test:` adding or updating tests
   - `refactor:` code refactoring
   - `chore:` maintenance tasks

5. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

6. **Create a Pull Request**:
   - Go to the original repository on GitHub
   - Click "New Pull Request"
   - Select your branch
   - Fill out the PR template
   - Link any related issues

7. **Code Review**:
   - Respond to review comments
   - Make requested changes
   - Push updates to your branch

8. **Merge**:
   - Once approved, a maintainer will merge your PR
   - Your branch will be deleted after merge

## 📏 Coding Standards

### Python Style

- Follow **PEP 8** style guidelines
- Use **Black** for code formatting (line length: 100)
- Use **isort** for import sorting
- Use **type hints** for function parameters and return values

### Code Quality

- **Keep functions small and focused** (single responsibility)
- **Write descriptive variable and function names**
- **Add docstrings** to all public functions and classes
- **Handle errors gracefully** with proper exception handling
- **Avoid hardcoding** - use configuration files

### Example:

```python
from typing import Optional

def process_user_input(
    user_input: str,
    max_length: int = 1000
) -> Optional[str]:
    """
    Process and validate user input.
    
    Args:
        user_input: Raw input from the user
        max_length: Maximum allowed length for input
        
    Returns:
        Processed input string, or None if invalid
        
    Raises:
        ValueError: If input exceeds max_length
    """
    if len(user_input) > max_length:
        raise ValueError(f"Input exceeds maximum length of {max_length}")
    
    return user_input.strip()
```

## ✅ Testing

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=dweepbot --cov-report=html

# Run specific test file
pytest tests/test_agent.py

# Run specific test
pytest tests/test_agent.py::test_agent_initialization
```

### Writing Tests

- Write tests for all new functionality
- Aim for >80% code coverage
- Use descriptive test names
- Follow the Arrange-Act-Assert pattern

```python
def test_agent_processes_task_correctly():
    # Arrange
    agent = Agent(config=test_config)
    task = "Write a hello world program"
    
    # Act
    result = agent.run(task)
    
    # Assert
    assert result.success is True
    assert "hello world" in result.output.lower()
```

## 📚 Documentation

- **Update README.md** if you add new features
- **Add docstrings** to all functions and classes
- **Update docs/** if you change core functionality
- **Include examples** for new features
- **Keep CHANGELOG.md** updated

### Documentation Style

```python
def my_function(param1: str, param2: int) -> bool:
    """
    Brief description of what the function does.
    
    More detailed explanation if needed. Can span multiple
    lines and include implementation details.
    
    Args:
        param1: Description of param1
        param2: Description of param2
        
    Returns:
        Description of return value
        
    Raises:
        ValueError: When param2 is negative
        
    Example:
        >>> my_function("test", 42)
        True
    """
    pass
```

## 🏷️ Versioning

We use [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes

## 📞 Getting Help

- 💬 **GitHub Discussions**: Ask questions and discuss ideas
- 🐛 **GitHub Issues**: Report bugs or request features
- 📧 **Email**: contact@dweepbot.dev for private inquiries

## 🙏 Recognition

Contributors will be recognized in:
- **CHANGELOG.md** for their contributions
- **README.md** in the contributors section
- GitHub's contributor list

Thank you for contributing to DweepBot Pro! 🚀
