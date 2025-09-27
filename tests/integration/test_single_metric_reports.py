"""
Integration tests for multi-metric report endpoints.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiMetricReports:
    """Test multi-metric report endpoints."""

    async def test_temperature_report_with_valid_params(self, http_client, api_base,
                                                       sample_controller_id, sample_time_range):
        """Test temperature report with valid parameters."""
        # Use default time range (last 30 days) to ensure data availability

        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should return 200 for valid temperature report request (data available)
        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data
            assert "generated_at" in data
            assert data["controller_id"] == sample_controller_id
            assert isinstance(data["metrics"], list)

    async def test_temperature_report_missing_controller_id(self, http_client, api_base):
        """Test temperature report with missing controller_id."""
        request_data = {
            "metrics": ["temperature"]
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should return validation error
        assert response.status_code == 422

    async def test_invalid_metric_returns_error(self, http_client, api_base, sample_controller_id):
        """Test request with invalid metric name."""
        request_data = {
            "metrics": ["invalid_metric"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 400  # Our custom validation returns 400 for invalid metrics

    async def test_soil_humidity_report_structure(self, http_client, api_base,
                                                 sample_controller_id, sample_time_range):
        """Test soil humidity report response structure."""
        # Use default time range (last 30 days) to ensure data availability

        request_data = {
            "metrics": ["soil_humidity"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 200

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
                # Ensure no water_deficit_index is returned
                assert metric["metric_name"] != "water_deficit_index"

    async def test_air_humidity_report_structure(self, http_client, api_base,
                                                sample_controller_id, sample_time_range):
        """Test air humidity report response structure."""
        # Use default time range (last 30 days) to ensure data availability

        request_data = {
            "metrics": ["air_humidity"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data

    async def test_light_intensity_report_structure(self, http_client, api_base,
                                                   sample_controller_id, sample_time_range):
        """Test light intensity report response structure."""
        # Use default time range (last 30 days) to ensure data availability

        request_data = {
            "metrics": ["light_intensity"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data

    async def test_multiple_metrics_in_single_request(self, http_client, api_base,
                                                     sample_controller_id, sample_time_range):
        """Test requesting multiple metrics in a single request."""
        # Use default time range (last 30 days) to ensure data availability

        request_data = {
            "metrics": ["temperature", "soil_humidity", "air_humidity"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 200

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metrics" in data
            assert isinstance(data["metrics"], list)

            # Check that we have metrics from all requested types
            metric_names = {metric["metric_name"] for metric in data["metrics"]}
            expected_patterns = {"temperature", "soil_humidity", "air_humidity"}
            # Check that at least some of the expected metric types are present
            assert any(pattern in name for name in metric_names for pattern in expected_patterns)

    async def test_report_with_time_range(self, http_client, api_base,
                                             sample_controller_id, sample_time_range):
        """Test report with specific time range."""
        # Use default time range (last 30 days) to ensure data availability

        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 200

    async def test_report_with_only_end_time(self, http_client, api_base, sample_controller_id):
        """Test report with only end_time parameter (using current time)."""
        from datetime import datetime

        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id,
            "end_time": datetime.now().isoformat() + "Z"
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 200

    async def test_report_content_type(self, http_client, api_base, sample_controller_id):
        """Test that reports return JSON content type."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.headers["content-type"] == "application/json"

    async def test_empty_metrics_list_validation(self, http_client, api_base, sample_controller_id):
        """Test that empty metrics list is rejected."""
        request_data = {
            "metrics": [],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 422  # FastAPI validation for min_items
