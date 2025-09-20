from datetime import datetime
from typing import Optional
from dataclasses import dataclass


@dataclass
class Measurement:
    """
    Domain entity representing a sensor measurement.
    This is the core data structure used throughout the analytics service.
    """
    controller_id: str
    timestamp: datetime
    soil_humidity: Optional[float] = None
    air_humidity: Optional[float] = None
    temperature: Optional[float] = None
    light_intensity: Optional[float] = None

    def __post_init__(self):
        """Validate measurement data after initialization."""
        if not self.controller_id:
            raise ValueError("controller_id is required")

        # Validate measurement ranges if values are provided
        if self.soil_humidity is not None:
            if not 0 <= self.soil_humidity <= 1:
                raise ValueError("soil_humidity must be between 0 and 1")

        if self.air_humidity is not None:
            if not 0 <= self.air_humidity <= 100:
                raise ValueError("air_humidity must be between 0 and 100")

        if self.temperature is not None:
            if not -50 <= self.temperature <= 60:
                raise ValueError("temperature must be between -50 and 60 degrees Celsius")

        if self.light_intensity is not None:
            if self.light_intensity < 0:
                raise ValueError("light_intensity must be non-negative")

    @property
    def has_temperature(self) -> bool:
        """Check if temperature measurement is available."""
        return self.temperature is not None

    @property
    def has_humidity_air(self) -> bool:
        """Check if air humidity measurement is available."""
        return self.air_humidity is not None

    @property
    def has_humidity_soil(self) -> bool:
        """Check if soil humidity measurement is available."""
        return self.soil_humidity is not None

    @property
    def has_light(self) -> bool:
        """Check if light measurement is available."""
        return self.light_intensity is not None
