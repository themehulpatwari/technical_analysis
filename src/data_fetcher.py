"""
Data fetching and validation module for stock market data.
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


def fetch_stock_data_with_retry(symbol: str, period: str = None) -> Optional[pd.DataFrame]:
    """
    Fetch stock data with retry mechanism and validation
    
    Args:
        symbol: Stock symbol to fetch
        period: Time period for data (default from config)
    
    Returns:
        pd.DataFrame or None: Stock data if successful, None otherwise
    """
    if period is None:
        period = config.DEFAULT_PERIOD
    
    if not symbol or not isinstance(symbol, str):
        logger.error(f"Invalid symbol provided: {symbol}")
        return None
    
    for attempt in range(config.MAX_RETRIES):
        try:
            logger.debug(f"Fetching data for {symbol} (attempt {attempt + 1}/{config.MAX_RETRIES})")
            
            stock = yf.Ticker(symbol)
            data = stock.history(period=period)
            
            # Add delay between requests to avoid rate limiting
            time.sleep(config.REQUEST_DELAY)
            
            if validate_stock_data(data, symbol):
                logger.debug(f"Successfully fetched and validated data for {symbol}")
                return data
            else:
                logger.warning(f"Data validation failed for {symbol}")
                return None
                
        except Exception as e:
            logger.warning(f"Attempt {attempt + 1} failed for {symbol}: {str(e)}")
            if attempt < config.MAX_RETRIES - 1:
                time.sleep(config.RETRY_DELAY * (attempt + 1))  # Exponential backoff
            else:
                logger.error(f"All retry attempts failed for {symbol}")
    
    return None


def fetch_stock_data(symbol: str, period: str = '6mo') -> Optional[pd.DataFrame]:
    """
    Legacy function wrapper for backward compatibility
    
    Args:
        symbol: Stock symbol to fetch
        period: Time period for data
    
    Returns:
        pd.DataFrame or None: Stock data if successful, None otherwise
    """
    return fetch_stock_data_with_retry(symbol, period)


def fetch_multiple_stocks_data(symbols: List[str], period: str = None) -> Dict[str, Optional[pd.DataFrame]]:
    """
    Fetch stock data for multiple symbols concurrently using threading
    
    Args:
        symbols: List of stock symbols to fetch
        period: Time period for data (default from config)
    
    Returns:
        Dict[str, Optional[pd.DataFrame]]: Dictionary mapping symbols to their data
    """
    if period is None:
        period = config.DEFAULT_PERIOD
    
    logger.info(f"Fetching data for {len(symbols)} stocks concurrently")
    
    # Use conservative thread count for cloud servers
    max_workers = config.MAX_FETCH_THREADS  # Use config value
    results = {}
    processed_count = 0
    lock = threading.Lock()
    
    def fetch_single_stock(symbol: str) -> Tuple[str, Optional[pd.DataFrame]]:
        """Fetch data for a single stock"""
        try:
            data = fetch_stock_data_with_retry(symbol, period)
            return symbol, data
        except Exception as e:
            logger.error(f"Error fetching data for {symbol}: {str(e)}")
            return symbol, None
    
    logger.info(f"Using {max_workers} threads for concurrent data fetching")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {executor.submit(fetch_single_stock, symbol): symbol for symbol in symbols}
        
        for future in as_completed(future_to_symbol):
            with lock:
                processed_count += 1
                if processed_count % 10 == 0 or processed_count == len(symbols):
                    logger.info(f"Data fetch progress: {processed_count}/{len(symbols)} completed")
            
            try:
                symbol, data = future.result()
                results[symbol] = data
            except Exception as e:
                symbol = future_to_symbol[future]
                logger.error(f"Error processing future for {symbol}: {str(e)}")
                results[symbol] = None
    
    successful_count = sum(1 for data in results.values() if data is not None)
    logger.info(f"Data fetching complete: {successful_count}/{len(symbols)} successful")
    
    return results


def get_stock_info(symbol: str) -> Optional[Dict[str, Any]]:
    """
    Fetch basic stock information including market cap and average volume
    
    Args:
        symbol: Stock symbol to fetch info for
    
    Returns:
        Dict containing stock info or None if failed
    """
    try:
        logger.debug(f"Fetching info for {symbol}")
        stock = yf.Ticker(symbol)
        info = stock.info
        
        # Add delay to avoid rate limiting
        time.sleep(config.REQUEST_DELAY)
        
        if not info:
            logger.warning(f"No info available for {symbol}")
            return None
        
        # Extract relevant information
        market_cap = info.get('marketCap', 0)
        avg_volume = info.get('averageVolume', 0)
        current_price = info.get('currentPrice', info.get('regularMarketPrice', 0))
        
        # Calculate daily volume in Rs (approximate)
        daily_volume_rs = avg_volume * current_price if avg_volume and current_price else 0
        
        return {
            'symbol': symbol,
            'market_cap': market_cap,
            'avg_volume': avg_volume,
            'current_price': current_price,
            'daily_volume_rs': daily_volume_rs,
            'company_name': info.get('longName', symbol.replace('.NS', ''))
        }
        
    except Exception as e:
        logger.warning(f"Failed to fetch info for {symbol}: {str(e)}")
        return None


def filter_stocks_by_criteria(symbols: List[str], min_market_cap_cr: float = 500, min_daily_volume_cr: float = 1) -> Tuple[List[str], List[Dict[str, Any]]]:
    """
    Filter stocks based on market cap and daily volume criteria using threading
    
    Args:
        symbols: List of stock symbols to filter
        min_market_cap_cr: Minimum market cap in crores (default: 500)
        min_daily_volume_cr: Minimum daily volume in crores Rs (default: 1)
    
    Returns:
        Tuple of (filtered_symbols, stock_info_list)
    """
    logger.info(f"Filtering {len(symbols)} stocks by market cap (≥₹{min_market_cap_cr} Cr) and daily volume (≥₹{min_daily_volume_cr} Cr)")
    
    filtered_symbols = []
    stock_info_list = []
    failed_count = 0
    
    min_market_cap = min_market_cap_cr * 10**7  # Convert crores to actual value
    min_daily_volume = min_daily_volume_cr * 10**7  # Convert crores to actual value
    
    # Use threading for concurrent stock info fetching
    max_workers = config.MAX_FILTER_THREADS  # Use config value
    processed_count = 0
    lock = threading.Lock()
    
    def process_symbol(symbol: str) -> Optional[Dict[str, Any]]:
        """Process a single symbol and return stock info if it passes criteria"""
        stock_info = get_stock_info(symbol)
        
        if stock_info:
            market_cap = stock_info.get('market_cap', 0)
            daily_volume_rs = stock_info.get('daily_volume_rs', 0)
            
            # Apply filters
            if market_cap >= min_market_cap and daily_volume_rs >= min_daily_volume:
                logger.info(f"✓ {symbol}: Market Cap ₹{market_cap/10**7:.1f} Cr, Daily Volume ₹{daily_volume_rs/10**7:.1f} Cr")
                return stock_info
            else:
                logger.debug(f"✗ {symbol}: Market Cap ₹{market_cap/10**7:.1f} Cr, Daily Volume ₹{daily_volume_rs/10**7:.1f} Cr (filtered out)")
        else:
            logger.warning(f"✗ {symbol}: Failed to fetch info")
        
        return None
    
    logger.info(f"Using {max_workers} threads for concurrent stock filtering")
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_symbol = {executor.submit(process_symbol, symbol): symbol for symbol in symbols}
        
        for future in as_completed(future_to_symbol):
            symbol = future_to_symbol[future]
            
            with lock:
                processed_count += 1
                if processed_count % 20 == 0 or processed_count == len(symbols):
                    logger.info(f"Progress: {processed_count}/{len(symbols)} symbols checked, {len(filtered_symbols)} passed criteria")
            
            try:
                result = future.result()
                if result:
                    with lock:
                        filtered_symbols.append(symbol)
                        stock_info_list.append(result)
                else:
                    with lock:
                        failed_count += 1
            except Exception as e:
                logger.error(f"Error processing {symbol}: {str(e)}")
                with lock:
                    failed_count += 1
    
    logger.info(f"Filtering complete: {len(filtered_symbols)} stocks passed criteria, {failed_count} failed to fetch info")
    
    return filtered_symbols, stock_info_list
