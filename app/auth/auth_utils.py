"""
Authentication utilities for JWT tokens and password hashing.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import jwt
from passlib.context import CryptContext
import logging
import secrets

from app.core.config import settings
from app.models.schemas import TokenData, SubscriptionTier

logger = logging.getLogger(__name__)

# Password hashing context
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a password against its hash.
    
    Args:
        plain_password: Plain text password
        hashed_password: Hashed password
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password.
    
    Args:
        password: Plain text password
        
    Returns:
        Hashed password
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Create JWT access token.
    
    Args:
        data: Data to encode in token
        expires_delta: Token expiration time
        
    Returns:
        JWT token string
    """
    to_encode = data.copy()
    
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire})
    
    try:
        encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
        return encoded_jwt
    except Exception as e:
        logger.error(f"Error creating access token: {e}")
        raise


def verify_token(token: str) -> Optional[TokenData]:
    """
    Verify JWT token and extract data.
    
    Args:
        token: JWT token string
        
    Returns:
        TokenData if valid, None otherwise
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        
        username: str = payload.get("sub")
        user_id: int = payload.get("user_id")
        tier: str = payload.get("tier")
        
        if username is None or user_id is None:
            return None
            
        return TokenData(username=username, user_id=user_id, tier=tier)
        
    except jwt.ExpiredSignatureError:
        logger.warning("Token has expired")
        return None
    except jwt.JWTError as e:
        logger.warning(f"JWT Error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error verifying token: {e}")
        return None


def create_api_key() -> str:
    """
    Create a new API key.
    
    Returns:
        API key string
    """
    return f"kalpi_{secrets.token_urlsafe(32)}"


def validate_api_key_format(api_key: str) -> bool:
    """
    Validate API key format.
    
    Args:
        api_key: API key to validate
        
    Returns:
        True if valid format, False otherwise
    """
    return api_key.startswith("kalpi_") and len(api_key) > 10


def generate_api_key() -> str:
    """Generate a secure API key."""
    return secrets.token_urlsafe(32)


def hash_api_key(api_key: str) -> str:
    """Hash an API key for storage."""
    return get_password_hash(api_key)


def verify_api_key(api_key: str, hashed_key: str) -> bool:
    """Verify an API key against its hash."""
    return verify_password(api_key, hashed_key)


def get_tier_limits(tier: SubscriptionTier) -> Dict[str, Any]:
    """
    Get rate limits and data access limits for a subscription tier.
    
    Args:
        tier: Subscription tier
        
    Returns:
        Dict: Tier limits configuration
    """
    limits = {
        SubscriptionTier.FREE: {
            "requests_per_day": settings.RATE_LIMIT_FREE,
            "data_limit_days": settings.DATA_LIMIT_FREE,
            "allowed_indicators": ["sma", "ema"],
            "description": "Free tier - Limited access"
        },
        SubscriptionTier.PRO: {
            "requests_per_day": settings.RATE_LIMIT_PRO,
            "data_limit_days": settings.DATA_LIMIT_PRO,
            "allowed_indicators": ["sma", "ema", "rsi", "macd"],
            "description": "Pro tier - Enhanced access"
        },
        SubscriptionTier.PREMIUM: {
            "requests_per_day": settings.RATE_LIMIT_PREMIUM,
            "data_limit_days": settings.DATA_LIMIT_PREMIUM,
            "allowed_indicators": ["sma", "ema", "rsi", "macd", "bollinger"],
            "description": "Premium tier - Full access"
        }
    }
    
    return limits.get(tier, limits[SubscriptionTier.FREE])


def is_indicator_allowed(tier: SubscriptionTier, indicator: str) -> bool:
    """
    Check if an indicator is allowed for a subscription tier.
    
    Args:
        tier: User subscription tier
        indicator: Indicator name
        
    Returns:
        bool: True if allowed, False otherwise
    """
    limits = get_tier_limits(tier)
    return indicator.lower() in limits["allowed_indicators"]
