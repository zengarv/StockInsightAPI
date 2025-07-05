"""
Rate limiting service.
"""
import time
import logging
from typing import Optional, Dict, Any
from datetime import datetime, timedelta

from app.core.config import settings

logger = logging.getLogger(__name__)


class RateLimitService:
    """Service for rate limiting operations."""
    
    def __init__(self):
        # In-memory storage for rate limiting (use Redis in production)
        self.request_counts: Dict[str, Dict[str, Any]] = {}
        self.tier_limits = {
            "free": settings.RATE_LIMIT_FREE,
            "pro": settings.RATE_LIMIT_PRO,
            "premium": settings.RATE_LIMIT_PREMIUM
        }
    
    def _get_daily_key(self, user_id: int) -> str:
        """Generate daily key for rate limiting."""
        today = datetime.now().date()
        return f"rate_limit:{user_id}:{today}"
    
    def _cleanup_old_entries(self) -> None:
        """Remove old rate limit entries."""
        current_time = time.time()
        yesterday = current_time - 86400  # 24 hours ago
        
        keys_to_remove = []
        for key, data in self.request_counts.items():
            if data.get("timestamp", 0) < yesterday:
                keys_to_remove.append(key)
        
        for key in keys_to_remove:
            del self.request_counts[key]
    
    def check_rate_limit(self, user_id: int, tier: str) -> Dict[str, Any]:
        """
        Check if user has exceeded rate limit.
        
        Args:
            user_id: User ID
            tier: User subscription tier
            
        Returns:
            Dict with rate limit information
        """
        # Clean up old entries periodically
        self._cleanup_old_entries()
        
        # Get daily limit for tier
        daily_limit = self.tier_limits.get(tier.lower())
        if daily_limit is None:  # Premium tier - unlimited
            return {
                "allowed": True,
                "limit": None,
                "used": 0,
                "remaining": None,
                "reset_time": None
            }
        
        # Get current request count
        daily_key = self._get_daily_key(user_id)
        current_count = self.request_counts.get(daily_key, {}).get("count", 0)
        
        # Check if limit exceeded
        if current_count >= daily_limit:
            # Calculate reset time (midnight)
            tomorrow = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)
            
            return {
                "allowed": False,
                "limit": daily_limit,
                "used": current_count,
                "remaining": 0,
                "reset_time": tomorrow.isoformat()
            }
        
        return {
            "allowed": True,
            "limit": daily_limit,
            "used": current_count,
            "remaining": daily_limit - current_count,
            "reset_time": None
        }
    
    def increment_request_count(self, user_id: int) -> None:
        """
        Increment request count for user.
        
        Args:
            user_id: User ID
        """
        daily_key = self._get_daily_key(user_id)
        current_time = time.time()
        
        if daily_key in self.request_counts:
            self.request_counts[daily_key]["count"] += 1
        else:
            self.request_counts[daily_key] = {
                "count": 1,
                "timestamp": current_time
            }
        
        logger.debug(f"Incremented request count for user {user_id}: {self.request_counts[daily_key]['count']}")
    
    def get_user_stats(self, user_id: int, tier: str) -> Dict[str, Any]:
        """
        Get rate limit statistics for user.
        
        Args:
            user_id: User ID
            tier: User subscription tier
            
        Returns:
            User rate limit statistics
        """
        rate_limit_info = self.check_rate_limit(user_id, tier)
        
        return {
            "user_id": user_id,
            "tier": tier,
            "daily_limit": rate_limit_info["limit"],
            "requests_used": rate_limit_info["used"],
            "requests_remaining": rate_limit_info["remaining"],
            "reset_time": rate_limit_info["reset_time"]
        }


# Global rate limit service instance
rate_limit_service = RateLimitService()
