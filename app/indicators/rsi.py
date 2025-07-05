"""
Relative Strength Index (RSI) calculation.
"""
import pandas as pd
import polars as pl
from typing import Union, Optional
import logging

logger = logging.getLogger(__name__)


def calculate_rsi_pandas(df: pd.DataFrame, period: int) -> pd.Series:
    """
    Calculate Relative Strength Index using pandas.
    
    Args:
        df: DataFrame with OHLC data
        period: Period for RSI calculation
        
    Returns:
        Series: RSI values
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        close = df['close']
        delta = close.diff()
        
        # Separate gains and losses
        gains = delta.where(delta > 0, 0)
        losses = -delta.where(delta < 0, 0)
        
        # Calculate average gains and losses
        avg_gains = gains.rolling(window=period, min_periods=1).mean()
        avg_losses = losses.rolling(window=period, min_periods=1).mean()
        
        # Calculate RSI
        rs = avg_gains / avg_losses
        rsi = 100 - (100 / (1 + rs))
        
        return rsi
    except Exception as e:
        logger.error(f"Error calculating RSI with pandas: {e}")
        raise


def calculate_rsi_polars(df: pl.DataFrame, period: int) -> pl.Series:
    """
    Calculate Relative Strength Index using polars.
    
    Args:
        df: DataFrame with OHLC data
        period: Period for RSI calculation
        
    Returns:
        Series: RSI values
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        result = df.select([
            pl.col('close'),
            pl.col('close').diff().alias('delta')
        ]).with_columns([
            pl.when(pl.col('delta') > 0)
            .then(pl.col('delta'))
            .otherwise(0)
            .alias('gains'),
            pl.when(pl.col('delta') < 0)
            .then(-pl.col('delta'))
            .otherwise(0)
            .alias('losses')
        ]).with_columns([
            pl.col('gains').rolling_mean(window_size=period, min_periods=1).alias('avg_gains'),
            pl.col('losses').rolling_mean(window_size=period, min_periods=1).alias('avg_losses')
        ]).with_columns([
            (pl.col('avg_gains') / pl.col('avg_losses')).alias('rs')
        ]).with_columns([
            (100 - (100 / (1 + pl.col('rs')))).alias('rsi')
        ])
        
        return result['rsi']
    except Exception as e:
        logger.error(f"Error calculating RSI with polars: {e}")
        raise


def calculate_rsi(df: Union[pd.DataFrame, pl.DataFrame], period: int) -> Union[pd.Series, pl.Series]:
    """
    Calculate Relative Strength Index.
    
    Args:
        df: DataFrame with OHLC data
        period: Period for RSI calculation
        
    Returns:
        Series: RSI values
    """
    if isinstance(df, pd.DataFrame):
        return calculate_rsi_pandas(df, period)
    elif isinstance(df, pl.DataFrame):
        return calculate_rsi_polars(df, period)
    else:
        raise TypeError("DataFrame must be pandas or polars DataFrame")
