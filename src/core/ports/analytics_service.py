from abc import ABC, abstractmethod
from typing import List, Optional, Dict, Any
from datetime import datetime

from ..domain.measurement import Measurement
from ..domain.analytics import (
    AnalyticsReport,
    MultiReportRequest,
    MultiReportResponse,
    TrendAnalysis,
    AnalyticsFilter,
    HistoricalQueryResponse,
    HistoricalQueryFilter,
    HistoricalAveragesResponse
)


class AnalyticsService(ABC):
    """
    Port (interface) for analytics business logic.
    This defines the contract for analytics operations and calculations.
    """

    @abstractmethod
    async def generate_single_metric_report(
        self,
        metric_name: str,
        controller_id: str,
        filters: AnalyticsFilter
    ) -> AnalyticsReport:
        """
        Generate analytics report for a single metric and controller.
        
        Args:
            metric_name: Name of the sensor metric (e.g., 'temperatura', 'humedad_tierra')
            controller_id: ID of the controller device
            filters: Filters to apply to the data query
            
        Returns:
            AnalyticsReport with calculated metrics
            
        Raises:
            AnalyticsServiceError: If calculation fails
            InvalidMetricError: If metric name is not supported
        """
        pass

    @abstractmethod
    async def generate_multi_report(
        self,
        request: MultiReportRequest
    ) -> MultiReportResponse:
        """
        Generate analytics report for multiple metrics and controllers.
        
        Args:
            request: Multi-report request with controllers, metrics, and filters
            
        Returns:
            MultiReportResponse with reports for each controller
            
        Raises:
            AnalyticsServiceError: If calculation fails
        """
        pass

    @abstractmethod
    async def generate_trend_analysis(
        self,
        metric_name: str,
        controller_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str,
        real_time: bool = False
    ) -> TrendAnalysis:
        """
        Generate trend analysis for a specific metric over time.
        
        Args:
            metric_name: Name of the sensor metric
            controller_id: ID of the controller device
            start_time: Start time for trend analysis
            end_time: End time for trend analysis
            interval: Time interval for data aggregation (e.g., '1h', '1d')
            real_time: Whether to bypass cache for real-time data
            
        Returns:
            TrendAnalysis with time-series data
            
        Raises:
            AnalyticsServiceError: If calculation fails
            InvalidMetricError: If metric name is not supported
        """
        pass

    @abstractmethod
    def get_supported_metrics(self) -> List[str]:
        """
        Get list of supported metric names.
        
        Returns:
            List of supported metric names
        """
        pass

    @abstractmethod
    def is_metric_supported(self, metric_name: str) -> bool:
        """
        Check if a metric is supported for analytics.
        
        Args:
            metric_name: Name of the metric to check
            
        Returns:
            True if metric is supported, False otherwise
        """
        pass

    @abstractmethod
    async def query_historical_data(
        self,
        filters: HistoricalQueryFilter
    ) -> HistoricalQueryResponse:
        """Retrieve historical measurement data applying advanced filters."""
        pass

    @abstractmethod
    async def query_historical_averages(
        self,
        filters: HistoricalQueryFilter,
        average_interval: int
    ) -> HistoricalAveragesResponse:
        """Retrieve averaged historical measurements for the specified interval."""
        pass

    @abstractmethod
    async def get_latest_measurement(
        self,
        controller_id: str
    ) -> Optional[Measurement]:
        """
        Get the most recent measurement for a specific controller.

        Args:
            controller_id: ID of the controller to get the latest measurement for

        Returns:
            The most recent Measurement object, or None if no data found in the last 10 minutes
        """
        pass

    @abstractmethod
    async def generate_comprehensive_analytics_report(
        self,
        controller_ids: List[str],
        metrics: List[str],
        filters: AnalyticsFilter
    ) -> Dict[str, Any]:
        """
        Generate a comprehensive analytics report with extensive statistical calculations.
        This is a computationally expensive operation that demonstrates cache benefits.
        
        Args:
            controller_ids: List of controller IDs to analyze
            metrics: List of metrics to calculate
            filters: filters including real_time flag
            
        Returns:
            Comprehensive analytics report with advanced statistics
        """
        pass
