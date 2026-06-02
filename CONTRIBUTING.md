# Contributing to Enterprise RAG System

First off, thank you for considering a contribution to the Enterprise RAG System! It's people like you that make this such a great tool.

## Code of Conduct

This project and everyone participating in it is governed by our Code of Conduct. By participating, you are expected to uphold this code.

## How Can I Contribute?

### Reporting Bugs
Before creating bug reports, please check the issue list as you might find out that you don't need to create one. When you are creating a bug report, please include as many details as possible:

* **Use a clear and descriptive title**
* **Describe the exact steps which reproduce the problem**
* **Provide specific examples to demonstrate the steps**
* **Describe the behavior you observed after following the steps**
* **Explain which behavior you expected to see instead and why**
* **Include screenshots and animated GIFs if possible**
* **Include your environment details** (Python version, OS, etc.)

### Suggesting Enhancements
Enhancement suggestions are tracked as GitHub issues. When creating an enhancement suggestion, please include:

* **Use a clear and descriptive title**
* **Provide a step-by-step description of the suggested enhancement**
* **Provide specific examples to demonstrate the steps**
* **Describe the current behavior and the expected behavior**
* **Explain why this enhancement would be useful**

### Pull Requests

* Fill in the required template
* Follow the Python styleguides (see below)
* Include appropriate test cases
* Update documentation as needed
* Ensure your branch is up-to-date with main

## Development Setup

### Prerequisites
- Python 3.13+
- uv package manager
- Git
- Anthropic API key

### Getting Started

1. **Fork and clone the repository**
```bash
git clone https://github.com/yourusername/enterprise-rag-system.git
cd enterprise-rag-system
```

2. **Install dependencies**
```bash
uv sync --group dev
```

3. **Create a feature branch**
```bash
git checkout -b feature/your-feature-name
```

4. **Set up your environment**
```bash
cp .env.example .env
# Add your ANTHROPIC_API_KEY to .env
```

5. **Start developing!**

### Running Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=backend

# Run specific test file
uv run pytest backend/tests/test_rag_system.py

# Run with verbose output
uv run pytest -v
```

### Code Quality

Before submitting a PR, ensure your code passes all checks:

```bash
# Format code
./scripts/format.sh

# Lint code
./scripts/lint.sh

# Run tests
uv run pytest
```

## Styleguides

### Python Code Style

We follow PEP 8 with some customizations:

* Use 4 spaces for indentation
* Maximum line length: 88 characters (Black default)
* Use type hints for function parameters and returns
* Write docstrings for public functions/classes

**Tools:**
- **Black** - Code formatting
- **isort** - Import sorting
- **Flake8** - Linting
- **mypy** - Type checking

Example:
```python
def semantic_search(
    query: str, 
    k: int = 5
) -> List[SearchResult]:
    """
    Perform semantic search on documents.
    
    Args:
        query: Search query string
        k: Number of results to return
        
    Returns:
        List of search results sorted by relevance
    """
    # Implementation
    return results
```

### Commit Messages

* Use the present tense ("Add feature" not "Added feature")
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...")
* Limit the first line to 72 characters or less
* Reference issues and pull requests liberally after the first line

Example:
```
Add semantic search refinement capability

This implements a second-round search based on initial results,
enabling Claude to refine searches for better accuracy.

Closes #123
Relates to #124
```

### Documentation

* Use Markdown for documentation
* Include code examples where appropriate
* Keep documentation up-to-date with code changes
* Reference related files and components

## Testing Guidelines

### Test Structure
```python
def test_feature_behavior():
    """Test that feature does X under condition Y."""
    # Arrange: Set up test data
    input_data = prepare_test_data()
    
    # Act: Execute the feature
    result = function_under_test(input_data)
    
    # Assert: Verify the result
    assert result == expected_output
```

### Test Coverage
* Aim for >85% coverage on core components
* Test both happy path and error cases
* Use fixtures for common test data
* Mock external dependencies (Claude API, etc.)

### Test Categories
Tag tests with markers:
```python
@pytest.mark.unit
def test_simple_function():
    pass

@pytest.mark.integration
def test_rag_pipeline():
    pass

@pytest.mark.slow
def test_large_document_processing():
    pass
```

## Architecture Decisions

Before implementing significant changes:

1. **Check existing patterns** - Look for similar implementations
2. **Discuss with maintainers** - Create an issue for discussion
3. **Keep it simple** - Avoid premature abstraction
4. **Document rationale** - Explain your design decisions

When modifying architecture:
- Update ARCHITECTURE.md
- Include migration notes if breaking changes
- Provide examples of new patterns

## Pull Request Process

1. Update documentation with any API changes
2. Add tests for new functionality
3. Ensure all tests pass (`uv run pytest`)
4. Run code quality checks (`./scripts/lint.sh`)
5. Request review from maintainers
6. Respond to feedback and update PR as needed

## Review Process

**What reviewers look for:**
- Code quality and style adherence
- Test coverage for new functionality
- Documentation clarity
- Performance implications
- Security considerations
- Backward compatibility

## Release Process

Releases follow semantic versioning (MAJOR.MINOR.PATCH):

* **MAJOR**: Breaking changes
* **MINOR**: New features (backward compatible)
* **PATCH**: Bug fixes

## Additional Notes

### Project Structure
- `/backend` - FastAPI application and core logic
- `/frontend` - Web interface
- `/examples` - Usage examples
- `/docs` - Documentation and guides
- `/scripts` - Development scripts

### Key Files
- `ARCHITECTURE.md` - System design and components
- `CLAUDE.md` - Development instructions
- `pyproject.toml` - Project configuration
- `README.md` - Project overview

### Questions?

* **General questions**: Open a GitHub Discussion
* **Bug reports**: Open a GitHub Issue
* **Security issues**: Please email directly (don't open public issue)

## Recognition

Contributors will be recognized in:
- README.md contributors section
- GitHub's contributor graph
- Release notes for significant contributions

---

Thank you for contributing! 🎉
