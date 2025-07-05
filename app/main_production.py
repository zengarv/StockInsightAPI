"""
Production-ready FastAPI application for Kalpi Tech API.
"""
from fastapi import FastAPI, HTTPException, status, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from contextlib import asynccontextmanager
import logging
from datetime import datetime
import time

from app.core.config import settings
from app.core.logging import setup_logging
from app.database.database import create_tables
from app.services.data_service import data_service
from app.services.cache_service import cache_service
from app.services.rate_limit_redis import rate_limit_service
from app.routers import auth
from app.routers.indicators_production import router as indicators_router
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
        logger.info("Creating database tables...")
        create_tables()
        
        # Load stock data
        logger.info("Loading stock data...")
        data_service.load_data()
        
        # Connect to Redis for caching
        logger.info("Connecting to Redis for caching...")
        await cache_service.connect()
        
        # Connect to Redis for rate limiting
        logger.info("Connecting to Redis for rate limiting...")
        await rate_limit_service.connect()
        
        logger.info("🚀 Kalpi Tech API startup completed successfully")
        
        yield
        
    except Exception as e:
        logger.error(f"Error during startup: {e}")
        raise
    
    finally:
        # Shutdown
        logger.info("Shutting down Kalpi Tech API...")
        
        # Disconnect from Redis
        await cache_service.disconnect()
        await rate_limit_service.disconnect()
        
        logger.info("🛑 Kalpi Tech API shutdown completed")


# Create FastAPI app
app = FastAPI(
    title=settings.PROJECT_NAME,
    description=settings.DESCRIPTION,
    version=settings.VERSION,
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)

# Add security middleware
app.add_middleware(
    TrustedHostMiddleware, 
    allowed_hosts=["localhost", "127.0.0.1", "*.kalpicapital.com"]
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["*"],
)


# Middleware for request logging
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests with timing."""
    start_time = time.time()
    
    # Log request
    logger.info(f"Request: {request.method} {request.url}")
    
    try:
        response = await call_next(request)
        
        # Log response
        process_time = time.time() - start_time
        logger.info(f"Response: {response.status_code} in {process_time:.4f}s")
        
        # Add timing header
        response.headers["X-Process-Time"] = str(process_time)
        
        return response
        
    except Exception as e:
        process_time = time.time() - start_time
        logger.error(f"Request failed: {request.method} {request.url} - {str(e)} in {process_time:.4f}s")
        raise


# Exception handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    """Handle HTTP exceptions with proper logging."""
    logger.warning(f"HTTP {exc.status_code}: {exc.detail} - {request.method} {request.url}")
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "status_code": exc.status_code,
            "message": exc.detail,
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


@app.exception_handler(500)
async def internal_server_error_handler(request: Request, exc: Exception):
    """Handle internal server errors."""
    logger.error(f"Internal server error: {str(exc)} - {request.method} {request.url}")
    
    return JSONResponse(
        status_code=500,
        content={
            "error": True,
            "status_code": 500,
            "message": "Internal server error",
            "timestamp": datetime.now().isoformat(),
            "path": str(request.url)
        }
    )


# Health check endpoint
@app.get("/health", response_model=HealthCheckResponse, tags=["Health"])
async def health_check():
    """Health check endpoint."""
    try:
        # Check data service
        data_loaded = data_service.data_loaded
        
        # Check cache service
        cache_status = "connected" if cache_service.redis else "disconnected"
        
        return HealthCheckResponse(
            status="healthy",
            timestamp=datetime.now(),
            version=settings.VERSION,
            data_loaded=data_loaded,
            cache_status=cache_status
        )
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Service unhealthy"
        )


# API information endpoint
@app.get("/info", tags=["Information"])
async def api_info():
    """Get API information and available endpoints."""
    return {
        "name": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "description": settings.DESCRIPTION,
        "documentation": "/docs",
        "health_check": "/health",
        "endpoints": {
            "authentication": {
                "register": "POST /api/v1/auth/register",
                "login": "POST /api/v1/auth/login",
                "user_info": "GET /api/v1/auth/me",
                "create_api_key": "POST /api/v1/auth/api-keys"
            },
            "indicators": {
                "symbols": "GET /api/v1/stocks/symbols",
                "user_limits": "GET /api/v1/user/limits",
                "sma": "GET /api/v1/indicators/sma",
                "ema": "GET /api/v1/indicators/ema",
                "rsi": "GET /api/v1/indicators/rsi",
                "macd": "GET /api/v1/indicators/macd",
                "bollinger": "GET /api/v1/indicators/bollinger"
            }
        },
        "subscription_tiers": {
            "free": {
                "requests_per_day": settings.RATE_LIMIT_FREE,
                "data_access_days": settings.DATA_LIMIT_FREE,
                "indicators": ["SMA", "EMA"]
            },
            "pro": {
                "requests_per_day": settings.RATE_LIMIT_PRO,
                "data_access_days": settings.DATA_LIMIT_PRO,
                "indicators": ["SMA", "EMA", "RSI", "MACD"]
            },
            "premium": {
                "requests_per_day": "unlimited",
                "data_access_days": "unlimited",
                "indicators": ["SMA", "EMA", "RSI", "MACD", "Bollinger Bands"]
            }
        }
    }


# Include routers
app.include_router(auth.router, prefix=settings.API_V1_STR + "/auth", tags=["Authentication"])
app.include_router(indicators_router, prefix=settings.API_V1_STR, tags=["Technical Indicators"])


# Root endpoint
@app.get("/", tags=["Root"])
async def root():
    """Root endpoint with welcome message."""
    return {
        "message": f"Welcome to {settings.PROJECT_NAME}",
        "version": settings.VERSION,
        "documentation": "/docs",
        "health": "/health",
        "info": "/info"
    }


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting Kalpi Tech API in development mode...")
    
    uvicorn.run(
        "app.main_production:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
