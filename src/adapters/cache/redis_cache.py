"""
Redis Cache Implementation.
Provides Redis-based caching functionality for the Analytics Service.
"""

import redis.asyncio as redis
from typing import Optional, List
import logging
from contextlib import asynccontextmanager

from ...core.ports.cache_service import CacheService
from ...core.ports.logger import Logger


class RedisCache(CacheService):
    """Redis implementation of the CacheService interface."""

    def __init__(
        self,
        host: str,
        port: int,
        password: Optional[str] = None,
        db: int = 0,
        default_ttl: int = 900,  # 15 minutes default
        logger: Optional[Logger] = None
    ):
        """
        Initialize Redis cache connection.
        
        Args:
            host: Redis server host
            port: Redis server port
            password: Redis password (optional)
            db: Redis database number
            default_ttl: Default TTL in seconds
            logger: Logger instance
        """
        self.host = host
        self.port = port
        self.password = password
        self.db = db
        self.default_ttl = default_ttl
        self.logger = logger or logging.getLogger(__name__)
        self._redis: Optional[redis.Redis] = None

    async def connect(self) -> bool:
        """
        Establish connection to Redis server.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            connection_kwargs = {
                "host": self.host,
                "port": self.port,
                "db": self.db,
                "decode_responses": True,
                "socket_connect_timeout": 5,
                "socket_timeout": 5,
                "retry_on_timeout": True,
                "health_check_interval": 30,
            }
            
            if self.password:
                connection_kwargs["password"] = self.password
            
            self._redis = redis.from_url(
                f"redis://:{self.password}@{self.host}:{self.port}/{self.db}" if self.password 
                else f"redis://{self.host}:{self.port}/{self.db}",
                **{k: v for k, v in connection_kwargs.items() if k not in ["host", "port", "db", "password"]}
            )
            
            # Test connection
            await self._redis.ping()
            
            if self.logger:
                self.logger.info(f"Connected to Redis at {self.host}:{self.port}")
            
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Failed to connect to Redis: {str(e)}")
            self._redis = None
            return False

    async def disconnect(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
            if self.logger:
                self.logger.info("Disconnected from Redis")

    @property
    def is_connected(self) -> bool:
        """Check if Redis connection is active."""
        return self._redis is not None

    async def _ensure_connected(self) -> bool:
        """Ensure Redis connection is active, reconnect if needed."""
        if not self.is_connected:
            return await self.connect()
        
        try:
            await self._redis.ping()
            return True
        except Exception:
            if self.logger:
                self.logger.warning("Redis connection lost, attempting to reconnect")
            return await self.connect()

    async def get(self, key: str) -> Optional[str]:
        """
        Retrieve a value from cache by key.
        
        Args:
            key: Cache key to retrieve
            
        Returns:
            Cached value as string, None if not found or expired
        """
        try:
            if not await self._ensure_connected():
                return None
                
            value = await self._redis.get(key)
            
            if self.logger and value is not None:
                self.logger.debug(f"Cache HIT for key: {key}")
            elif self.logger:
                self.logger.debug(f"Cache MISS for key: {key}")
                
            return value
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis GET error for key {key}: {str(e)}")
            return None

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
        try:
            if not await self._ensure_connected():
                return False
                
            ttl_to_use = ttl if ttl is not None else self.default_ttl
            
            result = await self._redis.setex(key, ttl_to_use, value)
            
            if self.logger and result:
                self.logger.debug(f"Cache SET for key: {key} (TTL: {ttl_to_use}s)")
                
            return bool(result)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis SET error for key {key}: {str(e)}")
            return False

    async def delete(self, key: str) -> bool:
        """
        Delete a key from cache.
        
        Args:
            key: Cache key to delete
            
        Returns:
            True if key was deleted, False if key didn't exist
        """
        try:
            if not await self._ensure_connected():
                return False
                
            result = await self._redis.delete(key)
            
            if self.logger:
                self.logger.debug(f"Cache DELETE for key: {key} (existed: {bool(result)})")
                
            return bool(result)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis DELETE error for key {key}: {str(e)}")
            return False

    async def exists(self, key: str) -> bool:
        """
        Check if a key exists in cache.
        
        Args:
            key: Cache key to check
            
        Returns:
            True if key exists, False otherwise
        """
        try:
            if not await self._ensure_connected():
                return False
                
            result = await self._redis.exists(key)
            return bool(result)
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis EXISTS error for key {key}: {str(e)}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching a pattern.
        
        Args:
            pattern: Pattern to match keys (e.g., "analytics:*")
            
        Returns:
            Number of keys deleted
        """
        try:
            if not await self._ensure_connected():
                return 0
                
            # Get all keys matching the pattern
            keys = await self._redis.keys(pattern)
            
            if not keys:
                return 0
                
            # Delete all matching keys
            result = await self._redis.delete(*keys)
            
            if self.logger:
                self.logger.debug(f"Cache CLEAR pattern: {pattern} (deleted: {result} keys)")
                
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis CLEAR PATTERN error for pattern {pattern}: {str(e)}")
            return 0

    async def get_ttl(self, key: str) -> Optional[int]:
        """
        Get remaining time to live for a key.
        
        Args:
            key: Cache key to check
            
        Returns:
            TTL in seconds, None if key doesn't exist or has no TTL
        """
        try:
            if not await self._ensure_connected():
                return None
                
            ttl = await self._redis.ttl(key)
            
            # Redis returns -2 if key doesn't exist, -1 if key exists but has no TTL
            if ttl < 0:
                return None
                
            return ttl
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis TTL error for key {key}: {str(e)}")
            return None

    async def get_info(self) -> dict:
        """
        Get Redis server information and statistics.
        
        Returns:
            Dictionary with Redis server info
        """
        try:
            if not await self._ensure_connected():
                return {}
                
            info = await self._redis.info()
            return {
                "redis_version": info.get("redis_version", "unknown"),
                "used_memory": info.get("used_memory_human", "unknown"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis INFO error: {str(e)}")
            return {}

    async def flush_db(self) -> bool:
        """
        Clear all keys in the current database. Use with caution!
        
        Returns:
            True if successful, False otherwise
        """
        try:
            if not await self._ensure_connected():
                return False
                
            await self._redis.flushdb()
            
            if self.logger:
                self.logger.warning(f"Redis database {self.db} flushed")
                
            return True
            
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis FLUSHDB error: {str(e)}")
            return False

    @asynccontextmanager
    async def pipeline(self):
        """
        Create a Redis pipeline for batch operations.
        
        Usage:
            async with cache.pipeline() as pipe:
                await pipe.set("key1", "value1")
                await pipe.set("key2", "value2")
                results = await pipe.execute()
        """
        try:
            if not await self._ensure_connected():
                raise RuntimeError("Redis connection not available")
                
            pipe = self._redis.pipeline()
            try:
                yield pipe
            finally:
                pass  # Pipeline cleanup is handled automatically
                
        except Exception as e:
            if self.logger:
                self.logger.error(f"Redis PIPELINE error: {str(e)}")
            raise