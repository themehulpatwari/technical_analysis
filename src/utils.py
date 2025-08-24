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


def log_memory_usage():
    """Log current memory usage if psutil is available"""
    try:
        import psutil
        import os
        
        process = psutil.Process(os.getpid())
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / 1024 / 1024
        logger.info(f"Current memory usage: {memory_mb:.1f} MB")
    except ImportError:
        logger.debug("psutil not available, skipping memory monitoring")
    except Exception as e:
        logger.debug(f"Error getting memory usage: {str(e)}")


def log_performance_summary(start_time: float, total_stocks: int, successful_stocks: int, stocks_with_signals: int):
    """
    Log performance summary
    
    Args:
        start_time: Start time of the analysis
        total_stocks: Total number of stocks processed
        successful_stocks: Number of successfully analyzed stocks
        stocks_with_signals: Number of stocks with trading signals
    """
    end_time = time.time()
    duration = end_time - start_time
    
    logger.info("=" * 60)
    logger.info("PERFORMANCE SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Total execution time: {duration:.2f} seconds")
    logger.info(f"Total stocks processed: {total_stocks}")
    logger.info(f"Successfully analyzed: {successful_stocks}")
    logger.info(f"Stocks with signals: {stocks_with_signals}")
    
    if duration > 0:
        stocks_per_second = successful_stocks / duration
        logger.info(f"Analysis rate: {stocks_per_second:.2f} stocks/second")
    
    if total_stocks > 0:
        success_rate = (successful_stocks / total_stocks) * 100
        signal_rate = (stocks_with_signals / successful_stocks) * 100 if successful_stocks > 0 else 0
        logger.info(f"Success rate: {success_rate:.1f}%")
        logger.info(f"Signal detection rate: {signal_rate:.1f}%")
    
    log_memory_usage()
    logger.info("=" * 60)


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


def display_results(results: List[Dict[str, Any]], companies_with_signals: List[Dict[str, Any]]) -> None:
    """
    Display analysis results in a formatted manner
    
    Args:
        results: All analysis results
        companies_with_signals: Results with trading signals
    """
    try:
        logger.info("=" * 60)
        logger.info("RSI & MACD ANALYSIS COMPLETE")
        logger.info("=" * 60)
        
        # Display summary
        total_analyzed = len(results)
        total_with_signals = len(companies_with_signals)
        
        logger.info(f"Total companies analyzed: {total_analyzed}")
        logger.info(f"Companies with RSI/MACD signals: {total_with_signals}")
        
        if total_analyzed > 0:
            success_rate = (total_with_signals / total_analyzed) * 100
            logger.info(f"Signal detection rate: {success_rate:.1f}%")
        
        # Display companies with signals
        if companies_with_signals:
            logger.info("=" * 80)
            logger.info("COMPANIES WITH RSI/MACD SIGNALS (TA-Lib Analysis):")
            logger.info("=" * 80)
            
            for company in companies_with_signals:
                try:
                    symbol = company.get('symbol', 'N/A')
                    company_name = company.get('company_name', 'N/A')
                    current_price = company.get('current_price', 0)
                    market_cap_cr = company.get('market_cap_cr', 0)
                    daily_volume_cr = company.get('daily_volume_cr', 0)
                    rsi = company.get('rsi')
                    macd = company.get('macd')
                    macd_signal = company.get('macd_signal')
                    signals = company.get('signals', [])
                    
                    logger.info(f"{symbol} - {company_name}")
                    logger.info(f"   Current Price: ₹{current_price:.2f}" if current_price > 0 else "   Current Price: N/A")
                    logger.info(f"   Market Cap: ₹{market_cap_cr:.1f} Cr" if market_cap_cr > 0 else "   Market Cap: N/A")
                    logger.info(f"   Daily Volume: ₹{daily_volume_cr:.1f} Cr" if daily_volume_cr > 0 else "   Daily Volume: N/A")
                    logger.info(f"   RSI: {rsi:.2f}" if rsi is not None else "   RSI: N/A")
                    logger.info(f"   MACD: {macd:.4f}" if macd is not None else "   MACD: N/A")
                    logger.info(f"   MACD Signal: {macd_signal:.4f}" if macd_signal is not None else "   MACD Signal: N/A")
                    logger.info("   Technical Signals:")
                    for signal in signals:
                        logger.info(f"   • {signal}")
                except Exception as e:
                    logger.error(f"Error displaying company result: {e}")
                    continue
        else:
            logger.info("No companies showing RSI oversold/overbought or MACD crossover signals.")
        
        # Create and display summary table
        summary_df = create_summary_dataframe(results)
        if not summary_df.empty:
            logger.info("=" * 100)
            logger.info("SUMMARY TABLE (RSI & MACD Only):")
            logger.info("=" * 100)
            logger.info(summary_df.to_string(index=False))
        else:
            logger.warning("Could not create summary table.")
            
    except Exception as e:
        logger.error(f"Error displaying results: {e}")
