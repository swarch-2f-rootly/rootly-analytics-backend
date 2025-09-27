"""
InfluxDB adapter for measurement data access.
This implements the MeasurementRepository port using InfluxDB.
"""

from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta, timezone
import logging
from collections import defaultdict

from influxdb_client import InfluxDBClient
from influxdb_client.client.query_api import QueryApi
from influxdb_client.client.write_api import WriteApi, SYNCHRONOUS

from ...core.ports.measurement_repository import MeasurementRepository
from ...core.ports.exceptions import RepositoryError
from ...core.domain.measurement import Measurement


class InfluxRepository(MeasurementRepository):
    """
    InfluxDB adapter that implements the MeasurementRepository port.
    Provides access to measurement data stored in InfluxDB.
    """

    def __init__(self, url: str, token: str, bucket: str, org: str):
        """
        Initialize the InfluxDB repository.

        Args:
            url: InfluxDB server URL (e.g., 'http://localhost:8086')
            token: InfluxDB authentication token
            bucket: Bucket name for data storage
            org: Organization name
        """
        self.url = url
        self.token = token
        self.bucket = bucket
        self.org = org
        self.measurement_name = "agricultural_sensors"
        self.logger = logging.getLogger(__name__)

        # Initialize client and APIs
        self.client = InfluxDBClient(url=url, token=token, org=org)
        self.query_api: QueryApi = self.client.query_api()
        self.write_api: WriteApi = self.client.write_api(write_options=SYNCHRONOUS)

    async def get_measurements(
        self,
        controller_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        interval: Optional[str] = None,
        sensor_id: Optional[str] = None,
        parameter: Optional[str] = None
    ) -> List[Measurement]:
        """
        Fetch measurements from InfluxDB with optional filters.

        Args:
            controller_id: Filter by controller ID
            start_time: Start time for the query range
            end_time: End time for the query range
            limit: Maximum number of measurements to return
            interval: Time interval for data aggregation

        Returns:
            List of Measurement objects

        Raises:
            RepositoryError: If data access fails
        """
        try:
            # Build Flux query
            flux_query = self._build_flux_query(
                controller_id=controller_id,
                start_time=start_time,
                end_time=end_time,
                limit=limit,
                interval=interval,
                sensor_id=sensor_id,
                parameter=parameter
            )

            self.logger.info(f"Executing Flux query: {flux_query}")

            # Execute query
            result = self.query_api.query(flux_query)

            # Process results
            measurements = self._process_query_results(result)

            self.logger.info(f"Successfully fetched {len(measurements)} measurements")
            return measurements

        except Exception as e:
            self.logger.error(f"Error fetching measurements from InfluxDB: {e}")
            raise RepositoryError("Failed to fetch measurements from InfluxDB", e)

    async def get_measurements_by_controllers(
        self,
        controllers: List[str],
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        sensor_id: Optional[str] = None,
        parameter: Optional[str] = None
    ) -> List[Measurement]:
        """
        Fetch measurements for multiple controllers.

        Args:
            controllers: List of controller IDs
            start_time: Start time for the query range
            end_time: End time for the query range
            limit: Maximum number of measurements per controller
            sensor_id: Filter by sensor identifier
            parameter: Filter by measurement parameter

        Returns:
            Combined list of Measurement objects from all controllers

        Raises:
            RepositoryError: If data fetching fails
        """
        all_measurements = []

        try:
            # Calculate per-controller limit if total limit is specified
            per_controller_limit = None
            if limit:
                per_controller_limit = max(1, limit // len(controllers))

            # Query each controller
            for controller_id in controllers:
                try:
                    measurements = await self.get_measurements(
                        controller_id=controller_id,
                        start_time=start_time,
                        end_time=end_time,
                        limit=per_controller_limit,
                        sensor_id=sensor_id,
                        parameter=parameter
                    )
                    all_measurements.extend(measurements)

                except Exception as e:
                    self.logger.warning(
                        f"Error fetching data for controller {controller_id}: {e}"
                    )
                    continue

            # Sort by timestamp
            all_measurements.sort(key=lambda m: m.timestamp)

            # Apply total limit if specified
            if limit and len(all_measurements) > limit:
                all_measurements = all_measurements[:limit]

            self.logger.info(
                f"Fetched {len(all_measurements)} measurements from {len(controllers)} controllers"
            )
            return all_measurements

        except Exception as e:
            self.logger.error(f"Error fetching measurements for multiple controllers: {e}")
            raise RepositoryError("Failed to fetch measurements for multiple controllers", e)

    async def get_latest_measurement(
        self,
        controller_id: str
    ) -> Optional[Measurement]:
        """
        Get the most recent measurement for a specific controller from the last 10 minutes.
        """
        try:
            # Build Flux query for latest measurement in last 10 minutes
            flux_query = self._build_latest_measurement_query(controller_id)

            self.logger.info(f"Executing latest measurement query for controller {controller_id}")

            # Execute query
            result = self.query_api.query(flux_query)

            # Process results
            measurements = self._process_query_results(result)

            if measurements:
                # Return the most recent measurement (already sorted by timestamp desc)
                latest_measurement = measurements[0]
                self.logger.info(f"Found latest measurement for controller {controller_id} at {latest_measurement.timestamp}")
                return latest_measurement
            else:
                self.logger.info(f"No recent measurements found for controller {controller_id} in the last 10 minutes")
                return None

        except Exception as e:
            self.logger.error(f"Error fetching latest measurement for controller {controller_id}: {e}")
            raise RepositoryError(f"Failed to fetch latest measurement for controller {controller_id}", e)

    async def health_check(self) -> bool:
        """
        Check if the InfluxDB connection is available and healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            # Try to execute a simple query
            health_query = f'''
                from(bucket: "{self.bucket}")
                |> range(start: -1m)
                |> limit(n: 1)
            '''

            result = self.query_api.query(health_query)
            # If we get here without exception, the service is healthy
            return True

        except Exception as e:
            self.logger.warning(f"InfluxDB health check failed: {e}")
            return False

    def close(self):
        """Close the InfluxDB client connection."""
        if self.client:
            self.client.close()
            self.logger.info("InfluxDB client connection closed")

    def _build_flux_query(
        self,
        controller_id: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: Optional[int] = None,
        interval: Optional[str] = None,
        sensor_id: Optional[str] = None,
        parameter: Optional[str] = None
    ) -> str:
        """Build a Flux query string based on the provided parameters."""
        query_parts = []

        # Base query
        query_parts.append(f'from(bucket: "{self.bucket}")')

        # Time range
        time_range = "|> range(start: -30d)"  # Default: last 30 days
        if start_time:
            if end_time:
                time_range = f'|> range(start: {self._format_datetime_for_flux(start_time)}, stop: {self._format_datetime_for_flux(end_time)})'
            else:
                time_range = f'|> range(start: {self._format_datetime_for_flux(start_time)})'
        elif end_time:
            time_range = f'|> range(start: -30d, stop: {self._format_datetime_for_flux(end_time)})'

        query_parts.append(time_range)

        # Filter by measurement name
        query_parts.append(f'|> filter(fn: (r) => r["_measurement"] == "{self.measurement_name}")')

        # Filter by controller ID if specified
        if controller_id:
            query_parts.append(f'|> filter(fn: (r) => r["controller_id"] == "{controller_id}")')

        if sensor_id:
            query_parts.append(f'|> filter(fn: (r) => r["sensor_id"] == "{sensor_id}")')

        if parameter:
            query_parts.append(f'|> filter(fn: (r) => r["_field"] == "{parameter}")')

        # Add aggregation if interval is specified
        if interval:
            query_parts.append(f'|> aggregateWindow(every: {interval}, fn: mean, createEmpty: false)')

        # Sort by time
        query_parts.append('|> sort(columns: ["_time"])')

        # Limit results if specified
        if limit:
            query_parts.append(f'|> limit(n: {limit})')

        return " ".join(query_parts)

    def _build_latest_measurement_query(self, controller_id: str) -> str:
        """Build a Flux query to get the most recent measurement for a controller in the last 10 minutes."""
        query_parts = []

        # Base query
        query_parts.append(f'from(bucket: "{self.bucket}")')

        # Time range: last 10 minutes
        query_parts.append('|> range(start: -10m)')

        # Filter by measurement name
        query_parts.append(f'|> filter(fn: (r) => r["_measurement"] == "{self.measurement_name}")')

        # Filter by controller ID
        query_parts.append(f'|> filter(fn: (r) => r["controller_id"] == "{controller_id}")')

        # Sort by time descending (most recent first)
        query_parts.append('|> sort(columns: ["_time"], desc: true)')

        # Limit to 1 result (most recent)
        query_parts.append('|> limit(n: 1)')

        return " ".join(query_parts)

    def _process_query_results(self, result) -> List[Measurement]:
        """
        Process InfluxDB query results into Measurement domain objects.

        Args:
            result: InfluxDB query result

        Returns:
            List of Measurement objects
        """
        # Group records by timestamp and controller_id
        measurement_groups: Dict[str, Dict[str, Any]] = defaultdict(dict)

        for table in result:
            for record in table.records:
                controller_id = record.values.get("controller_id", "")
                timestamp = record.get_time()
                sensor_id = record.values.get("sensor_id") or record.values.get("sensor")

                if not controller_id or not timestamp:
                    continue

                # Create unique key for grouping (per controller/sensor/time)
                sensor_key = sensor_id or "__unknown_sensor__"
                key = f"{controller_id}_{sensor_key}_{timestamp.isoformat()}"

                # Extract field value
                field = record.get_field()
                value = record.get_value()

                if field and value is not None:
                    if key not in measurement_groups:
                        measurement_groups[key] = {
                            "controller_id": controller_id,
                            "timestamp": timestamp,
                            "sensor_id": sensor_id,
                            "fields": {}
                        }

                    # Field names are the same in InfluxDB and domain
                    measurement_groups[key]["fields"][field] = float(value)

        # Convert grouped data to Measurement objects
        measurements = []
        for group_data in measurement_groups.values():
            measurement = Measurement(
                controller_id=group_data["controller_id"],
                timestamp=group_data["timestamp"],
                soil_humidity=group_data["fields"].get("soil_humidity"),
                air_humidity=group_data["fields"].get("air_humidity"),
                temperature=group_data["fields"].get("temperature"),
                light_intensity=group_data["fields"].get("light_intensity"),
                sensor_id=group_data.get("sensor_id")
            )
            measurements.append(measurement)

        # Sort measurements to guarantee chronological order per controller
        measurements.sort(key=lambda m: (m.controller_id, m.timestamp))

        return measurements

    def _format_datetime_for_flux(self, dt: datetime) -> str:
        """
        Format a datetime object for use in InfluxDB Flux queries.

        Args:
            dt: Datetime object to format

        Returns:
            String in RFC3339 format for Flux queries
        """
        # Ensure the datetime is in UTC
        if dt.tzinfo is None:
            # Assume naive datetime is in UTC
            dt = dt.replace(tzinfo=timezone.utc)
        else:
            # Convert to UTC if it's not already
            dt = dt.astimezone(timezone.utc)

        # Format as RFC3339 (ISO 8601 with Z suffix for UTC)
        return dt.isoformat().replace('+00:00', 'Z')
