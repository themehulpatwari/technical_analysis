"""
Technical indicators calculation and signal generation module.
"""

import logging
from typing import Optional, Dict, List, Any
from concurrent.futures import ThreadPoolExecutor
import numpy as np
import pandas as pd
import talib
try:
    from .config import config
    from .data_fetcher import validate_stock_data
except ImportError:
    from config import config
    from data_fetcher import validate_stock_data


logger = logging.getLogger(__name__)


def calculate_rsi_signals(rsi_value: float) -> List[str]:
    """
    Calculate RSI-based trading signals
    
    Args:
        rsi_value: Current RSI value
    
    Returns:
        List[str]: List of RSI signals
    """
    signals = []
    
    if rsi_value is None or np.isnan(rsi_value):
        return signals
    
    if rsi_value < config.RSI_OVERSOLD:
        signals.append(f"RSI Oversold ({rsi_value:.2f}) - Potential Buy")
    elif rsi_value > config.RSI_OVERBOUGHT:
        signals.append(f"RSI Overbought ({rsi_value:.2f}) - Potential Sell")
    
    return signals


def calculate_macd_signals(macd: np.ndarray, signal: np.ndarray, histogram: np.ndarray) -> List[str]:
    """
    Calculate MACD-based trading signals
    
    Args:
        macd: MACD line values
        signal: Signal line values
        histogram: MACD histogram values
    
    Returns:
        List[str]: List of MACD signals
    """
    signals = []
    
    if len(macd) < 2 or len(signal) < 2 or len(histogram) < 2:
        return signals
    
    latest_macd = macd[-1]
    latest_signal = signal[-1]
    prev_histogram = histogram[-2]
    
    # Check for valid values
    if any(np.isnan([latest_macd, latest_signal, prev_histogram])):
        return signals
    
    # Bullish crossover: MACD crosses above signal line
    if latest_macd > latest_signal and prev_histogram <= 0:
        signals.append("MACD Bullish Crossover - Buy Signal")
    # Bearish crossover: MACD crosses below signal line
    elif latest_macd < latest_signal and prev_histogram >= 0:
        signals.append("MACD Bearish Crossover - Sell Signal")
    
    return signals


def analyze_stock_with_talib(symbol: str, data: pd.DataFrame) -> Optional[Dict[str, Any]]:
    """
    Perform RSI and MACD analysis using TA-Lib with improved error handling
    
    Args:
        symbol: Stock symbol
        data: Stock price data
    
    Returns:
        Dict or None: Analysis results if successful, None otherwise
    """
    try:
        if not validate_stock_data(data, symbol):
            return None
        
        # Convert data to numpy arrays (required by TA-Lib)
        close = data['Close'].values
        
        # Ensure we have enough data points
        if len(close) < config.MIN_DATA_POINTS:
            logger.warning(f"Insufficient data points for {symbol}: {len(close)}")
            return None
        
        # Calculate RSI using TA-Lib
        rsi = talib.RSI(close, timeperiod=config.RSI_PERIOD)
        
        # Calculate MACD using TA-Lib
        macd, macdsignal, macdhist = talib.MACD(
            close, 
            fastperiod=config.MACD_FAST, 
            slowperiod=config.MACD_SLOW, 
            signalperiod=config.MACD_SIGNAL
        )
        
        # Get latest values with proper NaN handling
        latest_rsi = rsi[-1] if len(rsi) > 0 and not np.isnan(rsi[-1]) else None
        latest_macd = macd[-1] if len(macd) > 0 and not np.isnan(macd[-1]) else None
        latest_signal = macdsignal[-1] if len(macdsignal) > 0 and not np.isnan(macdsignal[-1]) else None
        latest_histogram = macdhist[-1] if len(macdhist) > 0 and not np.isnan(macdhist[-1]) else None
        latest_price = close[-1]
        
        # Validate price
        if latest_price <= 0 or np.isnan(latest_price):
            logger.error(f"Invalid latest price for {symbol}: {latest_price}")
            return None
        
        # Generate signals
        rsi_signals = calculate_rsi_signals(latest_rsi)
        macd_signals = calculate_macd_signals(macd, macdsignal, macdhist)
        all_signals = rsi_signals + macd_signals
        
        # Extract company name more safely
        company_name = symbol.replace('.NS', '') if symbol.endswith('.NS') else symbol
        
        result = {
            'symbol': symbol,
            'company_name': company_name,
            'current_price': latest_price,
            'rsi': latest_rsi,
            'macd': latest_macd,
            'macd_signal': latest_signal,
            'macd_histogram': latest_histogram,
            'signals': all_signals,
            'data': data,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'macd_signal': macdsignal,
                'macd_histogram': macdhist
            },
            'data_quality': {
                'data_points': len(close),
                'valid_rsi': latest_rsi is not None,
                'valid_macd': latest_macd is not None and latest_signal is not None
            }
        }
        
        logger.debug(f"Successfully analyzed {symbol}")
        return result
        
    except Exception as e:
        logger.error(f"Error analyzing {symbol} with TA-Lib: {str(e)}")
        return None


def analyze_multiple_stocks(stock_data_map: Dict[str, pd.DataFrame]) -> Dict[str, Optional[Dict[str, Any]]]:
    """
    Analyze multiple stocks concurrently using threading
    
    Args:
        stock_data_map: Dictionary mapping symbols to their stock data
    
    Returns:
        Dict mapping symbols to their analysis results
    """
    logger.info(f"Analyzing {len(stock_data_map)} stocks concurrently")
    
    results = {}
    
    def analyze_single(symbol: str, data: pd.DataFrame) -> tuple:
        """Analyze a single stock and return (symbol, result)"""
        try:
            result = analyze_stock_with_talib(symbol, data)
            return symbol, result
        except Exception as e:
            logger.error(f"Error analyzing {symbol}: {str(e)}")
            return symbol, None
    
    # Use threading for concurrent analysis
    max_workers = config.MAX_ANALYSIS_THREADS
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all analysis tasks
        futures = [
            executor.submit(analyze_single, symbol, data) 
            for symbol, data in stock_data_map.items() 
            if data is not None
        ]
        
        # Collect results
        for future in futures:
            try:
                symbol, result = future.result()
                results[symbol] = result
            except Exception as e:
                logger.error(f"Error processing analysis future: {str(e)}")
    
    successful_count = sum(1 for result in results.values() if result is not None)
    logger.info(f"Analysis complete: {successful_count}/{len(stock_data_map)} successful")
    
    return results
