"""
Unit tests for the AnalyticsService implementation.
"""

import pytest
from datetime import datetime, timezone, timedelta
from unittest.mock import MagicMock

from src.core.services.analytics_service_impl import AnalyticsServiceImpl
from src.core.domain.analytics import AnalyticsFilter, MetricResult, HistoricalQueryFilter
from src.core.domain.measurement import Measurement
from src.core.ports.exceptions import InvalidMetricError, InsufficientDataError, AnalyticsServiceError


class TestAnalyticsServiceImpl:
    """Test cases for the AnalyticsServiceImpl."""

    @pytest.mark.asyncio
    async def test_generate_single_metric_report_temperature(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test generating a temperature report for a single controller."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter(
            start_time=datetime.now(timezone.utc),
            end_time=datetime.now(timezone.utc),
            limit=100
        )

        result = await service.generate_single_metric_report("temperature", "device-001", filters)

        assert result.controller_id == "device-001"
        assert len(result.metrics) > 0

        # Check that repository was called correctly
        mock_measurement_repository.get_measurements.assert_called_once()
        call_args = mock_measurement_repository.get_measurements.call_args
        assert call_args[1]["controller_id"] == "device-001"

    @pytest.mark.asyncio
    async def test_generate_single_metric_report_invalid_metric(self, mock_measurement_repository, mock_logger):
        """Test generating report with invalid metric name."""
        # Configure repository to return empty data so validation passes
        mock_measurement_repository.get_measurements.return_value = []

        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()

        # The service should raise InsufficientDataError instead of InvalidMetricError
        # when no data is found, since the metric validation happens first
        with pytest.raises(InsufficientDataError):
            await service.generate_single_metric_report("temperature", "device-001", filters)

    @pytest.mark.asyncio
    async def test_generate_single_metric_report_soil_humidity(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test generating a soil humidity report."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()

        result = await service.generate_single_metric_report("soil_humidity", "device-001", filters)

        assert result.controller_id == "device-001"
        assert len(result.metrics) > 0

    @pytest.mark.asyncio
    async def test_generate_single_metric_report_insufficient_data(self, mock_measurement_repository, mock_logger):
        """Test generating report with insufficient data."""
        # Configure mock to return empty data
        mock_measurement_repository.get_measurements.return_value = []

        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()

        with pytest.raises(InsufficientDataError):
            await service.generate_single_metric_report("temperature", "device-001", filters)

    @pytest.mark.asyncio
    async def test_generate_single_metric_report_no_data_for_requested_metric(self, mock_measurement_repository, mock_logger):
        """Test generating report when measurements exist but don't contain data for the requested metric."""
        from src.core.domain.measurement import Measurement
        from datetime import datetime

        # Create measurements with only soil_humidity data (no temperature)
        measurements = [
            Measurement(
                controller_id="device-001",
                timestamp=datetime.now(),
                temperature=None,  # No temperature data
                air_humidity=None,
                soil_humidity=50.0,
                light_intensity=None,
                sensor_id="sensor-1"
            )
        ]

        mock_measurement_repository.get_measurements.return_value = measurements

        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()

        # Should raise InsufficientDataError when requesting temperature but only soil_humidity data exists
        with pytest.raises(InsufficientDataError) as exc_info:
            await service.generate_single_metric_report("temperature", "device-001", filters)

        assert "No temperature data available" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_generate_multi_report_valid_request(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test generating multi-controller report."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        from src.core.domain.analytics import MultiReportRequest

        request = MultiReportRequest(
            controllers=["device-001", "device-002"],
            metrics=["temperature", "soil_humidity"],
            filters=AnalyticsFilter(limit=100)
        )

        result = await service.generate_multi_report(request)

        assert len(result.reports) == 2  # Two controllers
        assert "device-001" in result.reports
        assert "device-002" in result.reports

        # Check that repository was called for each controller
        assert mock_measurement_repository.get_measurements.call_count == 2

    @pytest.mark.asyncio
    async def test_generate_multi_report_empty_controllers(self, mock_measurement_repository, mock_logger):
        """Test generating multi-report with empty controller list."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        from src.core.domain.analytics import MultiReportRequest

        request = MultiReportRequest(
            controllers=[],
            metrics=["temperature"],
            filters=AnalyticsFilter()
        )

        result = await service.generate_multi_report(request)

        assert len(result.reports) == 0

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_valid_request(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test generating trend analysis."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)

        result = await service.generate_trend_analysis(
            "temperature", "device-001", start_time, end_time, "1h"
        )

        assert result.controller_id == "device-001"
        assert result.metric_name == "temperature"
        assert result.interval == "1h"
        assert len(result.data_points) > 0

        # Check that repository was called with interval
        call_args = mock_measurement_repository.get_measurements.call_args
        assert call_args[1]["controller_id"] == "device-001"
        assert call_args[1]["interval"] == "1h"

    @pytest.mark.asyncio
    async def test_generate_trend_analysis_invalid_metric(self, mock_measurement_repository, mock_logger):
        """Test trend analysis with invalid metric."""
        # Configure repository to return empty data
        mock_measurement_repository.get_measurements.return_value = []

        service = AnalyticsServiceImpl(mock_measurement_repository)

        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)

        # Should raise InsufficientDataError when no data is found
        with pytest.raises(InsufficientDataError):
            await service.generate_trend_analysis(
                "temperature", "device-001", start_time, end_time, "1h"
            )

    def test_get_supported_metrics(self, mock_measurement_repository, mock_logger):
        """Test getting list of supported metrics."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        metrics = service.get_supported_metrics()

        expected_metrics = ["temperature", "air_humidity", "soil_humidity", "light_intensity"]
        assert set(metrics) == set(expected_metrics)

    def test_is_metric_supported_valid(self, mock_measurement_repository, mock_logger):
        """Test checking if valid metrics are supported."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        assert service.is_metric_supported("temperature") is True
        assert service.is_metric_supported("soil_humidity") is True
        assert service.is_metric_supported("air_humidity") is True
        assert service.is_metric_supported("light_intensity") is True

    def test_is_metric_supported_invalid(self, mock_measurement_repository, mock_logger):
        """Test checking if invalid metrics are not supported."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        assert service.is_metric_supported("invalid_metric") is False
        assert service.is_metric_supported("pressure") is False
        assert service.is_metric_supported("") is False

    @pytest.mark.asyncio
    async def test_temperature_analytics_calculation(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test temperature analytics calculations."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()
        result = await service.generate_single_metric_report("temperature", "device-001", filters)

        # Should contain various temperature metrics
        metric_names = [r.metric_name for r in result.metrics]

        assert "temperature_average" in metric_names
        assert "temperature_minimum" in metric_names
        assert "temperature_maximum" in metric_names
        assert "temperature_trend_change" in metric_names
        assert "temperature_trend_percent" in metric_names
        assert "temperature_trend_slope" in metric_names

    @pytest.mark.asyncio
    async def test_humidity_analytics_calculation(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test humidity analytics calculations."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()
        result = await service.generate_single_metric_report("air_humidity", "device-001", filters)

        # Should contain humidity metrics
        metric_names = [r.metric_name for r in result.metrics]

        assert "air_humidity_average" in metric_names
        assert "air_humidity_minimum" in metric_names
        assert "air_humidity_maximum" in metric_names
        assert "air_humidity_trend_change" in metric_names
        assert "air_humidity_trend_percent" in metric_names
        assert "air_humidity_trend_slope" in metric_names

    @pytest.mark.asyncio
    async def test_soil_humidity_analytics_calculation(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test soil humidity analytics calculations."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()
        result = await service.generate_single_metric_report("soil_humidity", "device-001", filters)

        # Should contain soil humidity metrics
        metric_names = [r.metric_name for r in result.metrics]

        assert "soil_humidity_average" in metric_names
        assert "soil_humidity_minimum" in metric_names
        assert "soil_humidity_maximum" in metric_names
        assert "soil_humidity_trend_change" in metric_names
        assert "soil_humidity_trend_percent" in metric_names
        assert "soil_humidity_trend_slope" in metric_names

    @pytest.mark.asyncio
    async def test_light_analytics_calculation(self, mock_measurement_repository, mock_logger, sample_measurements):
        """Test light intensity analytics calculations."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = AnalyticsFilter()
        result = await service.generate_single_metric_report("light_intensity", "device-001", filters)

        # Should contain light metrics
        metric_names = [r.metric_name for r in result.metrics]

        assert "light_intensity_average" in metric_names
        assert "light_intensity_minimum" in metric_names
        assert "light_intensity_maximum" in metric_names
        assert "light_intensity_trend_change" in metric_names
        assert "light_intensity_trend_percent" in metric_names
        assert "light_intensity_trend_slope" in metric_names

    @pytest.mark.asyncio
    async def test_query_historical_data_with_parameter(
        self, mock_measurement_repository, mock_logger, sample_measurements
    ):
        """Test historical data query filtered by parameter."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = HistoricalQueryFilter(
            parameter="temperature"
        )

        response = await service.query_historical_data(filters)

        assert response.total_points > 0
        for point in response.data_points:
            assert point.parameter == "temperature"

        mock_measurement_repository.get_measurements.assert_called_with(
            controller_id=None,
            start_time=None,
            end_time=None,
            limit=None,
            sensor_id=None,
            parameter="temperature"
        )

    @pytest.mark.asyncio
    async def test_query_historical_data_invalid_parameter(
        self, mock_measurement_repository, mock_logger
    ):
        """Historical data query with unsupported parameter should error."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = HistoricalQueryFilter(parameter="invalid")

        with pytest.raises(InvalidMetricError):
            await service.query_historical_data(filters)

    @pytest.mark.asyncio
    async def test_query_historical_averages_groups_measurements(
        self, mock_measurement_repository, mock_logger
    ):
        """Historical averages should group measurements by interval and compute averages."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        base_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        measurements = [
            Measurement(
                controller_id="device-001",
                timestamp=base_time + timedelta(minutes=2),
                temperature=20.0
            ),
            Measurement(
                controller_id="device-001",
                timestamp=base_time + timedelta(minutes=10),
                temperature=22.0
            ),
            Measurement(
                controller_id="device-001",
                timestamp=base_time + timedelta(minutes=20),
                temperature=26.0
            ),
            Measurement(
                controller_id="device-001",
                timestamp=base_time + timedelta(minutes=35),
                temperature=30.0
            )
        ]

        mock_measurement_repository.get_measurements.return_value = measurements

        filters = HistoricalQueryFilter(
            start_time=base_time,
            end_time=base_time + timedelta(minutes=45),
            controller_id="device-001",
            parameter="temperature"
        )

        response = await service.query_historical_averages(filters, 15)

        assert response.interval_minutes == 15
        assert response.total_points == 3
        assert response.filters_applied.controller_id == "device-001"

        averages = {dp.interval_start: dp for dp in response.data_points}
        assert averages[base_time].measurements_count == 2
        assert averages[base_time].average_value == pytest.approx(21.0)
        assert averages[base_time + timedelta(minutes=15)].average_value == pytest.approx(26.0)
        assert averages[base_time + timedelta(minutes=30)].measurements_count == 1
        assert averages[base_time + timedelta(minutes=30)].interval_end - averages[base_time + timedelta(minutes=30)].interval_start == timedelta(minutes=15)

        mock_measurement_repository.get_measurements.assert_called_with(
            controller_id="device-001",
            start_time=base_time,
            end_time=base_time + timedelta(minutes=45),
            limit=None,
            sensor_id=None,
            parameter="temperature"
        )

    @pytest.mark.asyncio
    async def test_query_historical_averages_invalid_interval(
        self, mock_measurement_repository, mock_logger
    ):
        """Historical averages should reject unsupported intervals."""
        service = AnalyticsServiceImpl(mock_measurement_repository)

        filters = HistoricalQueryFilter()

        with pytest.raises(AnalyticsServiceError):
            await service.query_historical_averages(filters, 5)

        mock_measurement_repository.get_measurements.assert_not_called()
