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
from .adapters.logger.standard_logger import StandardLogger
from .core.ports.logger import Logger
from .core.ports.exceptions import (
    AnalyticsServiceError,
    InvalidMetricError,
    RepositoryError,
    ExternalServiceError
)


# Configure logging using our custom logger
logger: Logger = StandardLogger("analytics")


# Configuration from environment variables
INFLUXDB_URL = os.getenv("INFLUXDB_URL", "http://localhost:8086")
INFLUXDB_TOKEN = os.getenv("INFLUXDB_TOKEN", "your-influxdb-token-here")
INFLUXDB_BUCKET = os.getenv("INFLUXDB_BUCKET", "rootly-bucket")
INFLUXDB_ORG = os.getenv("INFLUXDB_ORG", "rootly-org")
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "*").split(",")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    logger.info("Starting Analytics Service...")

    # Startup
    logger.info(f"Connecting to InfluxDB at: {INFLUXDB_URL}")
    yield

    # Shutdown
    logger.info("Shutting down Analytics Service...")


# Create FastAPI application
app = FastAPI(
    title="rootly Analytics Service",
    description="Advanced agricultural analytics service for crop monitoring data",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Dependency injection setup
def get_influx_repository() -> InfluxRepository:
    """Get InfluxDB repository instance."""
    return InfluxRepository(
        url=INFLUXDB_URL,
        token=INFLUXDB_TOKEN,
        bucket=INFLUXDB_BUCKET,
        org=INFLUXDB_ORG
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

# Include analytics routes
app.include_router(analytics_handlers.router)


# Global exception handlers
@app.exception_handler(InvalidMetricError)
async def invalid_metric_handler(request: Request, exc: InvalidMetricError):
    """Handle invalid metric errors."""
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid metric",
            "message": str(exc),
            "supported_metrics": exc.supported_metrics,
            "timestamp": str(exc.__class__.__name__)
        }
    )


@app.exception_handler(ExternalServiceError)
async def external_service_handler(request: Request, exc: ExternalServiceError):
    """Handle external service errors."""
    return JSONResponse(
        status_code=502,
        content={
            "error": "External service error",
            "message": f"Service '{exc.service_name}' is unavailable",
            "details": exc.details,
            "status_code": exc.status_code,
            "timestamp": str(exc.__class__.__name__)
        }
    )


@app.exception_handler(RepositoryError)
async def repository_error_handler(request: Request, exc: RepositoryError):
    """Handle repository errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Data access error",
            "message": exc.message,
            "details": exc.details,
            "timestamp": str(exc.__class__.__name__)
        }
    )


@app.exception_handler(AnalyticsServiceError)
async def analytics_service_error_handler(request: Request, exc: AnalyticsServiceError):
    """Handle general analytics service errors."""
    return JSONResponse(
        status_code=500,
        content={
            "error": "Analytics service error",
            "message": exc.message,
            "details": exc.details,
            "timestamp": str(exc.__class__.__name__)
        }
    )


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint with service information."""
    return {
        "service": "rootly Analytics Service",
        "version": "1.0.0",
        "description": "Advanced agricultural analytics for crop monitoring",
        "endpoints": {
            "docs": "/docs",
            "redoc": "/redoc",
            "health": "/api/v1/analytics/health",
            "metrics": "/api/v1/analytics/metrics"
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
            "influxdb_url": INFLUXDB_URL,
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
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )

