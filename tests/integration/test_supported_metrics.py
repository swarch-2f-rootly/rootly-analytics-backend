"""
Integration tests for supported metrics endpoint.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestSupportedMetrics:
    """Test supported metrics endpoint."""

    async def test_get_supported_metrics_returns_200(self, http_client, api_base):
        """Test that supported metrics endpoint returns success."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200

    async def test_get_supported_metrics_returns_list(self, http_client, api_base):
        """Test that supported metrics returns a list of metrics."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "metrics" in data
        assert isinstance(data["metrics"], list)
        assert len(data["metrics"]) > 0

    async def test_supported_metrics_includes_temperature(self, http_client, api_base):
        """Test that temperature is in supported metrics."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "temperature" in data["metrics"]

    async def test_supported_metrics_includes_soil_humidity(self, http_client, api_base):
        """Test that soil_humidity is in supported metrics."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "soil_humidity" in data["metrics"]

    async def test_supported_metrics_includes_air_humidity(self, http_client, api_base):
        """Test that air_humidity is in supported metrics."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "air_humidity" in data["metrics"]

    async def test_supported_metrics_includes_light_intensity(self, http_client, api_base):
        """Test that light_intensity is in supported metrics."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        data = response.json()

        assert "light_intensity" in data["metrics"]

    async def test_supported_metrics_content_type(self, http_client, api_base):
        """Test that supported metrics returns JSON content type."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"

    async def test_supported_metrics_no_query_params(self, http_client, api_base):
        """Test that supported metrics works without query parameters."""
        response = await http_client.get(f"{api_base}/metrics")

        assert response.status_code == 200
        data = response.json()
        assert "metrics" in data
