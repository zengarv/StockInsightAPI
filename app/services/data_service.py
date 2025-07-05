"""
Data service for loading and managing stock data.
"""
import polars as pl
import pandas as pd
from typing import Optional, Union, List
from datetime import datetime, date, timedelta
import logging
import os
from pathlib import Path

from app.core.config import settings

logger = logging.getLogger(__name__)


class DataService:
    """Service for managing stock data operations."""
    
    def __init__(self):
        self.data: Optional[pl.DataFrame] = None
        self.data_loaded = False
        self.available_symbols: List[str] = []
        self.date_range: Optional[tuple] = None
        
    def load_data(self) -> None:
        """Load stock data from parquet file."""
        try:
            data_path = Path(settings.DATA_FILE_PATH)
            if not data_path.exists():
                raise FileNotFoundError(f"Data file not found: {data_path}")
                
            logger.info(f"Loading stock data from {data_path}")
            self.data = pl.read_parquet(data_path)
            
            # Ensure date column is in the correct format
            if 'date' in self.data.columns:
                date_dtype = self.data['date'].dtype
                if date_dtype == pl.Datetime:
                    # Convert datetime to date for easier handling
                    self.data = self.data.with_columns(
                        pl.col('date').dt.date()
                    )
            
            # Sort by symbol and date
            self.data = self.data.sort(['symbol', 'date'])
            
            # Cache available symbols
            self.available_symbols = self.data.select('symbol').unique().to_series().to_list()
            
            # Cache date range
            date_stats = self.data.select([
                pl.col('date').min().alias('min_date'),
                pl.col('date').max().alias('max_date')
            ]).row(0)
            self.date_range = (date_stats[0], date_stats[1])
            
            self.data_loaded = True
            logger.info(f"Successfully loaded {len(self.data)} records for {len(self.available_symbols)} symbols")
            logger.info(f"Date range: {self.date_range[0]} to {self.date_range[1]}")
            
        except Exception as e:
            logger.error(f"Error loading stock data: {e}")
            raise
    
    def get_stock_data(
        self,
        symbol: str,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        use_pandas: bool = False
    ) -> Union[pl.DataFrame, pd.DataFrame]:
        """
        Get stock data for a specific symbol and date range.
        
        Args:
            symbol: Stock symbol
            start_date: Start date (optional)
            end_date: End date (optional)
            use_pandas: Return pandas DataFrame instead of polars
            
        Returns:
            DataFrame: Filtered stock data
        """
        if not self.data_loaded:
            raise RuntimeError("Data not loaded. Call load_data() first.")
            
        if symbol not in self.available_symbols:
            raise ValueError(f"Symbol {symbol} not found in data")
        
        # Filter by symbol
        filtered_data = self.data.filter(pl.col('symbol') == symbol)
        
        # Apply date filters
        if start_date:
            filtered_data = filtered_data.filter(pl.col('date') >= start_date)
        if end_date:
            filtered_data = filtered_data.filter(pl.col('date') <= end_date)
        
        # Sort by date
        filtered_data = filtered_data.sort('date')
        
        if use_pandas:
            return filtered_data.to_pandas()
        
        return filtered_data
    
    def validate_date_range(self, start_date: date, end_date: date, tier: str) -> tuple:
        """
        Validate and adjust date range based on user tier.
        
        Args:
            start_date: Requested start date
            end_date: Requested end date
            tier: User subscription tier
            
        Returns:
            tuple: (adjusted_start_date, adjusted_end_date)
        """
        if not self.data_loaded:
            raise RuntimeError("Data not loaded. Call load_data() first.")
        
        # Get current date
        current_date = datetime.now().date()
        
        # Define tier limits
        if tier == "free":
            max_days = settings.DATA_LIMIT_FREE
        elif tier == "pro":
            max_days = settings.DATA_LIMIT_PRO
        elif tier == "premium":
            max_days = settings.DATA_LIMIT_PREMIUM
        else:
            raise ValueError(f"Invalid tier: {tier}")
        
        # Adjust dates based on tier limits
        if max_days is not None:
            earliest_allowed = current_date - timedelta(days=max_days)
            if start_date < earliest_allowed:
                start_date = earliest_allowed
        
        # Ensure dates are within data range
        if self.date_range:
            data_start, data_end = self.date_range
            if start_date < data_start:
                start_date = data_start
            if end_date > data_end:
                end_date = data_end
        
        return start_date, end_date
    
    def get_available_symbols(self) -> List[str]:
        """Get list of available symbols."""
        return self.available_symbols.copy()
    
    def get_data_info(self) -> dict:
        """Get information about loaded data."""
        if not self.data_loaded:
            return {
                "loaded": False,
                "symbols": 0,
                "records": 0,
                "date_range": None
            }
        
        return {
            "loaded": True,
            "symbols": len(self.available_symbols),
            "records": len(self.data),
            "date_range": self.date_range
        }


# Global data service instance
data_service = DataService()
