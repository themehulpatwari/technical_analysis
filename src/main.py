"""
NSE Technical Analysis Email Reporter
Analyzes NSE stocks for RSI and MACD signals and sends comprehensive reports via email.
"""

import sys
import logging
import time
from datetime import datetime
from typing import List, Dict, Any, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading

# Import from our modules
try:
    # Try relative imports (when run as module)
    from .config import setup_logging, config
    from .data_fetcher import fetch_stock_data_with_retry, fetch_multiple_stocks_data, get_nse_stock_symbols, filter_stocks_by_criteria
    from .technical_indicators import analyze_stock_with_talib
    from .email_sender import send_email_report, test_email_configuration
    from .utils import performance_monitor, log_performance_summary
except ImportError:
    # Fall back to absolute imports (when run directly)
    from config import setup_logging, config
    from data_fetcher import fetch_stock_data_with_retry, fetch_multiple_stocks_data, get_nse_stock_symbols, filter_stocks_by_criteria
    from technical_indicators import analyze_stock_with_talib
    from email_sender import send_email_report, test_email_configuration
    from utils import performance_monitor, log_performance_summary

# Setup logging
logger = setup_logging()


@performance_monitor
def run_analysis_and_send_report() -> bool:
    """
    Run complete NSE technical analysis and send email report
    
    Returns:
        bool: True if analysis and email sent successfully, False otherwise
    """
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
        symbols, data_source = get_nse_stock_symbols(100)
        
        if not symbols:
            logger.error("No valid stock symbols found")
            return False
        
        logger.info(f"Found {len(symbols)} NSE symbols from source: {data_source}")
        
        # Filter stocks by market cap and daily volume criteria
        logger.info(f"Filtering stocks by market cap (≥₹{config.MIN_MARKET_CAP_CR} Cr) and daily volume (≥₹{config.MIN_DAILY_VOLUME_CR} Cr)...")
        filtered_symbols, stock_info_list = filter_stocks_by_criteria(
            symbols, 
            min_market_cap_cr=config.MIN_MARKET_CAP_CR, 
            min_daily_volume_cr=config.MIN_DAILY_VOLUME_CR
        )
        
        if not filtered_symbols:
            logger.error("No stocks passed the filtering criteria")
            return False
        
        logger.info(f"{len(filtered_symbols)} stocks passed filtering out of {len(symbols)} total")
        
        # Store results
        companies_with_signals = []
        failed_symbols = []
        total_analyzed = 0
        
        logger.info(f"Starting concurrent analysis of {len(filtered_symbols)} filtered NSE companies")
        
        # Use threading for concurrent stock analysis
        max_workers = config.MAX_ANALYSIS_THREADS  # Use config value - analysis is CPU intensive
        processed_count = 0
        lock = threading.Lock()
        
        def analyze_single_stock(symbol: str, stock_info: Dict[str, Any]) -> Optional[Dict[str, Any]]:
            """Analyze a single stock with pre-fetched stock info"""
            try:
                # Fetch stock data
                stock_data = fetch_stock_data_with_retry(symbol)
                
                if stock_data is not None:
                    # Analyze stock using TA-Lib (RSI & MACD only)
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
                else:
                    logger.warning(f"Data fetch failed for {symbol}")
                    return None
                    
            except Exception as e:
                logger.error(f"Unexpected error processing {symbol}: {str(e)}")
                return None
        
        # Create symbol-to-info mapping for easy lookup
        stock_info_map = {info['symbol']: info for info in stock_info_list}
        
        logger.info(f"Using {max_workers} threads for concurrent stock analysis")
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all analysis tasks
            future_to_symbol = {}
            for symbol in filtered_symbols:
                stock_info = stock_info_map.get(symbol, {})
                future = executor.submit(analyze_single_stock, symbol, stock_info)
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
                        else:
                            failed_symbols.append(symbol)
                            
                except Exception as e:
                    logger.error(f"Error processing analysis result for {symbol}: {str(e)}")
                    with lock:
                        failed_symbols.append(symbol)
        
        # Log summary statistics
        logger.info(f"Analysis complete: {total_analyzed} successful, {len(failed_symbols)} failed")
        if failed_symbols:
            logger.warning(f"Failed symbols: {', '.join(failed_symbols[:10])}" + ("..." if len(failed_symbols) > 10 else ""))
        
        logger.info(f"Found {len(companies_with_signals)} companies with trading signals")
        
        # Log performance summary
        analysis_end_time = time.time()
        log_performance_summary(
            start_time=0,  # Will be set properly in main
            total_stocks=len(filtered_symbols),
            successful_stocks=total_analyzed,
            stocks_with_signals=len(companies_with_signals)
        )
        
        # Send email report
        logger.info("Sending email report...")
        email_success = send_email_report(companies_with_signals, data_source, total_analyzed)
        
        if email_success:
            logger.info("Email report sent successfully")
            return True
        else:
            logger.error("Failed to send email report")
            return False
        
    except KeyboardInterrupt:
        logger.info("Analysis interrupted by user")
        return False
    except Exception as e:
        logger.error(f"Unexpected error in analysis: {str(e)}")
        return False


if __name__ == "__main__":
    try:
        logger.info("NSE Technical Analysis Email Reporter started")
        
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
        logger.info(f"Analysis started at {start_time}")
        
        success = run_analysis_and_send_report()
        
        end_time = datetime.now()
        duration = end_time - start_time
        logger.info(f"Analysis completed at {end_time}, duration: {duration}")
        
        if success:
            logger.info(f"Analysis completed successfully in {duration.total_seconds():.1f} seconds")
            logger.info("Email report sent to configured recipients")
            logger.info("Application completed successfully")
        else:
            logger.error("Analysis or email sending failed")
            logger.error("Application completed with errors")
            sys.exit(1)
        
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Fatal error in application: {str(e)}")
        sys.exit(1)
