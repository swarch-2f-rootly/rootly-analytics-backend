"""
Cache Service Port - Abstract interface for caching functionality.
Provides a standardized interface for caching operations across different cache implementations.
"""

from abc import ABC, abstractmethod
from typing import Optional, Any, Dict, List
from datetime import timedelta
import json
import hashlib


class CacheService(ABC):
    """Abstract base class for cache service implementations."""

    @abstractmethod
    async def get(self, key: str) -> Optional[str]:
        """
        Retrieve a value from cache by key.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value as string, None if not found or expired
        """
        pass

    @abstractmethod
    async def set(self, key: str, value: str, ttl: Optional[int] = None) -> bool:
        """
        Store a value in cache with optional TTL.
        
        Args:
            key: Cache key
            value: Value to cache (as string)
            ttl: Time to live in seconds, None for default TTL
            
        Returns:
            True if successfully cached, False otherwise
        """
        pass

    @abstractmethod
    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        pass

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        pass

    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match keys (e.g., "analytics:*")
            
        Returns:
            Number of keys deleted
        """
        pass

    @abstractmethod
    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining time to live for a key.
        
        Args:
            key: Cache key to check
            
        Returns:
            TTL in seconds, None if key doesn't exist or has no TTL
        """
        pass

    # Helper methods for common cache operations
    
    async def get_json(self, key: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve and deserialize JSON value from cache.
        
        Args:
            key: Cache key
            
        Returns:
            Deserialized JSON object, None if not found or invalid JSON
        """
        try:
            value = await self.get(key)
            if value is None:
                return None
            return json.loads(value)
        except (json.JSONDecodeError, TypeError):
            return None

    async def set_json(self, key: str, value: Dict[str, Any], ttl: Optional[int] = None) -> bool:
        """
        Serialize and store JSON value in cache.
        
        Args:
            key: Cache key
            value: Object to serialize and cache
            ttl: Time to live in seconds
            
        Returns:
            True if successfully cached, False otherwise
        """
        try:
            json_value = json.dumps(value, default=str, separators=(',', ':'))
            return await self.set(key, json_value, ttl)
        except (TypeError, ValueError):
            return False

    def generate_cache_key(self, prefix: str, **kwargs) -> str:
        """
        Generate a consistent cache key from parameters.
        
        Args:
            prefix: Key prefix (e.g., "analytics", "graphql")
            **kwargs: Parameters to include in key generation
            
        Returns:
            Generated cache key
        """
        # Sort kwargs for consistent key generation
        sorted_params = sorted(kwargs.items())
        param_str = "&".join(f"{k}={v}" for k, v in sorted_params if v is not None)
        
        # Create hash for long parameter strings
        if len(param_str) > 100:
            param_hash = hashlib.md5(param_str.encode()).hexdigest()[:12]
            return f"{prefix}:{param_hash}"
        
        # Use parameters directly for short strings
        param_str = param_str.replace(" ", "_").replace(":", "_")
        return f"{prefix}:{param_str}" if param_str else prefix

    async def get_or_set(self, key: str, getter_func, ttl: Optional[int] = None) -> Any:
        """
        Get value from cache, or compute and cache it if not present.
        
        Args:
            key: Cache key
            getter_func: Async function to compute value if not cached
            ttl: Time to live in seconds
            
        Returns:
            Cached or computed value
        """
        # Try to get from cache first
        cached_value = await self.get_json(key)
        if cached_value is not None:
            return cached_value

        # Compute value and cache it
        computed_value = await getter_func()
        if computed_value is not None:
            await self.set_json(key, computed_value, ttl)
        
        return computed_value


class CacheKeyPatterns:
    """Common cache key patterns for the analytics service."""
    
    # GraphQL resolver caches
    GRAPHQL_SINGLE_METRIC = "graphql:single_metric"
    GRAPHQL_MULTI_REPORT = "graphql:multi_report"
    GRAPHQL_TREND_ANALYSIS = "graphql:trend_analysis"
    GRAPHQL_LATEST_MEASUREMENT = "graphql:latest_measurement"
    GRAPHQL_SUPPORTED_METRICS = "graphql:supported_metrics"
    
    # Analytics service caches
    ANALYTICS_SINGLE_METRIC = "analytics:single_metric"
    ANALYTICS_MULTI_REPORT = "analytics:multi_report"
    ANALYTICS_TREND_ANALYSIS = "analytics:trend_analysis"
    ANALYTICS_CALCULATIONS = "analytics:calculations"
    
    # Repository caches
    REPO_MEASUREMENTS = "repo:measurements"
    REPO_LATEST_MEASUREMENT = "repo:latest_measurement"
    REPO_CONTROLLERS = "repo:controllers"


class CacheTTL:
    """Common TTL values in seconds."""
    
    REAL_TIME = 30         # 30 seconds - for real-time data that still benefits from minimal caching
    VERY_SHORT = 60        # 1 minute - for frequently changing data
    SHORT = 300            # 5 minutes - for semi-static data
    MEDIUM = 900           # 15 minutes - for reports and analytics
    LONG = 3600            # 1 hour - for static configuration
    VERY_LONG = 86400      # 24 hours - for rarely changing data