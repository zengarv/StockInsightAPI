"""
Pydantic models for request/response schemas.
"""
from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, List, Dict, Any
from datetime import datetime, date
from enum import Enum


class SubscriptionTier(str, Enum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class UserBase(BaseModel):
    """Base user model."""
    username: str = Field(..., min_length=3, max_length=50)
    email: str = Field(..., pattern=r'^[^@]+@[^@]+\.[^@]+$')


class UserCreate(UserBase):
    """User creation model."""
    password: str = Field(..., min_length=8)
    subscription_tier: SubscriptionTier = SubscriptionTier.FREE


class UserResponse(UserBase):
    """User response model."""
    id: int
    is_active: bool
    tier: SubscriptionTier
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """Token response model."""
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    tier: SubscriptionTier


class TokenData(BaseModel):
    """Token data model."""
    username: Optional[str] = None
    user_id: Optional[int] = None
    tier: Optional[SubscriptionTier] = None


class IndicatorRequest(BaseModel):
    """Base indicator request model."""
    symbol: str = Field(..., min_length=1, max_length=10, description="Stock symbol")
    start_date: Optional[date] = Field(None, description="Start date (YYYY-MM-DD)")
    end_date: Optional[date] = Field(None, description="End date (YYYY-MM-DD)")


class SMARequest(IndicatorRequest):
    """Simple Moving Average request model."""
    window: int = Field(default=20, ge=1, le=200, description="Window period")


class EMARequest(IndicatorRequest):
    """Exponential Moving Average request model."""
    window: int = Field(default=20, ge=1, le=200, description="Window period")


class RSIRequest(IndicatorRequest):
    """Relative Strength Index request model."""
    period: int = Field(default=14, ge=1, le=100, description="RSI period")


class MACDRequest(IndicatorRequest):
    """MACD request model."""
    fast_period: int = Field(default=12, ge=1, le=100, description="Fast EMA period")
    slow_period: int = Field(default=26, ge=1, le=200, description="Slow EMA period")
    signal_period: int = Field(default=9, ge=1, le=100, description="Signal line period")


class BollingerBandsRequest(IndicatorRequest):
    """Bollinger Bands request model."""
    period: int = Field(default=20, ge=1, le=200, description="Period")
    std_dev: float = Field(default=2.0, ge=0.1, le=5.0, description="Standard deviation multiplier")


class IndicatorDataPoint(BaseModel):
    """Single indicator data point."""
    date: date
    value: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class MACDDataPoint(BaseModel):
    """MACD data point."""
    date: date
    macd: Optional[float] = None
    signal: Optional[float] = None
    histogram: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class BollingerBandsDataPoint(BaseModel):
    """Bollinger Bands data point."""
    date: date
    upper: Optional[float] = None
    middle: Optional[float] = None
    lower: Optional[float] = None
    
    model_config = ConfigDict(from_attributes=True)


class IndicatorResponse(BaseModel):
    """Base indicator response model."""
    symbol: str
    indicator: str
    parameters: Dict[str, Any]
    data_points: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data: List[IndicatorDataPoint]


class MACDResponse(BaseModel):
    """MACD response model."""
    symbol: str
    indicator: str = "MACD"
    parameters: Dict[str, Any]
    data_points: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data: List[MACDDataPoint]


class BollingerBandsResponse(BaseModel):
    """Bollinger Bands response model."""
    symbol: str
    indicator: str = "Bollinger Bands"
    parameters: Dict[str, Any]
    data_points: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data: List[BollingerBandsDataPoint]


class SMAResponse(BaseModel):
    """SMA response model."""
    symbol: str
    window: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data: List[IndicatorDataPoint]


class EMAResponse(BaseModel):
    """EMA response model."""
    symbol: str
    window: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data: List[IndicatorDataPoint]


class RSIResponse(BaseModel):
    """RSI response model."""
    symbol: str
    window: int
    start_date: Optional[date] = None
    end_date: Optional[date] = None
    data: List[IndicatorDataPoint]


class ErrorResponse(BaseModel):
    """Error response model."""
    error: str
    detail: Optional[str] = None
    code: Optional[str] = None


class HealthCheckResponse(BaseModel):
    """Health check response model."""
    status: str
    timestamp: datetime
    version: str
    data_loaded: bool
    cache_status: str
    total_symbols: int
