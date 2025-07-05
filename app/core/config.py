"""
Configuration settings for the Kalpi Tech API.
"""
from pydantic_settings import BaseSettings
from typing import Optional
import os


class Settings(BaseSettings):
    """Application settings."""
    
    # API Settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = "Kalpi Tech API"
    VERSION: str = "1.0.0"
    DESCRIPTION: str = "Stock Technical Analysis API with tiered access"
    
    # Security
    SECRET_KEY: str = "your-secret-key-change-this-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
    # Database
    DATABASE_URL: str = "postgresql://user:password@localhost/kalpi_db"
    
    # Redis
    REDIS_URL: str = "redis://localhost:6379"
    CACHE_EXPIRE_MINUTES: int = 30
    
    # Data
    DATA_FILE_PATH: str = "data/stocks_ohlc_data.parquet"
    
    # Rate Limiting
    RATE_LIMIT_FREE: int = 50
    RATE_LIMIT_PRO: int = 500
    RATE_LIMIT_PREMIUM: Optional[int] = None
    
    # Data Access Limits (in days)
    DATA_LIMIT_FREE: int = 90  # 3 months
    DATA_LIMIT_PRO: int = 365  # 1 year
    DATA_LIMIT_PREMIUM: Optional[int] = None  # Unlimited
    
    # Environment
    DEBUG: bool = False
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# Global settings instance
settings = Settings()
