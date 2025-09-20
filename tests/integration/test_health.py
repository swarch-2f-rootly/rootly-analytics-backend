"""
Integration tests for health check endpoints.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestHealthCheck:
    """Test health check endpoints."""

    async def test_health_endpoint_returns_200(self, http_client):
        """Test that health endpoint returns success status."""
        response = await http_client.get("/health")

        assert response.status_code == 200

    async def test_health_endpoint_returns_valid_json(self, http_client):
        """Test that health endpoint returns valid JSON structure."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "service" in data
        assert "status" in data
        assert "timestamp" in data
        assert data["service"] == "analytics"

    async def test_health_endpoint_includes_service_info(self, http_client):
        """Test that health response includes service information."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert data["service"] == "analytics"
        assert "healthy" in data["status"].lower() or "degraded" in data["status"].lower()

    async def test_health_endpoint_includes_timestamp(self, http_client):
        """Test that health response includes a timestamp."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        data = response.json()

        assert "timestamp" in data
        # Should be parseable as datetime
        from datetime import datetime
        datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))

    async def test_health_endpoint_content_type(self, http_client):
        """Test that health endpoint returns JSON content type."""
        response = await http_client.get("/health")

        assert response.status_code == 200
        assert response.headers["content-type"] == "application/json"
