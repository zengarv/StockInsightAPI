"""
Moving Average Convergence Divergence (MACD) calculation.
"""
import pandas as pd
import polars as pl
from typing import Union, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_macd_pandas(df: pd.DataFrame, fast_period: int, slow_period: int, signal_period: int) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate MACD using pandas.
    
    Args:
        df: DataFrame with OHLC data
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Tuple: (MACD line, Signal line, Histogram)
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        close = df['close']
        
        # Calculate fast and slow EMAs
        fast_ema = close.ewm(span=fast_period, adjust=False).mean()
        slow_ema = close.ewm(span=slow_period, adjust=False).mean()
        
        # Calculate MACD line
        macd_line = fast_ema - slow_ema
        
        # Calculate signal line
        signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()
        
        # Calculate histogram
        histogram = macd_line - signal_line
        
        return macd_line, signal_line, histogram
    except Exception as e:
        logger.error(f"Error calculating MACD with pandas: {e}")
        raise


def calculate_macd_polars(df: pl.DataFrame, fast_period: int, slow_period: int, signal_period: int) -> Tuple[pl.Series, pl.Series, pl.Series]:
    """
    Calculate MACD using polars.
    
    Args:
        df: DataFrame with OHLC data
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Tuple: (MACD line, Signal line, Histogram)
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        # Calculate alphas for EMAs
        fast_alpha = 2.0 / (fast_period + 1)
        slow_alpha = 2.0 / (slow_period + 1)
        signal_alpha = 2.0 / (signal_period + 1)
        
        result = df.select([
            pl.col('close'),
            pl.col('close').ewm_mean(alpha=fast_alpha, adjust=False).alias('fast_ema'),
            pl.col('close').ewm_mean(alpha=slow_alpha, adjust=False).alias('slow_ema')
        ]).with_columns([
            (pl.col('fast_ema') - pl.col('slow_ema')).alias('macd_line')
        ]).with_columns([
            pl.col('macd_line').ewm_mean(alpha=signal_alpha, adjust=False).alias('signal_line')
        ]).with_columns([
            (pl.col('macd_line') - pl.col('signal_line')).alias('histogram')
        ])
        
        return result['macd_line'], result['signal_line'], result['histogram']
    except Exception as e:
        logger.error(f"Error calculating MACD with polars: {e}")
        raise


def calculate_macd(df: Union[pd.DataFrame, pl.DataFrame], fast_period: int, slow_period: int, signal_period: int) -> Tuple[Union[pd.Series, pl.Series], Union[pd.Series, pl.Series], Union[pd.Series, pl.Series]]:
    """
    Calculate MACD.
    
    Args:
        df: DataFrame with OHLC data
        fast_period: Fast EMA period
        slow_period: Slow EMA period
        signal_period: Signal line period
        
    Returns:
        Tuple: (MACD line, Signal line, Histogram)
    """
    if isinstance(df, pd.DataFrame):
        return calculate_macd_pandas(df, fast_period, slow_period, signal_period)
    elif isinstance(df, pl.DataFrame):
        return calculate_macd_polars(df, fast_period, slow_period, signal_period)
    else:
        raise TypeError("DataFrame must be pandas or polars DataFrame")
