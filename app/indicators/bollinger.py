"""
Bollinger Bands calculation.
"""
import pandas as pd
import polars as pl
from typing import Union, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


def calculate_bollinger_bands_pandas(df: pd.DataFrame, period: int, std_dev: float) -> Tuple[pd.Series, pd.Series, pd.Series]:
    """
    Calculate Bollinger Bands using pandas.
    
    Args:
        df: DataFrame with OHLC data
        period: Period for moving average
        std_dev: Standard deviation multiplier
        
    Returns:
        Tuple: (Upper band, Middle band, Lower band)
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        close = df['close']
        
        # Calculate middle band (SMA)
        middle_band = close.rolling(window=period, min_periods=1).mean()
        
        # Calculate standard deviation
        std = close.rolling(window=period, min_periods=1).std()
        
        # Calculate upper and lower bands
        upper_band = middle_band + (std * std_dev)
        lower_band = middle_band - (std * std_dev)
        
        return upper_band, middle_band, lower_band
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands with pandas: {e}")
        raise


def calculate_bollinger_bands_polars(df: pl.DataFrame, period: int, std_dev: float) -> Tuple[pl.Series, pl.Series, pl.Series]:
    """
    Calculate Bollinger Bands using polars.
    
    Args:
        df: DataFrame with OHLC data
        period: Period for moving average
        std_dev: Standard deviation multiplier
        
    Returns:
        Tuple: (Upper band, Middle band, Lower band)
    """
    try:
        if 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column")
        
        result = df.select([
            pl.col('close'),
            pl.col('close').rolling_mean(window_size=period, min_periods=1).alias('middle_band'),
            pl.col('close').rolling_std(window_size=period, min_periods=1).alias('std')
        ]).with_columns([
            (pl.col('middle_band') + (pl.col('std') * std_dev)).alias('upper_band'),
            (pl.col('middle_band') - (pl.col('std') * std_dev)).alias('lower_band')
        ])
        
        return result['upper_band'], result['middle_band'], result['lower_band']
    except Exception as e:
        logger.error(f"Error calculating Bollinger Bands with polars: {e}")
        raise


def calculate_bollinger_bands(df: Union[pd.DataFrame, pl.DataFrame], period: int, std_dev: float) -> Tuple[Union[pd.Series, pl.Series], Union[pd.Series, pl.Series], Union[pd.Series, pl.Series]]:
    """
    Calculate Bollinger Bands.
    
    Args:
        df: DataFrame with OHLC data
        period: Period for moving average
        std_dev: Standard deviation multiplier
        
    Returns:
        Tuple: (Upper band, Middle band, Lower band)
    """
    if isinstance(df, pd.DataFrame):
        return calculate_bollinger_bands_pandas(df, period, std_dev)
    elif isinstance(df, pl.DataFrame):
        return calculate_bollinger_bands_polars(df, period, std_dev)
    else:
        raise TypeError("DataFrame must be pandas or polars DataFrame")
