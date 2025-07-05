"""
Authentication dependencies for FastAPI.
"""
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from typing import Optional
import logging

from app.database.database import get_db
from app.database.models import User, APIKey
from app.auth.auth_utils import verify_token, validate_api_key_format
from app.models.schemas import TokenData

logger = logging.getLogger(__name__)

# Security scheme
security = HTTPBearer()


async def get_current_user_from_token(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from JWT token.
    
    Args:
        credentials: Authorization credentials
        db: Database session
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If token is invalid or user not found
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        token_data = verify_token(credentials.credentials)
        if token_data is None:
            raise credentials_exception
        
        user = db.query(User).filter(User.id == token_data.user_id).first()
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        return user
        
    except Exception as e:
        logger.error(f"Error getting current user: {e}")
        raise credentials_exception


async def get_current_user_from_api_key(
    api_key: str,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from API key.
    
    Args:
        api_key: API key
        db: Database session
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If API key is invalid or user not found
    """
    if not validate_api_key_format(api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key format"
        )
    
    api_key_record = db.query(APIKey).filter(
        APIKey.key == api_key,
        APIKey.is_active == True
    ).first()
    
    if not api_key_record:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key"
        )
    
    user = db.query(User).filter(User.id == api_key_record.user_id).first()
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive"
        )
    
    return user


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
    api_key: Optional[str] = None,
    db: Session = Depends(get_db)
) -> User:
    """
    Get current user from either JWT token or API key.
    
    Args:
        credentials: Authorization credentials (JWT)
        api_key: API key (optional)
        db: Database session
        
    Returns:
        User: Current user
        
    Raises:
        HTTPException: If authentication fails
    """
    # Try API key first if provided
    if api_key:
        return await get_current_user_from_api_key(api_key, db)
    
    # Try JWT token
    if credentials:
        return await get_current_user_from_token(credentials, db)
    
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No authentication provided"
    )


def require_tier(required_tier: str):
    """
    Dependency factory for requiring specific subscription tier.
    
    Args:
        required_tier: Required subscription tier
        
    Returns:
        Dependency function
    """
    def check_tier(current_user: User = Depends(get_current_user)):
        tier_hierarchy = {"free": 0, "pro": 1, "premium": 2}
        
        user_tier_level = tier_hierarchy.get(current_user.tier.value, 0)
        required_tier_level = tier_hierarchy.get(required_tier, 0)
        
        if user_tier_level < required_tier_level:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This endpoint requires {required_tier} tier or higher"
            )
        
        return current_user
    
    return check_tier
