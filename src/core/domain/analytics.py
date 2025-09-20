from dataclasses import dataclass
from typing import List, Dict, Any, Optional
from datetime import datetime


@dataclass
class AnalyticsFilter:
    """Value object representing filters for analytics queries."""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    limit: Optional[int] = None


@dataclass
class MetricResult:
    """Value object representing the result of a single metric calculation."""
    metric_name: str
    value: float
    unit: str
    calculated_at: datetime
    controller_id: str
    description: Optional[str] = None


@dataclass
class TrendDataPoint:
    """Value object representing a single data point in trend analysis."""
    timestamp: datetime
    value: float
    interval: str


@dataclass
class AnalyticsReport:
    """Aggregate representing a complete analytics report."""
    controller_id: str
    metrics: List[MetricResult]
    generated_at: datetime
    data_points_count: int
    filters_applied: AnalyticsFilter

    def get_metric_by_name(self, metric_name: str) -> Optional[MetricResult]:
        """Get a specific metric result by name."""
        for metric in self.metrics:
            if metric.metric_name == metric_name:
                return metric
        return None


@dataclass
class MultiReportRequest:
    """Value object for multi-controller analytics requests."""
    controllers: List[str]
    metrics: List[str]
    filters: AnalyticsFilter


@dataclass
class MultiReportResponse:
    """Aggregate representing a multi-controller analytics report."""
    reports: Dict[str, AnalyticsReport]
    generated_at: datetime
    total_controllers: int
    total_metrics: int

    def get_report_for_controller(self, controller_id: str) -> Optional[AnalyticsReport]:
        """Get analytics report for a specific controller."""
        return self.reports.get(controller_id)


@dataclass
class TrendAnalysis:
    """Aggregate representing trend analysis for a specific metric."""
    metric_name: str
    controller_id: str
    data_points: List[TrendDataPoint]
    interval: str
    generated_at: datetime
    filters_applied: AnalyticsFilter

    @property
    def total_points(self) -> int:
        """Get total number of data points in the trend."""
        return len(self.data_points)

    @property
    def average_value(self) -> float:
        """Calculate average value across all data points."""
        if not self.data_points:
            return 0.0
        return sum(point.value for point in self.data_points) / len(self.data_points)

    @property
    def min_value(self) -> float:
        """Get minimum value from data points."""
        if not self.data_points:
            return 0.0
        return min(point.value for point in self.data_points)

    @property
    def max_value(self) -> float:
        """Get maximum value from data points."""
        if not self.data_points:
            return 0.0
        return max(point.value for point in self.data_points)
