"""
Exponential Moving Average (EMA) calculation.
"""
import pandas as pd
import polars as pl
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_ema_pandas(df: pd.DataFrame, window: int) -> pd.Series:
    """
    Calculate Exponential Moving Average using pandas.
    
    Args:
        df: DataFrame with OHLC data
        window: Window period for EMA
        
    Returns:
        Series: EMA values
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        ema = df['close'].ewm(span=window, adjust=False).mean()
        return ema
    except Exception as e:
        logger.error(f"Error calculating EMA with pandas: {e}")
        raise


def calculate_ema_polars(df: pl.DataFrame, window: int) -> pl.Series:
    """
    Calculate Exponential Moving Average using polars.
    
    Args:
        df: DataFrame with OHLC data
        window: Window period for EMA
        
    Returns:
        Series: EMA values
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        # Calculate alpha for EMA
        alpha = 2.0 / (window + 1)
        
        # Use polars ewm_mean function
        ema = df.select(
            pl.col('close').ewm_mean(alpha=alpha, adjust=False).alias('ema')
        )['ema']
        return ema
    except Exception as e:
        logger.error(f"Error calculating EMA with polars: {e}")
        raise


def calculate_ema(df: Union[pd.DataFrame, pl.DataFrame], window: int) -> Union[pd.Series, pl.Series]:
    """
    Calculate Exponential Moving Average.
    
    Args:
        df: DataFrame with OHLC data
        window: Window period for EMA
        
    Returns:
        Series: EMA values
    """
    if isinstance(df, pd.DataFrame):
        return calculate_ema_pandas(df, window)
    elif isinstance(df, pl.DataFrame):
        return calculate_ema_polars(df, window)
    else:
        raise TypeError("DataFrame must be pandas or polars DataFrame")
