"""
Configuration settings for the Analytics Service.
Loads configuration from environment variables with sensible defaults.
"""

import os
from typing import List

from ...adapters.logger.standard_logger import StandardLogger
from ..ports.logger import Logger


# Configure logging using our custom logger
logger: Logger = StandardLogger("analytics")


# Configuration from environment variables
class Config:
    """Application configuration loaded from environment variables."""

    # InfluxDB configuration
    INFLUXDB_URL: str = os.getenv("INFLUXDB_URL", "http://localhost:8086")
    INFLUXDB_TOKEN: str = os.getenv("INFLUXDB_TOKEN", "your-influxdb-token-here")
    INFLUXDB_BUCKET: str = os.getenv("INFLUXDB_BUCKET", "rootly-bucket")
    INFLUXDB_ORG: str = os.getenv("INFLUXDB_ORG", "rootly-org")

    # CORS configuration - Allow all origins for maximum compatibility
    CORS_ORIGINS: List[str] = ["*"]

    # Application configuration
    APP_TITLE: str = "rootly Analytics Service"
    APP_DESCRIPTION: str = "Advanced agricultural analytics service for crop monitoring data"
    APP_VERSION: str = "1.0.0"
    DOCS_URL: str = "/docs"
    REDOC_URL: str = "/redoc"

    # GraphQL configuration
    GRAPHQL_PLAYGROUND_ENABLED: bool = os.getenv("GRAPHQL_PLAYGROUND_ENABLED", "true").lower() == "true"
    GRAPHQL_INTROSPECTION_ENABLED: bool = os.getenv("GRAPHQL_INTROSPECTION_ENABLED", "true").lower() == "true"
    GRAPHQL_ENDPOINT: str = "/api/v1/graphql"
    GRAPHQL_PLAYGROUND_ENDPOINT: str = "/api/v1/graphql/playground"

    # Server configuration
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    RELOAD: bool = os.getenv("RELOAD", "true").lower() == "true"
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "info")


# Global configuration instance
config = Config()
