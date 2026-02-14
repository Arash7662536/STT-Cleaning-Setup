# Contributing to Dataset Pipeline

Thank you for your interest in contributing to the Dataset Pipeline project!

## Development Setup

1. **Fork and clone the repository**

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install development dependencies**
   ```bash
   make install-dev
   # or
   pip install -e ".[dev]"
   ```

4. **Install pre-commit hooks** (optional but recommended)
   ```bash
   pip install pre-commit
   pre-commit install
   ```

## Code Style

We follow these conventions:

- **Black** for code formatting (line length: 100)
- **isort** for import sorting
- **flake8** for linting
- **Type hints** where appropriate
- **Docstrings** for all public functions and classes

### Format your code

```bash
make format
# or
black src/ tests/
isort src/ tests/
```

### Run linters

```bash
make lint
# or
flake8 src/ tests/
mypy src/
```

## Testing

All new features should include tests.

```bash
# Run tests
make test

# Run with coverage
make test-cov

# Run specific test
pytest tests/test_config.py -v
```

### Writing Tests

- Place tests in the `tests/` directory
- Name test files as `test_*.py`
- Use descriptive test function names: `test_feature_description`
- Use pytest fixtures for common setup

Example:
```python
def test_config_loading():
    """Test that config loads correctly from YAML."""
    config = Config.from_yaml("config/config.example.yaml")
    assert config.input_dir is not None
```

## Pull Request Process

1. Create a feature branch
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. Make your changes
   - Write code
   - Add tests
   - Update documentation

3. Ensure quality checks pass
   ```bash
   make format
   make lint
   make test
   ```

4. Commit your changes
   ```bash
   git add .
   git commit -m "Add feature: description"
   ```

5. Push and create a pull request
   ```bash
   git push origin feature/your-feature-name
   ```

## Commit Message Guidelines

- Use clear, descriptive messages
- Start with a verb in imperative mood
- Keep first line under 72 characters

Examples:
- ✅ `Add validation for empty SRT files`
- ✅ `Fix chunking error with overlapping timestamps`
- ✅ `Update documentation for CLI usage`
- ❌ `Fixed stuff`
- ❌ `WIP`

## Project Structure

When adding new features, maintain the project structure:

```
src/dataset_pipeline/
├── __init__.py       # Package exports
├── cli.py           # CLI interface
├── config.py        # Configuration
├── pipeline.py      # Main orchestrator
├── chunker.py       # Chunking logic
├── merger.py        # Merging logic
├── validator.py     # Validation logic
└── utils.py         # Utilities
```

## Documentation

- Update README.md for user-facing changes
- Add docstrings to new functions/classes
- Update type hints
- Add comments for complex logic

## Questions?

Feel free to open an issue for:
- Bug reports
- Feature requests
- Questions about contributing

Thank you for contributing! 🎉
