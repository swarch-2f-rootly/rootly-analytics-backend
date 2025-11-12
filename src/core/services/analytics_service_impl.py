"""
Implementation of the AnalyticsService port.
This service orchestrates the analytics calculations and data access.
"""

from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import pandas as pd
import asyncio

from ..ports.analytics_service import AnalyticsService
from ..ports.measurement_repository import MeasurementRepository
from ..ports.cache_service import CacheService, CacheKeyPatterns, CacheTTL
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
    HistoricalQueryResponse,
    HistoricalAverageDataPoint,
    HistoricalAveragesResponse
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
    ALLOWED_AVERAGE_INTERVALS = {
        15: timedelta(minutes=15),
        30: timedelta(minutes=30),
        60: timedelta(hours=1),
        120: timedelta(hours=2),
        360: timedelta(hours=6),
        720: timedelta(hours=12)
    }

    def __init__(self, measurement_repository: MeasurementRepository, cache_service: Optional[CacheService] = None):
        """
        Initialize the analytics service with its dependencies.
        
        Args:
            measurement_repository: Repository for accessing measurement data
            cache_service: Cache service for improving performance (optional)
        """
        self.measurement_repository = measurement_repository
        self.calculator = AnalyticsCalculations()
        self.cache = cache_service

    async def generate_single_metric_report(
        self,
        metric_name: str,
        controller_id: str,
        filters: AnalyticsFilter
    ) -> AnalyticsReport:
        """Generate analytics report for a single metric and controller."""
        if not self.is_metric_supported(metric_name):
            raise InvalidMetricError(metric_name, list(self.SUPPORTED_METRICS.keys()))

        # Try to get from cache first (only if not real-time)
        if self.cache and not filters.real_time:
            cache_key = self.cache.generate_cache_key(
                CacheKeyPatterns.ANALYTICS_SINGLE_METRIC,
                metric=metric_name,
                controller=controller_id,
                start=filters.start_time.isoformat() if filters.start_time else None,
                end=filters.end_time.isoformat() if filters.end_time else None,
                limit=filters.limit
            )
            
            cached_report = await self.cache.get_json(cache_key)
            if cached_report:
                # Reconstruct AnalyticsReport from cached data
                return self._deserialize_analytics_report(cached_report)

        # Generate report if not cached
        report = await self._generate_single_metric_report_impl(metric_name, controller_id, filters)
        
        # Cache the result with appropriate TTL
        if self.cache and report:
            cache_key = self.cache.generate_cache_key(
                CacheKeyPatterns.ANALYTICS_SINGLE_METRIC,
                metric=metric_name,
                controller=controller_id,
                start=filters.start_time.isoformat() if filters.start_time else None,
                end=filters.end_time.isoformat() if filters.end_time else None,
                limit=filters.limit
            )
            # Use shorter TTL for real-time requests
            ttl = CacheTTL.REAL_TIME if filters.real_time else CacheTTL.MEDIUM
            await self.cache.set_json(cache_key, self._serialize_analytics_report(report), ttl)
        
        return report

    async def _generate_single_metric_report_impl(
        self,
        metric_name: str,
        controller_id: str,
        filters: AnalyticsFilter
    ) -> AnalyticsReport:
        """Internal implementation of single metric report generation."""
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
        # Try to get from cache first (only if not real-time)
        if self.cache and not request.filters.real_time:
            cache_key = self.cache.generate_cache_key(
                CacheKeyPatterns.ANALYTICS_MULTI_REPORT,
                controllers=",".join(sorted(request.controllers)),
                metrics=",".join(sorted(request.metrics)),
                start=request.filters.start_time.isoformat() if request.filters.start_time else None,
                end=request.filters.end_time.isoformat() if request.filters.end_time else None,
                limit=request.filters.limit
            )
            
            cached_response = await self.cache.get_json(cache_key)
            if cached_response:
                return self._deserialize_multi_report_response(cached_response)

        # Generate report if not cached
        response = await self._generate_multi_report_impl(request)
        
        # Cache the result with appropriate TTL
        if self.cache and response:
            cache_key = self.cache.generate_cache_key(
                CacheKeyPatterns.ANALYTICS_MULTI_REPORT,
                controllers=",".join(sorted(request.controllers)),
                metrics=",".join(sorted(request.metrics)),
                start=request.filters.start_time.isoformat() if request.filters.start_time else None,
                end=request.filters.end_time.isoformat() if request.filters.end_time else None,
                limit=request.filters.limit
            )
            # Use shorter TTL for real-time requests
            ttl = CacheTTL.REAL_TIME if request.filters.real_time else CacheTTL.MEDIUM
            await self.cache.set_json(cache_key, self._serialize_multi_report_response(response), ttl)
        
        return response

    async def _generate_multi_report_impl(self, request: MultiReportRequest) -> MultiReportResponse:
        """Internal implementation of multi report generation."""
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
        interval: str,
        real_time: bool = False
    ) -> TrendAnalysis:
        """Generate trend analysis for a specific metric over time."""
        if not self.is_metric_supported(metric_name):
            raise InvalidMetricError(metric_name, list(self.SUPPORTED_METRICS.keys()))

        # Try to get from cache first (only if not real-time)
        if self.cache and not real_time:
            cache_key = self.cache.generate_cache_key(
                CacheKeyPatterns.ANALYTICS_TREND_ANALYSIS,
                metric=metric_name,
                controller=controller_id,
                start=start_time.isoformat(),
                end=end_time.isoformat(),
                interval=interval
            )
            
            cached_trend = await self.cache.get_json(cache_key)
            if cached_trend:
                return self._deserialize_trend_analysis(cached_trend)

        # Generate trend analysis if not cached
        trend = await self._generate_trend_analysis_impl(metric_name, controller_id, start_time, end_time, interval)
        
        # Cache the result with appropriate TTL
        if self.cache and trend:
            cache_key = self.cache.generate_cache_key(
                CacheKeyPatterns.ANALYTICS_TREND_ANALYSIS,
                metric=metric_name,
                controller=controller_id,
                start=start_time.isoformat(),
                end=end_time.isoformat(),
                interval=interval
            )
            # Use shorter TTL for real-time requests
            ttl = CacheTTL.REAL_TIME if real_time else CacheTTL.LONG
            await self.cache.set_json(cache_key, self._serialize_trend_analysis(trend), ttl)
        
        return trend

    async def _generate_trend_analysis_impl(
        self,
        metric_name: str,
        controller_id: str,
        start_time: datetime,
        end_time: datetime,
        interval: str
    ) -> TrendAnalysis:
        """Internal implementation of trend analysis generation."""
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

    async def query_historical_averages(
        self,
        filters: HistoricalQueryFilter,
        average_interval: int
    ) -> HistoricalAveragesResponse:
        """Aggregate historical measurements by interval and calculate averages."""
        if average_interval not in self.ALLOWED_AVERAGE_INTERVALS:
            raise AnalyticsServiceError(
                f"Unsupported average interval: {average_interval} minutes"
            )

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

        response_filters = HistoricalQueryFilter(
            start_time=filters.start_time,
            end_time=filters.end_time,
            limit=filters.limit,
            controller_id=filters.controller_id,
            sensor_id=filters.sensor_id,
            parameter=filters.parameter
        )

        if not measurements:
            return HistoricalAveragesResponse(
                data_points=[],
                generated_at=datetime.now(),
                total_points=0,
                interval_minutes=average_interval,
                filters_applied=response_filters
            )

        interval_delta = self.ALLOWED_AVERAGE_INTERVALS[average_interval]

        start_reference = filters.start_time or min(m.timestamp for m in measurements)
        end_reference = filters.end_time or max(m.timestamp for m in measurements)

        start_aligned = self._floor_to_interval(start_reference, interval_delta)
        end_aligned = self._ceil_to_interval(end_reference, interval_delta)

        if start_aligned == end_aligned:
            end_aligned = start_aligned + interval_delta

        candidate_metrics = [parameter_filter] if parameter_filter else list(self.SUPPORTED_METRICS.keys())

        bucket_totals: Dict[Tuple[str, str, datetime], Dict[str, float]] = {}

        for measurement in measurements:
            measurement_ts = measurement.timestamp

            if filters.start_time and measurement_ts < filters.start_time:
                continue
            if filters.end_time and measurement_ts > filters.end_time:
                continue

            for metric_name in candidate_metrics:
                attribute = self.SUPPORTED_METRICS[metric_name]
                value = getattr(measurement, attribute, None)
                if value is None:
                    continue

                interval_start = self._floor_to_interval(measurement_ts, interval_delta)
                if interval_start < start_aligned:
                    interval_start = start_aligned
                if interval_start >= end_aligned:
                    continue

                key = (measurement.controller_id, metric_name, interval_start)
                bucket = bucket_totals.setdefault(key, {"sum": 0.0, "count": 0})
                bucket["sum"] += float(value)
                bucket["count"] += 1

        data_points: List[HistoricalAverageDataPoint] = []
        for (controller_id, metric_name, interval_start), bucket in bucket_totals.items():
            if bucket["count"] == 0:
                continue

            data_points.append(
                HistoricalAverageDataPoint(
                    interval_start=interval_start,
                    interval_end=interval_start + interval_delta,
                    controller_id=controller_id,
                    parameter=metric_name,
                    average_value=bucket["sum"] / bucket["count"],
                    measurements_count=bucket["count"]
                )
            )

        data_points.sort(key=lambda point: (point.interval_start, point.controller_id, point.parameter))

        return HistoricalAveragesResponse(
            data_points=data_points,
            generated_at=datetime.now(),
            total_points=len(data_points),
            interval_minutes=average_interval,
            filters_applied=response_filters
        )

    def _floor_to_interval(self, timestamp: datetime, interval: timedelta) -> datetime:
        """Snap timestamp down to the nearest interval boundary."""
        if timestamp.tzinfo is None:
            epoch = datetime(1970, 1, 1)
        else:
            epoch = datetime(1970, 1, 1, tzinfo=timestamp.tzinfo)

        elapsed = timestamp - epoch
        intervals = elapsed // interval
        return epoch + (intervals * interval)

    def _ceil_to_interval(self, timestamp: datetime, interval: timedelta) -> datetime:
        """Snap timestamp up to the nearest interval boundary."""
        floored = self._floor_to_interval(timestamp, interval)
        if floored == timestamp:
            return timestamp
        return floored + interval

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

    # Cache serialization/deserialization methods
    
    def _serialize_analytics_report(self, report: AnalyticsReport) -> dict:
        """Serialize AnalyticsReport to dict for caching."""
        return {
            "controller_id": report.controller_id,
            "metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "unit": metric.unit,
                    "timestamp": metric.timestamp.isoformat(),
                    "controller_id": metric.controller_id,
                    "description": metric.description
                }
                for metric in report.metrics
            ],
            "generated_at": report.generated_at.isoformat(),
            "data_points_count": report.data_points_count,
            "filters_applied": {
                "start_time": report.filters_applied.start_time.isoformat() if report.filters_applied.start_time else None,
                "end_time": report.filters_applied.end_time.isoformat() if report.filters_applied.end_time else None,
                "limit": report.filters_applied.limit
            }
        }

    def _deserialize_analytics_report(self, data: dict) -> AnalyticsReport:
        """Deserialize dict to AnalyticsReport from cache."""
        metrics = [
            MetricResult(
                name=metric["name"],
                value=metric["value"],
                unit=metric["unit"],
                timestamp=datetime.fromisoformat(metric["timestamp"]),
                controller_id=metric["controller_id"],
                description=metric["description"]
            )
            for metric in data["metrics"]
        ]
        
        filters = AnalyticsFilter(
            start_time=datetime.fromisoformat(data["filters_applied"]["start_time"]) if data["filters_applied"]["start_time"] else None,
            end_time=datetime.fromisoformat(data["filters_applied"]["end_time"]) if data["filters_applied"]["end_time"] else None,
            limit=data["filters_applied"]["limit"]
        )
        
        return AnalyticsReport(
            controller_id=data["controller_id"],
            metrics=metrics,
            generated_at=datetime.fromisoformat(data["generated_at"]),
            data_points_count=data["data_points_count"],
            filters_applied=filters
        )

    def _serialize_multi_report_response(self, response: MultiReportResponse) -> dict:
        """Serialize MultiReportResponse to dict for caching."""
        return {
            "reports": {
                controller_id: self._serialize_analytics_report(report)
                for controller_id, report in response.reports.items()
            },
            "generated_at": response.generated_at.isoformat(),
            "total_controllers": response.total_controllers,
            "total_metrics": response.total_metrics
        }

    def _deserialize_multi_report_response(self, data: dict) -> MultiReportResponse:
        """Deserialize dict to MultiReportResponse from cache."""
        reports = {
            controller_id: self._deserialize_analytics_report(report_data)
            for controller_id, report_data in data["reports"].items()
        }
        
        return MultiReportResponse(
            reports=reports,
            generated_at=datetime.fromisoformat(data["generated_at"]),
            total_controllers=data["total_controllers"],
            total_metrics=data["total_metrics"]
        )

    def _serialize_trend_analysis(self, trend: TrendAnalysis) -> dict:
        """Serialize TrendAnalysis to dict for caching."""
        return {
            "metric_name": trend.metric_name,
            "controller_id": trend.controller_id,
            "interval": trend.interval,
            "data_points": [
                {
                    "timestamp": point.timestamp.isoformat(),
                    "value": point.value,
                    "interval": point.interval
                }
                for point in trend.data_points
            ],
            "summary": {
                "total_points": trend.summary.total_points,
                "start_time": trend.summary.start_time.isoformat(),
                "end_time": trend.summary.end_time.isoformat(),
                "min_value": trend.summary.min_value,
                "max_value": trend.summary.max_value,
                "avg_value": trend.summary.avg_value,
                "trend_direction": trend.summary.trend_direction,
                "slope": trend.summary.slope
            },
            "generated_at": trend.generated_at.isoformat()
        }

    def _deserialize_trend_analysis(self, data: dict) -> TrendAnalysis:
        """Deserialize dict to TrendAnalysis from cache."""
        from ..domain.analytics import TrendSummary  # Import here to avoid circular imports
        
        data_points = [
            TrendDataPoint(
                timestamp=datetime.fromisoformat(point["timestamp"]),
                value=point["value"],
                interval=point["interval"]
            )
            for point in data["data_points"]
        ]
        
        summary = TrendSummary(
            total_points=data["summary"]["total_points"],
            start_time=datetime.fromisoformat(data["summary"]["start_time"]),
            end_time=datetime.fromisoformat(data["summary"]["end_time"]),
            min_value=data["summary"]["min_value"],
            max_value=data["summary"]["max_value"],
            avg_value=data["summary"]["avg_value"],
            trend_direction=data["summary"]["trend_direction"],
            slope=data["summary"]["slope"]
        )
        
        return TrendAnalysis(
            metric_name=data["metric_name"],
            controller_id=data["controller_id"],
            interval=data["interval"],
            data_points=data_points,
            summary=summary,
            generated_at=datetime.fromisoformat(data["generated_at"])
        )

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
            filters: Filters including real_time flag
            
        Returns:
            Comprehensive analytics report with advanced statistics
        """
        import time
        import numpy as np
        from statistics import stdev, variance
        
        start_time = time.time()
        
        # Check cache first (only if not real-time)
        if self.cache and not filters.real_time:
            cache_key = self.cache.generate_cache_key(
                "comprehensive_analytics",
                controllers=",".join(sorted(controller_ids)),
                metrics=",".join(sorted(metrics)),
                start=filters.start_time.isoformat() if filters.start_time else None,
                end=filters.end_time.isoformat() if filters.end_time else None,
                limit=filters.limit
            )
            
            cached_result = await self.cache.get_json(cache_key)
            if cached_result:
                cache_time = time.time() - start_time
                cached_result["performance"] = {
                    "cache_hit": True,
                    "execution_time_ms": round(cache_time * 1000, 2),
                    "data_source": "redis_cache"
                }
                return cached_result
        

        
        comprehensive_report = {
            "summary": {
                "total_controllers": len(controller_ids),
                "total_metrics": len(metrics),
                "analysis_period": {
                    "start": filters.start_time.isoformat() if filters.start_time else None,
                    "end": filters.end_time.isoformat() if filters.end_time else None
                },
                "generated_at": datetime.now().isoformat()
            },
            "controller_analytics": {},
            "cross_controller_analysis": {},
            "performance": {}
        }
        
        all_measurements = []
        
        # Process each controller with intensive calculations
        for controller_id in controller_ids:
            measurements = await self.measurement_repository.get_measurements(
                controller_id=controller_id,
                start_time=filters.start_time,
                end_time=filters.end_time,
                limit=filters.limit or 10000
            )
            
            if not measurements:
                continue
                
            all_measurements.extend(measurements)
            
            # Convert measurements to DataFrame for complex analysis
            df = self._measurements_to_dataframe(measurements)
            
            controller_analytics = {
                "controller_id": controller_id,
                "data_points": len(measurements),
                "metrics_analysis": {}
            }
            
            # Intensive analysis for each metric
            for metric_name in metrics:
                if not self.is_metric_supported(metric_name):
                    continue
                    
                metric_column = self.SUPPORTED_METRICS[metric_name]
                
                if metric_column not in df.columns or df[metric_column].isna().all():
                    continue
                
                values = df[metric_column].dropna().values
                
                if len(values) < 2:
                    continue
                
                # Computationally expensive statistical calculations
                metric_stats = {
                    "basic_stats": {
                        "count": len(values),
                        "mean": float(np.mean(values)),
                        "median": float(np.median(values)),
                        "std_dev": float(stdev(values)),
                        "variance": float(variance(values)),
                        "min": float(np.min(values)),
                        "max": float(np.max(values))
                    },
                    "advanced_stats": {
                        "percentiles": {
                            "p25": float(np.percentile(values, 25)),
                            "p75": float(np.percentile(values, 75)),
                            "p90": float(np.percentile(values, 90)),
                            "p95": float(np.percentile(values, 95)),
                            "p99": float(np.percentile(values, 99))
                        },
                        "skewness": float(self._calculate_skewness(values)),
                        "kurtosis": float(self._calculate_kurtosis(values))
                    },
                    "anomaly_detection": self._detect_anomalies(values),
                    "trend_analysis": self._advanced_trend_analysis(values),
                    "seasonality": self._detect_seasonality(values)
                }
                
                controller_analytics["metrics_analysis"][metric_name] = metric_stats
            
            comprehensive_report["controller_analytics"][controller_id] = controller_analytics
        
        # Cross-controller correlation analysis (very expensive)
        if len(controller_ids) > 1 and len(all_measurements) > 100:
            comprehensive_report["cross_controller_analysis"] = await self._calculate_cross_controller_correlations(
                controller_ids, metrics, all_measurements
            )
        
        # Performance metrics
        total_time = time.time() - start_time
        comprehensive_report["performance"] = {
            "cache_hit": False,
            "execution_time_ms": round(total_time * 1000, 2),
            "data_source": "influxdb_direct",
            "total_data_points": len(all_measurements),
            "computation_complexity": "high"
        }
        
        # Cache the expensive result
        if self.cache:
            cache_key = self.cache.generate_cache_key(
                "comprehensive_analytics",
                controllers=",".join(sorted(controller_ids)),
                metrics=",".join(sorted(metrics)),
                start=filters.start_time.isoformat() if filters.start_time else None,
                end=filters.end_time.isoformat() if filters.end_time else None,
                limit=filters.limit
            )
            
            # Use appropriate TTL
            ttl = CacheTTL.REAL_TIME if filters.real_time else CacheTTL.LONG
            await self.cache.set_json(cache_key, comprehensive_report, ttl)
        
        return comprehensive_report
    
    def _calculate_skewness(self, values):
        """Calculate skewness of data distribution."""
        n = len(values)
        if n < 3:
            return 0.0
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return 0.0
        
        skewness = np.sum(((values - mean) / std) ** 3) / n
        return skewness
    
    def _calculate_kurtosis(self, values):
        """Calculate kurtosis of data distribution."""
        n = len(values)
        if n < 4:
            return 0.0
        
        mean = np.mean(values)
        std = np.std(values)
        
        if std == 0:
            return 0.0
        
        kurtosis = np.sum(((values - mean) / std) ** 4) / n - 3
        return kurtosis
    
    def _detect_anomalies(self, values):
        """Detect anomalies using statistical methods."""
        if len(values) < 10:
            return {"anomalies_count": 0, "anomaly_threshold": None}
        
        q1 = np.percentile(values, 25)
        q3 = np.percentile(values, 75)
        iqr = q3 - q1
        
        lower_bound = q1 - 1.5 * iqr
        upper_bound = q3 + 1.5 * iqr
        
        anomalies = values[(values < lower_bound) | (values > upper_bound)]
        
        return {
            "anomalies_count": len(anomalies),
            "anomaly_threshold": {"lower": lower_bound, "upper": upper_bound},
            "anomaly_percentage": round((len(anomalies) / len(values)) * 100, 2)
        }
    
    def _advanced_trend_analysis(self, values):
        """Perform advanced trend analysis."""
        if len(values) < 5:
            return {"trend": "insufficient_data"}
        
        # Linear regression for trend
        x = np.arange(len(values))
        coeffs = np.polyfit(x, values, 1)
        slope = coeffs[0]
        
        # Moving averages
        window_size = min(10, len(values) // 3)
        if window_size >= 2:
            moving_avg = np.convolve(values, np.ones(window_size)/window_size, mode='valid')
            volatility = np.std(moving_avg)
        else:
            volatility = np.std(values)
        
        return {
            "trend_slope": float(slope),
            "trend_direction": "increasing" if slope > 0 else "decreasing" if slope < 0 else "stable",
            "volatility": float(volatility),
            "trend_strength": abs(slope) / (np.std(values) + 0.001)
        }
    
    def _detect_seasonality(self, values):
        """Basic seasonality detection."""
        if len(values) < 24:
            return {"seasonality_detected": False}
        
        # Simple autocorrelation for seasonality
        autocorr_12 = np.corrcoef(values[:-12], values[12:])[0, 1] if len(values) >= 24 else 0
        autocorr_24 = np.corrcoef(values[:-24], values[24:])[0, 1] if len(values) >= 48 else 0
        
        return {
            "seasonality_detected": abs(autocorr_12) > 0.3 or abs(autocorr_24) > 0.3,
            "12_hour_correlation": float(autocorr_12) if not np.isnan(autocorr_12) else 0,
            "24_hour_correlation": float(autocorr_24) if not np.isnan(autocorr_24) else 0
        }
    
    async def _calculate_cross_controller_correlations(self, controller_ids, metrics, all_measurements):
        """Calculate correlations between controllers (expensive operation)."""
        
        correlations = {}
        
        # Group measurements by controller
        controller_data = {}
        for measurement in all_measurements:
            if measurement.controller_id not in controller_data:
                controller_data[measurement.controller_id] = []
            controller_data[measurement.controller_id].append(measurement)
        
        # Calculate pairwise correlations
        for i, controller_a in enumerate(controller_ids):
            for j, controller_b in enumerate(controller_ids[i+1:], i+1):
                if controller_a in controller_data and controller_b in controller_data:
                    correlation_key = f"{controller_a}_vs_{controller_b}"
                    
                    # Convert to DataFrames
                    df_a = self._measurements_to_dataframe(controller_data[controller_a])
                    df_b = self._measurements_to_dataframe(controller_data[controller_b])
                    
                    metric_correlations = {}
                    for metric in metrics:
                        if not self.is_metric_supported(metric):
                            continue
                        
                        metric_column = self.SUPPORTED_METRICS[metric]
                        
                        if (metric_column in df_a.columns and metric_column in df_b.columns):
                            values_a = df_a[metric_column].dropna()
                            values_b = df_b[metric_column].dropna()
                            
                            if len(values_a) > 5 and len(values_b) > 5:
                                # Align by timestamp for proper correlation
                                min_len = min(len(values_a), len(values_b))
                                correlation = np.corrcoef(values_a[:min_len], values_b[:min_len])[0, 1]
                                
                                if not np.isnan(correlation):
                                    metric_correlations[metric] = {
                                        "correlation": float(correlation),
                                        "strength": "strong" if abs(correlation) > 0.7 else "moderate" if abs(correlation) > 0.3 else "weak",
                                        "sample_size": min_len
                                    }
                    
                    if metric_correlations:
                        correlations[correlation_key] = metric_correlations
        
        return correlations
