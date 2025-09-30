"""
GraphQL resolvers for the Analytics Service.
Implements GraphQL query resolvers using the existing analytics service.
"""

import strawberry
from typing import List, Optional
import logging
from datetime import datetime

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
    HistoricalQueryFilter
)
from .types import (
    AnalyticsReport,
    MultiReportResponse,
    TrendAnalysis,
    HealthStatus,
    AnalyticsFilters,
    MultiMetricReportInput,
    TrendAnalysisInput,
    LatestMeasurementResponse,
    HistoricalQueryResponse,
    HistoricalQueryInput
)


# Global variables to store dependencies (will be set by create_graphql_query)
_analytics_service: Optional[AnalyticsService] = None
_influx_repository = None
_logger = logging.getLogger(__name__)


@strawberry.type
class Query:
    """GraphQL Query resolvers for Analytics Service."""

    @strawberry.field
    def get_supported_metrics(self) -> List[str]:
        """
        Get list of supported metrics available in the system.
        
        Returns:
            List of supported metric names
        """
        _logger.info("GraphQL query: getSupportedMetrics")
        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")
            metrics = _analytics_service.get_supported_metrics()
            return metrics
        except Exception as e:
            _logger.error(f"Error getting supported metrics: {e}")
            raise Exception(f"Failed to get supported metrics: {str(e)}")

    @strawberry.field
    async def get_analytics_health(self) -> HealthStatus:
        """
        Get health status of the analytics service and its dependencies.
        
        Returns:
            HealthStatus object with service status information
        """
        _logger.info("GraphQL query: getAnalyticsHealth")
        try:
            if _influx_repository is None:
                raise Exception("InfluxDB repository not initialized")
            # Check InfluxDB connectivity
            influxdb_healthy = await _influx_repository.health_check()
            
            return HealthStatus(
                status="healthy" if influxdb_healthy else "degraded",
                service="analytics",
                influxdb="healthy" if influxdb_healthy else "unhealthy",
                influxdb_url=_influx_repository.url,
                timestamp=datetime.now().isoformat()
            )
        except Exception as e:
            _logger.error(f"Health check failed: {e}")
            return HealthStatus(
                status="unhealthy",
                service="analytics",
                influxdb="unhealthy",
                influxdb_url=_influx_repository.url if _influx_repository else "unknown",
                timestamp=datetime.now().isoformat()
            )

    @strawberry.field
    async def get_latest_measurement(self, controller_id: str) -> LatestMeasurementResponse:
        """
        Get the most recent measurement for a specific controller from the last 10 minutes.

        Args:
            controller_id: ID of the controller to get the latest measurement for

        Returns:
            LatestMeasurementResponse with the most recent measurement data or null if no data

        Raises:
            Exception: If the query fails
        """
        _logger.info(f"GraphQL query: getLatestMeasurement - controller: {controller_id}")

        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")

            # Call the analytics service using the same port as REST API
            measurement = await _analytics_service.get_latest_measurement(controller_id)

            # Create response using the same logic as REST API
            response = LatestMeasurementResponse.from_measurement(controller_id, measurement)

            # Log the result
            if measurement:
                _logger.info(f"Latest measurement found for controller {controller_id}")
            else:
                _logger.info(f"No recent measurements found for controller {controller_id}")

            return response

        except Exception as e:
            _logger.error(f"Unexpected error in getLatestMeasurement: {e}")
            raise Exception(f"Failed to get latest measurement: {str(e)}")

    @strawberry.field
    async def get_historical_measurements(self, input: HistoricalQueryInput) -> HistoricalQueryResponse:
        """
        Query historical measurement data using advanced filters.

        Args:
            input: HistoricalQueryInput with optional filters for the query

        Returns:
            HistoricalQueryResponse with filtered historical measurement data

        Raises:
            Exception: If the query fails
        """
        _logger.info(f"GraphQL query: getHistoricalMeasurements - filters: {input}")

        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")

            # Convert GraphQL input to domain filters
            # Parse datetime strings
            start_time = None
            end_time = None

            if input.start_time:
                start_time = datetime.fromisoformat(input.start_time.replace('Z', '+00:00'))
            if input.end_time:
                end_time = datetime.fromisoformat(input.end_time.replace('Z', '+00:00'))

            # Create domain filters
            domain_filters = HistoricalQueryFilter(
                start_time=start_time,
                end_time=end_time,
                limit=input.limit,
                controller_id=input.controller_id,
                sensor_id=input.sensor_id,
                parameter=input.parameter
            )

            # Call the analytics service using the same port as REST API
            domain_response = await _analytics_service.query_historical_data(domain_filters)

            # Convert domain response to GraphQL type
            return HistoricalQueryResponse.from_domain(domain_response)

        except Exception as e:
            _logger.error(f"Unexpected error in getHistoricalMeasurements: {e}")
            raise Exception(f"Failed to query historical measurements: {str(e)}")

    @strawberry.field
    async def get_single_metric_report(
        self,
        metric_name: str,
        controller_id: str,
        filters: Optional[AnalyticsFilters] = None
    ) -> AnalyticsReport:
        """
        Generate analytics report for a single metric and controller.
        
        Args:
            metric_name: Name of the sensor metric (e.g., 'temperature', 'humidity')
            controller_id: ID of the controller device
            filters: Optional filters to apply to the data query
            
        Returns:
            AnalyticsReport with calculated metrics
            
        Raises:
            Exception: If report generation fails
        """
        _logger.info(f"GraphQL query: getSingleMetricReport - metric: {metric_name}, controller: {controller_id}")
        
        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")
            # Convert GraphQL filters to domain filters
            domain_filters = filters.to_domain() if filters else AnalyticsFilter()
            
            # Call the analytics service
            domain_report = await _analytics_service.generate_single_metric_report(
                metric_name=metric_name,
                controller_id=controller_id,
                filters=domain_filters
            )
            
            # Convert domain report to GraphQL type
            return AnalyticsReport.from_domain(domain_report)
            
        except InvalidMetricError as e:
            _logger.error(f"Invalid metric error: {e}")
            raise Exception(f"Invalid metric: {str(e)}")
        except InsufficientDataError as e:
            _logger.error(f"Insufficient data error: {e}")
            raise Exception(f"Insufficient data: {str(e)}")
        except AnalyticsServiceError as e:
            _logger.error(f"Analytics service error: {e}")
            raise Exception(f"Analytics error: {str(e)}")
        except Exception as e:
            _logger.error(f"Unexpected error in single metric report: {e}")
            raise Exception(f"Failed to generate report: {str(e)}")

    @strawberry.field
    async def get_multi_metric_report(
        self,
        input: MultiMetricReportInput
    ) -> MultiReportResponse:
        """
        Generate analytics reports for multiple metrics and controllers.
        
        Args:
            input: MultiMetricReportInput with controllers, metrics, and filters
            
        Returns:
            MultiReportResponse with reports for all requested combinations
            
        Raises:
            Exception: If report generation fails
        """
        _logger.info(f"GraphQL query: getMultiMetricReport - controllers: {input.controllers}, metrics: {input.metrics}")
        
        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")
            # Convert GraphQL input to domain request
            domain_filters = input.filters.to_domain() if input.filters else AnalyticsFilter()
            
            domain_request = MultiReportRequest(
                controllers=input.controllers,
                metrics=input.metrics,
                filters=domain_filters
            )
            
            # Call the analytics service
            domain_response = await _analytics_service.generate_multi_report(domain_request)
            
            # Convert domain response to GraphQL type
            return MultiReportResponse.from_domain(domain_response)
            
        except InvalidMetricError as e:
            _logger.error(f"Invalid metric error: {e}")
            raise Exception(f"Invalid metric: {str(e)}")
        except InsufficientDataError as e:
            _logger.error(f"Insufficient data error: {e}")
            raise Exception(f"Insufficient data: {str(e)}")
        except AnalyticsServiceError as e:
            _logger.error(f"Analytics service error: {e}")
            raise Exception(f"Analytics error: {str(e)}")
        except Exception as e:
            _logger.error(f"Unexpected error in multi metric report: {e}")
            raise Exception(f"Failed to generate multi-report: {str(e)}")

    @strawberry.field
    async def get_trend_analysis(
        self,
        input: TrendAnalysisInput
    ) -> TrendAnalysis:
        """
        Generate trend analysis for a specific metric over time.
        
        Args:
            input: TrendAnalysisInput with metric, controller, time range, and interval
            
        Returns:
            TrendAnalysis with time-series data and statistics
            
        Raises:
            Exception: If trend analysis fails
        """
        _logger.info(f"GraphQL query: getTrendAnalysis - metric: {input.metric_name}, controller: {input.controller_id}")
        
        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")
            # Parse datetime strings
            start_time = datetime.fromisoformat(input.start_time.replace('Z', '+00:00'))
            end_time = datetime.fromisoformat(input.end_time.replace('Z', '+00:00'))
            
            # Call the analytics service
            domain_trend = await _analytics_service.generate_trend_analysis(
                metric_name=input.metric_name,
                controller_id=input.controller_id,
                start_time=start_time,
                end_time=end_time,
                interval=input.interval
            )
            
            # Convert domain trend to GraphQL type
            return TrendAnalysis.from_domain(domain_trend)
            
        except InvalidMetricError as e:
            _logger.error(f"Invalid metric error: {e}")
            raise Exception(f"Invalid metric: {str(e)}")
        except InsufficientDataError as e:
            _logger.error(f"Insufficient data error: {e}")
            raise Exception(f"Insufficient data: {str(e)}")
        except AnalyticsServiceError as e:
            _logger.error(f"Analytics service error: {e}")
            raise Exception(f"Analytics error: {str(e)}")
        except ValueError as e:
            _logger.error(f"Invalid datetime format: {e}")
            raise Exception(f"Invalid datetime format: {str(e)}")
        except Exception as e:
            _logger.error(f"Unexpected error in trend analysis: {e}")
            raise Exception(f"Failed to generate trend analysis: {str(e)}")


def create_graphql_query(analytics_service: AnalyticsService, influx_repository) -> Query:
    """
    Factory function to create GraphQL Query with injected dependencies.
    
    Args:
        analytics_service: Implementation of the AnalyticsService port
        influx_repository: Repository for health checks
        
    Returns:
        Query instance with injected dependencies
    """
    global _analytics_service, _influx_repository
    _analytics_service = analytics_service
    _influx_repository = influx_repository
    return Query()