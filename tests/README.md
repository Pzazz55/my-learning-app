# Tests

This directory contains the test suite for the learning application.

## Structure

- `conftest.py` - Pytest configuration and shared fixtures
- `unit/` - Unit tests for individual components
- `integration/` - Integration tests for component interactions

## Running Tests

To run the test suite:

```bash
# Run all tests
pytest

# Run only unit tests
pytest tests/unit/

# Run only integration tests
pytest tests/integration/

# Run with coverage
pytest --cov=backend --cov=middleware --cov=ui
```

## Test Categories

### Unit Tests
- `test_config.py` - Configuration file validation
- `test_storage.py` - Storage and database functionality

### Integration Tests
- `test_backend_integration.py` - Backend service integration

## Adding New Tests

1. Place unit tests in `tests/unit/`
2. Place integration tests in `tests/integration/`
3. Use descriptive test names that follow the pattern `test_<functionality>_<scenario>`
4. Add fixtures to `conftest.py` if they're shared across multiple tests