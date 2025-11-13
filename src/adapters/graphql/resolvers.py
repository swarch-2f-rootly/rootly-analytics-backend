"""
GraphQL resolvers for the Analytics Service.
Implements GraphQL query resolvers using the existing analytics service.
"""

import strawberry
from typing import List, Optional
import logging
from datetime import datetime

from ...core.ports.analytics_service import AnalyticsService
from ...core.ports.cache_service import CacheService, CacheKeyPatterns, CacheTTL
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
    HistoricalQueryInput,
    ComprehensiveAnalyticsInput,
    ComprehensiveAnalyticsReport
)


# Global variables to store dependencies (will be set by create_graphql_query)
_analytics_service: Optional[AnalyticsService] = None
_influx_repository = None
_cache_service = None
_logger = logging.getLogger(__name__)


@strawberry.type
class Query:
    """GraphQL Query resolvers for Analytics Service."""

    @strawberry.field
    async def get_supported_metrics(self) -> List[str]:
        """
        Get list of supported metrics available in the system.
        
        Returns:
            List of supported metric names
        """
        _logger.info("GraphQL query: getSupportedMetrics")
        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")
            
            # Try to get from cache first
            if _cache_service:
                cache_key = CacheKeyPatterns.GRAPHQL_SUPPORTED_METRICS
                cached_metrics = await _cache_service.get_json(cache_key)
                if cached_metrics:
                    _logger.debug("Returning supported metrics from cache")
                    return cached_metrics
            
            # Get from service
            metrics = _analytics_service.get_supported_metrics()
            
            # Cache the result
            if _cache_service and metrics:
                await _cache_service.set_json(CacheKeyPatterns.GRAPHQL_SUPPORTED_METRICS, metrics, CacheTTL.VERY_LONG)
            
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
            
            # Check if real-time data is requested
            is_real_time = domain_filters.real_time if domain_filters.real_time is not None else False
            
            # Try to get from cache first (only if not real-time)
            if _cache_service and not is_real_time:
                cache_key = _cache_service.generate_cache_key(
                    CacheKeyPatterns.GRAPHQL_SINGLE_METRIC,
                    metric=metric_name,
                    controller=controller_id,
                    start=domain_filters.start_time.isoformat() if domain_filters.start_time else None,
                    end=domain_filters.end_time.isoformat() if domain_filters.end_time else None,
                    limit=domain_filters.limit
                )
                
                cached_report = await _cache_service.get_json(cache_key)
                if cached_report:
                    _logger.debug(f"Returning single metric report from cache for {metric_name}")
                    # Deserialize cached domain report
                    cached_domain_report = _analytics_service._deserialize_analytics_report(cached_report)
                    return AnalyticsReport.from_domain(cached_domain_report)
            
            # Call the analytics service
            domain_report = await _analytics_service.generate_single_metric_report(
                metric_name=metric_name,
                controller_id=controller_id,
                filters=domain_filters
            )
            
            # Convert domain report to GraphQL type
            graphql_report = AnalyticsReport.from_domain(domain_report)
            
            # Cache the result with appropriate TTL
            if _cache_service and graphql_report:
                cache_key = _cache_service.generate_cache_key(
                    CacheKeyPatterns.GRAPHQL_SINGLE_METRIC,
                    metric=metric_name,
                    controller=controller_id,
                    start=domain_filters.start_time.isoformat() if domain_filters.start_time else None,
                    end=domain_filters.end_time.isoformat() if domain_filters.end_time else None,
                    limit=domain_filters.limit
                )
                # Use shorter TTL for real-time requests to still benefit from minimal caching
                ttl = CacheTTL.REAL_TIME if is_real_time else CacheTTL.MEDIUM
                # Serialize domain report for caching  
                serialized_report = _analytics_service._serialize_analytics_report(domain_report)
                await _cache_service.set_json(cache_key, serialized_report, ttl)
                
                if is_real_time:
                    _logger.debug(f"Cached single metric report with real-time TTL ({CacheTTL.REAL_TIME}s)")
                else:
                    _logger.debug(f"Cached single metric report with standard TTL ({CacheTTL.MEDIUM}s)")
            
            return graphql_report
            
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
            
            # Check if real-time data is requested
            is_real_time = domain_filters.real_time if domain_filters.real_time is not None else False
            
            # Try to get from cache first (only if not real-time)
            if _cache_service and not is_real_time:
                cache_key = _cache_service.generate_cache_key(
                    CacheKeyPatterns.GRAPHQL_MULTI_REPORT,
                    controllers=",".join(sorted(input.controllers)),
                    metrics=",".join(sorted(input.metrics)),
                    start=domain_filters.start_time.isoformat() if domain_filters.start_time else None,
                    end=domain_filters.end_time.isoformat() if domain_filters.end_time else None,
                    limit=domain_filters.limit
                )
                
                cached_response = await _cache_service.get_json(cache_key)
                if cached_response:
                    _logger.debug("Returning multi metric report from cache")
                    # Deserialize cached domain response
                    reports = {
                        controller_id: _analytics_service._deserialize_analytics_report(report_data)
                        for controller_id, report_data in cached_response["reports"].items()
                    }
                    from ...core.domain.analytics import MultiReportResponse as DomainMultiReportResponse
                    from datetime import datetime
                    cached_domain_response = DomainMultiReportResponse(
                        reports=reports,
                        generated_at=datetime.fromisoformat(cached_response["generated_at"]),
                        total_controllers=cached_response["total_controllers"],
                        total_metrics=cached_response["total_metrics"]
                    )
                    return MultiReportResponse.from_domain(cached_domain_response)
            
            domain_request = MultiReportRequest(
                controllers=input.controllers,
                metrics=input.metrics,
                filters=domain_filters
            )
            
            # Call the analytics service
            domain_response = await _analytics_service.generate_multi_report(domain_request)
            
            # Convert domain response to GraphQL type
            graphql_response = MultiReportResponse.from_domain(domain_response)
            
            # Cache the result with appropriate TTL
            if _cache_service and domain_response:
                cache_key = _cache_service.generate_cache_key(
                    CacheKeyPatterns.GRAPHQL_MULTI_REPORT,
                    controllers=",".join(sorted(input.controllers)),
                    metrics=",".join(sorted(input.metrics)),
                    start=domain_filters.start_time.isoformat() if domain_filters.start_time else None,
                    end=domain_filters.end_time.isoformat() if domain_filters.end_time else None,
                    limit=domain_filters.limit
                )
                # Serialize domain response for caching
                cache_data = {
                    "reports": {
                        controller_id: _analytics_service._serialize_analytics_report(report)
                        for controller_id, report in domain_response.reports.items()
                    },
                    "generated_at": domain_response.generated_at.isoformat(),
                    "total_controllers": domain_response.total_controllers,
                    "total_metrics": domain_response.total_metrics
                }
                # Use shorter TTL for real-time requests
                ttl = CacheTTL.REAL_TIME if is_real_time else CacheTTL.MEDIUM
                await _cache_service.set_json(cache_key, cache_data, ttl)
                
                if is_real_time:
                    _logger.debug(f"Cached multi metric report with real-time TTL ({CacheTTL.REAL_TIME}s)")
                else:
                    _logger.debug(f"Cached multi metric report with standard TTL ({CacheTTL.MEDIUM}s)")
            
            return graphql_response
            
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
            
            # Check if real-time data is requested
            is_real_time = input.real_time if input.real_time is not None else False
            
            # Try to get from cache first (only if not real-time)
            if _cache_service and not is_real_time:
                cache_key = _cache_service.generate_cache_key(
                    CacheKeyPatterns.GRAPHQL_TREND_ANALYSIS,
                    metric=input.metric_name,
                    controller=input.controller_id,
                    start=start_time.isoformat(),
                    end=end_time.isoformat(),
                    interval=input.interval
                )
                
                cached_trend = await _cache_service.get_json(cache_key)
                if cached_trend:
                    _logger.debug(f"Returning trend analysis from cache for {input.metric_name}")
                    # Deserialize cached domain trend
                    cached_domain_trend = _analytics_service._deserialize_trend_analysis(cached_trend)
                    return TrendAnalysis.from_domain(cached_domain_trend)
            
            # Call the analytics service
            domain_trend = await _analytics_service.generate_trend_analysis(
                metric_name=input.metric_name,
                controller_id=input.controller_id,
                start_time=start_time,
                end_time=end_time,
                interval=input.interval,
                real_time=is_real_time
            )
            
            # Convert domain trend to GraphQL type
            graphql_trend = TrendAnalysis.from_domain(domain_trend)
            
            # Cache the result with appropriate TTL
            if _cache_service and graphql_trend:
                cache_key = _cache_service.generate_cache_key(
                    CacheKeyPatterns.GRAPHQL_TREND_ANALYSIS,
                    metric=input.metric_name,
                    controller=input.controller_id,
                    start=start_time.isoformat(),
                    end=end_time.isoformat(),
                    interval=input.interval
                )
                # Use shorter TTL for real-time requests
                ttl = CacheTTL.REAL_TIME if is_real_time else CacheTTL.LONG
                # Serialize domain trend for caching
                serialized_trend = _analytics_service._serialize_trend_analysis(domain_trend)
                await _cache_service.set_json(cache_key, serialized_trend, ttl)
                
                if is_real_time:
                    _logger.debug(f"Cached trend analysis with real-time TTL ({CacheTTL.REAL_TIME}s)")
                else:
                    _logger.debug(f"Cached trend analysis with standard TTL ({CacheTTL.LONG}s)")
            
            return graphql_trend
            
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

    @strawberry.field
    async def get_comprehensive_analytics_report(
        self,
        input: ComprehensiveAnalyticsInput
    ) -> ComprehensiveAnalyticsReport:
        """
        Generate comprehensive analytics report with extensive statistical calculations.
        This demonstrates cache performance benefits with computationally expensive operations.
        
        Args:
            input: ComprehensiveAnalyticsInput with controllers, metrics, and filters
            
        Returns:
            ComprehensiveAnalyticsReport with detailed analytics and performance metrics
            
        Raises:
            Exception: If report generation fails
        """
        _logger.info(f"GraphQL query: getComprehensiveAnalyticsReport - controllers: {len(input.controller_ids)}, metrics: {len(input.metrics)}")
        
        try:
            if _analytics_service is None:
                raise Exception("Analytics service not initialized")
            
            # Convert GraphQL input to domain filters
            domain_filters = input.filters.to_domain() if input.filters else AnalyticsFilter()
            
            # Log cache strategy being used
            cache_strategy = "real-time (bypass cache)" if domain_filters.real_time else "cached"
            _logger.info(f"Using cache strategy: {cache_strategy}")
            
            # Call the expensive analytics service method
            comprehensive_data = await _analytics_service.generate_comprehensive_analytics_report(
                controller_ids=input.controller_ids,
                metrics=input.metrics,
                filters=domain_filters
            )
            
            # Log performance metrics for demonstration
            performance = comprehensive_data.get("performance", {})
            execution_time = performance.get("execution_time_ms", 0)
            cache_hit = performance.get("cache_hit", False)
            data_source = performance.get("data_source", "unknown")
            
            _logger.info(
                f"Comprehensive analytics completed: "
                f"execution_time={execution_time}ms, "
                f"cache_hit={cache_hit}, "
                f"data_source={data_source}, "
                f"controllers={len(input.controller_ids)}, "
                f"metrics={len(input.metrics)}"
            )
            
            # Convert to GraphQL response
            return ComprehensiveAnalyticsReport.from_dict(comprehensive_data)
            
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
            _logger.error(f"Unexpected error in comprehensive analytics: {e}")
            raise Exception(f"Failed to generate comprehensive report: {str(e)}")


def create_graphql_query(analytics_service: AnalyticsService, influx_repository, cache_service: Optional[CacheService] = None) -> Query:
    """
    Factory function to create GraphQL Query with injected dependencies.
    
    Args:
        analytics_service: Implementation of the AnalyticsService port
        influx_repository: Repository for health checks
        cache_service: Cache service for improved performance (optional)
        
    Returns:
        Query instance with injected dependencies
    """
    global _analytics_service, _influx_repository, _cache_service
    _analytics_service = analytics_service
    _influx_repository = influx_repository
    _cache_service = cache_service
    return Query()