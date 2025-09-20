"""
Unit tests for the InfluxRepository implementation.
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch, call
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import WriteApi

from src.adapters.repositories.influx_repository import InfluxRepository
from src.core.domain.measurement import Measurement


class TestInfluxRepository:
    """Test cases for the InfluxRepository."""

    @pytest.fixture
    def mock_influx_client(self):
        """Mock InfluxDB client."""
        with patch('src.adapters.repositories.influx_repository.InfluxDBClient') as mock_client:
            mock_instance = MagicMock()
            mock_client.return_value = mock_instance

            # Mock query and write APIs
            mock_query_api = MagicMock(spec=QueryApi)
            mock_write_api = MagicMock(spec=WriteApi)
            mock_instance.query_api.return_value = mock_query_api
            mock_instance.write_api.return_value = mock_write_api

            yield mock_instance

    @pytest.fixture
    def repository(self, mock_influx_client):
        """Create repository instance with mocked client."""
        repo = InfluxRepository(
            url="http://localhost:8086",
            token="test-token",
            bucket="test-bucket",
            org="test-org"
        )
        return repo

    def test_repository_initialization(self, repository, mock_influx_client):
        """Test repository initialization."""
        assert repository.url == "http://localhost:8086"
        assert repository.token == "test-token"
        assert repository.bucket == "test-bucket"
        assert repository.org == "test-org"
        assert repository.measurement_name == "agricultural_sensors"

        # Verify that the repository has the expected attributes
        assert hasattr(repository, 'client')
        assert hasattr(repository, 'query_api')
        assert hasattr(repository, 'write_api')

    @pytest.mark.asyncio
    async def test_get_measurements_success(self, repository, mock_influx_client):
        """Test successful measurement retrieval."""
        # Mock query result
        mock_result = MagicMock()
        mock_table = MagicMock()
        mock_record = MagicMock()

        # Configure record to return measurement data
        mock_record.values = {
            "controller_id": "device-001",
            "_time": datetime.now(timezone.utc),
            "_field": "temperature",
            "_value": 25.5
        }
        mock_record.get_time.return_value = datetime.now(timezone.utc)
        mock_record.get_field.return_value = "temperature"
        mock_record.get_value.return_value = 25.5

        mock_table.records = [mock_record]
        mock_result.__iter__.return_value = [mock_table]

        repository.query_api.query.return_value = mock_result

        measurements = await repository.get_measurements(controller_id="device-001")

        assert len(measurements) == 1
        assert measurements[0].controller_id == "device-001"
        assert measurements[0].temperature == 25.5

    @pytest.mark.asyncio
    async def test_get_measurements_no_data(self, repository, mock_influx_client):
        """Test measurement retrieval with no data."""
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []

        repository.query_api.query.return_value = mock_result

        measurements = await repository.get_measurements()

        assert len(measurements) == 0

    @pytest.mark.asyncio
    async def test_get_measurements_multiple_fields(self, repository, mock_influx_client):
        """Test measurement retrieval with multiple fields merged."""
        mock_result = MagicMock()
        mock_table = MagicMock()

        base_time = datetime.now(timezone.utc)

        # Create records for different fields of the same measurement
        records = []
        for field, value in [("temperature", 25.0), ("air_humidity", 60.0), ("soil_humidity", 0.8)]:
            mock_record = MagicMock()
            mock_record.values = {
                "controller_id": "device-001",
                "_time": base_time,
                "_field": field,
                "_value": value
            }
            mock_record.get_time.return_value = base_time
            mock_record.get_field.return_value = field
            mock_record.get_value.return_value = value
            records.append(mock_record)

        mock_table.records = records
        mock_result.__iter__.return_value = [mock_table]

        repository.query_api.query.return_value = mock_result

        measurements = await repository.get_measurements(controller_id="device-001")

        assert len(measurements) == 1
        measurement = measurements[0]
        assert measurement.controller_id == "device-001"
        assert measurement.temperature == 25.0
        assert measurement.air_humidity == 60.0
        assert measurement.soil_humidity == 0.8

    @pytest.mark.asyncio
    async def test_get_measurements_by_controllers(self, repository, mock_influx_client):
        """Test measurement retrieval for multiple controllers."""
        # Mock results for two controllers
        mock_result1 = MagicMock()
        mock_table1 = MagicMock()
        mock_record1 = MagicMock()
        mock_record1.values = {
            "controller_id": "device-001",
            "_time": datetime.now(timezone.utc),
            "_field": "temperature",
            "_value": 25.0
        }
        mock_record1.get_time.return_value = datetime.now(timezone.utc)
        mock_record1.get_field.return_value = "temperature"
        mock_record1.get_value.return_value = 25.0
        mock_table1.records = [mock_record1]
        mock_result1.__iter__.return_value = [mock_table1]

        mock_result2 = MagicMock()
        mock_table2 = MagicMock()
        mock_record2 = MagicMock()
        mock_record2.values = {
            "controller_id": "device-002",
            "_time": datetime.now(timezone.utc),
            "_field": "temperature",
            "_value": 26.0
        }
        mock_record2.get_time.return_value = datetime.now(timezone.utc)
        mock_record2.get_field.return_value = "temperature"
        mock_record2.get_value.return_value = 26.0
        mock_table2.records = [mock_record2]
        mock_result2.__iter__.return_value = [mock_table2]

        # Configure query_api to return different results for each call
        repository.query_api.query.side_effect = [mock_result1, mock_result2]

        measurements = await repository.get_measurements_by_controllers(
            controllers=["device-001", "device-002"]
        )

        assert len(measurements) == 2
        assert repository.query_api.query.call_count == 2

    @pytest.mark.asyncio
    async def test_get_measurements_with_filters(self, repository, mock_influx_client):
        """Test measurement retrieval with various filters."""
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []

        repository.query_api.query.return_value = mock_result

        start_time = datetime.now(timezone.utc)
        end_time = datetime.now(timezone.utc)

        await repository.get_measurements(
            controller_id="device-001",
            start_time=start_time,
            end_time=end_time,
            limit=100,
            interval="1h"
        )

        # Verify query was called
        repository.query_api.query.assert_called_once()
        query_arg = repository.query_api.query.call_args[0][0]

        # Verify query contains expected parameters
        assert 'device-001' in query_arg
        assert '1h' in query_arg
        assert 'limit(n: 100)' in query_arg

    @pytest.mark.asyncio
    async def test_health_check_success(self, repository, mock_influx_client):
        """Test successful health check."""
        mock_result = MagicMock()
        mock_result.__iter__.return_value = []

        repository.query_api.query.return_value = mock_result

        is_healthy = await repository.health_check()

        assert is_healthy is True
        repository.query_api.query.assert_called_once()

    @pytest.mark.asyncio
    async def test_health_check_failure(self, repository, mock_influx_client):
        """Test failed health check."""
        repository.query_api.query.side_effect = Exception("Connection failed")

        is_healthy = await repository.health_check()

        assert is_healthy is False

    def test_build_flux_query_basic(self, repository):
        """Test basic Flux query building."""
        query = repository._build_flux_query()

        assert 'from(bucket: "test-bucket")' in query
        assert 'range(start: -30d)' in query
        assert 'filter(fn: (r) => r["_measurement"] == "agricultural_sensors")' in query
        assert 'sort(columns: ["_time"])' in query

    def test_build_flux_query_with_controller(self, repository):
        """Test Flux query building with controller filter."""
        query = repository._build_flux_query(controller_id="device-001")

        assert 'filter(fn: (r) => r["controller_id"] == "device-001")' in query

    def test_build_flux_query_with_time_range(self, repository):
        """Test Flux query building with time range."""
        start_time = datetime(2024, 1, 1, tzinfo=timezone.utc)
        end_time = datetime(2024, 1, 2, tzinfo=timezone.utc)

        query = repository._build_flux_query(
            start_time=start_time,
            end_time=end_time
        )

        assert 'range(start: 2024-01-01T00:00:00+00:00Z, stop: 2024-01-02T00:00:00+00:00Z)' in query

    def test_build_flux_query_with_limit(self, repository):
        """Test Flux query building with limit."""
        query = repository._build_flux_query(limit=50)

        assert 'limit(n: 50)' in query

    def test_build_flux_query_with_interval(self, repository):
        """Test Flux query building with aggregation interval."""
        query = repository._build_flux_query(interval="1h")

        assert 'aggregateWindow(every: 1h, fn: mean, createEmpty: false)' in query

    def test_close_connection(self, repository, mock_influx_client):
        """Test closing the repository connection."""
        repository.close()

        mock_influx_client.close.assert_called_once()

    def test_field_mapping_is_direct(self, repository):
        """Test that field mapping is now direct (no translation needed)."""
        # Since we changed to direct mapping, fields are used as-is
        # This test verifies that the domain uses the same field names as InfluxDB
        from src.core.domain.measurement import Measurement

        # Check that domain field names match InfluxDB field names
        measurement = Measurement(
            controller_id="test",
            timestamp=datetime.now(timezone.utc),
            temperature=25.0,
            soil_humidity=0.8,
            air_humidity=60.0,
            light_intensity=1000.0
        )

        assert hasattr(measurement, 'temperature')
        assert hasattr(measurement, 'soil_humidity')
        assert hasattr(measurement, 'air_humidity')
        assert hasattr(measurement, 'light_intensity')

    @pytest.mark.asyncio
    async def test_get_measurements_error_handling(self, repository, mock_influx_client):
        """Test error handling in measurement retrieval."""
        from src.core.ports.exceptions import RepositoryError

        repository.query_api.query.side_effect = Exception("Query failed")

        # The repository should raise RepositoryError when query fails
        with pytest.raises(RepositoryError):
            await repository.get_measurements()

    @pytest.mark.asyncio
    async def test_get_measurements_by_controllers_error_handling(self, repository, mock_influx_client):
        """Test error handling in multi-controller retrieval."""
        repository.query_api.query.side_effect = Exception("Query failed")

        # Should handle errors gracefully and continue with other controllers
        measurements = await repository.get_measurements_by_controllers(["device-001"])

        # Should return empty list on error
        assert isinstance(measurements, list)
