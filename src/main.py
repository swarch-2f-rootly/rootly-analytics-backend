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
from .adapters.cache.redis_cache import RedisCache
from .core.ports.cache_service import CacheService
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
    
    # Initialize services
    cache_service = await get_cache_service()
    analytics_service = await get_analytics_service(cache_service=cache_service)
    influx_repository = get_influx_repository()
    
    # Store services in app state for access in endpoints
    app.state.cache_service = cache_service
    app.state.analytics_service = analytics_service
    app.state.influx_repository = influx_repository
    
    # Setup routes during startup
    analytics_handlers = AnalyticsHandlers(app.state.analytics_service, app.state.cache_service)
    
    # Include REST API routes
    app.include_router(analytics_handlers.router)
    logger.info("REST API router configured successfully")
    
    # Setup and include GraphQL
    graphql_router = create_graphql_router(
        analytics_service=app.state.analytics_service,
        influx_repository=app.state.influx_repository,
        cache_service=app.state.cache_service,
        playground_enabled=config.GRAPHQL_PLAYGROUND_ENABLED,
        introspection_enabled=config.GRAPHQL_INTROSPECTION_ENABLED
    )
    app.include_router(graphql_router, prefix=config.GRAPHQL_ENDPOINT, tags=["GraphQL"])
    
    logger.info("GraphQL router configured successfully")
    
    yield

    # Shutdown
    logger.info("Shutting down Analytics Service...")
    
    # Cleanup cache connection
    if hasattr(app.state, 'cache_service') and app.state.cache_service:
        await app.state.cache_service.disconnect()


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


async def get_cache_service() -> CacheService:
    """Get cache service instance."""
    if not config.REDIS_ENABLED:
        logger.info("Redis cache is disabled")
        return None
    
    try:
        redis_cache = RedisCache(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASSWORD,
            db=config.REDIS_DB,
            default_ttl=config.CACHE_DEFAULT_TTL,
            logger=logger
        )
        
        # Test connection
        if await redis_cache.connect():
            logger.info("Redis cache connected successfully")
            return redis_cache
        else:
            logger.warning("Failed to connect to Redis cache, running without cache")
            return None
    except Exception as e:
        logger.error(f"Error initializing cache service: {e}")
        return None


async def get_analytics_service(
    influx_repo: InfluxRepository = None,
    cache_service: CacheService = None
) -> AnalyticsServiceImpl:
    """Get analytics service instance with injected dependencies."""
    if influx_repo is None:
        influx_repo = get_influx_repository()
    
    if cache_service is None:
        cache_service = await get_cache_service()

    return AnalyticsServiceImpl(
        measurement_repository=influx_repo,
        cache_service=cache_service
    )


# Routes are now configured in lifespan startup

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

