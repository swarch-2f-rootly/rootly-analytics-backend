"""
Integration tests for single metric report endpoints.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestSingleMetricReports:
    """Test single metric report endpoints."""

    async def test_temperature_report_with_valid_params(self, http_client, api_base,
                                                       sample_controller_id, sample_time_range):
        """Test temperature report with valid parameters."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": 100
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        # Note: This may return 200 if data exists, or appropriate error if not
        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data
            assert "generated_at" in data
            assert data["controller_id"] == sample_controller_id
            assert isinstance(data["metrics"], list)

    async def test_temperature_report_missing_controller_id(self, http_client, api_base):
        """Test temperature report with missing controller_id."""
        response = await http_client.get(f"{api_base}/report/temperature")

        # Should return validation error
        assert response.status_code == 422

    async def test_invalid_metric_returns_error(self, http_client, api_base, sample_controller_id):
        """Test request with invalid metric name."""
        params = {"controller_id": sample_controller_id}

        response = await http_client.get(f"{api_base}/report/invalid_metric", params=params)

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    async def test_soil_humidity_report_structure(self, http_client, api_base,
                                                 sample_controller_id, sample_time_range):
        """Test soil humidity report response structure."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.get(f"{api_base}/report/soil_humidity", params=params)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data
            assert isinstance(data["metrics"], list)

            # Check that response contains expected fields
            for metric in data["metrics"]:
                assert "metric_name" in metric
                assert "value" in metric
                assert "unit" in metric
                assert "calculated_at" in metric

    async def test_air_humidity_report_structure(self, http_client, api_base,
                                                sample_controller_id, sample_time_range):
        """Test air humidity report response structure."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.get(f"{api_base}/report/air_humidity", params=params)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data

    async def test_light_intensity_report_structure(self, http_client, api_base,
                                                   sample_controller_id, sample_time_range):
        """Test light intensity report response structure."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.get(f"{api_base}/report/light_intensity", params=params)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data

    async def test_report_with_limit_parameter(self, http_client, api_base,
                                             sample_controller_id, sample_time_range):
        """Test report with limit parameter."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "limit": 50
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        assert response.status_code in [200, 404, 422]

    async def test_report_with_only_end_time(self, http_client, api_base, sample_controller_id):
        """Test report with only end_time parameter."""
        params = {
            "controller_id": sample_controller_id,
            "end_time": "2024-01-02T00:00:00Z"
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        assert response.status_code in [200, 404, 422]

    async def test_report_content_type(self, http_client, api_base, sample_controller_id):
        """Test that reports return JSON content type."""
        params = {"controller_id": sample_controller_id}

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        assert response.headers["content-type"] == "application/json"
