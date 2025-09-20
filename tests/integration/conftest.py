"""
Configuration for integration tests.
"""

import pytest
import httpx
from datetime import datetime, timedelta


@pytest.fixture
def base_url():
    """Base URL for the analytics service."""
    return "http://localhost:8000"


@pytest.fixture
def api_base(base_url):
    """API base URL."""
    return f"{base_url}/api/v1/analytics"


@pytest.fixture
async def http_client(base_url):
    """HTTP client for testing."""
    async with httpx.AsyncClient(base_url=base_url, timeout=30.0) as client:
        yield client


@pytest.fixture
def sample_time_range():
    """Sample time range for testing."""
    end_time = datetime.now()
    start_time = end_time - timedelta(hours=24)
    return start_time, end_time


@pytest.fixture
def sample_controller_id():
    """Sample controller ID for testing."""
    return "device-001"


@pytest.fixture
def sample_metrics():
    """Sample metrics list."""
    return ["temperature", "soil_humidity", "air_humidity", "light_intensity"]
