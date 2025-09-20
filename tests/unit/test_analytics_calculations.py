"""
Unit tests for the AnalyticsCalculations module.
"""

import pytest
import math
from datetime import datetime, timezone
from src.core.services.analytics_calculations import AnalyticsCalculations
from src.core.domain.measurement import Measurement


class TestAnalyticsCalculations:
    """Test cases for analytics calculation functions."""

    def test_calculate_growing_degree_days_valid_data(self):
        """Test GDD calculation with valid temperature data."""
        timestamp = datetime.now(timezone.utc)

        measurements = [
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                temperature=20.0
            ),
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                temperature=25.0
            ),
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                temperature=15.0
            )
        ]

        gdd = AnalyticsCalculations.calculate_growing_degree_days(measurements, t_base=10.0)

        # GDD = ((25 + 15) / 2) - 10 = 10
        assert gdd == 10.0

    def test_calculate_growing_degree_days_no_temperature_data(self):
        """Test GDD calculation with no temperature measurements."""
        timestamp = datetime.now(timezone.utc)

        measurements = [
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                soil_humidity=0.8
            )
        ]

        gdd = AnalyticsCalculations.calculate_growing_degree_days(measurements)
        assert gdd == 0.0

    def test_calculate_growing_degree_days_empty_measurements(self):
        """Test GDD calculation with empty measurements list."""
        gdd = AnalyticsCalculations.calculate_growing_degree_days([])
        assert gdd == 0.0

    def test_calculate_growing_degree_days_negative_result(self):
        """Test GDD calculation that results in negative value (should return 0)."""
        timestamp = datetime.now(timezone.utc)

        measurements = [
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                temperature=5.0
            ),
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                temperature=8.0
            )
        ]

        # GDD = ((8 + 5) / 2) - 10 = -3.5 -> should return 0
        gdd = AnalyticsCalculations.calculate_growing_degree_days(measurements, t_base=10.0)
        assert gdd == 0.0

    def test_calculate_dew_point_valid_values(self):
        """Test dew point calculation with valid temperature and humidity."""
        dew_point = AnalyticsCalculations.calculate_dew_point(25.0, 60.0)

        # Dew point should be a reasonable value
        assert isinstance(dew_point, float)
        assert 15.0 <= dew_point <= 25.0  # Should be lower than temperature

    def test_calculate_dew_point_high_humidity(self):
        """Test dew point calculation with high humidity."""
        dew_point = AnalyticsCalculations.calculate_dew_point(25.0, 90.0)

        # High humidity should result in dew point close to temperature
        assert isinstance(dew_point, float)
        assert abs(dew_point - 25.0) < 5.0

    def test_calculate_dew_point_low_humidity(self):
        """Test dew point calculation with low humidity."""
        dew_point = AnalyticsCalculations.calculate_dew_point(25.0, 20.0)

        # Low humidity should result in much lower dew point
        assert isinstance(dew_point, float)
        assert dew_point < 15.0

    def test_calculate_dew_point_invalid_humidity_high(self):
        """Test dew point calculation with invalid high humidity."""
        with pytest.raises(ValueError, match="Humidity must be between 0 and 100"):
            AnalyticsCalculations.calculate_dew_point(25.0, 150.0)

    def test_calculate_dew_point_invalid_humidity_low(self):
        """Test dew point calculation with invalid low humidity."""
        with pytest.raises(ValueError, match="Humidity must be between 0 and 100"):
            AnalyticsCalculations.calculate_dew_point(25.0, -10.0)

    def test_calculate_dew_point_boundary_values(self):
        """Test dew point calculation with boundary humidity values."""
        # Test with valid humidity values (humidity must be > 0)
        dp_low = AnalyticsCalculations.calculate_dew_point(25.0, 0.1)
        dp_high = AnalyticsCalculations.calculate_dew_point(25.0, 100.0)

        assert isinstance(dp_low, float)
        assert isinstance(dp_high, float)

    def test_calculate_water_deficit_index_normal_conditions(self):
        """Test WDI calculation with normal soil moisture."""
        wdi = AnalyticsCalculations.calculate_water_deficit_index(0.7, 1.0, 0.0)

        # WDI = ((1.0 - 0.7) / (1.0 - 0.0)) * 100 = 30.0
        assert abs(wdi - 30.0) < 0.001  # Allow small floating point differences

    def test_calculate_water_deficit_index_dry_soil(self):
        """Test WDI calculation with dry soil."""
        wdi = AnalyticsCalculations.calculate_water_deficit_index(0.2, 1.0, 0.0)

        # WDI = ((1.0 - 0.2) / (1.0 - 0.0)) * 100 = 80.0
        assert wdi == 80.0

    def test_calculate_water_deficit_index_wet_soil(self):
        """Test WDI calculation with wet soil."""
        wdi = AnalyticsCalculations.calculate_water_deficit_index(0.9, 1.0, 0.0)

        # WDI = ((1.0 - 0.9) / (1.0 - 0.0)) * 100 = 10.0
        assert abs(wdi - 10.0) < 0.001  # Allow small floating point differences

    def test_calculate_water_deficit_index_invalid_range(self):
        """Test WDI calculation with invalid max/min values."""
        with pytest.raises(ValueError, match="max_moisture must be greater than min_moisture"):
            AnalyticsCalculations.calculate_water_deficit_index(0.5, 0.5, 0.5)

    def test_calculate_water_deficit_index_custom_range(self):
        """Test WDI calculation with custom moisture range."""
        wdi = AnalyticsCalculations.calculate_water_deficit_index(0.6, 0.8, 0.2)

        # WDI = ((0.8 - 0.6) / (0.8 - 0.2)) * 100 = 33.33...
        assert abs(wdi - 33.333) < 0.001

    def test_calculate_water_deficit_index_boundary_values(self):
        """Test WDI calculation at boundary values."""
        # At maximum moisture (no deficit)
        wdi_max = AnalyticsCalculations.calculate_water_deficit_index(1.0, 1.0, 0.0)
        assert wdi_max == 0.0

        # At minimum moisture (maximum deficit)
        wdi_min = AnalyticsCalculations.calculate_water_deficit_index(0.0, 1.0, 0.0)
        assert wdi_min == 100.0

    def test_calculate_daily_light_integral_with_data(self):
        """Test DLI calculation with light measurements."""
        # Calculate average light reading from measurements
        timestamp = datetime.now(timezone.utc)
        measurements = [
            Measurement(
                controller_id="device-001",
                timestamp=timestamp,
                light_intensity=1000.0  # lux
            )
        ]

        # Calculate average light intensity
        light_readings = [m.light_intensity for m in measurements if m.light_intensity is not None]
        if light_readings:
            avg_light = sum(light_readings) / len(light_readings)
            dli = AnalyticsCalculations.calculate_daily_light_integral(avg_light)

            # DLI = (1000 * 3600 * 24) / 1000000 = 86.4
            assert abs(dli - 86.4) < 0.1
        else:
            pytest.fail("No light measurements found")

    def test_calculate_daily_light_integral_no_light_data(self):
        """Test DLI calculation with no light measurements."""
        # When no light data is available, DLI should be 0
        dli = AnalyticsCalculations.calculate_daily_light_integral(0.0)
        assert dli == 0.0

    def test_calculate_daily_light_integral_multiple_measurements(self):
        """Test DLI calculation with multiple light measurements."""
        # Calculate average from multiple readings
        light_readings = [500.0, 1500.0, 2000.0]
        avg_light = sum(light_readings) / len(light_readings)

        dli = AnalyticsCalculations.calculate_daily_light_integral(avg_light)

        # Average light = 1333.33
        # DLI = (1333.33 * 3600 * 24) / 1000000 ≈ 115.2
        assert abs(dli - 115.2) < 1.0

    def test_calculate_vapor_pressure_deficit_valid_values(self):
        """Test VPD calculation with valid temperature and humidity."""
        vpd = AnalyticsCalculations.calculate_vapor_pressure_deficit(25.0, 60.0)

        assert isinstance(vpd, float)
        assert vpd > 0  # VPD should always be positive

    def test_vapor_pressure_deficit_high_humidity(self):
        """Test VPD calculation with high humidity (should be low VPD)."""
        vpd_low = AnalyticsCalculations.calculate_vapor_pressure_deficit(25.0, 90.0)
        vpd_high = AnalyticsCalculations.calculate_vapor_pressure_deficit(25.0, 30.0)

        assert vpd_high > vpd_low  # Lower humidity should give higher VPD

    def test_vapor_pressure_deficit_temperature_effect(self):
        """Test VPD calculation with different temperatures."""
        vpd_20 = AnalyticsCalculations.calculate_vapor_pressure_deficit(20.0, 50.0)
        vpd_30 = AnalyticsCalculations.calculate_vapor_pressure_deficit(30.0, 50.0)

        assert vpd_30 > vpd_20  # Higher temperature should give higher VPD

    @pytest.mark.parametrize("temp,humidity,expected_range", [
        (20.0, 50.0, (0.1, 1.5)),  # Typical range for moderate conditions
        (25.0, 60.0, (0.5, 2.5)),  # Slightly higher for warmer conditions
        (30.0, 70.0, (1.0, 4.0)),  # Higher for hot conditions
    ])
    def test_vapor_pressure_deficit_ranges(self, temp, humidity, expected_range):
        """Test VPD calculation produces reasonable values."""
        vpd = AnalyticsCalculations.calculate_vapor_pressure_deficit(temp, humidity)

        assert expected_range[0] <= vpd <= expected_range[1]

    def test_calculate_basic_statistics_with_data(self):
        """Test basic statistics calculation with valid data."""
        data = [10.0, 20.0, 30.0, 40.0, 50.0]

        stats = AnalyticsCalculations.calculate_basic_statistics(data)

        assert stats["mean"] == 30.0
        assert stats["min"] == 10.0
        assert stats["max"] == 50.0
        assert stats["std_dev"] > 0
        assert stats["count"] == 5

    def test_calculate_basic_statistics_empty_data(self):
        """Test basic statistics calculation with empty data."""
        stats = AnalyticsCalculations.calculate_basic_statistics([])

        assert stats["mean"] == 0.0
        assert stats["min"] == 0.0
        assert stats["max"] == 0.0
        assert stats["std_dev"] == 0.0
        assert stats["count"] == 0

    def test_calculate_basic_statistics_single_value(self):
        """Test basic statistics calculation with single value."""
        data = [42.0]

        stats = AnalyticsCalculations.calculate_basic_statistics(data)

        assert stats["mean"] == 42.0
        assert stats["min"] == 42.0
        assert stats["max"] == 42.0
        assert stats["std_dev"] == 0.0
        assert stats["count"] == 1
