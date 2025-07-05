"""
Simplified FastAPI application for demonstration.
"""
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional, List

from app.core.config import settings
from app.core.logging import setup_logging
from app.services.data_service import data_service
from app.indicators.sma import calculate_sma
from app.indicators.ema import calculate_ema
from app.indicators.rsi import calculate_rsi
from app.indicators.macd import calculate_macd
from app.indicators.bollinger import calculate_bollinger_bands
from app.models.schemas import (
    HealthCheckResponse, 
    SMARequest, SMAResponse,
    EMARequest, EMAResponse,
    RSIRequest, RSIResponse,
    MACDRequest, MACDResponse,
    BollingerBandsRequest, BollingerBandsResponse
)

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Kalpi Tech API (Demo Mode)...")
    
    try:
        # Load stock data
        logger.info("Loading stock data...")
        data_service.load_data()
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Kalpi Tech API...")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description=settings.DESCRIPTION,
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    lifespan=lifespan
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Global exception handler
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """Global exception handler."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        data_info = data_service.get_data_info()
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.utcnow(),
            version=settings.VERSION,
            data_loaded=data_info["loaded"],
            cache_status="disabled",
            total_symbols=len(data_service.get_available_symbols()) if data_info["loaded"] else 0
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


# Symbols endpoint
@app.get("/api/v1/stocks/symbols")
async def get_symbols():
    """Get available stock symbols."""
    try:
        symbols = data_service.get_available_symbols()
        return {
            "symbols": symbols,
            "total": len(symbols)
        }
    except Exception as e:
        logger.error(f"Error getting symbols: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving symbols"
        )


# SMA endpoint
@app.get("/api/v1/indicators/sma", response_model=SMAResponse)
async def get_sma(
    symbol: str,
    window: int = 20,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Calculate Simple Moving Average."""
    try:
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
        logger.error(f"Error calculating SMA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating SMA"
        )


# EMA endpoint
@app.get("/api/v1/indicators/ema", response_model=EMAResponse)
async def get_ema(
    symbol: str,
    window: int = 20,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Calculate Exponential Moving Average."""
    try:
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
        logger.error(f"Error calculating EMA: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating EMA"
        )


# RSI endpoint
@app.get("/api/v1/indicators/rsi", response_model=RSIResponse)
async def get_rsi(
    symbol: str,
    period: int = 14,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Calculate Relative Strength Index."""
    try:
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
        logger.error(f"Error calculating RSI: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating RSI"
        )


# MACD endpoint
@app.get("/api/v1/indicators/macd", response_model=MACDResponse)
async def get_macd(
    symbol: str,
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Calculate MACD."""
    try:
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
        logger.error(f"Error calculating MACD: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating MACD"
        )


# Bollinger Bands endpoint
@app.get("/api/v1/indicators/bollinger", response_model=BollingerBandsResponse)
async def get_bollinger_bands(
    symbol: str,
    window: int = 20,
    std_dev: float = 2.0,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None
):
    """Calculate Bollinger Bands."""
    try:
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
        logger.error(f"Error calculating Bollinger Bands: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error calculating Bollinger Bands"
        )


# Data info endpoint
@app.get("/data-info")
async def get_data_info():
    """Get information about loaded data."""
    try:
        data_info = data_service.get_data_info()
        symbols = data_service.get_available_symbols()
        
        return {
            "data_loaded": data_info["loaded"],
            "total_symbols": len(symbols),
            "total_records": data_info["records"],
            "date_range": data_info["date_range"],
            "available_symbols": symbols[:20] if len(symbols) > 20 else symbols,
            "sample_symbols": symbols[:10] if len(symbols) > 10 else symbols,
            "message": "This is a demo version. Full production version includes authentication, rate limiting, and subscription tiers."
        }
        
    except Exception as e:
        logger.error(f"Error getting data info: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error retrieving data information"
        )


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_demo:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
