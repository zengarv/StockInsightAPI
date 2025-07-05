"""
Database models and schemas.
"""
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum as PyEnum
from typing import Optional
from datetime import datetime

Base = declarative_base()


class SubscriptionTier(str, PyEnum):
    """User subscription tiers."""
    FREE = "free"
    PRO = "pro"
    PREMIUM = "premium"


class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)
    tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class APIKey(Base):
    """API Key model."""
    __tablename__ = "api_keys"
    
    id = Column(Integer, primary_key=True, index=True)
    key = Column(String, unique=True, index=True, nullable=False)
    user_id = Column(Integer, nullable=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    expires_at = Column(DateTime(timezone=True), nullable=True)


class RequestLog(Base):
    """Request logging model."""
    __tablename__ = "request_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, nullable=False)
    endpoint = Column(String, nullable=False)
    method = Column(String, nullable=False)
    status_code = Column(Integer, nullable=False)
    response_time = Column(Integer, nullable=False)  # in milliseconds
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
