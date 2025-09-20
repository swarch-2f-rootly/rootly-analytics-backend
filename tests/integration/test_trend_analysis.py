"""
Integration tests for trend analysis endpoints.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestTrendAnalysis:
    """Test trend analysis endpoints."""

    async def test_trend_analysis_valid_request(self, http_client, api_base,
                                               sample_controller_id, sample_time_range):
        """Test trend analysis with valid parameters."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/temperature", params=params)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert "controller_id" in data
            assert "metric_name" in data
            assert "interval" in data
            assert "data_points" in data
            assert "total_points" in data
            assert data["controller_id"] == sample_controller_id
            assert data["metric_name"] == "temperature"
            assert data["interval"] == "1h"

    async def test_trend_analysis_missing_controller_id(self, http_client, api_base, sample_time_range):
        """Test trend analysis with missing controller_id."""
        start_time, end_time = sample_time_range

        params = {
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/temperature", params=params)

        assert response.status_code == 422  # Validation error

    async def test_trend_analysis_missing_start_time(self, http_client, api_base,
                                                   sample_controller_id, sample_time_range):
        """Test trend analysis with missing start_time."""
        _, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "end_time": end_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/temperature", params=params)

        assert response.status_code == 422  # Validation error

    async def test_trend_analysis_missing_end_time(self, http_client, api_base,
                                                 sample_controller_id, sample_time_range):
        """Test trend analysis with missing end_time."""
        start_time, _ = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/temperature", params=params)

        assert response.status_code == 422  # Validation error

    async def test_trend_analysis_invalid_metric(self, http_client, api_base,
                                                sample_controller_id, sample_time_range):
        """Test trend analysis with invalid metric."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/invalid_metric", params=params)

        assert response.status_code == 400
        data = response.json()
        assert "error" in data

    async def test_trend_analysis_different_intervals(self, http_client, api_base,
                                                     sample_controller_id, sample_time_range):
        """Test trend analysis with different time intervals."""
        start_time, end_time = sample_time_range

        intervals = ["1h", "1d", "30m"]

        for interval in intervals:
            params = {
                "controller_id": sample_controller_id,
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "interval": interval
            }

            response = await http_client.get(f"{api_base}/trends/temperature", params=params)

            assert response.status_code in [200, 404, 422]

            if response.status_code == 200:
                data = response.json()
                assert data["interval"] == interval

    async def test_trend_analysis_soil_humidity(self, http_client, api_base,
                                               sample_controller_id, sample_time_range):
        """Test trend analysis for soil humidity."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "2h"
        }

        response = await http_client.get(f"{api_base}/trends/soil_humidity", params=params)

        assert response.status_code in [200, 404, 422]

        if response.status_code == 200:
            data = response.json()
            assert data["metric_name"] == "soil_humidity"

    async def test_trend_analysis_content_type(self, http_client, api_base,
                                             sample_controller_id, sample_time_range):
        """Test that trend analysis returns JSON content type."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/temperature", params=params)

        assert response.headers["content-type"] == "application/json"

    async def test_trend_analysis_data_points_structure(self, http_client, api_base,
                                                       sample_controller_id, sample_time_range):
        """Test that trend analysis data points have correct structure."""
        start_time, end_time = sample_time_range

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "interval": "1h"
        }

        response = await http_client.get(f"{api_base}/trends/temperature", params=params)

        if response.status_code == 200:
            data = response.json()
            assert "data_points" in data
            assert isinstance(data["data_points"], list)

            # Check structure of data points if any exist
            for point in data["data_points"]:
                assert "timestamp" in point
                assert "value" in point
