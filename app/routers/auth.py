"""
Authentication router for user management and authentication.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta
import logging

from app.database.database import get_db
from app.database.models import User, APIKey, SubscriptionTier
from app.auth.auth_utils import (
    verify_password, get_password_hash, create_access_token, create_api_key
)
from app.auth.dependencies import get_current_user
from app.models.schemas import (
    UserCreate, UserResponse, Token, ErrorResponse
)
from app.core.config import settings

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["authentication"])


@router.post("/register", response_model=UserResponse)
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """Register a new user."""
    try:
        # Check if user already exists
        existing_user = db.query(User).filter(
            (User.username == user_data.username) | (User.email == user_data.email)
        ).first()
        
        if existing_user:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username or email already registered"
            )
        
        # Create new user
        hashed_password = get_password_hash(user_data.password)
        
        # Convert subscription_tier string to enum
        tier_map = {
            "free": SubscriptionTier.FREE,
            "pro": SubscriptionTier.PRO,
            "premium": SubscriptionTier.PREMIUM
        }
        user_tier = tier_map.get(user_data.subscription_tier, SubscriptionTier.FREE)
        
        db_user = User(
            username=user_data.username,
            email=user_data.email,
            hashed_password=hashed_password,
            tier=user_tier
        )
        
        db.add(db_user)
        db.commit()
        db.refresh(db_user)
        
        logger.info(f"New user registered: {user_data.username}")
        
        return UserResponse(
            id=db_user.id,
            username=db_user.username,
            email=db_user.email,
            is_active=db_user.is_active,
            tier=db_user.tier,
            created_at=db_user.created_at
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Authenticate user and return access token."""
    try:
        # Find user by username
        user = db.query(User).filter(User.username == form_data.username).first()
        
        if not user or not verify_password(form_data.password, user.hashed_password):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect username or password",
                headers={"WWW-Authenticate": "Bearer"},
            )
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Inactive user"
            )
        
        # Create access token
        access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={
                "sub": user.username,
                "user_id": user.id,
                "tier": user.tier.value
            },
            expires_delta=access_token_expires
        )
        
        logger.info(f"User logged in: {user.username}")
        
        return Token(
            access_token=access_token,
            token_type="bearer",
            expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            tier=user.tier
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error during login: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/me", response_model=UserResponse)
async def get_current_user_info(
    current_user: User = Depends(get_current_user)
):
    """Get current user information."""
    return UserResponse(
        id=current_user.id,
        username=current_user.username,
        email=current_user.email,
        is_active=current_user.is_active,
        tier=current_user.tier,
        created_at=current_user.created_at
    )


@router.post("/api-key")
async def create_user_api_key(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new API key for the current user."""
    try:
        # Generate API key
        api_key = create_api_key()
        
        # Save to database
        db_api_key = APIKey(
            key=api_key,
            user_id=current_user.id,
            is_active=True
        )
        
        db.add(db_api_key)
        db.commit()
        
        logger.info(f"API key created for user: {current_user.username}")
        
        return {
            "api_key": api_key,
            "message": "API key created successfully. Store it securely as it won't be shown again."
        }
        
    except Exception as e:
        logger.error(f"Error creating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/api-keys")
async def list_user_api_keys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """List user's API keys (without revealing the actual keys)."""
    try:
        api_keys = db.query(APIKey).filter(APIKey.user_id == current_user.id).all()
        
        return {
            "api_keys": [
                {
                    "id": key.id,
                    "key_hint": f"{key.key[:10]}...",
                    "is_active": key.is_active,
                    "created_at": key.created_at,
                    "expires_at": key.expires_at
                }
                for key in api_keys
            ]
        }
        
    except Exception as e:
        logger.error(f"Error listing API keys: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.delete("/api-key/{api_key_id}")
async def deactivate_api_key(
    api_key_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Deactivate an API key."""
    try:
        api_key = db.query(APIKey).filter(
            APIKey.id == api_key_id,
            APIKey.user_id == current_user.id
        ).first()
        
        if not api_key:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="API key not found"
            )
        
        api_key.is_active = False
        db.commit()
        
        logger.info(f"API key deactivated: {api_key_id}")
        
        return {"message": "API key deactivated successfully"}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deactivating API key: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
