"""
FastAPI handlers for analytics endpoints.
These handlers implement the REST API interface for the analytics service.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timedelta
import logging

from ...core.ports.analytics_service import AnalyticsService
from ...core.ports.exceptions import (
    AnalyticsServiceError,
    InvalidMetricError,
    InsufficientDataError,
    ExternalServiceError
)
from ...core.domain.analytics import (
    AnalyticsFilter,
    AnalyticsReport,
    HistoricalQueryFilter,
    TrendAnalysis
)
from ..models import (
    SingleMetricReportResponse,
    MultiMetricReportRequest,
    MetricResultModel,
    AnalyticsFilterModel,
    ErrorResponse,
    HistoricalQueryResponseModel,
    SupportedMetricsResponse,
    LatestMeasurementResponse,
    HistoricalAveragesResponseModel
)


class AnalyticsHandlers:
    """
    FastAPI handlers for analytics endpoints.
    Implements the REST API interface defined in the project scope.
    """

    def __init__(self, analytics_service: AnalyticsService, cache_service=None):
        """
        Initialize handlers with analytics service dependency.
        
        Args:
            analytics_service: Implementation of the AnalyticsService port
            cache_service: Cache service for cache management operations (optional)
        """
        self.analytics_service = analytics_service
        self.cache_service = cache_service
        self.logger = logging.getLogger(__name__)
        
        # Create FastAPI router
        self.router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
        self._setup_routes()
        
        # Log registered routes
        route_count = len(self.router.routes)
        self.logger.info(f"Analytics router initialized with {route_count} routes")

    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.router.get(
            "/report/{metric_name}",
            response_model=SingleMetricReportResponse,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                422: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Single Metric Report",
            description="Generate analytics report for a single sensor metric"
        )
        async def single_metric_report(
            metric_name: str,
            controller_id: str = Query(..., description="Controller ID to get metrics for"),
            start_time: Optional[str] = Query(None, description="Start time for the report (ISO format)"),
            end_time: Optional[str] = Query(None, description="End time for the report (ISO format)"),
            limit: Optional[int] = Query(None, description="Maximum number of data points to return")
        ):
            self.logger.info(f"GET /report/{metric_name} called with controller_id={controller_id}")
            # Validate controller_id is not empty
            if not controller_id or not controller_id.strip():
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Validation error",
                        "message": "controller_id cannot be empty"
                    }
                )

            return await self._handle_single_metric_report(
                metric_name, controller_id, start_time, end_time, limit
            )


        @self.router.post(
            "/multi-report",
            response_model=SingleMetricReportResponse,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Multiple Metrics Report",
            description="Generate analytics report for multiple sensor metrics"
        )
        async def multi_metric_report(request: MultiMetricReportRequest):
            # Validate controller_id is not empty
            if not request.controller_id or not request.controller_id.strip():
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Validation error",
                        "message": "controller_id cannot be empty"
                    }
                )

            return await self._handle_multi_metric_report(request)


        @self.router.get(
            "/trends/{metric_name}",
            response_model=TrendAnalysis,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                422: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Trend Analysis",
            description="Returns time-series data aggregated by an interval for trend visualization"
        )
        async def trend_analysis(
            metric_name: str,
            controller_id: str = Query(..., description="Controller ID to get metrics for"),
            start_time: str = Query(..., description="Start time for the analysis (ISO format)"),
            end_time: str = Query(..., description="End time for the analysis (ISO format)"),
            interval: str = Query(..., description="Aggregation interval (e.g., '1h', '1d')")
        ):
            return await self._handle_trend_analysis(
                metric_name, controller_id, start_time, end_time, interval
            )


        @self.router.get(
            "/metrics",
            response_model=List[str],
            summary="Supported Metrics",
            description="Get list of supported metric names for analytics"
        )
        async def supported_metrics():
            return self.analytics_service.get_supported_metrics()


        @self.router.get(
            "/latest/{controller_id}",
            response_model=LatestMeasurementResponse,
            responses={
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Latest Measurement",
            description="Get the most recent measurement for a specific controller from the last 10 minutes"
        )
        async def get_latest_measurement(controller_id: str):
            return await self._handle_latest_measurement(controller_id)

        @self.router.get(
            "/historical",
            response_model=HistoricalQueryResponseModel,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Historical Measurements",
            description="Query historical measurement data using advanced filters"
        )
        async def historical_query(
            start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
            end_time: Optional[str] = Query(None, description="End time (ISO format)"),
            controller_id: Optional[str] = Query(None, description="Controller ID"),
            sensor_id: Optional[str] = Query(None, description="Sensor ID"),
            parameter: Optional[str] = Query(None, description="Measurement parameter name"),
            limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of records")
        ):
            return await self._handle_historical_query(
                start_time=start_time,
                end_time=end_time,
                controller_id=controller_id,
                sensor_id=sensor_id,
                parameter=parameter,
                limit=limit
            )

        @self.router.get(
            "/historical/averages",
            response_model=HistoricalAveragesResponseModel,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Averaged Historical Measurements",
            description="Query historical measurement data averaged over fixed intervals"
        )
        async def historical_averages(
            average_interval: int = Query(
                ...,
                description="Averaging interval in minutes (15, 30, 60, 120, 360, 720)",
                ge=1
            ),
            start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
            end_time: Optional[str] = Query(None, description="End time (ISO format)"),
            controller_id: Optional[str] = Query(None, description="Controller ID"),
            sensor_id: Optional[str] = Query(None, description="Sensor ID"),
            parameter: Optional[str] = Query(None, description="Measurement parameter name"),
            limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of records considered")
        ):
            return await self._handle_historical_averages(
                average_interval=average_interval,
                start_time=start_time,
                end_time=end_time,
                controller_id=controller_id,
                sensor_id=sensor_id,
                parameter=parameter,
                limit=limit
            )

        @self.router.get(
            "/health",
            summary="Analytics Service Health Check",
            description="Check the health status of the Analytics Service and its dependencies"
        )
        async def analytics_health_check():
            """Analytics service specific health check."""
            self.logger.info("GET /health called")
            try:
                # Get influx repository from the analytics service
                influx_repo = self.analytics_service.measurement_repository
                influxdb_healthy = await influx_repo.health_check()

                return {
                    "status": "healthy" if influxdb_healthy else "degraded",
                    "service": "analytics",
                    "influxdb": "healthy" if influxdb_healthy else "unhealthy",
                    "influxdb_url": influx_repo.url if hasattr(influx_repo, 'url') else "unknown",
                    "timestamp": str(datetime.now().isoformat())
                }
            except Exception as e:
                self.logger.error(f"Health check failed: {e}")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "status": "unhealthy",
                        "service": "analytics",
                        "error": str(e),
                        "timestamp": str(datetime.now().isoformat())
                    }
                )

        @self.router.post(
            "/cache/clear",
            summary="Clear Analytics Cache",
            description="Clear all cached analytics data from Redis. Useful for testing and debugging cache behavior."
        )
        async def clear_cache_endpoint():
            """Clear all cached data."""
            return await self.clear_cache()

    async def _handle_single_metric_report(
        self,
        metric_name: str,
        id_controlador: str,
        start_time: Optional[str],
        end_time: Optional[str],
        limit: Optional[int]
    ) -> SingleMetricReportResponse:
        """Handle single metric report request."""
        try:
            # Parse datetime parameters
            parsed_start_time = self._parse_datetime(start_time) if start_time else None
            parsed_end_time = self._parse_datetime(end_time) if end_time else None
            
            # Create filters
            filters = AnalyticsFilter(
                start_time=parsed_start_time,
                end_time=parsed_end_time,
                limit=limit
            )

            # Generate report
            report = await self.analytics_service.generate_single_metric_report(
                metric_name, id_controlador, filters
            )

            # Convert to response model
            return SingleMetricReportResponse.from_domain(report)

        except InvalidMetricError as e:
            self.logger.warning(f"Invalid metric requested: {e.metric_name}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid metric",
                    "message": str(e),
                    "supported_metrics": e.supported_metrics
                }
            )
        
        except InsufficientDataError as e:
            self.logger.warning(f"Insufficient data: {e}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Insufficient data",
                    "message": str(e)
                }
            )
        
        except ExternalServiceError as e:
            self.logger.error(f"External service error: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )
        
        except Exception as e:
            self.logger.error(f"Unexpected error in single metric report: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while generating the report"
                }
            )

    async def _handle_trend_analysis(
        self,
        metric_name: str,
        controller_id: str,
        start_time: str,
        end_time: str,
        interval: str
    ) -> TrendAnalysis:
        """Handle trend analysis request."""
        try:
            # Parse datetime parameters
            parsed_start_time = self._parse_datetime(start_time)
            parsed_end_time = self._parse_datetime(end_time)

            if parsed_start_time is None:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Invalid datetime format",
                        "message": "start_time must be a valid ISO format timestamp"
                    }
                )

            if parsed_end_time is None:
                raise HTTPException(
                    status_code=422,
                    detail={
                        "error": "Invalid datetime format",
                        "message": "end_time must be a valid ISO format timestamp"
                    }
                )

            # Generate trend analysis
            trend_analysis = await self.analytics_service.generate_trend_analysis(
                metric_name, controller_id, parsed_start_time, parsed_end_time, interval
            )

            return trend_analysis

        except InvalidMetricError as e:
            self.logger.warning(f"Invalid metric requested: {e.metric_name}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid metric",
                    "message": str(e),
                    "supported_metrics": e.supported_metrics
                }
            )

        except InsufficientDataError as e:
            self.logger.warning(f"Insufficient data: {e}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Insufficient data",
                    "message": str(e)
                }
            )

        except ExternalServiceError as e:
            self.logger.error(f"External service error: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in trend analysis: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while generating trend analysis"
                }
            )

    async def _handle_multi_metric_report(
        self, request: MultiMetricReportRequest
    ) -> SingleMetricReportResponse:
        """Handle multi-metric report request."""
        try:
            # Parse datetime parameters - if parsing fails, use None (will trigger default 30-day range)
            parsed_start_time = self._parse_datetime(request.start_time) if request.start_time else None
            parsed_end_time = self._parse_datetime(request.end_time) if request.end_time else None

            # If no time range is specified or if parsing failed for either timestamp, use last 30 days
            if not parsed_start_time and not parsed_end_time:
                now = datetime.now()
                parsed_end_time = now
                parsed_start_time = now - timedelta(days=30)
            elif not parsed_start_time or not parsed_end_time:
                # If only one timestamp is provided/valid, ignore it and use default 30-day range
                now = datetime.now()
                parsed_end_time = now
                parsed_start_time = now - timedelta(days=30)

            # Validate time range
            if parsed_start_time and parsed_end_time and parsed_start_time >= parsed_end_time:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid time range",
                        "message": "start_time must be before end_time"
                    }
                )

            # Create filters
            filters = AnalyticsFilter(
                start_time=parsed_start_time,
                end_time=parsed_end_time,
                limit=None  # No limit for multi-metric reports
            )

            # Generate reports for all metrics
            all_metrics = []
            total_data_points = 0
            latest_generated_at = None

            for metric_name in request.metrics:
                try:
                    report = await self.analytics_service.generate_single_metric_report(
                        metric_name, request.controller_id, filters
                    )

                    # Accumulate metrics
                    all_metrics.extend(report.metrics)
                    total_data_points = max(total_data_points, report.data_points_count)

                    # Keep the latest generation timestamp
                    if latest_generated_at is None or report.generated_at > latest_generated_at:
                        latest_generated_at = report.generated_at

                except InvalidMetricError as e:
                    self.logger.warning(f"Invalid metric '{metric_name}' requested: {e}")
                    raise HTTPException(
                        status_code=400,
                        detail={
                            "error": "Invalid metric",
                            "message": f"Metric '{metric_name}' is not valid",
                            "supported_metrics": e.supported_metrics
                        }
                    )

                except InsufficientDataError as e:
                    self.logger.warning(f"Insufficient data for metric '{metric_name}': {e}")
                    raise HTTPException(
                        status_code=404,
                        detail={
                            "error": "Insufficient data",
                            "message": f"Not enough data available for metric '{metric_name}': {str(e)}"
                        }
                    )

                except ExternalServiceError as e:
                    self.logger.error(f"External service error for metric '{metric_name}': {e}")
                    raise HTTPException(
                        status_code=502,
                        detail={
                            "error": "External service unavailable",
                            "message": f"Go backend service error for metric '{metric_name}': {e.message}",
                            "service": e.service_name
                        }
                    )

            # Create combined response
            return SingleMetricReportResponse(
                controller_id=request.controller_id,
                metrics=[MetricResultModel.from_domain(m) for m in all_metrics],
                generated_at=latest_generated_at,
                data_points_count=total_data_points,
                filters_applied=AnalyticsFilterModel(
                    start_time=parsed_start_time,
                    end_time=parsed_end_time,
                    limit=None
                )
            )

        except HTTPException:
            # Re-raise HTTP exceptions as they are already properly formatted
            raise

        except Exception as e:
            self.logger.error(f"Unexpected error in multi-metric report: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while generating the multi-metric report"
                }
            )


    def _parse_datetime(self, datetime_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string to datetime object."""
        if not datetime_str:
            return None
        
        try:
            # Handle ISO format with Z suffix
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str[:-1] + '+00:00'
            
            return datetime.fromisoformat(datetime_str)
        
        except ValueError as e:
            self.logger.warning(f"Invalid datetime format: {datetime_str}")
            return None

    async def _handle_historical_query(
        self,
        start_time: Optional[str],
        end_time: Optional[str],
        controller_id: Optional[str],
        sensor_id: Optional[str],
        parameter: Optional[str],
        limit: Optional[int]
    ) -> HistoricalQueryResponseModel:
        """Handle historical measurements query."""
        try:
            parsed_start_time = self._parse_datetime(start_time) if start_time else None
            parsed_end_time = self._parse_datetime(end_time) if end_time else None

            if parsed_start_time and parsed_end_time and parsed_start_time > parsed_end_time:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid time range",
                        "message": "start_time must be before end_time"
                    }
                )

            filters = HistoricalQueryFilter(
                start_time=parsed_start_time,
                end_time=parsed_end_time,
                limit=limit,
                controller_id=controller_id,
                sensor_id=sensor_id,
                parameter=parameter
            )

            response = await self.analytics_service.query_historical_data(filters)
            return HistoricalQueryResponseModel.from_domain(response)

        except InvalidMetricError as e:
            self.logger.warning(f"Invalid metric for historical query: {e.metric_name}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid metric",
                    "message": str(e),
                    "supported_metrics": e.supported_metrics
                }
            )

        except ExternalServiceError as e:
            self.logger.error(f"External service error in historical query: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in historical query: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while retrieving historical data"
                }
            )

    async def _handle_historical_averages(
        self,
        average_interval: int,
        start_time: Optional[str],
        end_time: Optional[str],
        controller_id: Optional[str],
        sensor_id: Optional[str],
        parameter: Optional[str],
        limit: Optional[int]
    ) -> HistoricalAveragesResponseModel:
        """Handle historical measurements averaging query."""
        try:
            parsed_start_time = self._parse_datetime(start_time) if start_time else None
            parsed_end_time = self._parse_datetime(end_time) if end_time else None

            if parsed_start_time and parsed_end_time and parsed_start_time > parsed_end_time:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid time range",
                        "message": "start_time must be before end_time"
                    }
                )

            filters = HistoricalQueryFilter(
                start_time=parsed_start_time,
                end_time=parsed_end_time,
                limit=limit,
                controller_id=controller_id,
                sensor_id=sensor_id,
                parameter=parameter
            )

            response = await self.analytics_service.query_historical_averages(filters, average_interval)
            return HistoricalAveragesResponseModel.from_domain(response)

        except InvalidMetricError as e:
            self.logger.warning(f"Invalid metric for historical averages query: {e.metric_name}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid metric",
                    "message": str(e),
                    "supported_metrics": e.supported_metrics
                }
            )

        except AnalyticsServiceError as e:
            self.logger.warning(f"Invalid historical averages request: {e}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid request",
                    "message": str(e)
                }
            )

        except ExternalServiceError as e:
            self.logger.error(f"External service error in historical averages query: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in historical averages query: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while retrieving averaged historical data"
                }
            )

    async def _handle_latest_measurement(
        self,
        controller_id: str
    ) -> LatestMeasurementResponse:
        """Handle latest measurement request."""
        try:
            # Get latest measurement from service
            measurement = await self.analytics_service.get_latest_measurement(controller_id)

            # Create response
            response = LatestMeasurementResponse.from_measurement(controller_id, measurement)

            # Log the result
            if measurement:
                self.logger.info(f"Latest measurement found for controller {controller_id}")
            else:
                self.logger.info(f"No recent measurements found for controller {controller_id}")

            return response

        except ExternalServiceError as e:
            self.logger.error(f"External service error in latest measurement: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )

        except Exception as e:
            self.logger.error(f"Unexpected error in latest measurement: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while retrieving latest measurement"
                }
            )
    
    async def clear_cache(self):
        """
        Clear all cached data from Redis.
        This endpoint is useful for testing and debugging cache behavior.
        
        Returns:
            dict: Confirmation message with operation status
            
        Raises:
            HTTPException: If cache clearing fails or cache service unavailable
        """
        self.logger.info("Cache clear operation requested")
        
        try:
            if self.cache_service is None:
                self.logger.warning("Cache clear requested but cache service not available")
                raise HTTPException(
                    status_code=503,
                    detail={
                        "error": "Cache service unavailable",
                        "message": "Cache service is not configured or disabled"
                    }
                )
            
            # Clear all cache data
            cleared = await self.cache_service.flush_db()
            self.logger.info(f"Cache flush_db result: {cleared}")
            
            if cleared:
                self.logger.info("Cache cleared successfully")
                return {
                    "status": "success",
                    "message": "All cached data has been cleared",
                    "timestamp": datetime.now().isoformat(),
                    "operation": "cache_clear"
                }
            else:
                self.logger.warning("Cache clear operation returned False")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "error": "Cache clear failed",
                        "message": "Cache clear operation did not complete successfully"
                    }
                )
                
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error clearing cache: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": f"An unexpected error occurred while clearing cache: {str(e)}"
                }
            )
