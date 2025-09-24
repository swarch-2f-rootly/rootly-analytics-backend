"""
Test configuration and fixtures for unit tests.
"""

import sys
import os
from pathlib import Path

# Add project root directory to Python path so src module can be found
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock

from src.core.domain.measurement import Measurement
from src.core.ports.measurement_repository import MeasurementRepository
from src.core.ports.logger import Logger


@pytest.fixture
def sample_measurements():
    """Fixture providing sample measurement data."""
    timestamp = datetime.now(timezone.utc)

    # Create measurements with all required attributes
    measurements = []

    m1 = Measurement(
        controller_id="device-001",
        timestamp=timestamp,
        soil_humidity=0.8,
        air_humidity=65.0,
        temperature=25.0,
        light_intensity=1500.0
    )
    measurements.append(m1)

    m2 = Measurement(
        controller_id="device-001",
        timestamp=timestamp,
        soil_humidity=0.6,
        air_humidity=70.0,
        temperature=26.0,
        light_intensity=1600.0
    )
    measurements.append(m2)

    m3 = Measurement(
        controller_id="device-002",
        timestamp=timestamp,
        soil_humidity=0.7,
        air_humidity=60.0,
        temperature=24.0,
        light_intensity=1400.0
    )
    measurements.append(m3)

    return measurements


@pytest.fixture
def mock_measurement_repository(sample_measurements):
    """Fixture providing a mock MeasurementRepository."""
    from unittest.mock import AsyncMock

    mock_repo = MagicMock(spec=MeasurementRepository)

    # Configure the mock to return sample data (async)
    mock_repo.get_measurements = AsyncMock(return_value=sample_measurements)
    mock_repo.get_measurements_by_controllers = AsyncMock(return_value=sample_measurements)
    mock_repo.health_check = AsyncMock(return_value=True)

    return mock_repo


@pytest.fixture
def mock_logger():
    """Fixture providing a mock Logger."""
    mock_logger = MagicMock(spec=Logger)
    return mock_logger
