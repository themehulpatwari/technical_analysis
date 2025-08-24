"""
Visualization module for plotting technical analysis charts.
"""

import logging
from typing import Dict, Any
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend for EC2
import matplotlib.pyplot as plt
from config import config


logger = logging.getLogger(__name__)


def plot_technical_analysis(analysis_result: Dict[str, Any]) -> bool:
    """
    Plot stock price with RSI and MACD indicators using TA-Lib data
    
    Args:
        analysis_result: Analysis result dictionary
    
    Returns:
        bool: True if plot was successful, False otherwise
    """
    try:
        if analysis_result is None:
            logger.error("Cannot plot: analysis_result is None")
            return False
        
        required_keys = ['data', 'symbol', 'indicators']
        if not all(key in analysis_result for key in required_keys):
            logger.error(f"Missing required keys in analysis_result: {required_keys}")
            return False
        
        data = analysis_result['data']
        symbol = analysis_result['symbol']
        indicators = analysis_result['indicators']
        
        # Validate indicators
        required_indicators = ['rsi', 'macd', 'macd_signal', 'macd_histogram']
        if not all(key in indicators for key in required_indicators):
            logger.error(f"Missing required indicators: {required_indicators}")
            return False
        
        # Check if we have valid data for plotting
        if len(data) == 0:
            logger.error(f"No data available for plotting {symbol}")
            return False
        
        fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
        fig.suptitle(f'{symbol} - RSI & MACD Analysis (TA-Lib)', fontsize=16)
        
        # Price chart
        try:
            ax1.plot(data.index, data['Close'], label='Close Price', linewidth=2, color='blue')
            ax1.set_title('Stock Price')
            ax1.set_ylabel('Price (₹)')
            ax1.legend()
            ax1.grid(True, alpha=0.3)
        except Exception as e:
            logger.error(f"Error plotting price chart for {symbol}: {e}")
            return False
        
        # RSI chart
        try:
            rsi_data = indicators['rsi']
            # Only plot non-NaN values
            valid_rsi_mask = ~np.isnan(rsi_data)
            if valid_rsi_mask.any():
                ax2.plot(data.index[valid_rsi_mask], rsi_data[valid_rsi_mask], 
                        label='RSI', color='purple', linewidth=2)
            
            ax2.axhline(y=config.RSI_OVERBOUGHT, color='r', linestyle='--', alpha=0.7, 
                       label=f'Overbought ({config.RSI_OVERBOUGHT})')
            ax2.axhline(y=config.RSI_OVERSOLD, color='g', linestyle='--', alpha=0.7, 
                       label=f'Oversold ({config.RSI_OVERSOLD})')
            ax2.axhline(y=50, color='blue', linestyle='-', alpha=0.3, label='Neutral (50)')
            ax2.set_title('RSI (Relative Strength Index)')
            ax2.set_ylabel('RSI')
            ax2.legend()
            ax2.grid(True, alpha=0.3)
            ax2.set_ylim(0, 100)
        except Exception as e:
            logger.error(f"Error plotting RSI chart for {symbol}: {e}")
            return False
        
        # MACD chart
        try:
            macd_data = indicators['macd']
            signal_data = indicators['macd_signal']
            hist_data = indicators['macd_histogram']
            
            # Only plot non-NaN values
            valid_macd_mask = ~np.isnan(macd_data)
            valid_signal_mask = ~np.isnan(signal_data)
            valid_hist_mask = ~np.isnan(hist_data)
            
            if valid_macd_mask.any():
                ax3.plot(data.index[valid_macd_mask], macd_data[valid_macd_mask], 
                        label='MACD', color='blue', linewidth=2)
            
            if valid_signal_mask.any():
                ax3.plot(data.index[valid_signal_mask], signal_data[valid_signal_mask], 
                        label='Signal', color='red', linewidth=2)
            
            if valid_hist_mask.any():
                ax3.bar(data.index[valid_hist_mask], hist_data[valid_hist_mask], 
                       label='Histogram', alpha=0.7, color='gray', width=1)
            
            ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
            ax3.set_title('MACD (Moving Average Convergence Divergence)')
            ax3.set_ylabel('MACD')
            ax3.set_xlabel('Date')
            ax3.legend()
            ax3.grid(True, alpha=0.3)
        except Exception as e:
            logger.error(f"Error plotting MACD chart for {symbol}: {e}")
            return False
        
        plt.tight_layout()
        
        # Save the plot instead of showing it (for EC2 instance)
        plot_filename = f"{symbol.replace('.NS', '')}_technical_analysis.png"
        plt.savefig(plot_filename, dpi=150, bbox_inches='tight')
        plt.close()  # Close the plot to free memory
        
        logger.info(f"Successfully plotted and saved chart for {symbol} as {plot_filename}")
        return True
        
    except Exception as e:
        logger.error(f"Unexpected error while plotting for {symbol}: {str(e)}")
        return False
