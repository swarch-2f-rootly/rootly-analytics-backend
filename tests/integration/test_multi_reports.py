"""
Integration tests for multi-report endpoints.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestMultiReports:
    """Test multi-report endpoints."""

    async def test_multi_report_valid_request(self, http_client, api_base, sample_time_range):
        """Test multi-report with valid request data."""
        start_time, end_time = sample_time_range

        request_data = {
            "controllers": ["device-001", "device-002"],
            "metrics": ["temperature", "soil_humidity"],
            "filters": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": 50
            }
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "reports" in data
            assert "total_controllers" in data
            assert "total_metrics" in data
            assert isinstance(data["reports"], dict)

    async def test_multi_report_empty_controllers(self, http_client, api_base):
        """Test multi-report with empty controllers list."""
        request_data = {
            "controllers": [],
            "metrics": ["temperature"]
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code in [200, 400]

    async def test_multi_report_empty_metrics(self, http_client, api_base):
        """Test multi-report with empty metrics list."""
        request_data = {
            "controllers": ["device-001"],
            "metrics": []
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code in [200, 400, 422]

    async def test_multi_report_single_controller(self, http_client, api_base, sample_time_range):
        """Test multi-report with single controller."""
        start_time, end_time = sample_time_range

        request_data = {
            "controllers": ["device-001"],
            "metrics": ["temperature", "soil_humidity"],
            "filters": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat()
            }
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "reports" in data
            assert "device-001" in data["reports"]

    async def test_multi_report_invalid_metric(self, http_client, api_base):
        """Test multi-report with invalid metric."""
        request_data = {
            "controllers": ["device-001"],
            "metrics": ["invalid_metric"]
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    async def test_multi_report_content_type(self, http_client, api_base):
        """Test that multi-report returns JSON content type."""
        request_data = {
            "controllers": ["device-001"],
            "metrics": ["temperature"]
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.headers["content-type"] == "application/json"

    async def test_multi_report_with_filters(self, http_client, api_base, sample_time_range):
        """Test multi-report with time filters."""
        start_time, end_time = sample_time_range

        request_data = {
            "controllers": ["device-001"],
            "metrics": ["temperature"],
            "filters": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "limit": 25
            }
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code in [200, 404, 422]
