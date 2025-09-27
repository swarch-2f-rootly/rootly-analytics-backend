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

        assert response.status_code == 422  # FastAPI returns 422 for malformed JSON

    async def test_empty_json_body_returns_validation_error(self, http_client, api_base):
        """Test that empty JSON body returns validation error."""
        response = await http_client.post(f"{api_base}/multi-report", json={})

        assert response.status_code == 422

    async def test_invalid_datetime_format(self, http_client, api_base, sample_controller_id):
        """Test invalid datetime format in parameters - should use default 30-day range."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id,
            "start_time": "invalid-date",
            "end_time": "2024-01-02T00:00:00Z"
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should succeed and use default 30-day range since invalid timestamps are ignored
        assert response.status_code == 200

    async def test_literal_string_timestamps_use_default_range(self, http_client, api_base, sample_controller_id):
        """Test that literal string timestamps like 'string' use default 30-day range."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id,
            "start_time": "string",
            "end_time": "string"
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should succeed and use default 30-day range
        assert response.status_code == 200
        response_data = response.json()
        assert "filters_applied" in response_data
        # Verify that the filters show the 30-day default range was applied
        filters = response_data["filters_applied"]
        assert filters["start_time"] is not None
        assert filters["end_time"] is not None

    async def test_no_timestamps_use_default_30_days(self, http_client, api_base, sample_controller_id):
        """Test that omitting timestamps uses default 30-day range."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should succeed and use default 30-day range
        assert response.status_code == 200
        response_data = response.json()
        assert "filters_applied" in response_data
        filters = response_data["filters_applied"]
        assert filters["start_time"] is not None
        assert filters["end_time"] is not None

    async def test_future_start_time(self, http_client, api_base, sample_controller_id):
        """Test with start time in the future."""
        from datetime import datetime, timedelta

        future_time = datetime.now() + timedelta(days=1)
        end_time = datetime.now() + timedelta(days=2)

        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id,
            "start_time": future_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Future dates return 404 when no data exists
        assert response.status_code == 404

    async def test_end_time_before_start_time(self, http_client, api_base, sample_controller_id):
        """Test with end time before start time."""
        from datetime import datetime, timedelta

        end_time = datetime.now() - timedelta(days=1)
        start_time = datetime.now()

        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id,
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat()
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should return bad request for invalid time range
        assert response.status_code == 400

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
        assert response.status_code == 404  # No data found for very old dates

    async def test_default_time_range_last_30_days(self, http_client, api_base, sample_controller_id):
        """Test report generation with default time range (last 30 days)."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": sample_controller_id
            # No start_time or end_time specified - should use last 30 days
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Should handle gracefully with default time range (data available)
        assert response.status_code == 200

    async def test_special_characters_in_controller_id(self, http_client, api_base):
        """Test with special characters in controller_id."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": "device-001<script>alert('xss')</script>"
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        # Controller with special characters doesn't exist, should return 404
        assert response.status_code == 404

    async def test_empty_controller_id(self, http_client, api_base):
        """Test with empty controller_id."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": ""
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 422  # Validation error

    async def test_null_values_in_report_request(self, http_client, api_base):
        """Test report request with null controller_id."""
        request_data = {
            "metrics": ["temperature"],
            "controller_id": None
        }

        response = await http_client.post(f"{api_base}/multi-report", json=request_data)

        assert response.status_code == 422

    async def test_timeout_simulation(self, http_client, api_base, sample_controller_id):
        """Test behavior with potential timeouts (using short timeout)."""
        import httpx

        # Create client with very short timeout
        timeout_client = httpx.AsyncClient(
            base_url=http_client.base_url,
            timeout=0.001  # Very short timeout
        )

        try:
            request_data = {
                "metrics": ["temperature"],
                "controller_id": sample_controller_id
            }
            response = await timeout_client.post(f"{api_base}/multi-report", json=request_data)

            # Should timeout with very short timeout
            assert response.status_code == 408

        except httpx.TimeoutException:
            # This is expected with such a short timeout
            pass
        finally:
            await timeout_client.aclose()
