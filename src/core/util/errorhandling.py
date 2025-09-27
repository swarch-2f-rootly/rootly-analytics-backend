"""
Error handling utilities for the Analytics Service.
Provides centralized exception handlers for FastAPI application.
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from ..ports.exceptions import (
    AnalyticsServiceError,
    InvalidMetricError,
    RepositoryError,
    ExternalServiceError
)


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


def register_error_handlers(app: FastAPI):
    """
    Register all exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """
    app.add_exception_handler(InvalidMetricError, invalid_metric_handler)
    app.add_exception_handler(ExternalServiceError, external_service_handler)
    app.add_exception_handler(RepositoryError, repository_error_handler)
    app.add_exception_handler(AnalyticsServiceError, analytics_service_error_handler)
