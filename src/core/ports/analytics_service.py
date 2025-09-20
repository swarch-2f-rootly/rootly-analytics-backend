from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..domain.analytics import (
    AnalyticsReport,
    MultiReportRequest,
    MultiReportResponse,
    TrendAnalysis,
    AnalyticsFilter
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
        interval: str
    ) -> TrendAnalysis:
        """
        Generate trend analysis for a specific metric over time.
        
        Args:
            metric_name: Name of the sensor metric
            controller_id: ID of the controller device
            start_time: Start time for trend analysis
            end_time: End time for trend analysis
            interval: Time interval for data aggregation (e.g., '1h', '1d')
            
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
