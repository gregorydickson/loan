# Test Runner Documentation

This directory contains comprehensive test runners for the Loan Document Extraction System.

## Available Test Runners

### 1. Full Test Suite (`run_tests.py` or `run_tests.sh`)

The comprehensive test runner that executes all test suites separately with detailed output.

**Features:**
- 🎨 Beautiful ASCII art banner
- 📊 Separate execution of unit, extraction, and integration tests
- 📈 Coverage reports (terminal and HTML)
- ⏱️ Detailed timing for each test suite
- 📋 Comprehensive summary with pass/fail statistics
- 🎨 Color-coded output for easy reading

**Usage:**
```bash
# Using Python directly
python3 run_tests.py

# Using shell wrapper (auto-activates venv if present)
./run_tests.sh
```

### 2. Quick Test Runner (`run_tests_quick.py`)

Fast test runner that executes all tests in a single pass.

**Features:**
- ⚡ Faster execution (single pytest invocation)
- 🎨 ASCII art banner
- 📊 Combined coverage report
- ⏱️ Total duration timing

**Usage:**
```bash
python3 run_tests_quick.py
```

## Test Organization

```
tests/
├── unit/              # Unit tests for individual components
├── extraction/        # Tests for extraction logic
└── integration/       # End-to-end integration tests
```

## Test Commands Reference

### Run Specific Test Suites

```bash
# Unit tests only
pytest tests/unit -v

# Extraction tests only
pytest tests/extraction -v

# Integration tests only
pytest tests/integration -v -m integration

# Run with coverage
pytest tests/ --cov=src --cov-report=term-missing

# Run tests in parallel (faster)
pytest tests/ -n auto

# Run specific test file
pytest tests/unit/test_document_service.py -v

# Run specific test function
pytest tests/unit/test_document_service.py::test_create_document -v
```

### Coverage Commands

```bash
# Generate coverage report
coverage report

# Generate HTML coverage report
coverage html

# View HTML report (opens in browser)
open htmlcov/index.html
```

### Advanced Options

```bash
# Run with verbose output and show print statements
pytest tests/ -v -s

# Run only failed tests from last run
pytest --lf

# Run tests matching a pattern
pytest -k "document" -v

# Stop on first failure
pytest -x

# Show local variables in tracebacks
pytest -l
```

## Coverage Requirements

The project maintains a minimum coverage threshold of **80%** as configured in `pyproject.toml`.

Current coverage status is displayed at the end of each test run.

## Continuous Integration

These test runners are designed to be used both locally and in CI/CD pipelines.

**Exit Codes:**
- `0`: All tests passed
- `1`: One or more tests failed

## Test Markers

Tests are organized using pytest markers:

- `@pytest.mark.integration`: Integration tests (can be skipped with `-m "not integration"`)

## Configuration

Test configuration is managed in `pyproject.toml`:

```toml
[tool.pytest.ini_options]
testpaths = ["tests"]
asyncio_mode = "auto"
asyncio_default_fixture_loop_scope = "function"
addopts = "-v --cov=src --cov-report=term-missing"
```

## Troubleshooting

### Tests are slow
- Use the quick runner: `python3 run_tests_quick.py`
- Run tests in parallel: `pytest tests/ -n auto`
- Skip integration tests: `pytest tests/ -m "not integration"`

### Coverage report not found
- Make sure tests have been run at least once
- Run: `coverage html` to regenerate the HTML report

### Import errors
- Ensure you're in the backend directory
- Activate your virtual environment
- Install dev dependencies: `pip install -e ".[dev]"`

## Contributing

When adding new tests:
1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Mark integration tests with `@pytest.mark.integration`
4. Ensure new code maintains the 80% coverage threshold
5. Run the full test suite before committing

## Examples

```bash
# Full test run before committing
./run_tests.sh

# Quick check during development
python3 run_tests_quick.py

# Debug a specific failing test
pytest tests/unit/test_document_service.py::test_create_document -v -s

# Check coverage for a specific module
pytest tests/unit/test_document_service.py --cov=src.services.document_service --cov-report=term-missing
```
