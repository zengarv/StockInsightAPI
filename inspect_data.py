#!/usr/bin/env python3
"""
Check the structure of the stock data file.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    import polars as pl
    from pathlib import Path
    
    data_path = Path("data/stocks_ohlc_data.parquet")
    print(f"📊 Checking data file: {data_path}")
    
    if not data_path.exists():
        print("❌ Data file not found")
        exit(1)
    
    # Read the data
    print("📖 Reading data...")
    data = pl.read_parquet(data_path)
    
    print(f"✓ Data loaded successfully")
    print(f"📏 Shape: {data.shape}")
    print(f"🔍 Columns: {data.columns}")
    print(f"🏷️ Data types: {data.dtypes}")
    
    print("\n📋 First few rows:")
    print(data.head())
    
    print("\n📈 Unique symbols:")
    if 'symbol' in data.columns:
        symbols = data.select('symbol').unique().to_series().to_list()
        print(f"Count: {len(symbols)}")
        print(f"First 10: {symbols[:10]}")
    
    print("\n📅 Date range:")
    if 'date' in data.columns:
        date_range = data.select([
            pl.col('date').min().alias('min_date'),
            pl.col('date').max().alias('max_date')
        ]).row(0)
        print(f"From: {date_range[0]} to {date_range[1]}")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
