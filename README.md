# NSE Technical Analysis Email Reporter

An automated technical analysis tool that analyzes NSE stocks for RSI and MACD signals and sends comprehensive reports via email.

## Quick Start

1. **Set up email configuration:**
   ```bash
   cp .env.template .env
   # Edit .env with your Gmail credentials
   ```

2. **Test email configuration:**
   ```bash
   python src/main.py --test-email
   ```

3. **Run analysis and send report:**
   ```bash
   python src/main.py
   ```

## Security Features

- Environment Variables: Sensitive email credentials stored in `.env` file
- Git Protection: `.env` file automatically ignored by git
- Template Configuration: Use `.env.template` for setup guidance
- App Passwords: Uses Gmail app passwords for enhanced security

## Project Structure

- `src/main.py` - Entry point and analysis orchestration
- `src/config.py` - Configuration with environment variable loading
- `src/data_fetcher.py` - Stock data fetching with source tracking
- `src/technical_indicators.py` - RSI/MACD calculations and signals
- `src/email_sender.py` - Email functionality with CSV reports
- `src/utils.py` - Utility functions for data processing

## Features

- Automated Analysis: RSI and MACD signal detection
- Data Source Tracking: Know whether data comes from live NSE, fallback files, or emergency sources
- Email Reports: HTML emails with analysis summaries
- CSV Attachments: Detailed data for stocks showing signals
- Stock Filtering: Market cap and volume-based filtering
- Error Handling: Robust retry mechanisms and comprehensive logging
- No Manual Intervention: Fully automated email delivery

## Analysis Coverage

- NSE Stock Universe: Up to 50 stocks from NSE equity list
- Filtering Criteria: Market cap ≥ ₹500 Cr, Daily volume ≥ ₹1 Cr
- Technical Indicators: RSI (14-period) and MACD (12/26/9)
- Signal Detection: Oversold/overbought conditions and crossover signals

## Email Report Contents

- HTML Summary: Analysis overview with data source information
- Signal Details: Companies showing trading signals with key metrics
- CSV Attachment: Complete data for further analysis
- Transparency: Clear indication of data source (live/fallback)

## Installation

Dependencies are managed via pyproject.toml:
```bash
# Install dependencies (includes python-dotenv for security)
pip install -e .
```

## Requirements

- Python 3.12+
- TA-Lib (Technical Analysis Library)
- python-dotenv (for environment variables)
- yfinance, pandas, numpy, matplotlib, requests

## Configuration

See EMAIL_SETUP.md for detailed configuration instructions including:
- Gmail app password setup
- Environment variable configuration
- Security best practices
- Troubleshooting guide

## Data Sources

The system automatically handles multiple data sources:
1. Live NSE Website: Fresh equity data from NSE archives
2. Local Fallback: Pre-stored symbol list for reliability
3. Emergency Fallback: Popular stocks list as last resort

Email reports indicate which source was used for transparency.

## Example Usage

```bash
# Test email configuration
python src/main.py --test-email

# Run full analysis and send report
python src/main.py

# Check logs for detailed information
tail -f technical_analysis.log
```

## Automation Ready

Perfect for cron jobs or scheduled tasks:
```bash
# Example cron entry for daily reports at 3:30 PM
30 15 * * * cd /home/mtpat/Code/technical_analysis && .venv/bin/python src/main.py
```

## License

MIT License

Copyright (c) 2025 themehulpatwari

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.

**Disclaimer:** This project is for educational and research purposes. Not investment advice.