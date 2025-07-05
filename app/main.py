"""
Main FastAPI application for Kalpi Tech API.
"""
from fastapi import FastAPI, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager
import logging
from datetime import datetime

from app.core.config import settings
from app.core.logging import setup_logging
from app.database.database import create_tables
from app.services.data_service import data_service
from app.services.cache_service import cache_service
from app.routers import indicators, auth
from app.models.schemas import HealthCheckResponse

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    logger.info("Starting Kalpi Tech API...")
    
    try:
        # Create database tables
        create_tables()
        
        # Load stock data
        logger.info("Loading stock data...")
        data_service.load_data()
        
        # Connect to Redis
        logger.info("Connecting to Redis...")
        await cache_service.connect()
        
        logger.info("Application startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Kalpi Tech API...")
        await cache_service.disconnect()
        logger.info("Application shutdown completed")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """Handle HTTP exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "status_code": exc.status_code,
            "timestamp": datetime.now().isoformat()
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """Handle general exceptions."""
    logger.error(f"Unhandled exception: {exc}")
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.now().isoformat()
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse)
async def health_check():
    """Health check endpoint."""
    try:
        # Check data service
        data_info = data_service.get_data_info()
        
        # Check cache service
        cache_stats = await cache_service.get_cache_stats()
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=settings.VERSION,
            data_loaded=data_info["loaded"],
            cache_status="connected" if cache_stats.get("connected", False) else "disconnected"
        )
        
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        return HealthCheckResponse(
            status="unhealthy",
            timestamp=datetime.now(),
            version=settings.VERSION,
            data_loaded=False,
            cache_status="error"
        )


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR)
app.include_router(indicators.router, prefix=settings.API_V1_STR)


# Root endpoint
@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Welcome to Kalpi Tech API",
        "version": settings.VERSION,
        "docs": "/docs",
        "health": "/health"
    }


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
            "available_symbols": symbols[:20] if len(symbols) > 20 else symbols,  # Limit to first 20
            "sample_symbols": symbols[:10] if len(symbols) > 10 else symbols
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
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="debug" if settings.DEBUG else "info"
    )
