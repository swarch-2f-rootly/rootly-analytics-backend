#!/usr/bin/env python3
"""
Example script for testing the Analytics Service API endpoints.
This demonstrates basic usage of the analytics service API.
"""

import asyncio
import httpx
from datetime import datetime, timedelta


BASE_URL = "http://localhost:8000"
API_BASE = f"{BASE_URL}/api/v1/analytics"


async def test_health():
    """Test service health check."""
    print("Testing health check...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{BASE_URL}/health")
        print(f"Health check status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Service: {data.get('service')}")
            print(f"Status: {data.get('status')}")


async def test_supported_metrics():
    """Test getting supported metrics."""
    print("\nTesting supported metrics...")

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/metrics")
        print(f"Supported metrics status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            # API returns list directly, not wrapped in object
            if isinstance(data, list):
                print(f"Supported metrics: {data}")
                print(f"Number of metrics: {len(data)}")
            else:
                print(f"Unexpected response format: {data}")


async def test_single_metric():
    """Test single metric report."""
    print("\nTesting single metric report...")

    params = {
        "controller_id": "device-001",
        "start_time": (datetime.now() - timedelta(hours=24)).isoformat(),
        "end_time": datetime.now().isoformat(),
        "limit": 100
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE}/report/temperature", params=params)
        print(f"Single metric status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            print(f"Controller: {data.get('controller_id')}")
            print(f"Metrics count: {len(data.get('metrics', []))}")
        elif response.status_code == 404:
            print("No data found (expected if no sensor data exists)")
        else:
            print(f"Unexpected status: {response.status_code}")


async def main():
    """Run example tests."""
    print("Analytics Service API Example\n")

    try:
        await test_health()
        await test_supported_metrics()
        await test_single_metric()

        print("\nExample completed successfully!")
        print(f"API Documentation: {BASE_URL}/docs")

    except Exception as e:
        print(f"Error during testing: {e}")
        print("Make sure the analytics service is running.")


if __name__ == "__main__":
    asyncio.run(main())





