"""
Utility functions for input validation, result processing, display, and performance monitoring.
"""

import logging
import time
from typing import List, Dict, Any
from functools import wraps
import pandas as pd


logger = logging.getLogger(__name__)


def performance_monitor(func):
    """
    Decorator to monitor function performance
    
    Args:
        func: Function to monitor
    
    Returns:
        Wrapped function with performance logging
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        logger.info(f"Starting {func.__name__}...")
        
        try:
            result = func(*args, **kwargs)
            end_time = time.time()
            duration = end_time - start_time
            logger.info(f"Completed {func.__name__} in {duration:.2f} seconds")
            return result
        except Exception as e:
            end_time = time.time()
            duration = end_time - start_time
            logger.error(f"Failed {func.__name__} after {duration:.2f} seconds: {str(e)}")
            raise
    
    return wrapper


def create_summary_dataframe(results: List[Dict[str, Any]]) -> pd.DataFrame:
    """
    Create summary DataFrame from analysis results
    
    Args:
        results: List of analysis results
    
    Returns:
        pd.DataFrame: Summary DataFrame
    """
    if not results:
        logger.warning("No results to create summary DataFrame")
        return pd.DataFrame()
    
    summary_data = []
    for result in results:
        try:
            # Safely extract values with defaults
            symbol = result.get('symbol', 'N/A')
            company_name = result.get('company_name', 'N/A')
            current_price = result.get('current_price', 0)
            market_cap_cr = result.get('market_cap_cr', 0)
            daily_volume_cr = result.get('daily_volume_cr', 0)
            rsi = result.get('rsi')
            macd = result.get('macd')
            macd_signal = result.get('macd_signal')
            signals = result.get('signals', [])
            
            summary_data.append({
                'Symbol': symbol,
                'Company': company_name,
                'Price': f"₹{current_price:.2f}" if current_price > 0 else "N/A",
                'Market_Cap_Cr': f"₹{market_cap_cr:.1f}" if market_cap_cr > 0 else "N/A",
                'Daily_Vol_Cr': f"₹{daily_volume_cr:.1f}" if daily_volume_cr > 0 else "N/A",
                'RSI': f"{rsi:.2f}" if rsi is not None else "N/A",
                'MACD': f"{macd:.4f}" if macd is not None else "N/A",
                'MACD_Signal': f"{macd_signal:.4f}" if macd_signal is not None else "N/A",
                'Signals': len(signals),
                'Signal_Details': '; '.join(signals) if signals else 'None'
            })
        except Exception as e:
            logger.error(f"Error processing result for summary: {e}")
            continue
    
    return pd.DataFrame(summary_data)
