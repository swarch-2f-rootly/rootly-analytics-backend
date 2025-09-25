"""
Pydantic models for FastAPI request/response serialization.
These models handle the conversion between HTTP and domain objects.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...core.domain.analytics import (
    AnalyticsReport,
    MetricResult,
    MultiReportRequest,
    MultiReportResponse,
    TrendAnalysis,
    TrendDataPoint,
    AnalyticsFilter,
    HistoricalQueryResponse,
    HistoricalDataPoint,
    HistoricalQueryFilter
)


class MetricResultModel(BaseModel):
    """Model for metric calculation results."""
    metric_name: str = Field(..., description="Name of the calculated metric")
    value: float = Field(..., description="Calculated metric value")
    unit: str = Field(..., description="Unit of measurement")
    calculated_at: datetime = Field(..., description="Timestamp when metric was calculated")
    controller_id: str = Field(..., description="Controller ID for this metric")
    description: Optional[str] = Field(None, description="Description of the metric")

    @classmethod
    def from_domain(cls, metric: MetricResult) -> "MetricResultModel":
        """Convert from domain object to model."""
        return cls(
            metric_name=metric.metric_name,
            value=metric.value,
            unit=metric.unit,
            calculated_at=metric.calculated_at,
            controller_id=metric.controller_id,
            description=metric.description
        )


class AnalyticsFilterModel(BaseModel):
    """Model for analytics query filters."""
    start_time: Optional[datetime] = Field(None, description="Start time for data query")
    end_time: Optional[datetime] = Field(None, description="End time for data query")
    limit: Optional[int] = Field(None, ge=1, le=10000, description="Maximum number of records")

    def to_domain(self) -> AnalyticsFilter:
        """Convert to domain object."""
        return AnalyticsFilter(
            start_time=self.start_time,
            end_time=self.end_time,
            limit=self.limit
        )


class SingleMetricReportResponse(BaseModel):
    """Response model for single metric analytics report."""
    controller_id: str = Field(..., description="Controller ID")
    metrics: List[MetricResultModel] = Field(..., description="Calculated metrics")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    data_points_count: int = Field(..., description="Number of data points analyzed")
    filters_applied: AnalyticsFilterModel = Field(..., description="Filters applied to the data")

    @classmethod
    def from_domain(cls, report: AnalyticsReport) -> "SingleMetricReportResponse":
        """Convert from domain object to response model."""
        return cls(
            controller_id=report.controller_id,
            metrics=[MetricResultModel.from_domain(m) for m in report.metrics],
            generated_at=report.generated_at,
            data_points_count=report.data_points_count,
            filters_applied=AnalyticsFilterModel(
                start_time=report.filters_applied.start_time,
                end_time=report.filters_applied.end_time,
                limit=report.filters_applied.limit
            )
        )


class MultiReportRequestModel(BaseModel):
    """Request model for multi-controller analytics report."""
    controllers: List[str] = Field(..., min_items=1, description="List of controller IDs")
    metrics: List[str] = Field(..., min_items=1, description="List of metric names to calculate")
    filters: AnalyticsFilterModel = Field(..., description="Filters to apply to data queries")

    @validator('controllers')
    def validate_controllers(cls, v):
        """Validate controller IDs are not empty."""
        if not all(controller.strip() for controller in v):
            raise ValueError("Controller IDs cannot be empty")
        return v

    @validator('metrics')
    def validate_metrics(cls, v):
        """Validate metric names are not empty."""
        if not all(metric.strip() for metric in v):
            raise ValueError("Metric names cannot be empty")
        return v

    def to_domain(self) -> MultiReportRequest:
        """Convert to domain object."""
        return MultiReportRequest(
            controllers=self.controllers,
            metrics=self.metrics,
            filters=self.filters.to_domain()
        )


class MultiReportResponseModel(BaseModel):
    """Response model for multi-controller analytics report."""
    reports: Dict[str, SingleMetricReportResponse] = Field(..., description="Reports by controller ID")
    generated_at: datetime = Field(..., description="Report generation timestamp")
    total_controllers: int = Field(..., description="Total number of controllers requested")
    total_metrics: int = Field(..., description="Total number of metrics requested")

    @classmethod
    def from_domain(cls, response: MultiReportResponse) -> "MultiReportResponseModel":
        """Convert from domain object to response model."""
        reports = {
            controller_id: SingleMetricReportResponse.from_domain(report)
            for controller_id, report in response.reports.items()
        }
        
        return cls(
            reports=reports,
            generated_at=response.generated_at,
            total_controllers=response.total_controllers,
            total_metrics=response.total_metrics
        )


class TrendDataPointModel(BaseModel):
    """Model for trend analysis data points."""
    timestamp: datetime = Field(..., description="Data point timestamp")
    value: float = Field(..., description="Aggregated value for this time period")
    interval: str = Field(..., description="Time interval used for aggregation")

    @classmethod
    def from_domain(cls, point: TrendDataPoint) -> "TrendDataPointModel":
        """Convert from domain object to model."""
        return cls(
            timestamp=point.timestamp,
            value=point.value,
            interval=point.interval
        )


class TrendAnalysisResponse(BaseModel):
    """Response model for trend analysis."""
    metric_name: str = Field(..., description="Name of the analyzed metric")
    controller_id: str = Field(..., description="Controller ID")
    data_points: List[TrendDataPointModel] = Field(..., description="Time-series data points")
    interval: str = Field(..., description="Time interval used for aggregation")
    generated_at: datetime = Field(..., description="Analysis generation timestamp")
    filters_applied: AnalyticsFilterModel = Field(..., description="Filters applied to the data")
    
    # Additional computed properties for convenience
    total_points: int = Field(..., description="Total number of data points")
    average_value: float = Field(..., description="Average value across all data points")
    min_value: float = Field(..., description="Minimum value in the dataset")
    max_value: float = Field(..., description="Maximum value in the dataset")

    @classmethod
    def from_domain(cls, trend: TrendAnalysis) -> "TrendAnalysisResponse":
        """Convert from domain object to response model."""
        return cls(
            metric_name=trend.metric_name,
            controller_id=trend.controller_id,
            data_points=[TrendDataPointModel.from_domain(p) for p in trend.data_points],
            interval=trend.interval,
            generated_at=trend.generated_at,
            filters_applied=AnalyticsFilterModel(
                start_time=trend.filters_applied.start_time,
                end_time=trend.filters_applied.end_time,
                limit=trend.filters_applied.limit
            ),
            total_points=trend.total_points,
            average_value=trend.average_value,
            min_value=trend.min_value,
            max_value=trend.max_value
        )


class ErrorResponse(BaseModel):
    """Standard error response model."""
    error: str = Field(..., description="Error type or category")
    message: str = Field(..., description="Human-readable error message")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional error details")
    timestamp: datetime = Field(default_factory=datetime.now, description="Error timestamp")


class HealthResponse(BaseModel):
    """Health check response model."""
    status: str = Field(..., description="Service health status")
    service: str = Field(..., description="Service name")
    timestamp: datetime = Field(..., description="Health check timestamp")
    details: Optional[Dict[str, Any]] = Field(None, description="Additional health information")


class HistoricalQueryFiltersModel(BaseModel):
    """Model describing filters used for historical queries."""
    start_time: Optional[datetime] = Field(None, description="Start time for the query")
    end_time: Optional[datetime] = Field(None, description="End time for the query")
    limit: Optional[int] = Field(None, description="Maximum number of measurements returned")
    controller_id: Optional[str] = Field(None, description="Controller identifier filter")
    sensor_id: Optional[str] = Field(None, description="Sensor identifier filter")
    zone: Optional[str] = Field(None, description="Zone identifier filter")
    parameter: Optional[str] = Field(None, description="Measurement parameter filter")

    @classmethod
    def from_domain(cls, filters: HistoricalQueryFilter) -> "HistoricalQueryFiltersModel":
        return cls(
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=filters.limit,
            controller_id=filters.controller_id,
            sensor_id=filters.sensor_id,
            zone=filters.zone,
            parameter=filters.parameter
        )


class HistoricalDataPointModel(BaseModel):
    """Model representing a single historical measurement entry."""
    timestamp: datetime = Field(..., description="Timestamp of the measurement")
    controller_id: str = Field(..., description="Controller identifier")
    parameter: str = Field(..., description="Measurement parameter name")
    value: float = Field(..., description="Measured value")
    sensor_id: Optional[str] = Field(None, description="Sensor identifier")
    zone: Optional[str] = Field(None, description="Zone identifier")

    @classmethod
    def from_domain(cls, data_point: HistoricalDataPoint) -> "HistoricalDataPointModel":
        return cls(
            timestamp=data_point.timestamp,
            controller_id=data_point.controller_id,
            parameter=data_point.parameter,
            value=data_point.value,
            sensor_id=data_point.sensor_id,
            zone=data_point.zone
        )


class HistoricalQueryResponseModel(BaseModel):
    """Response model encapsulating historical measurement data."""
    data_points: List[HistoricalDataPointModel] = Field(..., description="Historical measurement entries")
    generated_at: datetime = Field(..., description="Response generation timestamp")
    total_points: int = Field(..., description="Total number of data points returned")
    filters_applied: HistoricalQueryFiltersModel = Field(..., description="Filters applied to the query")

    @classmethod
    def from_domain(cls, response: HistoricalQueryResponse) -> "HistoricalQueryResponseModel":
        return cls(
            data_points=[HistoricalDataPointModel.from_domain(dp) for dp in response.data_points],
            generated_at=response.generated_at,
            total_points=response.total_points,
            filters_applied=HistoricalQueryFiltersModel.from_domain(response.filters_applied)
        )
