"""
Data fetching and validation module for stock market data.
Optimized to eliminate redundant API calls to yfinance.
"""

import time
import logging
import sys
import os
from typing import Optional, List, Dict, Any, Tuple
from io import StringIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
import requests
import yfinance as yf
import pandas as pd
try:
    from .config import config
except ImportError:
    from config import config

# Add the project root to the path so we can import from data folder
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

logger = logging.getLogger(__name__)


# ==============================================================================
# NSE SYMBOL FETCHING
# ==============================================================================


def fetch_nse_equity_list() -> Optional[List[str]]:
    """
    Fetch the NSE equity list CSV file and return the first column (symbol names).
    
    Returns:
        List[str] or None: List of equity symbols from the first column, or None if failed
    """
    url = "https://nsearchives.nseindia.com/content/equities/EQUITY_L.csv"
    
    try:
        logger.info(f"Fetching NSE equity list from: {url}")
        
        # Set headers to mimic a browser request
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }
        
        # Make the request
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        # Read the CSV content
        csv_content = StringIO(response.text)
        df = pd.read_csv(csv_content)
        
        # Get the first column
        if df.empty:
            logger.warning("CSV file is empty")
            return None
        
        first_column = df.iloc[:, 0].tolist()
        
        # Remove any NaN values and convert to strings
        first_column = [str(symbol).strip() for symbol in first_column if pd.notna(symbol)]
        
        logger.info(f"Successfully fetched {len(first_column)} equity symbols")
        logger.debug(f"First 10 symbols: {first_column[:10]}")
        
        return first_column
        
    except requests.RequestException as e:
        logger.error(f"Request failed: {str(e)}")
        return None
    except pd.errors.EmptyDataError:
        logger.error("CSV file is empty or invalid")
        return None
    except Exception as e:
        logger.error(f"Unexpected error while fetching NSE equity list: {str(e)}")
        return None


def get_fallback_nse_symbols() -> List[str]:
    """
    Get NSE symbols from the local fallback file
    
    Returns:
        List[str]: List of NSE stock symbols from local file
    """
    try:
        from data.nse_symbols_list import nse_equity_symbols
        logger.info(f"Loaded {len(nse_equity_symbols)} symbols from fallback file")
        return nse_equity_symbols
    except ImportError as e:
        logger.error(f"Failed to import fallback symbols: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error loading fallback symbols: {str(e)}")
        return []


def get_nse_stock_symbols(symbol_limit: Optional[int] = None) -> Tuple[List[str], str]:
    """
    Get NSE stock symbols dynamically from the web with fallback to local data.
    Symbols are converted to Yahoo Finance format (.NS suffix).
    
    Args:
        symbol_limit: Optional limit on number of symbols to return (overrides config)
    
    Returns:
        Tuple[List[str], str]: List of NSE stock symbols in Yahoo Finance format and data source flag
        Data source flags:
        - "live_website": Data fetched from live NSE website
        - "first_fallback": Data from local fallback file  
        - "second_fallback": Data from minimal popular stocks list
    """
    logger.info("Starting dynamic NSE symbol fetching...")
    
    # Check if web fetch is enabled
    if not config.USE_WEB_FETCH:
        logger.info("Web fetch disabled in config, using fallback only")
        symbols, source = _get_fallback_symbols(symbol_limit)
        return symbols, source
    
    # First try to fetch from web
    try:
        logger.info("Attempting to fetch NSE symbols from web...")
        
        web_symbols = fetch_nse_equity_list()
        
        if web_symbols and len(web_symbols) > 0:
            logger.info(f"Successfully fetched {len(web_symbols)} symbols from web")
            
            # Convert to Yahoo Finance format by adding .NS suffix
            yahoo_symbols = [f"{symbol}.NS" for symbol in web_symbols if symbol and isinstance(symbol, str)]
            
            # Apply limit if specified
            if symbol_limit and symbol_limit > 0:
                yahoo_symbols = yahoo_symbols[:symbol_limit]
                logger.info(f"Limited symbols to {len(yahoo_symbols)} as per configuration")
            
            logger.info(f"Returning {len(yahoo_symbols)} symbols from web source")
            return yahoo_symbols, "live_website"
        else:
            logger.warning("Web fetch returned empty or invalid symbol list")
            
    except Exception as e:
        logger.warning(f"Web fetch failed: {str(e)}")
    
    # Fallback to local symbols
    symbols, source = _get_fallback_symbols(symbol_limit)
    return symbols, source


def _get_fallback_symbols(symbol_limit: Optional[int]) -> Tuple[List[str], str]:
    """
    Internal helper to get fallback symbols with limit applied
    
    Args:
        symbol_limit: Optional limit on number of symbols
        
    Returns:
        Tuple[List[str], str]: List of symbols from fallback sources and data source flag
    """
    logger.info("Falling back to local symbol file...")
    
    try:
        fallback_symbols = get_fallback_nse_symbols()
        
        if fallback_symbols and len(fallback_symbols) > 0:
            # Convert to Yahoo Finance format by adding .NS suffix
            yahoo_symbols = [f"{symbol}.NS" for symbol in fallback_symbols if symbol and isinstance(symbol, str)]
            
            # Apply limit if specified
            if symbol_limit and symbol_limit > 0:
                yahoo_symbols = yahoo_symbols[:symbol_limit]
                logger.info(f"Limited fallback symbols to {len(yahoo_symbols)} as per configuration")
            
            logger.info(f"Using {len(yahoo_symbols)} symbols from fallback file")
            return yahoo_symbols, "first_fallback"
        else:
            logger.error("Fallback symbols are empty or invalid")
            
    except Exception as e:
        logger.error(f"Fallback failed: {str(e)}")
    
    # Last resort: return a minimal set of popular stocks
    logger.error("Both web and fallback failed, using minimal popular stock list")
    popular_stocks = [
        'RELIANCE.NS', 'TCS.NS', 'HDFCBANK.NS', 'INFY.NS', 'HINDUNILVR.NS',
        'ICICIBANK.NS', 'KOTAKBANK.NS', 'BHARTIARTL.NS', 'SBIN.NS', 'BAJFINANCE.NS'
    ]
    
    if symbol_limit and symbol_limit > 0:
        popular_stocks = popular_stocks[:symbol_limit]
    
    logger.warning(f"Using minimal popular stock list with {len(popular_stocks)} symbols")
    return popular_stocks, "second_fallback"


def validate_stock_data(data: pd.DataFrame, symbol: str) -> bool:
    """
    Validate fetched stock data for quality and completeness
    
    Args:
        data: Stock data DataFrame
        symbol: Stock symbol for logging
    
    Returns:
        bool: True if data is valid, False otherwise
    """
    if data is None or data.empty:
        logger.warning(f"No data available for {symbol}")
        return False
    
    # Check required columns
    required_columns = ['Open', 'High', 'Low', 'Close', 'Volume']
    missing_columns = [col for col in required_columns if col not in data.columns]
    if missing_columns:
        logger.warning(f"Missing columns for {symbol}: {missing_columns}")
        return False
    
    # Check data length
    if len(data) < config.MIN_DATA_POINTS:
        logger.warning(f"Insufficient data for {symbol}: {len(data)} points (min: {config.MIN_DATA_POINTS})")
        return False
    
    # Check for excessive NaN values
    nan_ratio = data['Close'].isna().sum() / len(data)
    if nan_ratio > 0.1:  # More than 10% NaN values
        logger.warning(f"Too many NaN values for {symbol}: {nan_ratio:.2%}")
        return False
    
    # Check for zero or negative prices
    if (data['Close'] <= 0).any():
        logger.warning(f"Invalid price data for {symbol}: found zero or negative prices")
        return False
    
    # Check for unrealistic price changes (more than 50% in a day)
    price_changes = data['Close'].pct_change().abs()
    if (price_changes > 0.5).any():
        logger.warning(f"Suspicious price changes detected for {symbol}")
    
    return True


# ==============================================================================
# OPTIMIZED UNIFIED DATA FETCHING - CORE FUNCTIONS
# ==============================================================================


def fetch_complete_stock_data(symbol: str, period: str = None, include_info: bool = True) -> Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]:
    """
    Fetch both historical data and stock info in a single yfinance call with retry mechanism
    
    Args:
        symbol: Stock symbol to fetch
        period: Time period for data (default from config)
        include_info: Whether to fetch stock info (default True)
    
    Returns:
        Tuple[pd.DataFrame or None, Dict or None]: Historical data and stock info if successful
    """
    if period is None:
        period = config.DEFAULT_PERIOD
    
    if not symbol or not isinstance(symbol, str):
        logger.error(f"Invalid symbol provided: {symbol}")
        return None, None
    
    for attempt in range(config.MAX_RETRIES):
        try:
            logger.debug(f"Fetching complete data for {symbol} (attempt {attempt + 1}/{config.MAX_RETRIES})")
            
            # Single yfinance Ticker object - fetch everything at once
            stock = yf.Ticker(symbol)
            
            # Fetch historical data
            data = stock.history(period=period)
            
            # Fetch stock info if requested
            stock_info = None
            if include_info:
                try:
                    info = stock.info
                    if info:
                        # Extract relevant information
                        market_cap = info.get('marketCap', 0)
                        avg_volume = info.get('averageVolume', 0)
                        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
                        
                        # Calculate daily volume in Rs (approximate)
                        daily_volume_rs = avg_volume * current_price if avg_volume and current_price else 0
                        
                        stock_info = {
                            'symbol': symbol,
                            'market_cap': market_cap,
                            'avg_volume': avg_volume,
                            'current_price': current_price,
                            'daily_volume_rs': daily_volume_rs,
                            'company_name': info.get('longName', symbol.replace('.NS', ''))
                        }
                except Exception as info_error:
                    logger.warning(f"Failed to fetch info for {symbol}: {str(info_error)}")
                    stock_info = None
            
            # Add delay between requests to avoid rate limiting
            time.sleep(config.REQUEST_DELAY)
            
            # Validate historical data
            if validate_stock_data(data, symbol):
                logger.debug(f"Successfully fetched and validated complete data for {symbol}")
                return data, stock_info
            else:
                logger.warning(f"Data validation failed for {symbol}")
                return None, stock_info
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"All retry attempts failed for {symbol}")
    
    return None, None


# ==============================================================================
# SIMPLE WRAPPER FUNCTIONS (for backwards compatibility if needed)
# ==============================================================================


def fetch_stock_data_with_retry(symbol: str, period: str = None) -> Optional[pd.DataFrame]:
    """
    Fetch stock data with retry mechanism and validation
    
    Args:
        symbol: Stock symbol to fetch
        period: Time period for data (default from config)
    
    Returns:
        pd.DataFrame or None: Stock data if successful, None otherwise
    """
    data, _ = fetch_complete_stock_data(symbol, period, include_info=False)
    return data


def fetch_multiple_stocks_complete_data(symbols: List[str], period: str = None) -> Dict[str, Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]]:
    """
    Fetch both historical data and stock info for multiple symbols concurrently
    This is the most efficient method as it fetches everything in one API call per symbol
    
    Args:
        symbols: List of stock symbols to fetch
        period: Time period for data (default from config)
    
    Returns:
        Dict[str, Tuple[Optional[pd.DataFrame], Optional[Dict]]]: Dictionary mapping symbols to (data, info) tuples
    """
    if period is None:
        period = config.DEFAULT_PERIOD
    
    logger.info(f"Fetching complete data (history + info) for {len(symbols)} stocks concurrently")
    
    # Use conservative thread count for cloud servers
    max_workers = config.MAX_FETCH_THREADS  # Use config value
    results = {}
    processed_count = 0
    lock = threading.Lock()
    
    def fetch_single_stock_complete(symbol: str) -> Tuple[str, Tuple[Optional[pd.DataFrame], Optional[Dict[str, Any]]]]:
        """Fetch complete data for a single stock"""
        try:
            data, info = fetch_complete_stock_data(symbol, period, include_info=True)
            return symbol, (data, info)
        except Exception as e:
            logger.error(f"Error fetching complete data for {symbol}: {str(e)}")
            return symbol, (None, None)
    
    logger.info(f"Using {max_workers} threads for concurrent complete data fetching")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {executor.submit(fetch_single_stock_complete, symbol): symbol for symbol in symbols}
        
        for future in as_completed(future_to_symbol):
            with lock:
                processed_count += 1
                if processed_count % 10 == 0 or processed_count == len(symbols):
                    logger.info(f"Complete data fetch progress: {processed_count}/{len(symbols)} completed")
            
            try:
                symbol, (data, info) = future.result()
                results[symbol] = (data, info)
            except Exception as e:
                symbol = future_to_symbol[future]
                logger.error(f"Error processing future for {symbol}: {str(e)}")
                results[symbol] = (None, None)
    
    successful_data_count = sum(1 for data, _ in results.values() if data is not None)
    successful_info_count = sum(1 for _, info in results.values() if info is not None)
    logger.info(f"Complete data fetching finished: {successful_data_count}/{len(symbols)} historical data successful, {successful_info_count}/{len(symbols)} info successful")
    
    return results


def filter_and_fetch_stocks_efficiently(symbols: List[str], min_market_cap_cr: float = 500, min_daily_volume_cr: float = 1, period: str = None) -> Tuple[List[str], Dict[str, pd.DataFrame], List[Dict[str, Any]]]:
    """
    Super-efficient function that filters stocks and fetches complete data in one go
    This eliminates redundant API calls by fetching everything once per symbol
    
    Args:
        symbols: List of stock symbols to process
        min_market_cap_cr: Minimum market cap in crores (default: 500)
        min_daily_volume_cr: Minimum daily volume in crores Rs (default: 1)
        period: Time period for historical data (default from config)
    
    Returns:
        Tuple of (filtered_symbols, historical_data_dict, stock_info_list)
    """
    if period is None:
        period = config.DEFAULT_PERIOD
        
    logger.info(f"Starting super-efficient filtering and data fetching for {len(symbols)} stocks")
    logger.info(f"Criteria: Market cap ≥₹{min_market_cap_cr} Cr, Daily volume ≥₹{min_daily_volume_cr} Cr")
    
    # Fetch complete data for all symbols in one batch
    complete_data = fetch_multiple_stocks_complete_data(symbols, period)
    
    # Filter based on criteria
    filtered_symbols = []
    historical_data_dict = {}
    stock_info_list = []
    failed_count = 0
    
    min_market_cap = min_market_cap_cr * 10**7  # Convert crores to actual value
    min_daily_volume = min_daily_volume_cr * 10**7  # Convert crores to actual value
    
    for symbol, (data, info) in complete_data.items():
        try:
            if info:
                market_cap = info.get('market_cap', 0)
                daily_volume_rs = info.get('daily_volume_rs', 0)
                
                # Apply filters
                if market_cap >= min_market_cap and daily_volume_rs >= min_daily_volume:
                    if data is not None:  # Only include if we have both valid data and info
                        filtered_symbols.append(symbol)
                        historical_data_dict[symbol] = data
                        stock_info_list.append(info)
                        logger.info(f"✓ {symbol}: Market Cap ₹{market_cap/10**7:.1f} Cr, Daily Volume ₹{daily_volume_rs/10**7:.1f} Cr - INCLUDED")
                    else:
                        logger.warning(f"✗ {symbol}: Passed criteria but missing historical data")
                        failed_count += 1
                else:
                    logger.debug(f"✗ {symbol}: Market Cap ₹{market_cap/10**7:.1f} Cr, Daily Volume ₹{daily_volume_rs/10**7:.1f} Cr (filtered out)")
            else:
                logger.warning(f"✗ {symbol}: Failed to fetch stock info")
                failed_count += 1
        except Exception as e:
            logger.error(f"Error processing {symbol}: {str(e)}")
            failed_count += 1
    
    logger.info(f"Super-efficient filtering complete: {len(filtered_symbols)} stocks passed criteria with complete data, {failed_count} failed")
    logger.info(f"Performance benefit: Single API call per symbol instead of 2+ calls")
    
    return filtered_symbols, historical_data_dict, stock_info_list


def get_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch basic stock information
    
    Args:
        symbol: Stock symbol to fetch info for
    
    Returns:
        Dict containing stock info or None if failed
    """
    _, stock_info = fetch_complete_stock_data(symbol, period='1d', include_info=True)
    return stock_info


# ==============================================================================
# SUPER-EFFICIENT BATCH PROCESSING FUNCTIONS
# ==============================================================================


