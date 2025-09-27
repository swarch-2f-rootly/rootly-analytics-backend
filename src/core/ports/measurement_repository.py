from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from ..domain.measurement import Measurement


class MeasurementRepository(ABC):
    """
    Port (interface) for measurement data access.
    This defines the contract for fetching measurement data from external sources.
    """

    @abstractmethod
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
        Fetch measurements with optional filters.

        Args:
            controller_id: Filter by controller ID
            start_time: Start time for the query range
            end_time: End time for the query range
            limit: Maximum number of measurements to return
            interval: Time interval for data aggregation
            sensor_id: Filter by sensor identifier
            parameter: Filter by measurement parameter/field

        Returns:
            List of Measurement objects

        Raises:
            RepositoryError: If data access fails
        """
        pass

    @abstractmethod
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
            limit: Maximum number of measurements to return
            
        Returns:
            List of Measurement objects
            
        Raises:
            RepositoryError: If data access fails
        """
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

        Raises:
            RepositoryError: If data access fails
        """
        pass

    @abstractmethod
    async def health_check(self) -> bool:
        """
        Check if the data source is available and healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        pass
