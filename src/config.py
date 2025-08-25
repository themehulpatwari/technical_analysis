"""
Configuration module for technical analysis parameters and logging setup.
"""

import logging
import os
from dataclasses import dataclass
from typing import List
import warnings
from dotenv import load_dotenv
from datetime import datetime

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
    MAX_RETRIES: int = 5
    RETRY_DELAY: float = 180
    REQUEST_DELAY: float = 0.5  # Delay between API requests (increased for rate limiting)
    DEFAULT_PERIOD: str = '6mo'
    # Threading configuration optimized for GCP e2-standard-4 (4 vCPUs, 16 GB Memory)
    MAX_ANALYSIS_THREADS: int = 4    # Threads for stock analysis (CPU intensive) - matches vCPU count
    MAX_FETCH_THREADS: int = 2       # Threads for data fetching (I/O intensive) - higher for I/O bound
    MAX_FILTER_THREADS: int = 2     # Threads for stock filtering (I/O intensive) - highest for filtering phase
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
    ALERT_EMAIL: str = ""
    SMTP_SERVER: str = "smtp.gmail.com"
    SMTP_PORT: int = 587

    def __post_init__(self):
        """Load email configuration from environment variables"""
        # Load email credentials from environment
        self.EMAIL_SENDER = os.getenv('EMAIL_SENDER', '')
        self.EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD', '')
        
        # Load alert email from environment
        self.ALERT_EMAIL = os.getenv('ALERT_EMAIL', '')
        
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
        if not self.ALERT_EMAIL:
            logging.warning("ALERT_EMAIL not set in environment variables")


# Global configuration instance
config = Config()


def setup_logging() -> logging.Logger:
    """
    Setup logging configuration for the application
    
    Returns:
        logging.Logger: Configured logger instance
    """
    # Create logs directory if it doesn't exist
    os.makedirs("logs", exist_ok=True)
    
    # Create daily log file name
    today = datetime.now().strftime("%Y-%m-%d")
    log_filename = f"logs/technical_analysis_{today}.log"
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_filename)
        ]
    )
    return logging.getLogger(__name__)


def cleanup_old_logs(max_days: int = 10):
    """
    Delete log files older than max_days
    
    Args:
        max_days: Maximum number of days to keep logs (default: 10)
    """
    import glob
    from datetime import timedelta
    
    try:
        cutoff_date = datetime.now() - timedelta(days=max_days)
        log_pattern = "logs/technical_analysis_*.log"
        log_files = glob.glob(log_pattern)
        
        deleted_count = 0
        for log_file in log_files:
            try:
                # Extract date from filename
                filename = os.path.basename(log_file)
                date_str = filename.replace("technical_analysis_", "").replace(".log", "")
                file_date = datetime.strptime(date_str, "%Y-%m-%d")
                
                if file_date < cutoff_date:
                    os.remove(log_file)
                    deleted_count += 1
                    print(f"Deleted old log file: {log_file}")
            except (ValueError, OSError):
                continue
        
        if deleted_count > 0:
            print(f"Cleaned up {deleted_count} old log files")
                
    except Exception as e:
        print(f"Warning: Error during log cleanup: {e}")
