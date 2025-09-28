"""
Implementation of the AnalyticsService port.
This service orchestrates the analytics calculations and data access.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import pandas as pd

from ..ports.analytics_service import AnalyticsService
from ..ports.measurement_repository import MeasurementRepository
from ..ports.exceptions import (
    AnalyticsServiceError,
    InvalidMetricError,
    InsufficientDataError
)
from ..domain.analytics import (
    AnalyticsReport,
    MetricResult,
    MultiReportRequest,
    MultiReportResponse,
    TrendAnalysis,
    TrendDataPoint,
    AnalyticsFilter,
    HistoricalQueryFilter,
    HistoricalDataPoint,
    HistoricalQueryResponse
)
from ..domain.measurement import Measurement
from .analytics_calculations import AnalyticsCalculations


class AnalyticsServiceImpl(AnalyticsService):
    """
    Concrete implementation of the AnalyticsService port.
    Handles business logic for agricultural analytics calculations.
    """

    # Supported sensor metrics mapping
    SUPPORTED_METRICS = {
        "temperature": "temperature",
        "air_humidity": "air_humidity",
        "soil_humidity": "soil_humidity",
        "light_intensity": "light_intensity"
    }

    def __init__(self, measurement_repository: MeasurementRepository):
        """
        Initialize the analytics service with its dependencies.
        
        Args:
            measurement_repository: Repository for accessing measurement data
        """
        self.measurement_repository = measurement_repository
        self.calculator = AnalyticsCalculations()

    async def generate_single_metric_report(
        self,
        metric_name: str,
        controller_id: str,
        filters: AnalyticsFilter
    ) -> AnalyticsReport:
        """Generate analytics report for a single metric and controller."""
        if not self.is_metric_supported(metric_name):
            raise InvalidMetricError(metric_name, list(self.SUPPORTED_METRICS.keys()))

        # Fetch measurement data
        measurements = await self.measurement_repository.get_measurements(
            controller_id=controller_id,
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=filters.limit
        )

        if not measurements:
            raise InsufficientDataError(f"No data found for controller {controller_id}")

        # Calculate metrics for the specific sensor type
        metric_results = await self._calculate_metrics_for_sensor(
            metric_name, measurements, controller_id
        )

        # Check if we have data for the requested metric
        if not metric_results:
            raise InsufficientDataError(f"No {metric_name} data available for controller {controller_id}")

        return AnalyticsReport(
            controller_id=controller_id,
            metrics=metric_results,
            generated_at=datetime.now(),
            data_points_count=len(measurements),
            filters_applied=filters
        )

    async def generate_multi_report(
        self, request: MultiReportRequest
    ) -> MultiReportResponse:
        """Generate analytics report for multiple metrics and controllers."""
        reports = {}
        
        for controller_id in request.controllers:
            try:
                # Get measurements for this controller
                measurements = await self.measurement_repository.get_measurements(
                    controller_id=controller_id,
                    start_time=request.filters.start_time,
                    end_time=request.filters.end_time,
                    limit=request.filters.limit
                )

                if measurements:
                    # Calculate metrics for all requested sensor types
                    all_metrics = []
                    for metric_name in request.metrics:
                        if self.is_metric_supported(metric_name):
                            metric_results = await self._calculate_metrics_for_sensor(
                                metric_name, measurements, controller_id
                            )
                            all_metrics.extend(metric_results)

                    # Check if we have data for at least one of the requested metrics
                    if not all_metrics:
                        raise InsufficientDataError(f"No data available for requested metrics in controller {controller_id}")

                    reports[controller_id] = AnalyticsReport(
                        controller_id=controller_id,
                        metrics=all_metrics,
                        generated_at=datetime.now(),
                        data_points_count=len(measurements),
                        filters_applied=request.filters
                    )
            except Exception as e:
                # Log error but continue with other controllers
                continue

        return MultiReportResponse(
            reports=reports,
            generated_at=datetime.now(),
            total_controllers=len(request.controllers),
            total_metrics=len(request.metrics)
        )

    async def generate_trend_analysis(
        self,
        metric_name: str,
        controller_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> TrendAnalysis:
        """Generate trend analysis for a specific metric over time."""
        if not self.is_metric_supported(metric_name):
            raise InvalidMetricError(metric_name, list(self.SUPPORTED_METRICS.keys()))

        # Fetch measurements with interval aggregation
        measurements = await self.measurement_repository.get_measurements(
            controller_id=controller_id,
            start_time=start_time,
            end_time=end_time,
            interval=interval
        )

        if not measurements:
            raise InsufficientDataError(
                f"No data found for controller {controller_id} in the specified time range"
            )

        # Convert to pandas DataFrame for time-series analysis
        df = self._measurements_to_dataframe(measurements)
        
        # Get the specific metric column
        metric_column = self.SUPPORTED_METRICS[metric_name]
        
        if metric_column not in df.columns or df[metric_column].isna().all():
            raise InsufficientDataError(f"No {metric_name} data available")

        # Aggregate by interval
        df.set_index('timestamp', inplace=True)
        aggregated = df[metric_column].resample(interval).mean().dropna()

        # Create trend data points
        data_points = [
            TrendDataPoint(
                timestamp=timestamp,
                value=float(value),
                interval=interval
            )
            for timestamp, value in aggregated.items()
        ]

        filters = AnalyticsFilter(
            start_time=start_time,
            end_time=end_time
        )

        return TrendAnalysis(
            metric_name=metric_name,
            controller_id=controller_id,
            data_points=data_points,
            interval=interval,
            generated_at=datetime.now(),
            filters_applied=filters
        )

    def get_supported_metrics(self) -> List[str]:
        """Get list of supported metric names."""
        return list(self.SUPPORTED_METRICS.keys())

    def is_metric_supported(self, metric_name: str) -> bool:
        """Check if a metric is supported for analytics."""
        return metric_name in self.SUPPORTED_METRICS

    async def query_historical_data(
        self,
        filters: HistoricalQueryFilter
    ) -> HistoricalQueryResponse:
        """Retrieve historical measurements applying provided filters."""
        # Validate parameter if provided
        parameter_filter = None
        if filters.parameter:
            if not self.is_metric_supported(filters.parameter):
                raise InvalidMetricError(filters.parameter, list(self.SUPPORTED_METRICS.keys()))
            parameter_filter = filters.parameter

        measurements = await self.measurement_repository.get_measurements(
            controller_id=filters.controller_id,
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=filters.limit,
            sensor_id=filters.sensor_id,
            parameter=parameter_filter
        )

        if parameter_filter:
            candidate_metrics = [parameter_filter]
        else:
            candidate_metrics = list(self.SUPPORTED_METRICS.keys())

        data_points: List[HistoricalDataPoint] = []
        for measurement in measurements:
            for metric_name in candidate_metrics:
                attribute = self.SUPPORTED_METRICS[metric_name]
                value = getattr(measurement, attribute, None)
                if value is None:
                    continue

                data_points.append(
                    HistoricalDataPoint(
                        timestamp=measurement.timestamp,
                        controller_id=measurement.controller_id,
                        parameter=metric_name,
                        value=float(value),
                        sensor_id=measurement.sensor_id
                    )
                )

        data_points.sort(key=lambda point: point.timestamp)

        response_filters = HistoricalQueryFilter(
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=filters.limit,
            controller_id=filters.controller_id,
            sensor_id=filters.sensor_id,
            parameter=filters.parameter
        )

        return HistoricalQueryResponse(
            data_points=data_points,
            generated_at=datetime.now(),
            total_points=len(data_points),
            filters_applied=response_filters
        )

    async def _calculate_metrics_for_sensor(
        self, 
        metric_name: str, 
        measurements: List[Measurement], 
        controller_id: str
    ) -> List[MetricResult]:
        """Calculate all relevant metrics for a specific sensor type."""
        results = []
        now = datetime.now()

        if metric_name == "temperature":
            results.extend(await self._calculate_temperature_metrics(
                measurements, controller_id, now
            ))
        elif metric_name == "air_humidity":
            results.extend(await self._calculate_humidity_air_metrics(
                measurements, controller_id, now
            ))
        elif metric_name == "soil_humidity":
            results.extend(await self._calculate_humidity_soil_metrics(
                measurements, controller_id, now
            ))
        elif metric_name == "light_intensity":
            results.extend(await self._calculate_light_metrics(
                measurements, controller_id, now
            ))

        return results

    async def _calculate_temperature_metrics(
        self, measurements: List[Measurement], controller_id: str, timestamp: datetime
    ) -> List[MetricResult]:
        """Calculate temperature-related metrics."""
        results = []
        temp_measurements = [m for m in measurements if m.has_temperature]
        
        if not temp_measurements:
            return results

        temperatures = [m.temperature for m in temp_measurements]
        stats = self.calculator.calculate_basic_statistics(temperatures)

        # Basic statistics
        results.extend([
            MetricResult("temperature_average", stats["mean"], "°C", timestamp, controller_id),
            MetricResult("temperature_minimum", stats["min"], "°C", timestamp, controller_id),
            MetricResult("temperature_maximum", stats["max"], "°C", timestamp, controller_id),
            MetricResult("temperature_std_deviation", stats["std_dev"], "°C", timestamp, controller_id)
        ])

        # Growing Degree Days
        gdd = self.calculator.calculate_growing_degree_days(temp_measurements)
        results.append(
            MetricResult("growing_degree_days", gdd, "GDD", timestamp, controller_id,
                        "Predicts plant development stages")
        )

        # Calculate dew point and VPD if humidity data is available
        humid_measurements = [m for m in measurements if m.has_humidity_air and m.has_temperature]
        if humid_measurements:
            avg_temp = sum(m.temperature for m in humid_measurements) / len(humid_measurements)
            avg_humidity = sum(m.air_humidity for m in humid_measurements) / len(humid_measurements)
            
            dew_point = self.calculator.calculate_dew_point(avg_temp, avg_humidity)
            vpd = self.calculator.calculate_vapor_pressure_deficit(avg_temp, avg_humidity)
            
            results.extend([
                MetricResult("dew_point", dew_point, "°C", timestamp, controller_id,
                           "Temperature at which water vapor condenses"),
                MetricResult("vapor_pressure_deficit", vpd, "kPa", timestamp, controller_id,
                           "Plant transpiration indicator")
            ])

        temperature_series = self._extract_time_series(
            measurements, controller_id, "temperature"
        )
        temperature_trend = self.calculator.calculate_trend_metrics(temperature_series)
        results.extend(
            self._build_trend_metric_results(
                metric_prefix="temperature",
                controller_id=controller_id,
                timestamp=timestamp,
                trend_data=temperature_trend,
                value_unit="°C",
                slope_unit="°C/h"
            )
        )

        return results

    async def _calculate_humidity_air_metrics(
        self, measurements: List[Measurement], controller_id: str, timestamp: datetime
    ) -> List[MetricResult]:
        """Calculate air humidity-related metrics."""
        results = []
        humid_measurements = [m for m in measurements if m.has_humidity_air]
        
        if not humid_measurements:
            return results

        humidities = [m.air_humidity for m in humid_measurements]
        stats = self.calculator.calculate_basic_statistics(humidities)

        results.extend([
            MetricResult("air_humidity_average", stats["mean"], "%", timestamp, controller_id),
            MetricResult("air_humidity_minimum", stats["min"], "%", timestamp, controller_id),
            MetricResult("air_humidity_maximum", stats["max"], "%", timestamp, controller_id),
            MetricResult("air_humidity_std_deviation", stats["std_dev"], "%", timestamp, controller_id)
        ])

        humidity_air_series = self._extract_time_series(
            measurements, controller_id, "air_humidity"
        )
        humidity_air_trend = self.calculator.calculate_trend_metrics(humidity_air_series)
        results.extend(
            self._build_trend_metric_results(
                metric_prefix="air_humidity",
                controller_id=controller_id,
                timestamp=timestamp,
                trend_data=humidity_air_trend,
                value_unit="%",
                slope_unit="%/h"
            )
        )

        return results

    async def _calculate_humidity_soil_metrics(
        self, measurements: List[Measurement], controller_id: str, timestamp: datetime
    ) -> List[MetricResult]:
        """Calculate soil humidity-related metrics."""
        results = []
        soil_measurements = [m for m in measurements if m.has_humidity_soil]
        
        if not soil_measurements:
            return results

        soil_humidities = [m.soil_humidity for m in soil_measurements]
        stats = self.calculator.calculate_basic_statistics(soil_humidities)

        results.extend([
            MetricResult("soil_humidity_average", stats["mean"], "", timestamp, controller_id),
            MetricResult("soil_humidity_minimum", stats["min"], "", timestamp, controller_id),
            MetricResult("soil_humidity_maximum", stats["max"], "", timestamp, controller_id),
            MetricResult("soil_humidity_std_deviation", stats["std_dev"], "", timestamp, controller_id)
        ])

        soil_series = self._extract_time_series(
            measurements, controller_id, "soil_humidity"
        )
        soil_trend = self.calculator.calculate_trend_metrics(soil_series)
        results.extend(
            self._build_trend_metric_results(
                metric_prefix="soil_humidity",
                controller_id=controller_id,
                timestamp=timestamp,
                trend_data=soil_trend,
                value_unit="",
                slope_unit="fraction/h"
            )
        )

        return results

    async def _calculate_light_metrics(
        self, measurements: List[Measurement], controller_id: str, timestamp: datetime
    ) -> List[MetricResult]:
        """Calculate light-related metrics."""
        results = []
        light_measurements = [m for m in measurements if m.has_light]
        
        if not light_measurements:
            return results

        light_values = [m.light_intensity for m in light_measurements]
        stats = self.calculator.calculate_basic_statistics(light_values)

        results.extend([
            MetricResult("light_intensity_average", stats["mean"], "lux", timestamp, controller_id),
            MetricResult("light_intensity_minimum", stats["min"], "lux", timestamp, controller_id),
            MetricResult("light_intensity_maximum", stats["max"], "lux", timestamp, controller_id),
            MetricResult("light_intensity_std_deviation", stats["std_dev"], "lux", timestamp, controller_id)
        ])

        # Daily Light Integral
        dli = self.calculator.calculate_daily_light_integral(stats["mean"])
        results.append(
            MetricResult("daily_light_integral", dli, "mol/m²/day", timestamp, controller_id,
                        "Total photosynthetic radiation per day")
        )

        light_series = self._extract_time_series(
            measurements, controller_id, "light_intensity"
        )
        light_trend = self.calculator.calculate_trend_metrics(light_series)
        results.extend(
            self._build_trend_metric_results(
                metric_prefix="light_intensity",
                controller_id=controller_id,
                timestamp=timestamp,
                trend_data=light_trend,
                value_unit="lux",
                slope_unit="lux/h"
            )
        )

        return results

    def _measurements_to_dataframe(self, measurements: List[Measurement]) -> pd.DataFrame:
        """Convert measurements to pandas DataFrame for analysis."""
        data = []
        for m in measurements:
            data.append({
                'timestamp': m.timestamp,
                'controller_id': m.controller_id,
                'temperature': m.temperature,
                'air_humidity': m.air_humidity,
                'soil_humidity': m.soil_humidity,
                'light_intensity': m.light_intensity
            })
        
        return pd.DataFrame(data)

    def _extract_time_series(
        self,
        measurements: List[Measurement],
        controller_id: str,
        attribute: str
    ) -> List[Tuple[datetime, float]]:
        """Build ordered time series for the requested attribute."""
        series = [
            (m.timestamp, getattr(m, attribute))
            for m in measurements
            if m.controller_id == controller_id and getattr(m, attribute) is not None
        ]
        series.sort(key=lambda item: item[0])
        return series

    def _build_trend_metric_results(
        self,
        metric_prefix: str,
        controller_id: str,
        timestamp: datetime,
        trend_data: Optional[dict],
        value_unit: str,
        slope_unit: Optional[str] = None
    ) -> List[MetricResult]:
        """Create metric results for trend information."""
        if not trend_data:
            return []

        slope_unit = slope_unit or (f"{value_unit}/h" if value_unit else "unit/h")

        return [
            MetricResult(
                f"{metric_prefix}_trend_change",
                trend_data["change"],
                value_unit,
                timestamp,
                controller_id,
                "Absolute change during the analyzed period"
            ),
            MetricResult(
                f"{metric_prefix}_trend_percent",
                trend_data["percent_change"],
                "%",
                timestamp,
                controller_id,
                "Percentage change relative to first data point"
            ),
            MetricResult(
                f"{metric_prefix}_trend_slope",
                trend_data["slope_per_hour"],
                slope_unit,
                timestamp,
                controller_id,
                "Average change per hour"
            ),
        ]

    async def get_latest_measurement(
        self,
        controller_id: str
    ) -> Optional[Measurement]:
        """Get the most recent measurement for a specific controller."""
        return await self.measurement_repository.get_latest_measurement(controller_id)
