"""
Advanced rate limiting service with Redis support.
"""
from datetime import datetime, timedelta
from typing import Dict, Optional
import asyncio
import aioredis
import logging

from app.core.config import settings
from app.models.schemas import SubscriptionTier
from app.auth.auth_utils import get_tier_limits

logger = logging.getLogger(__name__)


class RateLimitService:
    """Rate limiting service using Redis for persistence and in-memory fallback."""
    
    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.fallback_storage: Dict[str, Dict] = {}  # In-memory fallback
        
    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis = aioredis.from_url(
                settings.REDIS_URL,
                password=settings.REDIS_PASSWORD,
                db=settings.REDIS_DB,
                decode_responses=True
            )
            # Test connection
            await self.redis.ping()
            logger.info("Connected to Redis for rate limiting")
        except Exception as e:
            logger.warning(f"Failed to connect to Redis: {e}. Using in-memory fallback")
            self.redis = None
    
    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            self.redis = None
    
    async def is_request_allowed(self, user_id: int, tier: SubscriptionTier) -> bool:
        """
        Check if a request is allowed based on rate limits.
        
        Args:
            user_id: User ID
            tier: User subscription tier
            
        Returns:
            bool: True if request is allowed, False otherwise
        """
        limits = get_tier_limits(tier)
        requests_per_day = limits["requests_per_day"]
        
        # Premium tier has unlimited requests
        if tier == SubscriptionTier.PREMIUM:
            return True
            
        # Get current request count
        current_count = await self._get_request_count(user_id)
        
        if current_count >= requests_per_day:
            logger.warning(f"Rate limit exceeded for user {user_id} (tier: {tier})")
            return False
            
        # Increment request count
        await self._increment_request_count(user_id)
        return True
    
    async def get_remaining_requests(self, user_id: int, tier: SubscriptionTier) -> int:
        """
        Get remaining requests for today.
        
        Args:
            user_id: User ID
            tier: User subscription tier
            
        Returns:
            int: Remaining requests
        """
        limits = get_tier_limits(tier)
        requests_per_day = limits["requests_per_day"]
        
        # Premium tier has unlimited requests
        if tier == SubscriptionTier.PREMIUM:
            return 999999  # Effectively unlimited
            
        current_count = await self._get_request_count(user_id)
        return max(0, requests_per_day - current_count)
    
    async def _get_request_count(self, user_id: int) -> int:
        """Get current request count for today."""
        key = self._get_rate_limit_key(user_id)
        
        if self.redis:
            try:
                count = await self.redis.get(key)
                return int(count) if count else 0
            except Exception as e:
                logger.error(f"Error getting request count from Redis: {e}")
                return self._get_fallback_count(user_id)
        else:
            return self._get_fallback_count(user_id)
    
    async def _increment_request_count(self, user_id: int):
        """Increment request count for today."""
        key = self._get_rate_limit_key(user_id)
        
        if self.redis:
            try:
                # Increment count with expiry
                await self.redis.incr(key)
                # Set expiry to end of day
                await self.redis.expire(key, self._seconds_until_midnight())
            except Exception as e:
                logger.error(f"Error incrementing request count in Redis: {e}")
                self._increment_fallback_count(user_id)
        else:
            self._increment_fallback_count(user_id)
    
    def _get_rate_limit_key(self, user_id: int) -> str:
        """Generate Redis key for rate limiting."""
        today = datetime.now().strftime("%Y-%m-%d")
        return f"rate_limit:{user_id}:{today}"
    
    def _seconds_until_midnight(self) -> int:
        """Calculate seconds until midnight."""
        now = datetime.now()
        midnight = (now + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)
        return int((midnight - now).total_seconds())
    
    def _get_fallback_count(self, user_id: int) -> int:
        """Get request count from in-memory fallback."""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}:{today}"
        
        if key not in self.fallback_storage:
            self.fallback_storage[key] = {"count": 0, "expires": datetime.now() + timedelta(days=1)}
        
        # Clean expired entries
        self._cleanup_fallback_storage()
        
        return self.fallback_storage.get(key, {}).get("count", 0)
    
    def _increment_fallback_count(self, user_id: int):
        """Increment request count in in-memory fallback."""
        today = datetime.now().strftime("%Y-%m-%d")
        key = f"{user_id}:{today}"
        
        if key not in self.fallback_storage:
            self.fallback_storage[key] = {"count": 0, "expires": datetime.now() + timedelta(days=1)}
        
        self.fallback_storage[key]["count"] += 1
        self._cleanup_fallback_storage()
    
    def _cleanup_fallback_storage(self):
        """Clean up expired entries from fallback storage."""
        now = datetime.now()
        expired_keys = [k for k, v in self.fallback_storage.items() if v["expires"] < now]
        for key in expired_keys:
            del self.fallback_storage[key]


# Global rate limit service instance
rate_limit_service = RateLimitService()
