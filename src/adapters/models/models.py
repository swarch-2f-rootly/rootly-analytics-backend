"""
Pydantic models for FastAPI request/response serialization.
These models handle the conversion between HTTP and domain objects.
"""

from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any
from datetime import datetime

from ...core.domain.measurement import Measurement
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
    HistoricalQueryFilter,
    HistoricalAverageDataPoint,
    HistoricalAveragesResponse
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


class MultiMetricReportRequest(BaseModel):
    """Request model for multiple metrics analytics report."""
    metrics: List[str] = Field(..., min_items=1, description="List of metric names to calculate")
    controller_id: str = Field(..., description="Controller ID for the report")
    start_time: Optional[str] = Field(None, description="Start time (ISO format)")
    end_time: Optional[str] = Field(None, description="End time (ISO format)")

    @validator('metrics')
    def validate_metrics(cls, v):
        """Validate metric names are not empty."""
        if not all(metric.strip() for metric in v):
            raise ValueError("Metric names cannot be empty")
        return v

    @validator('start_time', 'end_time', pre=True, always=True)
    def validate_datetime_fields(cls, v):
        """Convert empty strings to None for datetime fields."""
        if v == "" or (isinstance(v, str) and not v.strip()):
            return None
        return v


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
    parameter: Optional[str] = Field(None, description="Measurement parameter filter")

    @classmethod
    def from_domain(cls, filters: HistoricalQueryFilter) -> "HistoricalQueryFiltersModel":
        return cls(
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=filters.limit,
            controller_id=filters.controller_id,
            sensor_id=filters.sensor_id,
            parameter=filters.parameter
        )


class HistoricalDataPointModel(BaseModel):
    """Model representing a single historical measurement entry."""
    timestamp: datetime = Field(..., description="Timestamp of the measurement")
    controller_id: str = Field(..., description="Controller identifier")
    parameter: str = Field(..., description="Measurement parameter name")
    value: float = Field(..., description="Measured value")
    sensor_id: Optional[str] = Field(None, description="Sensor identifier")

    @classmethod
    def from_domain(cls, data_point: HistoricalDataPoint) -> "HistoricalDataPointModel":
        return cls(
            timestamp=data_point.timestamp,
            controller_id=data_point.controller_id,
            parameter=data_point.parameter,
            value=data_point.value,
            sensor_id=data_point.sensor_id
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


class HistoricalAverageDataPointModel(BaseModel):
    """Model representing averaged measurement data for a time interval."""
    interval_start: datetime = Field(..., description="Start timestamp of the averaging interval")
    interval_end: datetime = Field(..., description="End timestamp of the averaging interval (exclusive)")
    controller_id: str = Field(..., description="Controller identifier")
    parameter: str = Field(..., description="Measurement parameter name")
    average_value: float = Field(..., description="Average value across the interval")
    measurements_count: int = Field(..., ge=1, description="Number of measurements used to compute the average")

    @classmethod
    def from_domain(cls, data_point: HistoricalAverageDataPoint) -> "HistoricalAverageDataPointModel":
        return cls(
            interval_start=data_point.interval_start,
            interval_end=data_point.interval_end,
            controller_id=data_point.controller_id,
            parameter=data_point.parameter,
            average_value=data_point.average_value,
            measurements_count=data_point.measurements_count
        )


class HistoricalAveragesResponseModel(BaseModel):
    """Response model encapsulating averaged historical measurement data."""
    data_points: List[HistoricalAverageDataPointModel] = Field(..., description="Averaged measurement entries")
    generated_at: datetime = Field(..., description="Response generation timestamp")
    total_points: int = Field(..., description="Total number of averaged intervals returned")
    interval_minutes: int = Field(..., description="Length of the averaging interval in minutes")
    filters_applied: HistoricalQueryFiltersModel = Field(..., description="Filters applied to the query")

    @classmethod
    def from_domain(cls, response: HistoricalAveragesResponse) -> "HistoricalAveragesResponseModel":
        return cls(
            data_points=[HistoricalAverageDataPointModel.from_domain(dp) for dp in response.data_points],
            generated_at=response.generated_at,
            total_points=response.total_points,
            interval_minutes=response.interval_minutes,
            filters_applied=HistoricalQueryFiltersModel.from_domain(response.filters_applied)
        )


class SupportedMetricsResponse(BaseModel):
    """Response model for supported metrics endpoint."""
    metrics: List[str] = Field(..., description="List of supported metric names")


class LatestMeasurementResponse(BaseModel):
    """Response model for latest measurement endpoint."""
    controller_id: str = Field(..., description="Controller ID requested")
    measurement: Optional[MetricResultModel] = Field(None, description="Latest measurement data, null if no data")
    status: str = Field(..., description="Response status: 'data' or 'no_data'")
    last_checked: datetime = Field(default_factory=datetime.now, description="Timestamp when the check was performed")
    data_age_minutes: Optional[float] = Field(None, description="How old the data is in minutes (null if no data)")

    @classmethod
    def from_measurement(
        cls,
        controller_id: str,
        measurement: Optional[Measurement]
    ) -> "LatestMeasurementResponse":
        """Create response from a measurement or None."""

        if measurement:
            # Create a metric result with basic measurement info
            # Since this is "latest measurement", we'll use temperature as the primary metric
            # or whichever is available
            primary_value = None
            primary_unit = None
            primary_name = "measurement"

            if measurement.has_temperature:
                primary_value = measurement.temperature
                primary_unit = "°C"
                primary_name = "temperature"
            elif measurement.has_humidity_air:
                primary_value = measurement.air_humidity
                primary_unit = "%"
                primary_name = "air_humidity"
            elif measurement.has_humidity_soil:
                primary_value = measurement.soil_humidity
                primary_unit = ""
                primary_name = "soil_humidity"
            elif measurement.has_light:
                primary_value = measurement.light_intensity
                primary_unit = "lux"
                primary_name = "light_intensity"

            if primary_value is not None:
                metric_result = MetricResult(
                    metric_name=primary_name,
                    value=primary_value,
                    unit=primary_unit,
                    calculated_at=measurement.timestamp,
                    controller_id=controller_id,
                    description="Latest measurement"
                )
                metric_model = MetricResultModel.from_domain(metric_result)

                # Calculate data age
                data_age = (datetime.now() - measurement.timestamp).total_seconds() / 60

                return cls(
                    controller_id=controller_id,
                    measurement=metric_model,
                    status="data",
                    data_age_minutes=round(data_age, 2)
                )

        # No data case
        return cls(
            controller_id=controller_id,
            measurement=None,
            status="no_data",
            data_age_minutes=None
        )
