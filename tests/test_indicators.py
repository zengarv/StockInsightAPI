"""
Test technical indicators calculations.
"""
import pytest
import pandas as pd
import polars as pl
from datetime import date, timedelta
import numpy as np

from app.indicators import (
    calculate_sma, calculate_ema, calculate_rsi, 
    calculate_macd, calculate_bollinger_bands
)


@pytest.fixture
def sample_data():
    """Create sample stock data for testing."""
    dates = [date(2023, 1, 1) + timedelta(days=i) for i in range(100)]
    prices = [100 + i * 0.5 + np.sin(i * 0.1) * 5 for i in range(100)]
    
    data = {
        "date": dates,
        "symbol": ["AAPL"] * 100,
        "open": prices,
        "high": [p * 1.02 for p in prices],
        "low": [p * 0.98 for p in prices],
        "close": prices,
        "volume": [1000000 + i * 10000 for i in range(100)]
    }
    
    return pd.DataFrame(data), pl.DataFrame(data)


def test_sma_pandas(sample_data):
    """Test SMA calculation with pandas."""
    df_pandas, _ = sample_data
    
    sma = calculate_sma(df_pandas, window=20)
    
    assert len(sma) == len(df_pandas)
    assert not pd.isna(sma.iloc[-1])  # Last value should not be NaN
    
    # Test that SMA is actually the mean of the last 20 values
    expected_sma = df_pandas['close'].iloc[-20:].mean()
    assert abs(sma.iloc[-1] - expected_sma) < 0.0001


def test_sma_polars(sample_data):
    """Test SMA calculation with polars."""
    _, df_polars = sample_data
    
    sma = calculate_sma(df_polars, window=20)
    
    assert len(sma) == len(df_polars)
    assert sma[-1] is not None  # Last value should not be None


def test_ema_pandas(sample_data):
    """Test EMA calculation with pandas."""
    df_pandas, _ = sample_data
    
    ema = calculate_ema(df_pandas, window=20)
    
    assert len(ema) == len(df_pandas)
    assert not pd.isna(ema.iloc[-1])  # Last value should not be NaN
    
    # EMA should be different from SMA
    sma = calculate_sma(df_pandas, window=20)
    assert abs(ema.iloc[-1] - sma.iloc[-1]) > 0.01


def test_ema_polars(sample_data):
    """Test EMA calculation with polars."""
    _, df_polars = sample_data
    
    ema = calculate_ema(df_polars, window=20)
    
    assert len(ema) == len(df_polars)
    assert ema[-1] is not None  # Last value should not be None


def test_rsi_pandas(sample_data):
    """Test RSI calculation with pandas."""
    df_pandas, _ = sample_data
    
    rsi = calculate_rsi(df_pandas, period=14)
    
    assert len(rsi) == len(df_pandas)
    assert not pd.isna(rsi.iloc[-1])  # Last value should not be NaN
    assert 0 <= rsi.iloc[-1] <= 100  # RSI should be between 0 and 100


def test_rsi_polars(sample_data):
    """Test RSI calculation with polars."""
    _, df_polars = sample_data
    
    rsi = calculate_rsi(df_polars, period=14)
    
    assert len(rsi) == len(df_polars)
    assert rsi[-1] is not None  # Last value should not be None
    assert 0 <= rsi[-1] <= 100  # RSI should be between 0 and 100


def test_macd_pandas(sample_data):
    """Test MACD calculation with pandas."""
    df_pandas, _ = sample_data
    
    macd_line, signal_line, histogram = calculate_macd(df_pandas, 12, 26, 9)
    
    assert len(macd_line) == len(df_pandas)
    assert len(signal_line) == len(df_pandas)
    assert len(histogram) == len(df_pandas)
    
    # Check that histogram is the difference between MACD and signal
    assert abs(histogram.iloc[-1] - (macd_line.iloc[-1] - signal_line.iloc[-1])) < 0.0001


def test_macd_polars(sample_data):
    """Test MACD calculation with polars."""
    _, df_polars = sample_data
    
    macd_line, signal_line, histogram = calculate_macd(df_polars, 12, 26, 9)
    
    assert len(macd_line) == len(df_polars)
    assert len(signal_line) == len(df_polars)
    assert len(histogram) == len(df_polars)


def test_bollinger_bands_pandas(sample_data):
    """Test Bollinger Bands calculation with pandas."""
    df_pandas, _ = sample_data
    
    upper, middle, lower = calculate_bollinger_bands(df_pandas, period=20, std_dev=2.0)
    
    assert len(upper) == len(df_pandas)
    assert len(middle) == len(df_pandas)
    assert len(lower) == len(df_pandas)
    
    # Upper band should be higher than middle, middle higher than lower
    assert upper.iloc[-1] > middle.iloc[-1]
    assert middle.iloc[-1] > lower.iloc[-1]


def test_bollinger_bands_polars(sample_data):
    """Test Bollinger Bands calculation with polars."""
    _, df_polars = sample_data
    
    upper, middle, lower = calculate_bollinger_bands(df_polars, period=20, std_dev=2.0)
    
    assert len(upper) == len(df_polars)
    assert len(middle) == len(df_polars)
    assert len(lower) == len(df_polars)
    
    # Upper band should be higher than middle, middle higher than lower
    assert upper[-1] > middle[-1]
    assert middle[-1] > lower[-1]


def test_invalid_dataframe():
    """Test with invalid DataFrame."""
    df = pd.DataFrame({"wrong_column": [1, 2, 3]})
    
    with pytest.raises(ValueError):
        calculate_sma(df, window=2)


def test_edge_cases():
    """Test edge cases."""
    # Test with small dataset
    small_df = pd.DataFrame({
        "date": [date(2023, 1, 1), date(2023, 1, 2)],
        "close": [100, 105]
    })
    
    sma = calculate_sma(small_df, window=5)  # Window larger than data
    assert len(sma) == 2
    assert not pd.isna(sma.iloc[-1])  # Should still calculate with min_periods=1
