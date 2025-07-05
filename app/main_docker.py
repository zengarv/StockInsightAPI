"""
Production-ready FastAPI application with compatibility fixes.
"""
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.core.config import settings
from app.core.logging import setup_logging
from app.database.database import create_tables
from app.services.data_service import data_service
from app.routers import auth
from app.routers.indicators import router as indicators_router
from app.models.schemas import HealthCheckResponse

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Kalpi Tech API (Docker Production)...")
    
    try:
        # Create database tables
        logger.info("Creating database tables...")
        create_tables()
        
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
    description=settings.DESCRIPTION + " - Docker Production",
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
            cache_status="enabled",
            total_symbols=len(data_service.get_available_symbols()) if data_info["loaded"] else 0
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Health check failed"
        )


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(indicators_router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Kalpi Tech API - Docker Production",
        "version": settings.VERSION,
        "docs_url": "/docs",
        "health_url": "/health",
        "environment": "docker"
    }


# Info endpoint
@app.get("/info")
async def info():
    """API information endpoint."""
    data_info = data_service.get_data_info()
    symbols = data_service.get_available_symbols()
    
    return {
        "api_name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": "docker",
        "data_loaded": data_info["loaded"],
        "total_symbols": len(symbols),
        "total_records": data_info["records"],
        "date_range": data_info["date_range"],
        "sample_symbols": symbols[:10] if symbols else [],
        "features": {
            "authentication": True,
            "rate_limiting": True,
            "caching": True,
            "subscription_tiers": True
        },
        "subscription_tiers": {
            "free": {
                "rate_limit": "50 requests/day",
                "indicators": ["SMA", "EMA"],
                "data_access": "3 months"
            },
            "pro": {
                "rate_limit": "500 requests/day", 
                "indicators": ["SMA", "EMA", "RSI", "MACD"],
                "data_access": "1 year"
            },
            "premium": {
                "rate_limit": "Unlimited",
                "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger Bands"],
                "data_access": "3 years"
            }
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main_docker:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
