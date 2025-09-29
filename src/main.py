"""
Main application entry point for the Analytics Service.
Sets up FastAPI app with dependency injection and error handling.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import logging
import os
from contextlib import asynccontextmanager
from datetime import datetime

from .core.services.analytics_service_impl import AnalyticsServiceImpl
from .adapters.repositories.influx_repository import InfluxRepository
from .adapters.handlers.analytics_handlers import AnalyticsHandlers
from .adapters.graphql.schema import create_graphql_router
from .core.ports.exceptions import (
    AnalyticsServiceError,
    InvalidMetricError,
    RepositoryError,
    ExternalServiceError
)

# Import configuration
from .core.config.config import config, logger

# Import error handlers
from .core.util.errorhandling import register_error_handlers


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Analytics Service...")

    # Startup
    logger.info(f"Connecting to InfluxDB at: {config.INFLUXDB_URL}")
    yield

    # Shutdown
    logger.info("Shutting down Analytics Service...")


# Create FastAPI application
app = FastAPI(
    title=config.APP_TITLE,
    description=config.APP_DESCRIPTION,
    version=config.APP_VERSION,
    docs_url=config.DOCS_URL,
    redoc_url=config.REDOC_URL,
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=config.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection setup
def get_influx_repository() -> InfluxRepository:
    """Get InfluxDB repository instance."""
    return InfluxRepository(
        url=config.INFLUXDB_URL,
        token=config.INFLUXDB_TOKEN,
        bucket=config.INFLUXDB_BUCKET,
        org=config.INFLUXDB_ORG
    )


def get_analytics_service(
    influx_repo: InfluxRepository = None
) -> AnalyticsServiceImpl:
    """Get analytics service instance with injected dependencies."""
    if influx_repo is None:
        influx_repo = get_influx_repository()

    return AnalyticsServiceImpl(
        measurement_repository=influx_repo
    )


# Setup analytics handlers
analytics_service = get_analytics_service()
analytics_handlers = AnalyticsHandlers(analytics_service)
influx_repository = get_influx_repository()

# Include REST API routes
app.include_router(analytics_handlers.router)

# Setup and include GraphQL
graphql_router = create_graphql_router(
    analytics_service=analytics_service,
    influx_repository=influx_repository,
    playground_enabled=config.GRAPHQL_PLAYGROUND_ENABLED,
    introspection_enabled=config.GRAPHQL_INTROSPECTION_ENABLED
)
app.include_router(graphql_router, prefix=config.GRAPHQL_ENDPOINT, tags=["GraphQL"])

# Register error handlers
register_error_handlers(app)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": config.APP_TITLE,
        "version": config.APP_VERSION,
        "description": config.APP_DESCRIPTION,
        "endpoints": {
            "docs": config.DOCS_URL,
            "redoc": config.REDOC_URL,
            "health": "/api/v1/analytics/health",
            "metrics": "/api/v1/analytics/metrics",
            "graphql": config.GRAPHQL_ENDPOINT,
            "playground": config.GRAPHQL_PLAYGROUND_ENDPOINT if config.GRAPHQL_PLAYGROUND_ENABLED else None
        }
    }


# Health check endpoint
@app.get("/health")
async def health_check():
    """Service health check."""
    try:
        # Check InfluxDB connectivity
        influx_repo = get_influx_repository()
        influxdb_healthy = await influx_repo.health_check()

        return {
            "status": "healthy" if influxdb_healthy else "degraded",
            "service": "analytics",
            "influxdb": "healthy" if influxdb_healthy else "unhealthy",
            "influxdb_url": config.INFLUXDB_URL,
            "timestamp": str(datetime.now().isoformat())
        }
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "service": "analytics",
                "error": str(e),
                "timestamp": str(datetime.now().isoformat())
            }
        )


if __name__ == "__main__":
    import uvicorn

    # Run the application
    uvicorn.run(
        "src.main:app",
        host=config.HOST,
        port=config.PORT,
        reload=config.RELOAD,
        log_level=config.LOG_LEVEL
    )

