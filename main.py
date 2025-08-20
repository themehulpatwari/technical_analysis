import yfinance as yf
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import talib
from datetime import datetime, timedelta
import warnings
warnings.filterwarnings('ignore')

def get_indian_stock_symbols():
    """Get a list of popular Indian stock symbols"""
    # Popular Indian stocks with their Yahoo Finance symbols (NSE)
    indian_stocks = [
        'RELIANCE.NS',   # Reliance Industries
        'TCS.NS',        # Tata Consultancy Services
        'HDFCBANK.NS',   # HDFC Bank
        'INFY.NS',       # Infosys
        'HINDUNILVR.NS', # Hindustan Unilever
        'ICICIBANK.NS',  # ICICI Bank
        'KOTAKBANK.NS',  # Kotak Mahindra Bank
        'BHARTIARTL.NS', # Bharti Airtel
        'SBIN.NS',       # State Bank of India
        'BAJFINANCE.NS', # Bajaj Finance
        'ASIANPAINT.NS', # Asian Paints
        'MARUTI.NS',     # Maruti Suzuki
        'LTIM.NS',       # LTIMindtree
        'SUNPHARMA.NS',  # Sun Pharmaceutical
        'TITAN.NS',      # Titan Company
        'ULTRACEMCO.NS', # UltraTech Cement
        'WIPRO.NS',      # Wipro
        'NESTLEIND.NS',  # Nestle India
        'POWERGRID.NS',  # Power Grid Corporation
        'NTPC.NS'        # NTPC
    ]
    return indian_stocks

def fetch_stock_data(symbol, period='6mo'):
    """Fetch stock data for a given symbol"""
    try:
        stock = yf.Ticker(symbol)
        data = stock.history(period=period)
        if data.empty:
            print(f"No data found for {symbol}")
            return None
        return data
    except Exception as e:
        print(f"Error fetching data for {symbol}: {e}")
        return None

def analyze_stock_with_talib(symbol, data):
    """Perform RSI and MACD analysis using TA-Lib"""
    if data is None or len(data) < 50:
        return None
    
    # Convert data to numpy arrays (required by TA-Lib)
    close = data['Close'].values
    
    try:
        # Calculate RSI using TA-Lib
        rsi = talib.RSI(close, timeperiod=14)
        
        # Calculate MACD using TA-Lib
        macd, macdsignal, macdhist = talib.MACD(close, 
                                               fastperiod=12, 
                                               slowperiod=26, 
                                               signalperiod=9)
        
        # Get latest values (handle NaN values)
        latest_rsi = rsi[-1] if not np.isnan(rsi[-1]) else None
        latest_macd = macd[-1] if not np.isnan(macd[-1]) else None
        latest_signal = macdsignal[-1] if not np.isnan(macdsignal[-1]) else None
        latest_histogram = macdhist[-1] if not np.isnan(macdhist[-1]) else None
        latest_price = close[-1]
        
        # Determine signals
        signals = []
        
        # RSI signals
        if latest_rsi is not None:
            if latest_rsi < 30:
                signals.append(f"RSI Oversold ({latest_rsi:.2f}) - Potential Buy")
            elif latest_rsi > 70:
                signals.append(f"RSI Overbought ({latest_rsi:.2f}) - Potential Sell")
        
        # MACD signals
        if latest_macd is not None and latest_signal is not None:
            if latest_macd > latest_signal and len(macdhist) > 1 and macdhist[-2] <= 0:
                signals.append("MACD Bullish Crossover - Buy Signal")
            elif latest_macd < latest_signal and len(macdhist) > 1 and macdhist[-2] >= 0:
                signals.append("MACD Bearish Crossover - Sell Signal")
        
        return {
            'symbol': symbol,
            'company_name': symbol.replace('.NS', ''),
            'current_price': latest_price,
            'rsi': latest_rsi,
            'macd': latest_macd,
            'macd_signal': latest_signal,
            'macd_histogram': latest_histogram,
            'signals': signals,
            'data': data,
            'indicators': {
                'rsi': rsi,
                'macd': macd,
                'macd_signal': macdsignal,
                'macd_histogram': macdhist
            }
        }
        
    except Exception as e:
        print(f"Error analyzing {symbol} with TA-Lib: {e}")
        return None

def plot_technical_analysis(analysis_result):
    """Plot stock price with RSI and MACD indicators using TA-Lib data"""
    if analysis_result is None:
        return
    
    data = analysis_result['data']
    symbol = analysis_result['symbol']
    indicators = analysis_result['indicators']
    
    fig, (ax1, ax2, ax3) = plt.subplots(3, 1, figsize=(12, 10))
    fig.suptitle(f'{symbol} - RSI & MACD Analysis (TA-Lib)', fontsize=16)
    
    # Price chart
    ax1.plot(data.index, data['Close'], label='Close Price', linewidth=2, color='blue')
    ax1.set_title('Stock Price')
    ax1.set_ylabel('Price (₹)')
    ax1.legend()
    ax1.grid(True, alpha=0.3)
    
    # RSI chart
    ax2.plot(data.index, indicators['rsi'], label='RSI', color='purple', linewidth=2)
    ax2.axhline(y=70, color='r', linestyle='--', alpha=0.7, label='Overbought (70)')
    ax2.axhline(y=30, color='g', linestyle='--', alpha=0.7, label='Oversold (30)')
    ax2.axhline(y=50, color='blue', linestyle='-', alpha=0.3, label='Neutral (50)')
    ax2.set_title('RSI (Relative Strength Index)')
    ax2.set_ylabel('RSI')
    ax2.legend()
    ax2.grid(True, alpha=0.3)
    ax2.set_ylim(0, 100)
    
    # MACD chart
    ax3.plot(data.index, indicators['macd'], label='MACD', color='blue', linewidth=2)
    ax3.plot(data.index, indicators['macd_signal'], label='Signal', color='red', linewidth=2)
    ax3.bar(data.index, indicators['macd_histogram'], label='Histogram', alpha=0.7, color='gray', width=1)
    ax3.axhline(y=0, color='black', linestyle='-', alpha=0.5)
    ax3.set_title('MACD (Moving Average Convergence Divergence)')
    ax3.set_ylabel('MACD')
    ax3.set_xlabel('Date')
    ax3.legend()
    ax3.grid(True, alpha=0.3)
    
    plt.tight_layout()
    plt.show()

def main():
    """Main function to run RSI and MACD analysis using TA-Lib"""
    print("Starting Indian Stock Market Analysis - RSI & MACD (TA-Lib)...")
    print("=" * 60)
    
    # Get Indian stock symbols
    symbols = get_indian_stock_symbols()
    
    # Store results
    results = []
    companies_with_signals = []
    
    print(f"Analyzing {len(symbols)} Indian companies for RSI & MACD signals...")
    
    for i, symbol in enumerate(symbols, 1):
        print(f"Processing {i}/{len(symbols)}: {symbol}")
        
        # Fetch stock data
        stock_data = fetch_stock_data(symbol)
        
        if stock_data is not None:
            # Analyze stock using TA-Lib (RSI & MACD only)
            analysis = analyze_stock_with_talib(symbol, stock_data)
            
            if analysis is not None:
                results.append(analysis)
                
                # Check if stock has signals
                if analysis['signals']:
                    companies_with_signals.append(analysis)
    
    print("\n" + "=" * 60)
    print("RSI & MACD ANALYSIS COMPLETE")
    print("=" * 60)
    
    # Display summary
    print(f"\nTotal companies analyzed: {len(results)}")
    print(f"Companies with RSI/MACD signals: {len(companies_with_signals)}")
    
    # Display companies with signals
    if companies_with_signals:
        print("\n" + "=" * 80)
        print("COMPANIES WITH RSI/MACD SIGNALS (TA-Lib Analysis):")
        print("=" * 80)
        
        for company in companies_with_signals:
            print(f"\n📊 {company['symbol']} - {company['company_name']}")
            print(f"   Current Price: ₹{company['current_price']:.2f}")
            print(f"   RSI: {company['rsi']:.2f}" if company['rsi'] else "   RSI: N/A")
            print(f"   MACD: {company['macd']:.4f}" if company['macd'] else "   MACD: N/A")
            print(f"   MACD Signal: {company['macd_signal']:.4f}" if company['macd_signal'] else "   MACD Signal: N/A")
            print("   Technical Signals:")
            for signal in company['signals']:
                print(f"   • {signal}")
    else:
        print("\n❌ No companies showing RSI oversold/overbought or MACD crossover signals.")
    
    # Create summary DataFrame
    summary_data = []
    for result in results:
        summary_data.append({
            'Symbol': result['symbol'],
            'Company': result['company_name'],
            'Price': f"₹{result['current_price']:.2f}",
            'RSI': f"{result['rsi']:.2f}" if result['rsi'] else "N/A",
            'MACD': f"{result['macd']:.4f}" if result['macd'] else "N/A",
            'MACD_Signal': f"{result['macd_signal']:.4f}" if result['macd_signal'] else "N/A",
            'Signals': len(result['signals']),
            'Signal_Details': '; '.join(result['signals']) if result['signals'] else 'None'
        })
    
    summary_df = pd.DataFrame(summary_data)
    
    print("\n" + "=" * 100)
    print("SUMMARY TABLE (RSI & MACD Only):")
    print("=" * 100)
    print(summary_df.to_string(index=False))
    
    # Optional: Plot charts for companies with signals
    plot_charts = input("\nDo you want to see RSI & MACD charts for companies with signals? (y/n): ").lower().strip()
    if plot_charts == 'y' and companies_with_signals:
        for company in companies_with_signals:
            print(f"\nPlotting RSI & MACD chart for {company['symbol']}...")
            plot_technical_analysis(company)
    
    return results, companies_with_signals

# Required libraries installation command (run in terminal):
# pip install yfinance pandas numpy matplotlib TA-Lib

if __name__ == "__main__":
    print("Note: Make sure TA-Lib is properly installed.")
    print("Installation: pip install TA-Lib")
    print("If installation fails, you may need system dependencies first.")
    print("\n" + "=" * 60)
    
    # Run the analysis
    all_results, signal_companies = main()