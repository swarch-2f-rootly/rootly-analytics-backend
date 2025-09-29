"""
GraphQL types for the Analytics Service.
Strawberry GraphQL type definitions based on domain entities.
"""

import strawberry
from typing import List, Optional
from datetime import datetime

from ...core.domain.analytics import (
    MetricResult as DomainMetricResult,
    AnalyticsReport as DomainAnalyticsReport,
    TrendDataPoint as DomainTrendDataPoint,
    TrendAnalysis as DomainTrendAnalysis,
    MultiReportResponse as DomainMultiReportResponse,
    AnalyticsFilter as DomainAnalyticsFilter
)


@strawberry.type
class MetricResult:
    """GraphQL type for metric results."""
    metric_name: str
    value: float
    unit: str
    calculated_at: datetime
    controller_id: str
    description: Optional[str] = None

    @classmethod
    def from_domain(cls, domain_metric: DomainMetricResult) -> "MetricResult":
        """Convert domain MetricResult to GraphQL type."""
        return cls(
            metric_name=domain_metric.metric_name,
            value=domain_metric.value,
            unit=domain_metric.unit,
            calculated_at=domain_metric.calculated_at,
            controller_id=domain_metric.controller_id,
            description=domain_metric.description
        )


@strawberry.type
class AnalyticsReport:
    """GraphQL type for analytics reports."""
    controller_id: str
    metrics: List[MetricResult]
    generated_at: datetime
    data_points_count: int

    @classmethod
    def from_domain(cls, domain_report: DomainAnalyticsReport) -> "AnalyticsReport":
        """Convert domain AnalyticsReport to GraphQL type."""
        return cls(
            controller_id=domain_report.controller_id,
            metrics=[MetricResult.from_domain(metric) for metric in domain_report.metrics],
            generated_at=domain_report.generated_at,
            data_points_count=domain_report.data_points_count
        )


@strawberry.type
class TrendDataPoint:
    """GraphQL type for trend data points."""
    timestamp: datetime
    value: float
    interval: str

    @classmethod
    def from_domain(cls, domain_point: DomainTrendDataPoint) -> "TrendDataPoint":
        """Convert domain TrendDataPoint to GraphQL type."""
        return cls(
            timestamp=domain_point.timestamp,
            value=domain_point.value,
            interval=domain_point.interval
        )


@strawberry.type
class TrendAnalysis:
    """GraphQL type for trend analysis."""
    metric_name: str
    controller_id: str
    data_points: List[TrendDataPoint]
    interval: str
    generated_at: datetime
    total_points: int
    average_value: float
    min_value: float
    max_value: float

    @classmethod
    def from_domain(cls, domain_trend: DomainTrendAnalysis) -> "TrendAnalysis":
        """Convert domain TrendAnalysis to GraphQL type."""
        return cls(
            metric_name=domain_trend.metric_name,
            controller_id=domain_trend.controller_id,
            data_points=[TrendDataPoint.from_domain(point) for point in domain_trend.data_points],
            interval=domain_trend.interval,
            generated_at=domain_trend.generated_at,
            total_points=domain_trend.total_points,
            average_value=domain_trend.average_value,
            min_value=domain_trend.min_value,
            max_value=domain_trend.max_value
        )


@strawberry.type
class MultiReportResponse:
    """GraphQL type for multi-controller reports."""
    reports: List[AnalyticsReport]
    generated_at: datetime
    total_controllers: int
    total_metrics: int

    @classmethod
    def from_domain(cls, domain_response: DomainMultiReportResponse) -> "MultiReportResponse":
        """Convert domain MultiReportResponse to GraphQL type."""
        return cls(
            reports=[AnalyticsReport.from_domain(report) for report in domain_response.reports.values()],
            generated_at=domain_response.generated_at,
            total_controllers=domain_response.total_controllers,
            total_metrics=domain_response.total_metrics
        )


@strawberry.type
class HealthStatus:
    """GraphQL type for service health status."""
    status: str
    service: str
    influxdb: str
    influxdb_url: str
    timestamp: str


# Input types for GraphQL mutations and queries
@strawberry.input
class AnalyticsFilters:
    """GraphQL input type for analytics filters."""
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    limit: Optional[int] = None

    def to_domain(self) -> DomainAnalyticsFilter:
        """Convert GraphQL input to domain AnalyticsFilter."""
        start_dt = None
        end_dt = None
        
        if self.start_time:
            start_dt = datetime.fromisoformat(self.start_time.replace('Z', '+00:00'))
        if self.end_time:
            end_dt = datetime.fromisoformat(self.end_time.replace('Z', '+00:00'))
            
        return DomainAnalyticsFilter(
            start_time=start_dt,
            end_time=end_dt,
            limit=self.limit
        )


@strawberry.input
class MultiMetricReportInput:
    """GraphQL input type for multi-metric reports."""
    controllers: List[str]
    metrics: List[str]
    filters: Optional[AnalyticsFilters] = None


@strawberry.input
class TrendAnalysisInput:
    """GraphQL input type for trend analysis."""
    metric_name: str
    controller_id: str
    start_time: str
    end_time: str
    interval: str = "1h"