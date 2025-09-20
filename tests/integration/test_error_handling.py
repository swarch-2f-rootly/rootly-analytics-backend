"""
Integration tests for error handling and edge cases.
"""

import pytest


@pytest.mark.integration
@pytest.mark.asyncio
class TestErrorHandling:
    """Test error handling and edge cases."""

    async def test_invalid_endpoint_returns_404(self, http_client):
        """Test that invalid endpoints return 404."""
        response = await http_client.get("/api/v1/analytics/invalid-endpoint")

        assert response.status_code == 404

    async def test_invalid_method_returns_405(self, http_client, api_base):
        """Test that invalid HTTP methods return 405."""
        response = await http_client.put(f"{api_base}/metrics")

        assert response.status_code == 405

    async def test_malformed_json_returns_400(self, http_client, api_base):
        """Test that malformed JSON in POST requests returns 400."""
        response = await http_client.post(
            f"{api_base}/multi-report",
            content="{invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 400

    async def test_empty_json_body_returns_validation_error(self, http_client, api_base):
        """Test that empty JSON body returns validation error."""
        response = await http_client.post(f"{api_base}/multi-report", json={})

        assert response.status_code in [400, 422]

    async def test_invalid_datetime_format(self, http_client, api_base, sample_controller_id):
        """Test invalid datetime format in parameters."""
        params = {
            "controller_id": sample_controller_id,
            "start_time": "invalid-date",
            "end_time": "2024-01-02T00:00:00Z"
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        assert response.status_code == 422

    async def test_future_start_time(self, http_client, api_base, sample_controller_id):
        """Test with start time in the future."""
        from datetime import datetime, timedelta

        future_time = datetime.now() + timedelta(days=1)
        end_time = datetime.now() + timedelta(days=2)

        params = {
            "controller_id": sample_controller_id,
            "start_time": future_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        # Should handle gracefully (may return empty results or validation error)
        assert response.status_code in [200, 400, 422]

    async def test_end_time_before_start_time(self, http_client, api_base, sample_controller_id):
        """Test with end time before start time."""
        from datetime import datetime, timedelta

        end_time = datetime.now() - timedelta(days=1)
        start_time = datetime.now()

        params = {
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        # Should handle gracefully or return validation error
        assert response.status_code in [200, 400, 422]

    async def test_very_old_dates(self, http_client, api_base, sample_controller_id):
        """Test with very old dates."""
        from datetime import datetime

        old_start = datetime(2000, 1, 1)
        old_end = datetime(2000, 1, 2)

        params = {
            "controller_id": sample_controller_id,
            "start_time": old_start.isoformat(),
            "end_time": old_end.isoformat()
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        # Should handle gracefully (likely return empty results)
        assert response.status_code in [200, 404]

    async def test_extremely_large_limit(self, http_client, api_base, sample_controller_id):
        """Test with extremely large limit parameter."""
        params = {
            "controller_id": sample_controller_id,
            "limit": 1000000  # Very large limit
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        # Should handle gracefully or return validation error
        assert response.status_code in [200, 400, 422]

    async def test_special_characters_in_controller_id(self, http_client, api_base):
        """Test with special characters in controller_id."""
        params = {
            "controller_id": "device-001<script>alert('xss')</script>",
            "limit": 10
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        # Should handle gracefully or validate input
        assert response.status_code in [200, 400, 422]

    async def test_empty_controller_id(self, http_client, api_base):
        """Test with empty controller_id."""
        params = {
            "controller_id": "",
            "limit": 10
        }

        response = await http_client.get(f"{api_base}/report/temperature", params=params)

        assert response.status_code == 422  # Validation error

    async def test_null_values_in_multi_report(self, http_client, api_base):
        """Test multi-report with null values."""
        request_data = {
            "controllers": None,
            "metrics": ["temperature"]
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code in [400, 422]

    async def test_timeout_simulation(self, http_client, api_base, sample_controller_id):
        """Test behavior with potential timeouts (using short timeout)."""
        import httpx

        # Create client with very short timeout
        timeout_client = httpx.AsyncClient(
            base_url=http_client.base_url,
            timeout=0.001  # Very short timeout
        )

        try:
            params = {"controller_id": sample_controller_id}
            response = await timeout_client.get(f"{api_base}/report/temperature", params=params)

            # May timeout or succeed depending on service speed
            assert response.status_code in [200, 404, 408, 504]

        except httpx.TimeoutException:
            # This is expected with such a short timeout
            pass
        finally:
            await timeout_client.aclose()
