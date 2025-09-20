"""
FastAPI handlers for analytics endpoints.
These handlers implement the REST API interface for the analytics service.
"""

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime
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
    MultiReportRequest,
    AnalyticsReport,
    MultiReportResponse,
    TrendAnalysis
)
from ..models import (
    SingleMetricReportResponse,
    MultiReportRequestModel,
    MultiReportResponseModel,
    TrendAnalysisResponse,
    ErrorResponse
)


class AnalyticsHandlers:
    """
    FastAPI handlers for analytics endpoints.
    Implements the REST API interface defined in the project scope.
    """

    def __init__(self, analytics_service: AnalyticsService):
        """
        Initialize handlers with analytics service dependency.
        
        Args:
            analytics_service: Implementation of the AnalyticsService port
        """
        self.analytics_service = analytics_service
        self.logger = logging.getLogger(__name__)
        
        # Create FastAPI router
        self.router = APIRouter(prefix="/api/v1/analytics", tags=["analytics"])
        self._setup_routes()

    def _setup_routes(self):
        """Setup FastAPI routes."""
        
        @self.router.get(
            "/report/{metric_name}",
            response_model=SingleMetricReportResponse,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Single Metric Report",
            description="Generate analytics report for a single sensor metric"
        )
        async def single_metric_report(
            metric_name: str,
            id_controlador: str = Query(..., description="Controller ID (required)"),
            start_time: Optional[str] = Query(None, description="Start time (ISO format)"),
            end_time: Optional[str] = Query(None, description="End time (ISO format)"),
            limit: Optional[int] = Query(None, ge=1, le=10000, description="Maximum number of records")
        ):
            return await self._handle_single_metric_report(
                metric_name, id_controlador, start_time, end_time, limit
            )

        @self.router.post(
            "/multi-report",
            response_model=MultiReportResponseModel,
            responses={
                400: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Multiple Metrics Report",
            description="Generate analytics report for multiple sensor metrics and controllers"
        )
        async def multi_report(request: MultiReportRequestModel):
            return await self._handle_multi_report(request)

        @self.router.get(
            "/trends/{metric_name}",
            response_model=TrendAnalysisResponse,
            responses={
                400: {"model": ErrorResponse},
                404: {"model": ErrorResponse},
                500: {"model": ErrorResponse}
            },
            summary="Trend Analysis",
            description="Generate trend analysis for a specific metric over time"
        )
        async def trend_analysis(
            metric_name: str,
            id_controlador: str = Query(..., description="Controller ID (required)"),
            start_time: str = Query(..., description="Start time (ISO format, required)"),
            end_time: str = Query(..., description="End time (ISO format, required)"),
            interval: str = Query("1h", description="Time interval (e.g., '1h', '1d')")
        ):
            return await self._handle_trend_analysis(
                metric_name, id_controlador, start_time, end_time, interval
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
            "/health",
            summary="Health Check",
            description="Check if the analytics service is healthy"
        )
        async def health_check():
            return {"status": "healthy", "service": "analytics", "timestamp": datetime.now()}

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

    async def _handle_multi_report(
        self, request: MultiReportRequestModel
    ) -> MultiReportResponseModel:
        """Handle multi-report request."""
        try:
            # Convert to domain object
            domain_request = request.to_domain()

            # Generate multi-report
            response = await self.analytics_service.generate_multi_report(domain_request)

            # Convert to response model
            return MultiReportResponseModel.from_domain(response)

        except InvalidMetricError as e:
            self.logger.warning(f"Invalid metric in multi-report: {e.metric_name}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid metric",
                    "message": str(e),
                    "supported_metrics": e.supported_metrics
                }
            )
        
        except ExternalServiceError as e:
            self.logger.error(f"External service error in multi-report: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )
        
        except Exception as e:
            self.logger.error(f"Unexpected error in multi-report: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while generating the multi-report"
                }
            )

    async def _handle_trend_analysis(
        self,
        metric_name: str,
        id_controlador: str,
        start_time: str,
        end_time: str,
        interval: str
    ) -> TrendAnalysisResponse:
        """Handle trend analysis request."""
        try:
            # Parse required datetime parameters
            parsed_start_time = self._parse_datetime(start_time)
            parsed_end_time = self._parse_datetime(end_time)
            
            if not parsed_start_time or not parsed_end_time:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid datetime format",
                        "message": "start_time and end_time must be valid ISO format timestamps"
                    }
                )

            # Validate time range
            if parsed_start_time >= parsed_end_time:
                raise HTTPException(
                    status_code=400,
                    detail={
                        "error": "Invalid time range",
                        "message": "start_time must be before end_time"
                    }
                )

            # Generate trend analysis
            trend = await self.analytics_service.generate_trend_analysis(
                metric_name, id_controlador, parsed_start_time, parsed_end_time, interval
            )

            # Convert to response model
            return TrendAnalysisResponse.from_domain(trend)

        except InvalidMetricError as e:
            self.logger.warning(f"Invalid metric for trend analysis: {e.metric_name}")
            raise HTTPException(
                status_code=400,
                detail={
                    "error": "Invalid metric",
                    "message": str(e),
                    "supported_metrics": e.supported_metrics
                }
            )
        
        except InsufficientDataError as e:
            self.logger.warning(f"Insufficient data for trend analysis: {e}")
            raise HTTPException(
                status_code=404,
                detail={
                    "error": "Insufficient data",
                    "message": str(e)
                }
            )
        
        except ExternalServiceError as e:
            self.logger.error(f"External service error in trend analysis: {e}")
            raise HTTPException(
                status_code=502,
                detail={
                    "error": "External service unavailable",
                    "message": f"Go backend service error: {e.message}",
                    "service": e.service_name
                }
            )
        
        except HTTPException:
            # Re-raise HTTP exceptions
            raise
        
        except Exception as e:
            self.logger.error(f"Unexpected error in trend analysis: {e}")
            raise HTTPException(
                status_code=500,
                detail={
                    "error": "Internal server error",
                    "message": "An unexpected error occurred while generating trend analysis"
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

