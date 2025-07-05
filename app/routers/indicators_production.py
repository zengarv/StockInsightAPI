"""
Production-ready indicators router with authentication, rate limiting, and tier enforcement.
"""
from fastapi import APIRouter, HTTPException, status, Query, Depends
from typing import List, Optional
from datetime import date, datetime, timedelta
import logging

from app.models.schemas import (
    SMAResponse, EMAResponse, RSIResponse, MACDResponse, BollingerBandsResponse,
    IndicatorDataPoint, MACDDataPoint, BollingerBandsDataPoint,
    SubscriptionTier
)
from app.services.data_service import data_service
from app.services.cache_service import cache_service
from app.auth.dependencies import (
    SMAAccess, EMAAccess, RSIAccess, MACDAccess, BollingerAccess, 
    RateLimitedUser, CurrentUser
)
from app.database.models import User
from app.indicators import (
    calculate_sma, calculate_ema, calculate_rsi, 
    calculate_macd, calculate_bollinger_bands
)
from app.auth.auth_utils import get_tier_limits

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/stocks/symbols", response_model=List[str])
async def get_available_symbols(current_user: CurrentUser):
    """Get list of available stock symbols."""
    try:
        symbols = data_service.get_available_symbols()
        logger.info(f"User {current_user.id} retrieved {len(symbols)} available symbols")
        return symbols
    except Exception as e:
        logger.error(f"Error retrieving symbols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve available symbols"
        )


@router.get("/user/limits")
async def get_user_limits(current_user: CurrentUser):
    """Get current user's subscription limits and usage."""
    try:
        limits = get_tier_limits(current_user.tier)
        
        # Get remaining requests (this would need to be implemented in rate_limit_service)
        # remaining_requests = await rate_limit_service.get_remaining_requests(current_user.id, current_user.tier)
        
        return {
            "user_id": current_user.id,
            "username": current_user.username,
            "tier": current_user.tier.value,
            "limits": limits,
            "remaining_requests_today": "N/A"  # Would be remaining_requests
        }
    except Exception as e:
        logger.error(f"Error getting user limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve user limits"
        )


def validate_date_range(start_date: date, end_date: date, user_tier: SubscriptionTier):
    """Validate date range based on user tier."""
    if start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Start date must be before end date"
        )
    
    # Check tier data limits
    limits = get_tier_limits(user_tier)
    data_limit_days = limits.get("data_limit_days")
    
    if data_limit_days is not None:
        max_start_date = date.today() - timedelta(days=data_limit_days)
        if start_date < max_start_date:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. {user_tier.value} tier can only access last {data_limit_days} days of data"
            )


@router.get("/indicators/sma", response_model=SMAResponse)
async def calculate_sma_endpoint(
    symbol: str = Query(..., description="Stock symbol"),
    window: int = Query(default=20, ge=1, le=200, description="SMA window"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: SMAAccess = Depends()
):
    """Calculate Simple Moving Average."""
    try:
        # Set default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Validate date range
        validate_date_range(start_date, end_date, current_user.tier)
        
        # Check cache first
        cache_key = f"sma:{symbol}:{window}:{start_date}:{end_date}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached SMA for {symbol}")
            return cached_result
        
        # Get stock data
        try:
            stock_data = data_service.get_stock_data(symbol, start_date, end_date)
        except ValueError as e:
            if "not found in data" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Symbol {symbol} not found"
                )
            raise
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in the specified date range"
            )
        
        # Calculate SMA
        sma_values = calculate_sma(stock_data, window)
        
        # Convert to pandas Series if it's a Polars Series
        if hasattr(sma_values, 'to_pandas'):
            sma_values = sma_values.to_pandas()
        
        # Prepare response data
        data_points = []
        stock_data_pd = stock_data.to_pandas()
        for i, (idx, row) in enumerate(stock_data_pd.iterrows()):
            if i >= window - 1:  # SMA starts after window period
                data_points.append(IndicatorDataPoint(
                    date=row['date'],
                    value=float(sma_values.iloc[i])
                ))
        
        response = SMAResponse(
            symbol=symbol,
            window=window,
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the result
        await cache_service.set(cache_key, response, expire_minutes=30)
        
        logger.info(f"SMA calculated for {symbol}, window={window}, {len(data_points)} points")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating SMA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate SMA"
        )


@router.get("/indicators/ema", response_model=EMAResponse)
async def calculate_ema_endpoint(
    symbol: str = Query(..., description="Stock symbol"),
    window: int = Query(default=20, ge=1, le=200, description="EMA window"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: EMAAccess = Depends()
):
    """Calculate Exponential Moving Average."""
    try:
        # Set default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Validate date range
        validate_date_range(start_date, end_date, current_user.tier)
        
        # Check cache first
        cache_key = f"ema:{symbol}:{window}:{start_date}:{end_date}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached EMA for {symbol}")
            return cached_result
        
        # Get stock data
        try:
            stock_data = data_service.get_stock_data(symbol, start_date, end_date)
        except ValueError as e:
            if "not found in data" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Symbol {symbol} not found"
                )
            raise
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in the specified date range"
            )
        
        # Calculate EMA
        ema_values = calculate_ema(stock_data, window)
        
        # Convert to pandas Series if it's a Polars Series
        if hasattr(ema_values, 'to_pandas'):
            ema_values = ema_values.to_pandas()
        
        # Prepare response data
        data_points = []
        stock_data_pd = stock_data.to_pandas()
        for i, (idx, row) in enumerate(stock_data_pd.iterrows()):
            if i >= window - 1:  # EMA starts after window period
                data_points.append(IndicatorDataPoint(
                    date=row['date'],
                    value=float(ema_values.iloc[i])
                ))
        
        response = EMAResponse(
            symbol=symbol,
            window=window,
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the result
        await cache_service.set(cache_key, response, expire_minutes=30)
        
        logger.info(f"EMA calculated for {symbol}, window={window}, {len(data_points)} points")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating EMA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate EMA"
        )


@router.get("/indicators/rsi", response_model=RSIResponse)
async def calculate_rsi_endpoint(
    symbol: str = Query(..., description="Stock symbol"),
    window: int = Query(default=14, ge=1, le=100, description="RSI window"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: RSIAccess = Depends()
):
    """Calculate Relative Strength Index."""
    try:
        # Set default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Validate date range
        validate_date_range(start_date, end_date, current_user.tier)
        
        # Check cache first
        cache_key = f"rsi:{symbol}:{window}:{start_date}:{end_date}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached RSI for {symbol}")
            return cached_result
        
        # Get stock data
        try:
            stock_data = data_service.get_stock_data(symbol, start_date, end_date)
        except ValueError as e:
            if "not found in data" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Symbol {symbol} not found"
                )
            raise
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in the specified date range"
            )
        
        # Calculate RSI
        rsi_values = calculate_rsi(stock_data, window)
        
        # Convert to pandas Series if it's a Polars Series
        if hasattr(rsi_values, 'to_pandas'):
            rsi_values = rsi_values.to_pandas()
        
        # Prepare response data
        data_points = []
        stock_data_pd = stock_data.to_pandas()
        for i, (idx, row) in enumerate(stock_data_pd.iterrows()):
            if i >= window:  # RSI starts after window period
                data_points.append(IndicatorDataPoint(
                    date=row['date'],
                    value=float(rsi_values.iloc[i])
                ))
        
        response = RSIResponse(
            symbol=symbol,
            window=window,
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the result
        await cache_service.set(cache_key, response, expire_minutes=30)
        
        logger.info(f"RSI calculated for {symbol}, window={window}, {len(data_points)} points")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating RSI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate RSI"
        )


@router.get("/indicators/macd", response_model=MACDResponse)
async def calculate_macd_endpoint(
    symbol: str = Query(..., description="Stock symbol"),
    fast: int = Query(default=12, ge=1, le=50, description="Fast EMA period"),
    slow: int = Query(default=26, ge=1, le=200, description="Slow EMA period"),
    signal: int = Query(default=9, ge=1, le=50, description="Signal line period"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: MACDAccess = Depends()
):
    """Calculate MACD (Moving Average Convergence Divergence)."""
    try:
        # Set default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Validate date range
        validate_date_range(start_date, end_date, current_user.tier)
        
        # Check cache first
        cache_key = f"macd:{symbol}:{fast}:{slow}:{signal}:{start_date}:{end_date}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached MACD for {symbol}")
            return cached_result
        
        # Get stock data
        try:
            stock_data = data_service.get_stock_data(symbol, start_date, end_date)
        except ValueError as e:
            if "not found in data" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Symbol {symbol} not found"
                )
            raise
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in the specified date range"
            )
        
        # Calculate MACD
        macd_line, signal_line, histogram = calculate_macd(stock_data, fast, slow, signal)
        
        # Convert to pandas Series if needed
        if hasattr(macd_line, 'to_pandas'):
            macd_line = macd_line.to_pandas()
            signal_line = signal_line.to_pandas()
            histogram = histogram.to_pandas()
        
        # Prepare response data
        data_points = []
        stock_data_pd = stock_data.to_pandas()
        for i, (idx, row) in enumerate(stock_data_pd.iterrows()):
            if i >= slow - 1:  # MACD starts after slow period
                data_points.append(MACDDataPoint(
                    date=row['date'],
                    macd=float(macd_line.iloc[i]) if not pd.isna(macd_line.iloc[i]) else 0.0,
                    signal=float(signal_line.iloc[i]) if not pd.isna(signal_line.iloc[i]) else 0.0,
                    histogram=float(histogram.iloc[i]) if not pd.isna(histogram.iloc[i]) else 0.0
                ))
        
        response = MACDResponse(
            symbol=symbol,
            indicator="MACD",
            parameters={"fast": fast, "slow": slow, "signal": signal},
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the result
        await cache_service.set(cache_key, response, expire_minutes=30)
        
        logger.info(f"MACD calculated for {symbol}, {len(data_points)} points")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating MACD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate MACD"
        )


@router.get("/indicators/bollinger", response_model=BollingerBandsResponse)
async def calculate_bollinger_endpoint(
    symbol: str = Query(..., description="Stock symbol"),
    period: int = Query(default=20, ge=1, le=200, description="Period for moving average"),
    std_dev: float = Query(default=2.0, ge=0.1, le=5.0, description="Standard deviation multiplier"),
    start_date: Optional[date] = Query(None, description="Start date (YYYY-MM-DD)"),
    end_date: Optional[date] = Query(None, description="End date (YYYY-MM-DD)"),
    current_user: BollingerAccess = Depends()
):
    """Calculate Bollinger Bands."""
    try:
        # Set default date range
        if not end_date:
            end_date = date.today()
        if not start_date:
            start_date = end_date - timedelta(days=90)
        
        # Validate date range
        validate_date_range(start_date, end_date, current_user.tier)
        
        # Check cache first
        cache_key = f"bollinger:{symbol}:{period}:{std_dev}:{start_date}:{end_date}"
        cached_result = await cache_service.get(cache_key)
        if cached_result:
            logger.info(f"Returning cached Bollinger Bands for {symbol}")
            return cached_result
        
        # Get stock data
        try:
            stock_data = data_service.get_stock_data(symbol, start_date, end_date)
        except ValueError as e:
            if "not found in data" in str(e):
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Symbol {symbol} not found"
                )
            raise
        
        if len(stock_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No data found for symbol {symbol} in the specified date range"
            )
        
        # Calculate Bollinger Bands
        upper_band, middle_band, lower_band = calculate_bollinger_bands(stock_data, period, std_dev)
        
        # Convert to pandas Series if needed
        if hasattr(upper_band, 'to_pandas'):
            upper_band = upper_band.to_pandas()
            middle_band = middle_band.to_pandas()
            lower_band = lower_band.to_pandas()
        
        # Prepare response data
        data_points = []
        stock_data_pd = stock_data.to_pandas()
        for i, (idx, row) in enumerate(stock_data_pd.iterrows()):
            if i >= period - 1:  # Bollinger starts after period
                data_points.append(BollingerBandsDataPoint(
                    date=row['date'],
                    upper=float(upper_band.iloc[i]) if not pd.isna(upper_band.iloc[i]) else 0.0,
                    middle=float(middle_band.iloc[i]) if not pd.isna(middle_band.iloc[i]) else 0.0,
                    lower=float(lower_band.iloc[i]) if not pd.isna(lower_band.iloc[i]) else 0.0
                ))
        
        response = BollingerBandsResponse(
            symbol=symbol,
            indicator="Bollinger Bands",
            parameters={"period": period, "std_dev": std_dev},
            data_points=len(data_points),
            start_date=start_date,
            end_date=end_date,
            data=data_points
        )
        
        # Cache the result
        await cache_service.set(cache_key, response, expire_minutes=30)
        
        logger.info(f"Bollinger Bands calculated for {symbol}, {len(data_points)} points")
        return response
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to calculate Bollinger Bands"
        )
