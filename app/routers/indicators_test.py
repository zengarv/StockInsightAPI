"""
Modified indicators router for testing without Redis dependencies.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
from datetime import datetime, timedelta

from app.services.data_service import data_service
from app.indicators.sma import calculate_sma
from app.indicators.ema import calculate_ema
from app.indicators.rsi import calculate_rsi
from app.indicators.macd import calculate_macd
from app.indicators.bollinger import calculate_bollinger_bands
from app.models.schemas import (
    SMAResponse, EMAResponse, RSIResponse, 
    MACDResponse, BollingerBandsResponse,
    SubscriptionTier
)
from app.database.models import User
from app.auth.dependencies import get_current_user, require_tier
from app.services.rate_limit_service import RateLimitService

router = APIRouter()

# Create rate limiter instance
rate_limiter = RateLimitService()


async def check_rate_limit(user: User = Depends(get_current_user)):
    """Check rate limit for current user."""
    # Get rate limit based on user tier
    if user.tier == SubscriptionTier.FREE:
        limit = 50
    elif user.tier == SubscriptionTier.PRO:
        limit = 500
    else:  # PREMIUM
        return user  # No rate limit for premium users
    
    # Check if user is rate limited
    user_key = f"user_{user.id}_{user.tier.value}"
    if not rate_limiter.is_allowed(user_key, limit):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. {user.tier.value.title()} tier allows {limit} requests per day."
        )
    
    return user


def check_data_access(user: User, start_date: Optional[str] = None, end_date: Optional[str] = None):
    """Check if user has access to requested date range."""
    if user.tier == SubscriptionTier.PREMIUM:
        return  # Premium users have access to all data
    
    # Calculate maximum allowed date range
    today = datetime.now().date()
    if user.tier == SubscriptionTier.FREE:
        max_days = 90  # 3 months
    else:  # PRO
        max_days = 365  # 1 year
    
    earliest_allowed = today - timedelta(days=max_days)
    
    # If no start date specified, use the earliest allowed date
    if start_date is None:
        return
    
    # Parse start date
    try:
        start_date_obj = datetime.strptime(start_date, "%Y-%m-%d").date()
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid start_date format. Use YYYY-MM-DD."
        )
    
    # Check if requested date is within allowed range
    if start_date_obj < earliest_allowed:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"{user.tier.value.title()} tier only allows access to last {max_days} days of data."
        )


@router.get("/indicators/sma", response_model=SMAResponse)
async def get_sma(
    symbol: str = Query(..., description="Stock symbol"),
    window: int = Query(20, ge=1, le=200, description="Window size for SMA"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: User = Depends(check_rate_limit)
):
    """Calculate Simple Moving Average. Available to all tiers."""
    try:
        # Check data access
        check_data_access(user, start_date, end_date)
        
        # Get stock data
        stock_data = data_service.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if stock_data is None or len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}"
            )
        
        # Calculate SMA
        sma_values = calculate_sma(stock_data, window=window)
        
        # Prepare response
        results = []
        for i, row in enumerate(stock_data.iter_rows(named=True)):
            results.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": row["close"],
                "sma": sma_values[i] if i < len(sma_values) else None
            })
        
        return SMAResponse(
            symbol=symbol,
            window=window,
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating SMA"
        )


@router.get("/indicators/ema", response_model=EMAResponse)
async def get_ema(
    symbol: str = Query(..., description="Stock symbol"),
    window: int = Query(20, ge=1, le=200, description="Window size for EMA"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: User = Depends(check_rate_limit)
):
    """Calculate Exponential Moving Average. Available to all tiers."""
    try:
        # Check data access
        check_data_access(user, start_date, end_date)
        
        # Get stock data
        stock_data = data_service.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if stock_data is None or len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}"
            )
        
        # Calculate EMA
        ema_values = calculate_ema(stock_data, window=window)
        
        # Prepare response
        results = []
        for i, row in enumerate(stock_data.iter_rows(named=True)):
            results.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": row["close"],
                "ema": ema_values[i] if i < len(ema_values) else None
            })
        
        return EMAResponse(
            symbol=symbol,
            window=window,
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating EMA"
        )


@router.get("/indicators/rsi", response_model=RSIResponse)
async def get_rsi(
    symbol: str = Query(..., description="Stock symbol"),
    period: int = Query(14, ge=1, le=100, description="Period for RSI"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: User = Depends(require_tier(SubscriptionTier.PRO))
):
    """Calculate Relative Strength Index. Available to Pro and Premium tiers."""
    try:
        # Check rate limit
        user = await check_rate_limit(user)
        
        # Check data access
        check_data_access(user, start_date, end_date)
        
        # Get stock data
        stock_data = data_service.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if stock_data is None or len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}"
            )
        
        # Calculate RSI
        rsi_values = calculate_rsi(stock_data, period=period)
        
        # Prepare response
        results = []
        for i, row in enumerate(stock_data.iter_rows(named=True)):
            results.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": row["close"],
                "rsi": rsi_values[i] if i < len(rsi_values) else None
            })
        
        return RSIResponse(
            symbol=symbol,
            period=period,
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating RSI"
        )


@router.get("/indicators/macd", response_model=MACDResponse)
async def get_macd(
    symbol: str = Query(..., description="Stock symbol"),
    fast_period: int = Query(12, ge=1, le=50, description="Fast period for MACD"),
    slow_period: int = Query(26, ge=1, le=100, description="Slow period for MACD"),
    signal_period: int = Query(9, ge=1, le=50, description="Signal period for MACD"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: User = Depends(require_tier(SubscriptionTier.PRO))
):
    """Calculate MACD. Available to Pro and Premium tiers."""
    try:
        # Check rate limit
        user = await check_rate_limit(user)
        
        # Check data access
        check_data_access(user, start_date, end_date)
        
        # Get stock data
        stock_data = data_service.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if stock_data is None or len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}"
            )
        
        # Calculate MACD
        macd_result = calculate_macd(stock_data, fast_period=fast_period, slow_period=slow_period, signal_period=signal_period)
        
        # Prepare response
        results = []
        for i, row in enumerate(stock_data.iter_rows(named=True)):
            results.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": row["close"],
                "macd": macd_result["macd"][i] if i < len(macd_result["macd"]) else None,
                "signal": macd_result["signal"][i] if i < len(macd_result["signal"]) else None,
                "histogram": macd_result["histogram"][i] if i < len(macd_result["histogram"]) else None
            })
        
        return MACDResponse(
            symbol=symbol,
            fast_period=fast_period,
            slow_period=slow_period,
            signal_period=signal_period,
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating MACD"
        )


@router.get("/indicators/bollinger", response_model=BollingerBandsResponse)
async def get_bollinger_bands(
    symbol: str = Query(..., description="Stock symbol"),
    window: int = Query(20, ge=1, le=200, description="Window size for Bollinger Bands"),
    std_dev: float = Query(2.0, ge=0.1, le=5.0, description="Standard deviation multiplier"),
    start_date: Optional[str] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[str] = Query(None, description="End date (YYYY-MM-DD)"),
    user: User = Depends(require_tier(SubscriptionTier.PREMIUM))
):
    """Calculate Bollinger Bands. Available to Premium tier only."""
    try:
        # Check rate limit (premium has no rate limit, but we still track)
        user = await check_rate_limit(user)
        
        # Check data access (premium has access to all data)
        check_data_access(user, start_date, end_date)
        
        # Get stock data
        stock_data = data_service.get_stock_data(
            symbol=symbol,
            start_date=start_date,
            end_date=end_date
        )
        
        if stock_data is None or len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol: {symbol}"
            )
        
        # Calculate Bollinger Bands
        bb_result = calculate_bollinger_bands(stock_data, window=window, std_dev=std_dev)
        
        # Prepare response
        results = []
        for i, row in enumerate(stock_data.iter_rows(named=True)):
            results.append({
                "date": row["date"].strftime("%Y-%m-%d"),
                "close": row["close"],
                "upper_band": bb_result["upper_band"][i] if i < len(bb_result["upper_band"]) else None,
                "middle_band": bb_result["middle_band"][i] if i < len(bb_result["middle_band"]) else None,
                "lower_band": bb_result["lower_band"][i] if i < len(bb_result["lower_band"]) else None
            })
        
        return BollingerBandsResponse(
            symbol=symbol,
            window=window,
            std_dev=std_dev,
            data=results
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating Bollinger Bands"
        )
