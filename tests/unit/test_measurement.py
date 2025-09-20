"""
Unit tests for the Measurement domain entity.
"""

import pytest
from datetime import datetime, timezone
from src.core.domain.measurement import Measurement


class TestMeasurement:
    """Test cases for the Measurement domain entity."""

    def test_measurement_creation_valid(self):
        """Test creating a valid measurement."""
        timestamp = datetime.now(timezone.utc)

        measurement = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            soil_humidity=0.7,
            air_humidity=65.0,
            temperature=25.5,
            light_intensity=1500.0
        )

        assert measurement.controller_id == "device-001"
        assert measurement.timestamp == timestamp
        assert measurement.soil_humidity == 0.7
        assert measurement.air_humidity == 65.0
        assert measurement.temperature == 25.5
        assert measurement.light_intensity == 1500.0

    def test_measurement_creation_minimal(self):
        """Test creating a measurement with minimal required fields."""
        timestamp = datetime.now(timezone.utc)

        measurement = Measurement(
            controller_id="device-001",
            timestamp=timestamp
        )

        assert measurement.controller_id == "device-001"
        assert measurement.timestamp == timestamp
        assert measurement.soil_humidity is None
        assert measurement.air_humidity is None
        assert measurement.temperature is None
        assert measurement.light_intensity is None

    def test_measurement_controller_id_required(self):
        """Test that controller_id is required."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="controller_id is required"):
            Measurement(
                controller_id="",
                timestamp=timestamp
            )

        with pytest.raises(ValueError, match="controller_id is required"):
            Measurement(
                controller_id=None,
                timestamp=timestamp
            )

    @pytest.mark.parametrize("invalid_soil_humidity", [-0.1, 1.1, -1.0, 2.0])
    def test_measurement_soil_humidity_validation(self, invalid_soil_humidity):
        """Test soil humidity validation."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="soil_humidity must be between 0 and 1"):
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                soil_humidity=invalid_soil_humidity
            )

    @pytest.mark.parametrize("invalid_air_humidity", [-1.0, -0.1, 100.1, 150.0])
    def test_measurement_air_humidity_validation(self, invalid_air_humidity):
        """Test air humidity validation."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="air_humidity must be between 0 and 100"):
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                air_humidity=invalid_air_humidity
            )

    @pytest.mark.parametrize("invalid_temperature", [-51.0, -100.0, 61.0, 100.0])
    def test_measurement_temperature_validation(self, invalid_temperature):
        """Test temperature validation."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="temperature must be between -50 and 60"):
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                temperature=invalid_temperature
            )

    @pytest.mark.parametrize("invalid_light_intensity", [-1.0, -100.0, -0.1])
    def test_measurement_light_intensity_validation(self, invalid_light_intensity):
        """Test light intensity validation."""
        timestamp = datetime.now(timezone.utc)

        with pytest.raises(ValueError, match="light_intensity must be non-negative"):
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                light_intensity=invalid_light_intensity
            )

    def test_measurement_has_temperature_property(self):
        """Test the has_temperature property."""
        timestamp = datetime.now(timezone.utc)

        measurement_with_temp = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            temperature=25.0
        )

        measurement_without_temp = Measurement(
            controller_id="device-001",
            timestamp=timestamp
        )

        assert measurement_with_temp.has_temperature is True
        assert measurement_without_temp.has_temperature is False

    def test_measurement_has_humidity_air_property(self):
        """Test the has_humidity_air property."""
        timestamp = datetime.now(timezone.utc)

        measurement_with_humidity = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            air_humidity=60.0
        )

        measurement_without_humidity = Measurement(
            controller_id="device-001",
            timestamp=timestamp
        )

        assert measurement_with_humidity.has_humidity_air is True
        assert measurement_without_humidity.has_humidity_air is False

    def test_measurement_has_humidity_soil_property(self):
        """Test the has_humidity_soil property."""
        timestamp = datetime.now(timezone.utc)

        measurement_with_soil = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            soil_humidity=0.8
        )

        measurement_without_soil = Measurement(
            controller_id="device-001",
            timestamp=timestamp
        )

        assert measurement_with_soil.has_humidity_soil is True
        assert measurement_without_soil.has_humidity_soil is False

    def test_measurement_has_light_property(self):
        """Test the has_light property."""
        timestamp = datetime.now(timezone.utc)

        measurement_with_light = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            light_intensity=1200.0
        )

        measurement_without_light = Measurement(
            controller_id="device-001",
            timestamp=timestamp
        )

        assert measurement_with_light.has_light is True
        assert measurement_without_light.has_light is False

    @pytest.mark.parametrize("valid_soil_humidity", [0.0, 0.5, 1.0, 0.25, 0.75])
    def test_measurement_valid_soil_humidity_values(self, valid_soil_humidity):
        """Test valid soil humidity values."""
        timestamp = datetime.now(timezone.utc)

        measurement = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            soil_humidity=valid_soil_humidity
        )

        assert measurement.soil_humidity == valid_soil_humidity

    @pytest.mark.parametrize("valid_air_humidity", [0.0, 50.0, 100.0, 25.5, 75.0])
    def test_measurement_valid_air_humidity_values(self, valid_air_humidity):
        """Test valid air humidity values."""
        timestamp = datetime.now(timezone.utc)

        measurement = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            air_humidity=valid_air_humidity
        )

        assert measurement.air_humidity == valid_air_humidity

    @pytest.mark.parametrize("valid_temperature", [-50.0, 0.0, 25.0, 60.0, -25.5, 45.5])
    def test_measurement_valid_temperature_values(self, valid_temperature):
        """Test valid temperature values."""
        timestamp = datetime.now(timezone.utc)

        measurement = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            temperature=valid_temperature
        )

        assert measurement.temperature == valid_temperature

    @pytest.mark.parametrize("valid_light_intensity", [0.0, 100.0, 1000.0, 5000.0, 10000.0])
    def test_measurement_valid_light_intensity_values(self, valid_light_intensity):
        """Test valid light intensity values."""
        timestamp = datetime.now(timezone.utc)

        measurement = Measurement(
            controller_id="device-001",
            timestamp=timestamp,
            light_intensity=valid_light_intensity
        )

        assert measurement.light_intensity == valid_light_intensity
