"""
Technical Analysis Package for Indian Stock Market

This package provides tools for technical analysis of Indian stocks using RSI and MACD indicators.
Now includes email reporting functionality.
"""

from .config import config, setup_logging
from .data_fetcher import get_nse_stock_symbols, filter_and_fetch_stocks_efficiently, fetch_complete_stock_data, fetch_multiple_stocks_complete_data
from .technical_indicators import analyze_stock_with_talib
from .email_sender import send_email_report, create_csv_report
from .utils import create_summary_dataframe, performance_monitor

__version__ = "2.0.0"
__author__ = "Technical Analysis Team"

__all__ = [
    "config",
    "setup_logging",
    "get_nse_stock_symbols",
    "filter_and_fetch_stocks_efficiently",
    "fetch_complete_stock_data",
    "fetch_multiple_stocks_complete_data",
    "analyze_stock_with_talib",
    "send_email_report",
    "create_csv_report",
    "create_summary_dataframe",
    "performance_monitor",
]
