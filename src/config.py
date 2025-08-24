"""
Configuration module for technical analysis parameters and logging setup.
"""

import logging
import os
from dataclasses import dataclass
from typing import List
import warnings
from dotenv import load_dotenv

warnings.filterwarnings('ignore')

# Load environment variables from .env file
load_dotenv()


@dataclass
class Config:
    """Configuration class for technical analysis parameters"""
    RSI_PERIOD: int = 14
    RSI_OVERSOLD: float = 20.0
    RSI_OVERBOUGHT: float = 80.0
    MACD_FAST: int = 12
    MACD_SLOW: int = 26
    MACD_SIGNAL: int = 9
    MIN_DATA_POINTS: int = 50
    MAX_RETRIES: int = 3
    RETRY_DELAY: float = 1.0
    REQUEST_DELAY: float = 0.1  # Delay between API requests
    DEFAULT_PERIOD: str = '6mo'
    # Threading configuration
    MAX_ANALYSIS_THREADS: int = 4    # Threads for stock analysis (CPU intensive)
    MAX_FETCH_THREADS: int = 5       # Threads for data fetching (I/O intensive)
    MAX_FILTER_THREADS: int = 6      # Threads for stock filtering (I/O intensive)
    # New symbol fetching configuration
    MAX_SYMBOLS: int = None  # Set to None for no limit, or a number to limit symbols for testing
    USE_WEB_FETCH: bool = True  # Set to False to skip web fetch and use only fallback
    # Stock filtering criteria
    MIN_MARKET_CAP_CR: float = 500  # Minimum market cap in crores
    MIN_DAILY_VOLUME_CR: float = 1   # Minimum daily volume in crores Rs
    # Email configuration - loaded from environment variables
    EMAIL_SENDER: str = ""
    EMAIL_PASSWORD: str = ""
    EMAIL_RECIPIENTS: List[str] = None
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    def __post_init__(self):
        """Load email configuration from environment variables"""
        # Load email credentials from environment
        self.EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
        self.EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
        
        # Load recipients from environment (comma-separated string)
        recipients_env = os.getenv('EMAIL_RECIPIENTS', '')
        if recipients_env:
            self.EMAIL_RECIPIENTS = [email.strip() for email in recipients_env.split(',') if email.strip()]
        else:
            # Default recipients if not set in environment
            self.EMAIL_RECIPIENTS = []
        
        # Optional: Override SMTP settings from environment
        self.SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
        self.SMTP_PORT = int(os.getenv('SMTP_PORT', '587'))
        
        # Validate email configuration
        if not self.EMAIL_SENDER:
            logging.warning("EMAIL_SENDER not set in environment variables")
        if not self.EMAIL_PASSWORD:
            logging.warning("EMAIL_PASSWORD not set in environment variables")
        if not self.EMAIL_RECIPIENTS:
            logging.warning("EMAIL_RECIPIENTS not set in environment variables")


# Global configuration instance
config = Config()


def setup_logging() -> logging.Logger:
    """
    Setup logging configuration for the application
    
    Returns:
        logging.Logger: Configured logger instance
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('technical_analysis.log')
        ]
    )
    return logging.getLogger(__name__)
