"""
Caching service using Redis.
"""
import redis.asyncio as redis
import json
import logging
from typing import Optional, Any, Dict
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class CacheService:
    """Service for caching operations using Redis."""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self.is_connected = False
    
    async def connect(self) -> None:
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(
                settings.REDIS_URL,
                decode_responses=True,
                socket_keepalive=True,
                socket_keepalive_options={}
            )
            
            # Test connection
            await self.redis_client.ping()
            self.is_connected = True
            logger.info("Connected to Redis successfully")
            
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}")
            self.is_connected = False
    
    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            self.is_connected = False
            logger.info("Disconnected from Redis")
    
    def _generate_cache_key(self, symbol: str, indicator: str, params: Dict[str, Any]) -> str:
        """Generate cache key for indicator data."""
        # Sort parameters for consistent key generation
        sorted_params = sorted(params.items())
        params_str = "_".join([f"{k}:{v}" for k, v in sorted_params])
        return f"indicator:{symbol}:{indicator}:{params_str}"
    
    async def get_cached_data(self, symbol: str, indicator: str, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        Get cached indicator data.
        
        Args:
            symbol: Stock symbol
            indicator: Indicator name
            params: Indicator parameters
            
        Returns:
            Cached data or None if not found
        """
        if not self.is_connected:
            return None
        
        try:
            cache_key = self._generate_cache_key(symbol, indicator, params)
            cached_data = await self.redis_client.get(cache_key)
            
            if cached_data:
                data = json.loads(cached_data)
                logger.debug(f"Cache hit for key: {cache_key}")
                return data
            
            logger.debug(f"Cache miss for key: {cache_key}")
            return None
            
        except Exception as e:
            logger.error(f"Error getting cached data: {e}")
            return None
    
    async def set_cached_data(
        self,
        symbol: str,
        indicator: str,
        params: Dict[str, Any],
        data: Dict[str, Any],
        expire_minutes: Optional[int] = None
    ) -> bool:
        """
        Set cached indicator data.
        
        Args:
            symbol: Stock symbol
            indicator: Indicator name
            params: Indicator parameters
            data: Data to cache
            expire_minutes: Cache expiration in minutes
            
        Returns:
            True if successful, False otherwise
        """
        if not self.is_connected:
            return False
        
        try:
            cache_key = self._generate_cache_key(symbol, indicator, params)
            
            # Add timestamp to data
            data_with_timestamp = {
                **data,
                "_cached_at": datetime.now().isoformat()
            }
            
            # Set cache with expiration
            expire_seconds = (expire_minutes or settings.CACHE_EXPIRE_MINUTES) * 60
            await self.redis_client.setex(
                cache_key,
                expire_seconds,
                json.dumps(data_with_timestamp, default=str)
            )
            
            logger.debug(f"Cached data for key: {cache_key}")
            return True
            
        except Exception as e:
            logger.error(f"Error setting cached data: {e}")
            return False
    
    async def invalidate_cache(self, pattern: str) -> int:
        """
        Invalidate cache entries matching pattern.
        
        Args:
            pattern: Redis key pattern (e.g., "indicator:AAPL:*")
            
        Returns:
            Number of keys deleted
        """
        if not self.is_connected:
            return 0
        
        try:
            keys = await self.redis_client.keys(pattern)
            if keys:
                deleted = await self.redis_client.delete(*keys)
                logger.info(f"Invalidated {deleted} cache entries matching pattern: {pattern}")
                return deleted
            return 0
            
        except Exception as e:
            logger.error(f"Error invalidating cache: {e}")
            return 0
    
    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.
        
        Returns:
            Cache statistics
        """
        if not self.is_connected:
            return {"connected": False}
        
        try:
            info = await self.redis_client.info()
            return {
                "connected": True,
                "used_memory": info.get("used_memory_human", "N/A"),
                "connected_clients": info.get("connected_clients", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"Error getting cache stats: {e}")
            return {"connected": False, "error": str(e)}


# Global cache service instance
cache_service = CacheService()
