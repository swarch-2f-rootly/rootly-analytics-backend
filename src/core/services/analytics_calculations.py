"""
Analytics calculations module containing all complex agricultural metrics.
Each function implements a specific agronomic formula as defined in the project scope.
"""

import math
from datetime import datetime
from typing import List, Optional, Tuple
from ..domain.measurement import Measurement


class AnalyticsCalculations:
    """
    Static class containing all agricultural analytics calculations.
    These formulas are based on agronomic science and provide actionable insights.
    """

    @staticmethod
    def calculate_growing_degree_days(
        measurements: List[Measurement],
        t_base: float = 10.0
    ) -> float:
        """
        Calculate Growing Degree Days (GDD) - predicts plant development stages.
        
        Formula: GDD = (T_max + T_min) / 2 - T_base
        
        Args:
            measurements: List of temperature measurements
            t_base: Base temperature for crop (default 10°C for most crops)
            
        Returns:
            Accumulated GDD value
        """
        if not measurements:
            return 0.0
        
        temp_measurements = [m for m in measurements if m.has_temperature]
        if not temp_measurements:
            return 0.0
        
        temperatures = [m.temperature for m in temp_measurements]
        t_max = max(temperatures)
        t_min = min(temperatures)
        
        gdd = (t_max + t_min) / 2 - t_base
        return max(0.0, gdd)  # GDD cannot be negative

    @staticmethod
    def calculate_dew_point(temperature: float, humidity: float) -> float:
        """
        Calculate Dew Point - temperature at which water vapor condenses.
        
        Formula: Td = 243.12 * (ln(RH/100) + (17.62 * T) / (243.12 + T)) / 
                     (17.62 - (ln(RH/100) + (17.62 * T) / (243.12 + T)))
        
        Args:
            temperature: Air temperature in Celsius
            humidity: Relative humidity in percentage (0-100)
            
        Returns:
            Dew point temperature in Celsius
        """
        if humidity <= 0 or humidity > 100:
            raise ValueError("Humidity must be between 0 and 100")
        
        # Convert humidity to decimal
        rh_decimal = humidity / 100.0
        
        # Calculate intermediate values
        a = 17.62
        b = 243.12
        
        alpha = math.log(rh_decimal) + (a * temperature) / (b + temperature)
        dew_point = (b * alpha) / (a - alpha)
        
        return dew_point

    @staticmethod
    def calculate_water_deficit_index(
        current_moisture: float,
        max_moisture: float = 1.0,
        min_moisture: float = 0.0
    ) -> float:
        """
        Calculate Water Deficit Index (WDI) - indicates crop water stress.
        
        Formula: WDI = ((Moisture_Max - Moisture_Actual) / (Moisture_Max - Moisture_Min)) * 100
        
        Args:
            current_moisture: Current soil moisture reading
            max_moisture: Maximum possible moisture (default 1.0)
            min_moisture: Minimum possible moisture (default 0.0)
            
        Returns:
            Water deficit index as percentage (0-100)
        """
        if max_moisture <= min_moisture:
            raise ValueError("max_moisture must be greater than min_moisture")
        
        if current_moisture < min_moisture:
            current_moisture = min_moisture
        elif current_moisture > max_moisture:
            current_moisture = max_moisture
        
        wdi = ((max_moisture - current_moisture) / (max_moisture - min_moisture)) * 100
        return max(0.0, min(100.0, wdi))

    @staticmethod
    def calculate_daily_light_integral(average_light_reading: float) -> float:
        """
        Calculate Daily Light Integral (DLI) - total PAR received in one day.
        
        Formula: DLI = (Average_Light_Reading * 3600 * 24) / 1000000
        
        Args:
            average_light_reading: Average light reading for the day
            
        Returns:
            Daily Light Integral in mol/m²/day
        """
        if average_light_reading < 0:
            raise ValueError("Light reading cannot be negative")
        
        # Convert from µmol/m²/s to mol/m²/day
        seconds_per_day = 3600 * 24
        micromol_to_mol = 1000000
        
        dli = (average_light_reading * seconds_per_day) / micromol_to_mol
        return dli

    @staticmethod
    def calculate_saturated_vapor_pressure(temperature: float) -> float:
        """
        Calculate Saturated Vapor Pressure (SVP).
        
        Formula: SVP = 0.6108 * exp((17.27 * T) / (T + 237.3))
        
        Args:
            temperature: Air temperature in Celsius
            
        Returns:
            Saturated vapor pressure in kPa
        """
        svp = 0.6108 * math.exp((17.27 * temperature) / (temperature + 237.3))
        return svp

    @staticmethod
    def calculate_actual_vapor_pressure(temperature: float, humidity: float) -> float:
        """
        Calculate Actual Vapor Pressure (AVP).
        
        Formula: AVP = (RH / 100) * SVP
        
        Args:
            temperature: Air temperature in Celsius
            humidity: Relative humidity in percentage
            
        Returns:
            Actual vapor pressure in kPa
        """
        svp = AnalyticsCalculations.calculate_saturated_vapor_pressure(temperature)
        avp = (humidity / 100) * svp
        return avp

    @staticmethod
    def calculate_vapor_pressure_deficit(temperature: float, humidity: float) -> float:
        """
        Calculate Vapor Pressure Deficit (VPD) - key indicator of plant transpiration.
        
        Formula: VPD = SVP - AVP
        
        Args:
            temperature: Air temperature in Celsius
            humidity: Relative humidity in percentage
            
        Returns:
            Vapor pressure deficit in kPa
        """
        svp = AnalyticsCalculations.calculate_saturated_vapor_pressure(temperature)
        avp = AnalyticsCalculations.calculate_actual_vapor_pressure(temperature, humidity)
        vpd = svp - avp
        return max(0.0, vpd)  # VPD cannot be negative

    @staticmethod
    def calculate_basic_statistics(values: List[float]) -> dict:
        """
        Calculate basic statistical measures for a dataset.

        Args:
            values: List of numerical values

        Returns:
            Dictionary with mean, min, max, std_dev, count
        """
        if not values:
            return {
                "mean": 0.0,
                "min": 0.0,
                "max": 0.0,
                "std_dev": 0.0,
                "count": 0
            }

        count = len(values)
        mean = sum(values) / count
        min_val = min(values)
        max_val = max(values)

        # Calculate standard deviation
        if count > 1:
            variance = sum((x - mean) ** 2 for x in values) / (count - 1)
            std_dev = math.sqrt(variance)
        else:
            std_dev = 0.0

        return {
            "mean": mean,
            "min": min_val,
            "max": max_val,
            "std_dev": std_dev,
            "count": count
        }

    @staticmethod
    def calculate_trend_metrics(
        time_series: List[Tuple[datetime, float]]
    ) -> Optional[dict]:
        """
        Calculate trend metrics (absolute change, percent change, slope).

        Args:
            time_series: Ordered list of (timestamp, value) pairs

        Returns:
            Dictionary with trend information or None if insufficient data
        """
        if len(time_series) < 2:
            return None

        start_time, start_value = time_series[0]
        end_time, end_value = time_series[-1]

        if start_value is None or end_value is None:
            return None

        change = end_value - start_value
        percent_change = 0.0
        if start_value != 0:
            percent_change = (change / start_value) * 100

        duration_hours = (end_time - start_time).total_seconds() / 3600
        duration_hours = max(duration_hours, 0.0)

        slope_per_hour = 0.0
        if duration_hours > 0:
            slope_per_hour = change / duration_hours

        return {
            "start_value": start_value,
            "end_value": end_value,
            "change": change,
            "percent_change": percent_change,
            "slope_per_hour": slope_per_hour,
            "duration_hours": duration_hours,
            "data_points": len(time_series)
        }
