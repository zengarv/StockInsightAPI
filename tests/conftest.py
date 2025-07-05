"""
Test configuration and fixtures.
"""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
import tempfile
import os

from app.main import app
from app.database.database import get_db
from app.database.models import Base
from app.services.data_service import data_service


# Create test database
SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base.metadata.create_all(bind=engine)


def override_get_db():
    """Override database dependency for testing."""
    try:
        db = TestingSessionLocal()
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="session")
def client():
    """Create test client."""
    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def test_user():
    """Create test user data."""
    return {
        "username": "testuser",
        "email": "test@example.com",
        "password": "testpassword123"
    }


@pytest.fixture(scope="session")
def setup_test_data():
    """Setup test data."""
    # Create a small test dataset
    import polars as pl
    from datetime import date, timedelta
    
    # Generate sample data
    symbols = ["AAPL", "GOOGL", "MSFT"]
    start_date = date(2023, 1, 1)
    end_date = date(2023, 12, 31)
    
    data = []
    for symbol in symbols:
        current_date = start_date
        price = 100.0
        
        while current_date <= end_date:
            # Simple price simulation
            import random
            change = random.uniform(-0.05, 0.05)
            price = price * (1 + change)
            
            data.append({
                "date": current_date,
                "symbol": symbol,
                "open": price,
                "high": price * 1.02,
                "low": price * 0.98,
                "close": price,
                "volume": random.randint(1000000, 10000000)
            })
            
            current_date += timedelta(days=1)
    
    # Create temporary parquet file
    df = pl.DataFrame(data)
    temp_file = tempfile.NamedTemporaryFile(suffix=".parquet", delete=False)
    df.write_parquet(temp_file.name)
    
    # Override data service path
    original_path = data_service.data_file_path
    data_service.data_file_path = temp_file.name
    
    yield temp_file.name
    
    # Cleanup
    data_service.data_file_path = original_path
    os.unlink(temp_file.name)
