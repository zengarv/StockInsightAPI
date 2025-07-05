"""
Simple Moving Average (SMA) calculation.
"""
import pandas as pd
import polars as pl
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_sma_pandas(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate Simple Moving Average using pandas.
    
    Args:
        df: DataFrame with OHLC data
        window: Window period for SMA
        
    Returns:
        Series: SMA values
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        sma = df['close'].rolling(window=window, min_periods=1).mean()
        return sma
    except Exception as e:
        logger.error(f"Error calculating SMA with pandas: {e}")
        raise


def calculate_sma_polars(df: pl.DataFrame, window: int) -> pl.Series:
    """
    Calculate Simple Moving Average using polars.
    
    Args:
        df: DataFrame with OHLC data
        window: Window period for SMA
        
    Returns:
        Series: SMA values
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        sma = df.select(
            pl.col('close').rolling_mean(window_size=window, min_periods=1).alias('sma')
        )['sma']
        return sma
    except Exception as e:
        logger.error(f"Error calculating SMA with polars: {e}")
        raise


def calculate_sma(df: Union[pd.DataFrame, pl.DataFrame], window: int) -> Union[pd.Series, pl.Series]:
    """
    Calculate Simple Moving Average.
    
    Args:
        df: DataFrame with OHLC data
        window: Window period for SMA
        
    Returns:
        Series: SMA values
    """
    if isinstance(df, pd.DataFrame):
        return calculate_sma_pandas(df, window)
    elif isinstance(df, pl.DataFrame):
        return calculate_sma_polars(df, window)
    else:
        raise TypeError("DataFrame must be pandas or polars DataFrame")
