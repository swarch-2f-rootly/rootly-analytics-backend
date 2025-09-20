# Tests Documentation

This directory contains comprehensive test suites for the Analytics Service.

## Test Structure

```
tests/
├── unit/                    # Unit tests
│   ├── conftest.py         # Shared fixtures for unit tests
│   ├── test_*.py          # Individual unit test files
│   └── __init__.py
├── integration/            # Integration tests
│   ├── conftest.py        # Shared fixtures for integration tests
│   ├── test_*.py          # Individual integration test files
│   └── __init__.py
└── README.md              # This file
```

## Test Types

### Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Mocking**: External dependencies are mocked
- **Scope**: Single functions, classes, or modules
- **Execution**: Can run without external services

### Integration Tests (`tests/integration/`)
- **Purpose**: Test API endpoints and service interactions
- **Dependencies**: Require running analytics service
- **Scope**: HTTP endpoints, request/response cycles
- **Execution**: Need service running on localhost:8000

## Running Tests

### Prerequisites

For integration tests, ensure the analytics service is running:
```bash
# Terminal 1: Start the service
cd rootly-analytics-backend
python -m src.main

# Terminal 2: Run tests
cd rootly-analytics-backend
```

### Run All Tests
```bash
# Run all tests (unit + integration)
pytest

# With coverage
pytest --cov=src --cov-report=html
```

### Run Unit Tests Only
```bash
# Run only unit tests
pytest tests/unit/

# With coverage
pytest tests/unit/ --cov=src --cov-report=html
```

### Run Integration Tests Only
```bash
# Run only integration tests (requires service running)
pytest -m integration

# Or explicitly
pytest tests/integration/
```

### Run Specific Test Files
```bash
# Run specific unit test file
pytest tests/unit/test_measurement.py

# Run specific integration test file
pytest tests/integration/test_health.py
```

### Run Tests with Markers
```bash
# Run only integration tests
pytest -m integration

# Run only unit tests
pytest -m "not integration"

# Run slow tests
pytest -m slow
```

### Run Tests with Different Output
```bash
# Verbose output
pytest -v

# Show less output
pytest -q

# Stop on first failure
pytest -x

# Show coverage in terminal
pytest --cov=src --cov-report=term-missing
```

## Test Configuration

### pytest.ini
- **testpaths**: Directories containing tests
- **markers**: Custom markers for test categorization
- **addopts**: Default pytest options
- **cov-fail-under**: Minimum coverage required (80%)

### Coverage Settings
- **Source**: `src/` directory
- **Reports**: Terminal and HTML format
- **Minimum Coverage**: 80%
- **Output**: `htmlcov/` directory for HTML reports

## Test Fixtures

### Unit Test Fixtures (`tests/unit/conftest.py`)
- `sample_measurements`: Mock measurement data
- `mock_measurement_repository`: Mocked repository
- `mock_logger`: Mocked logger

### Integration Test Fixtures (`tests/integration/conftest.py`)
- `base_url`: Service base URL
- `api_base`: API base path
- `http_client`: HTTP client for testing
- `sample_time_range`: Time range for testing
- `sample_controller_id`: Test controller ID
- `sample_metrics`: List of supported metrics

## Writing New Tests

### Unit Tests
```python
import pytest
from src.core.domain.measurement import Measurement

def test_measurement_creation():
    """Test measurement object creation."""
    measurement = Measurement(
        controller_id="test-001",
        timestamp=datetime.now(),
        temperature=25.0
    )

    assert measurement.controller_id == "test-001"
    assert measurement.temperature == 25.0
```

### Integration Tests
```python
import pytest

@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthCheck:
    async def test_health_endpoint(self, http_client):
        """Test health endpoint returns 200."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()
        assert "status" in data
```

## Continuous Integration

Tests are designed to run in CI/CD pipelines:

1. **Unit tests** run first (fast, no dependencies)
2. **Integration tests** run after service startup
3. **Coverage reports** generated automatically
4. **Minimum coverage** enforced (80%)

## Troubleshooting

### Integration Tests Fail
- Ensure service is running: `python -m src.main`
- Check service URL in `conftest.py`
- Verify service logs for errors

### Coverage Issues
- Run `pytest --cov=src --cov-report=html`
- Open `htmlcov/index.html` to see uncovered lines
- Add tests for uncovered code

### Import Errors
- Ensure you're in the correct directory
- Check Python path: `PYTHONPATH=src pytest`
- Verify all dependencies are installed: `pip install -r requirements.txt`
