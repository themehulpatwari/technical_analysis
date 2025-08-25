"""
NSE Technical Analysis Email Reporter
Analyzes NSE stocks for RSI and MACD signals and sends comprehensive reports via email.
"""

import sys
import logging
import time
import os
import pandas as pd
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Import from our modules
try:
    from .data_fetcher import get_nse_stock_symbols, filter_and_fetch_stocks_efficiently
    from .technical_indicators import analyze_stock_with_talib
    from .email_sender import send_email_report, test_email_configuration, send_data_source_error_email, send_general_error_email, send_report_failure_email
    from .config import config, setup_logging, cleanup_old_logs
    from .utils import performance_monitor
except ImportError:
    # Fallback for direct execution
    from data_fetcher import get_nse_stock_symbols, filter_and_fetch_stocks_efficiently
    from technical_indicators import analyze_stock_with_talib
    from email_sender import send_email_report, test_email_configuration, send_data_source_error_email, send_general_error_email, send_report_failure_email
    from config import config, setup_logging, cleanup_old_logs
    from utils import performance_monitor

# Setup logging
logger = setup_logging()


@performance_monitor
def run_analysis_and_send_report() -> bool:
    """
    Run complete NSE technical analysis and send email report
    
    Returns:
        bool: True if analysis and email sent successfully, False otherwise
    """
    start_time = time.time()
    
    try:
        logger.info("Starting NSE Stock Market Analysis for Email Report")
        
        # Check if required libraries are available
        try:
            import talib
            logger.info("TA-Lib is available")
        except ImportError:
            logger.error("TA-Lib is not installed or not available. Please install it first: pip install TA-Lib")
            return False
        
        # Get NSE stock symbols dynamically with fallback and data source tracking
        symbols, data_source = get_nse_stock_symbols()
        
        if not symbols:
            logger.error("No valid stock symbols found")
            send_general_error_email("No valid stock symbols found")
            return False
        
        logger.info(f"Found {len(symbols)} NSE symbols from source: {data_source}")
        
        # Send alert if data source is not live NSE
        if data_source != "live_website":
            logger.warning(f"Data source is not live NSE: {data_source}")
            send_data_source_error_email(data_source)
        
        # SUPER-EFFICIENT APPROACH: Filter stocks and fetch all data in one optimized batch
        # This eliminates redundant API calls by fetching both stock info and historical data once per symbol
        logger.info(f"Using super-efficient filtering and data fetching approach...")
        filtered_symbols, historical_data_dict, stock_info_list = filter_and_fetch_stocks_efficiently(
            symbols, 
            min_market_cap_cr=config.MIN_MARKET_CAP_CR, 
            min_daily_volume_cr=config.MIN_DAILY_VOLUME_CR
        )
        
        if not filtered_symbols:
            logger.error("No stocks passed the filtering criteria")
            send_general_error_email("No stocks passed the filtering criteria")
            return False
        
        logger.info(f"{len(filtered_symbols)} stocks passed filtering with complete data out of {len(symbols)} total")
        logger.info(f"Performance benefit: Reduced API calls from {len(symbols) * 2} to {len(symbols)} (50% reduction)")
        
        # Store results
        companies_with_signals = []
        total_analyzed = 0
        
        logger.info(f"Starting concurrent analysis of {len(filtered_symbols)} filtered NSE companies")
        
        # Use threading for concurrent stock analysis
        max_workers = config.MAX_ANALYSIS_THREADS  # Use config value - analysis is CPU intensive
        processed_count = 0
        lock = threading.Lock()
        
        def analyze_single_stock_optimized(symbol: str, stock_data: pd.DataFrame, stock_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Analyze a single stock with pre-fetched data and info - NO ADDITIONAL API CALLS NEEDED"""
            try:
                # Analyze stock using TA-Lib (RSI & MACD only) - data already available
                analysis = analyze_stock_with_talib(symbol, stock_data)
                
                if analysis is not None:
                    # Add market cap and volume info to analysis result
                    if stock_info:
                        analysis['market_cap_cr'] = stock_info.get('market_cap', 0) / 10**7
                        analysis['daily_volume_cr'] = stock_info.get('daily_volume_rs', 0) / 10**7
                        analysis['company_name'] = stock_info.get('company_name', symbol.replace('.NS', ''))
                    
                    return analysis
                else:
                    logger.warning(f"Analysis failed for {symbol}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error processing {symbol}: {str(e)}")
                return None
        
        # Create symbol-to-info mapping for easy lookup
        stock_info_map = {info['symbol']: info for info in stock_info_list}
        
        logger.info(f"Using {max_workers} threads for concurrent stock analysis (with pre-fetched data)")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all analysis tasks with pre-fetched data
            future_to_symbol = {}
            for symbol in filtered_symbols:
                stock_data = historical_data_dict[symbol]  # Data already fetched!
                stock_info = stock_info_map.get(symbol, {})
                future = executor.submit(analyze_single_stock_optimized, symbol, stock_data, stock_info)
                future_to_symbol[future] = symbol
            
            # Process completed tasks
            for future in as_completed(future_to_symbol):
                symbol = future_to_symbol[future]
                
                with lock:
                    processed_count += 1
                    if processed_count % 10 == 0 or processed_count == len(filtered_symbols):
                        logger.info(f"Analysis progress: {processed_count}/{len(filtered_symbols)} completed")
                
                try:
                    analysis = future.result()
                    
                    with lock:
                        if analysis is not None:
                            total_analyzed += 1
                            
                            # Check if stock has signals
                            if analysis.get('signals', []):
                                companies_with_signals.append(analysis)
                                logger.info(f"Found signals for {symbol}: {len(analysis['signals'])} signals")
                        
                except Exception as e:
                    logger.error(f"Error processing analysis result for {symbol}: {str(e)}")
        
        # Log summary statistics
        logger.info(f"Analysis complete: {total_analyzed} successful, {len(filtered_symbols) - total_analyzed} failed")
        
        logger.info(f"Found {len(companies_with_signals)} companies with trading signals")
        
        # Log basic performance summary
        end_time = time.time()
        duration = end_time - start_time if 'start_time' in locals() else 0
        logger.info("=" * 60)
        logger.info("ANALYSIS SUMMARY")
        logger.info("=" * 60)
        logger.info(f"Total execution time: {duration:.2f} seconds")
        logger.info(f"Total stocks processed: {len(filtered_symbols)}")
        logger.info(f"Successfully analyzed: {total_analyzed}")
        logger.info(f"Stocks with signals: {len(companies_with_signals)}")
        if len(filtered_symbols) > 0:
            success_rate = (total_analyzed / len(filtered_symbols)) * 100
            logger.info(f"Success rate: {success_rate:.1f}%")
        if total_analyzed > 0:
            signal_rate = (len(companies_with_signals) / total_analyzed) * 100
            logger.info(f"Signal detection rate: {signal_rate:.1f}%")
        logger.info("=" * 60)
        
        # Send email report
        logger.info("Sending email report...")
        email_success = send_email_report(companies_with_signals, data_source, total_analyzed)
        
        if email_success:
            logger.info("Email report sent successfully")
            return True
        else:
            logger.error("Failed to send email report")
            send_report_failure_email()
            return False
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {str(e)}")
        send_general_error_email(f"Unexpected error in analysis: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        logger.info("NSE Technical Analysis Email Reporter started")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Current working directory: {os.getcwd()}")
        
        # Log configuration details
        logger.info(f"Max analysis threads: {config.MAX_ANALYSIS_THREADS}")
        logger.info(f"Max fetch threads: {config.MAX_FETCH_THREADS}")
        logger.info(f"Min market cap: ₹{config.MIN_MARKET_CAP_CR} Cr")
        logger.info(f"Min daily volume: ₹{config.MIN_DAILY_VOLUME_CR} Cr")
        
        # Optional: Test email configuration first
        if len(sys.argv) > 1 and sys.argv[1] == "--test-email":
            logger.info("Testing email configuration...")
            if test_email_configuration():
                logger.info("Email configuration test successful")
            else:
                logger.error("Email configuration test failed. Check your config.py settings.")
            sys.exit(0)
        
        # Run analysis and send report
        start_time = datetime.now()
        logger.info(f"Analysis started at {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        success = run_analysis_and_send_report()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Analysis completed at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        logger.info(f"Total execution time: {duration}")
        
        if success:
            logger.info(f"✓ Analysis completed successfully in {duration.total_seconds():.1f} seconds")
            logger.info("✓ Email report sent to configured recipients")
            logger.info("✓ Application completed successfully")
        else:
            logger.error("✗ Analysis or email sending failed")
            logger.error("✗ Application completed with errors")
        
        # Clean up old log files (older than 10 days)
        logger.info("Cleaning up old log files...")
        cleanup_old_logs(max_days=10)
        logger.info("=" * 80)
        
        if not success:
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user (Ctrl+C)")
        logger.info("=" * 80)
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in application: {str(e)}")
        logger.error("=" * 80)
        sys.exit(1)
