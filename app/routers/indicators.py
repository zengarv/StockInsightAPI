"""
API router for technical indicators.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime, date, timedelta
import logging

from app.database.database import get_db
from app.database.models import User
from app.auth.dependencies import get_current_user, require_tier
from app.models.schemas import (
    SMARequest, EMARequest, RSIRequest, MACDRequest, BollingerBandsRequest,
    IndicatorResponse, MACDResponse, BollingerBandsResponse,
    IndicatorDataPoint, MACDDataPoint, BollingerBandsDataPoint,
    ErrorResponse
)
from app.services.data_service import data_service
from app.services.cache_service import cache_service
from app.services.rate_limit_service import rate_limit_service
from app.indicators import (
    calculate_sma, calculate_ema, calculate_rsi, 
    calculate_macd, calculate_bollinger_bands
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/indicators", tags=["indicators"])


@router.get("/stocks", response_model=List[str])
async def get_available_stocks():
    """Get list of available stock symbols."""
    try:
        symbols = data_service.get_available_symbols()
        logger.info(f"Retrieved {len(symbols)} available symbols")
        return symbols
    except Exception as e:
        logger.error(f"Error retrieving symbols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available symbols"
        )


def check_rate_limit(user: User):
    """Check rate limit for user."""
    rate_limit_info = rate_limit_service.check_rate_limit(user.id, user.tier.value)
    
    if not rate_limit_info["allowed"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Used {rate_limit_info['used']}/{rate_limit_info['limit']} requests today.",
            headers={"X-RateLimit-Limit": str(rate_limit_info['limit'])}
        )
    
    # Increment request count
    rate_limit_service.increment_request_count(user.id)


@router.get("/sma", response_model=IndicatorResponse)
async def get_sma(
    symbol: str = Query(..., description="Stock symbol"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    window: int = Query(20, ge=1, le=200, description="Window period"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate Simple Moving Average."""
    try:
        # Check rate limit
        check_rate_limit(current_user)
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Validate and adjust date range based on tier
        start_date, end_date = data_service.validate_date_range(
            start_date, end_date, current_user.tier.value
        )
        
        # Check cache first
        cache_params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "window": window
        }
        cached_data = await cache_service.get_cached_data(symbol, "SMA", cache_params)
        if cached_data:
            return cached_data
        
        # Get stock data
        stock_data = data_service.get_stock_data(symbol, start_date, end_date, use_pandas=False)
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in date range"
            )
        
        # Calculate SMA
        sma_values = calculate_sma(stock_data, window)
        
        # Convert to response format
        data_points = []
        dates = stock_data.select("date").to_series().to_list()
        
        for i, (date_val, sma_val) in enumerate(zip(dates, sma_values)):
            data_points.append(IndicatorDataPoint(
                date=date_val,
                value=float(sma_val) if sma_val is not None else None
            ))
        
        response = IndicatorResponse(
            symbol=symbol,
            indicator="SMA",
            parameters={"window": window},
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the response
        await cache_service.set_cached_data(symbol, "SMA", cache_params, response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating SMA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/ema", response_model=IndicatorResponse)
async def get_ema(
    symbol: str = Query(..., description="Stock symbol"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    window: int = Query(20, ge=1, le=200, description="Window period"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Calculate Exponential Moving Average."""
    try:
        # Check rate limit
        check_rate_limit(current_user)
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Validate and adjust date range based on tier
        start_date, end_date = data_service.validate_date_range(
            start_date, end_date, current_user.tier.value
        )
        
        # Check cache first
        cache_params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "window": window
        }
        cached_data = await cache_service.get_cached_data(symbol, "EMA", cache_params)
        if cached_data:
            return cached_data
        
        # Get stock data
        stock_data = data_service.get_stock_data(symbol, start_date, end_date, use_pandas=False)
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in date range"
            )
        
        # Calculate EMA
        ema_values = calculate_ema(stock_data, window)
        
        # Convert to response format
        data_points = []
        dates = stock_data.select("date").to_series().to_list()
        
        for i, (date_val, ema_val) in enumerate(zip(dates, ema_values)):
            data_points.append(IndicatorDataPoint(
                date=date_val,
                value=float(ema_val) if ema_val is not None else None
            ))
        
        response = IndicatorResponse(
            symbol=symbol,
            indicator="EMA",
            parameters={"window": window},
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the response
        await cache_service.set_cached_data(symbol, "EMA", cache_params, response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating EMA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/rsi", response_model=IndicatorResponse)
async def get_rsi(
    symbol: str = Query(..., description="Stock symbol"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    period: int = Query(14, ge=1, le=100, description="RSI period"),
    current_user: User = Depends(require_tier("pro")),
    db: Session = Depends(get_db)
):
    """Calculate Relative Strength Index (Pro tier required)."""
    try:
        # Check rate limit
        check_rate_limit(current_user)
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Validate and adjust date range based on tier
        start_date, end_date = data_service.validate_date_range(
            start_date, end_date, current_user.tier.value
        )
        
        # Check cache first
        cache_params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "period": period
        }
        cached_data = await cache_service.get_cached_data(symbol, "RSI", cache_params)
        if cached_data:
            return cached_data
        
        # Get stock data
        stock_data = data_service.get_stock_data(symbol, start_date, end_date, use_pandas=False)
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in date range"
            )
        
        # Calculate RSI
        rsi_values = calculate_rsi(stock_data, period)
        
        # Convert to response format
        data_points = []
        dates = stock_data.select("date").to_series().to_list()
        
        for i, (date_val, rsi_val) in enumerate(zip(dates, rsi_values)):
            data_points.append(IndicatorDataPoint(
                date=date_val,
                value=float(rsi_val) if rsi_val is not None else None
            ))
        
        response = IndicatorResponse(
            symbol=symbol,
            indicator="RSI",
            parameters={"period": period},
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the response
        await cache_service.set_cached_data(symbol, "RSI", cache_params, response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/macd", response_model=MACDResponse)
async def get_macd(
    symbol: str = Query(..., description="Stock symbol"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    fast_period: int = Query(12, ge=1, le=100, description="Fast EMA period"),
    slow_period: int = Query(26, ge=1, le=200, description="Slow EMA period"),
    signal_period: int = Query(9, ge=1, le=100, description="Signal line period"),
    current_user: User = Depends(require_tier("pro")),
    db: Session = Depends(get_db)
):
    """Calculate MACD (Pro tier required)."""
    try:
        # Check rate limit
        check_rate_limit(current_user)
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Validate and adjust date range based on tier
        start_date, end_date = data_service.validate_date_range(
            start_date, end_date, current_user.tier.value
        )
        
        # Check cache first
        cache_params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "fast_period": fast_period,
            "slow_period": slow_period,
            "signal_period": signal_period
        }
        cached_data = await cache_service.get_cached_data(symbol, "MACD", cache_params)
        if cached_data:
            return cached_data
        
        # Get stock data
        stock_data = data_service.get_stock_data(symbol, start_date, end_date, use_pandas=False)
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in date range"
            )
        
        # Calculate MACD
        macd_line, signal_line, histogram = calculate_macd(stock_data, fast_period, slow_period, signal_period)
        
        # Convert to response format
        data_points = []
        dates = stock_data.select("date").to_series().to_list()
        
        for i, date_val in enumerate(dates):
            data_points.append(MACDDataPoint(
                date=date_val,
                macd=float(macd_line[i]) if macd_line[i] is not None else None,
                signal=float(signal_line[i]) if signal_line[i] is not None else None,
                histogram=float(histogram[i]) if histogram[i] is not None else None
            ))
        
        response = MACDResponse(
            symbol=symbol,
            indicator="MACD",
            parameters={
                "fast_period": fast_period,
                "slow_period": slow_period,
                "signal_period": signal_period
            },
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the response
        await cache_service.set_cached_data(symbol, "MACD", cache_params, response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )


@router.get("/bollinger_bands", response_model=BollingerBandsResponse)
async def get_bollinger_bands(
    symbol: str = Query(..., description="Stock symbol"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    period: int = Query(20, ge=1, le=200, description="Period"),
    std_dev: float = Query(2.0, ge=0.1, le=5.0, description="Standard deviation multiplier"),
    current_user: User = Depends(require_tier("premium")),
    db: Session = Depends(get_db)
):
    """Calculate Bollinger Bands (Premium tier required)."""
    try:
        # Check rate limit
        check_rate_limit(current_user)
        
        # Set default date range if not provided
        if end_date is None:
            end_date = datetime.now().date()
        if start_date is None:
            start_date = end_date - timedelta(days=365)
        
        # Validate and adjust date range based on tier
        start_date, end_date = data_service.validate_date_range(
            start_date, end_date, current_user.tier.value
        )
        
        # Check cache first
        cache_params = {
            "start_date": start_date.isoformat(),
            "end_date": end_date.isoformat(),
            "period": period,
            "std_dev": std_dev
        }
        cached_data = await cache_service.get_cached_data(symbol, "BOLLINGER", cache_params)
        if cached_data:
            return cached_data
        
        # Get stock data
        stock_data = data_service.get_stock_data(symbol, start_date, end_date, use_pandas=False)
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in date range"
            )
        
        # Calculate Bollinger Bands
        upper_band, middle_band, lower_band = calculate_bollinger_bands(stock_data, period, std_dev)
        
        # Convert to response format
        data_points = []
        dates = stock_data.select("date").to_series().to_list()
        
        for i, date_val in enumerate(dates):
            data_points.append(BollingerBandsDataPoint(
                date=date_val,
                upper=float(upper_band[i]) if upper_band[i] is not None else None,
                middle=float(middle_band[i]) if middle_band[i] is not None else None,
                lower=float(lower_band[i]) if lower_band[i] is not None else None
            ))
        
        response = BollingerBandsResponse(
            symbol=symbol,
            indicator="Bollinger Bands",
            parameters={
                "period": period,
                "std_dev": std_dev
            },
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the response
        await cache_service.set_cached_data(symbol, "BOLLINGER", cache_params, response.dict())
        
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error"
        )
