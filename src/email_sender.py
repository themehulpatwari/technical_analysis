"""
Email functionality for sending technical analysis reports.
"""

import smtplib
import logging
import os
import tempfile
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import pandas as pd

try:
    from .config import config
except ImportError:
    from config import config

logger = logging.getLogger(__name__)


def create_csv_report(companies_with_signals: List[Dict[str, Any]], data_source: str) -> str:
    """
    Create a CSV report from companies with signals
    
    Args:
        companies_with_signals: List of analysis results with trading signals
        data_source: Source of the data (live_website, first_fallback, second_fallback)
    
    Returns:
        str: Path to the created CSV file
    """
    if not companies_with_signals:
        logger.warning("No companies with signals to create CSV report")
        return None
    
    try:
        # Prepare data for CSV
        csv_data = []
        for company in companies_with_signals:
            symbol = company.get('symbol', 'N/A')
            company_name = company.get('company_name', 'N/A')
            current_price = company.get('current_price', 0)
            market_cap_cr = company.get('market_cap_cr', 0)
            daily_volume_cr = company.get('daily_volume_cr', 0)
            rsi = company.get('rsi')
            macd = company.get('macd')
            macd_signal = company.get('macd_signal')
            signals = company.get('signals', [])
            
            # Clean signal details by removing numbers in parentheses
            cleaned_signals = []
            for signal in signals:
                # Remove patterns like "(81.21)" or similar numerical values in parentheses
                cleaned_signal = re.sub(r'\s*\([0-9.]+\)', '', signal)
                cleaned_signals.append(cleaned_signal)
            
            csv_data.append({
                'Symbol': symbol,
                'Company_Name': company_name,
                'Current_Price_Rs': f"{current_price:.2f}" if current_price > 0 else "N/A",
                'Total_Signals': len(signals),
                'Signal_Details': '; '.join(cleaned_signals) if cleaned_signals else 'None',
                'RSI': f"{rsi:.2f}" if rsi is not None else "N/A",
                'MACD': f"{macd:.4f}" if macd is not None else "N/A",
                'MACD_Signal': f"{macd_signal:.4f}" if macd_signal is not None else "N/A",
                'MACD_Histogram': f"{(macd - macd_signal):.4f}" if (macd is not None and macd_signal is not None) else "N/A",
                'Market_Cap_Cr': f"{market_cap_cr:.1f}" if market_cap_cr > 0 else "N/A",
                'Daily_Volume_Cr': f"{daily_volume_cr:.1f}" if daily_volume_cr > 0 else "N/A",
                'Data_Source': data_source,
                'Report_Generated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Create DataFrame and save to CSV
        df = pd.DataFrame(csv_data)
        
        # Create temporary file
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        csv_filename = f"nse_technical_analysis_{timestamp}.csv"
        csv_path = os.path.join(tempfile.gettempdir(), csv_filename)
        
        df.to_csv(csv_path, index=False)
        logger.info(f"CSV report created: {csv_path}")
        
        return csv_path
        
    except Exception as e:
        logger.error(f"Error creating CSV report: {str(e)}")
        return None


def create_email_body(companies_with_signals: List[Dict[str, Any]], data_source: str, total_analyzed: int) -> str:
    """
    Create HTML email body with analysis summary
    
    Args:
        companies_with_signals: List of analysis results with trading signals
        data_source: Source of the data
        total_analyzed: Total number of stocks analyzed
    
    Returns:
        str: HTML formatted email body
    """
    # Map data source to readable format
    data_source_mapping = {
        "live_website": "Live NSE Website",
        "first_fallback": "Local Fallback File",
        "second_fallback": "Popular Stocks List (Emergency Fallback)"
    }
    
    data_source_readable = data_source_mapping.get(data_source, data_source)
    
    # Count signals by category
    signal_counts = {
        'RSI Oversold': 0,
        'RSI Overbought': 0,
        'MACD Bullish Crossover': 0,
        'MACD Bearish Crossover': 0
    }
    
    for company in companies_with_signals:
        signals = company.get('signals', [])
        for signal in signals:
            if 'RSI Oversold' in signal:
                signal_counts['RSI Oversold'] += 1
            elif 'RSI Overbought' in signal:
                signal_counts['RSI Overbought'] += 1
            elif 'MACD Bullish Crossover' in signal:
                signal_counts['MACD Bullish Crossover'] += 1
            elif 'MACD Bearish Crossover' in signal:
                signal_counts['MACD Bearish Crossover'] += 1
    
    # Create HTML content
    html_body = f"""
    <html>
    <head>
        <style>
            body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 0; padding: 20px; background-color: #f8f9fa; }}
            .container {{ max-width: 800px; margin: 0 auto; background-color: white; box-shadow: 0 2px 10px rgba(0,0,0,0.1); border-radius: 8px; overflow: hidden; }}
            .header {{ background-color: #ffffff; border-bottom: 3px solid #007bff; padding: 25px; }}
            .header h1 {{ margin: 0; font-size: 28px; font-weight: 700; color: #2c3e50; }}
            .header .subtitle {{ margin: 10px 0 0 0; color: #6c757d; font-size: 16px; }}
            .header .meta-info {{ margin: 15px 0 0 0; padding: 12px; background-color: #f8f9fa; border-radius: 6px; border-left: 4px solid #007bff; }}
            .header .meta-info strong {{ color: #495057; }}
            .content {{ padding: 25px; }}
            .summary {{ background-color: #f8f9fa; border-left: 4px solid #007bff; padding: 20px; margin: 20px 0; border-radius: 6px; }}
            .summary h2 {{ margin-top: 0; color: #2c3e50; font-size: 20px; }}
            .metrics {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 15px; margin: 15px 0; }}
            .metric {{ background: white; padding: 20px; border-radius: 8px; border: 1px solid #e9ecef; text-align: center; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .metric-value {{ font-size: 28px; font-weight: bold; color: #007bff; }}
            .metric-label {{ font-size: 13px; color: #6c757d; text-transform: uppercase; letter-spacing: 0.5px; margin-top: 5px; }}
            .signal-category {{ background: white; border: 1px solid #dee2e6; padding: 18px; margin: 12px 0; border-radius: 8px; box-shadow: 0 1px 3px rgba(0,0,0,0.1); }}
            .signal-category.buy {{ border-left: 5px solid #28a745; }}
            .signal-category.sell {{ border-left: 5px solid #dc3545; }}
            .signal-header {{ display: flex; align-items: center; margin-bottom: 5px; }}
            .signal-type {{ font-weight: 600; color: #495057; font-size: 16px; }}
            .signal-count {{ font-weight: 700; color: #007bff; font-size: 18px; margin: 0 8px; }}
            .signal-description {{ color: #6c757d; font-style: italic; }}
            .buy-signal {{ color: #28a745; }}
            .sell-signal {{ color: #dc3545; }}
            .warning {{ background-color: #fff3cd; border: 1px solid #ffeaa7; color: #856404; padding: 20px; border-radius: 6px; }}
            .parameters {{ background-color: #f8f9fa; padding: 25px; border-radius: 8px; margin: 20px 0; }}
            .parameters h3 {{ margin-top: 0; color: #2c3e50; font-size: 18px; }}
            .parameters ul {{ margin: 10px 0; padding-left: 20px; }}
            .parameters li {{ margin: 8px 0; color: #495057; }}
            .attachment-note {{ background: #e8f4fd; border: 1px solid #b8daff; padding: 18px; border-radius: 8px; margin: 20px 0; }}
            .attachment-note strong {{ color: #004085; }}
            .disclaimer {{ font-size: 12px; color: #6c757d; margin-top: 25px; padding-top: 20px; border-top: 1px solid #dee2e6; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1>NSE Technical Analysis Report</h1>
                <div class="subtitle">Algorithmic Screening & Technical Signal Detection</div>
                <div class="meta-info">
                    <strong>Report Generated:</strong> {datetime.now().strftime('%B %d, %Y at %H:%M IST')} &nbsp;&nbsp;|&nbsp;&nbsp; 
                    <strong>Data Source:</strong> {data_source_readable}
                </div>
            </div>
            
            <div class="content">
                <div class="summary">
                    <h2>Executive Summary</h2>
                    <div class="metrics">
                        <div class="metric">
                            <div class="metric-value">{total_analyzed}</div>
                            <div class="metric-label">Stocks Analyzed</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{len(companies_with_signals)}</div>
                            <div class="metric-label">Signal Alerts</div>
                        </div>
                        <div class="metric">
                            <div class="metric-value">{(len(companies_with_signals)/total_analyzed*100):.1f}%</div>
                            <div class="metric-label">Hit Rate</div>
                        </div>
                    </div>
                </div>
    """
    
    if companies_with_signals:
        html_body += """
                <div class="summary">
                    <h2>Signal Distribution Analysis</h2>
                    <p>Technical indicators have identified the following trading opportunities based on RSI momentum and MACD crossover patterns:</p>
                </div>
        """
        
        if signal_counts['RSI Oversold'] > 0:
            html_body += f"""
                <div class="signal-category buy">
                    <div class="signal-header">
                        <span class="signal-type">RSI Oversold Conditions:</span>
                        <span class="signal-count">{signal_counts["RSI Oversold"]}</span>
                        <span class="signal-type">securities</span>
                    </div>
                    <div class="signal-description buy-signal">Potential Accumulation Opportunity</div>
                </div>"""
        
        if signal_counts['RSI Overbought'] > 0:
            html_body += f"""
                <div class="signal-category sell">
                    <div class="signal-header">
                        <span class="signal-type">RSI Overbought Conditions:</span>
                        <span class="signal-count">{signal_counts["RSI Overbought"]}</span>
                        <span class="signal-type">securities</span>
                    </div>
                    <div class="signal-description sell-signal">Potential Distribution Opportunity</div>
                </div>"""
        
        if signal_counts['MACD Bullish Crossover'] > 0:
            html_body += f"""
                <div class="signal-category buy">
                    <div class="signal-header">
                        <span class="signal-type">MACD Bullish Crossovers:</span>
                        <span class="signal-count">{signal_counts["MACD Bullish Crossover"]}</span>
                        <span class="signal-type">securities</span>
                    </div>
                    <div class="signal-description buy-signal">Momentum Confirmation Signals</div>
                </div>"""
        
        if signal_counts['MACD Bearish Crossover'] > 0:
            html_body += f"""
                <div class="signal-category sell">
                    <div class="signal-header">
                        <span class="signal-type">MACD Bearish Crossovers:</span>
                        <span class="signal-count">{signal_counts["MACD Bearish Crossover"]}</span>
                        <span class="signal-type">securities</span>
                    </div>
                    <div class="signal-description sell-signal">Momentum Deterioration Signals</div>
                </div>"""
        
        html_body += """
                <div class="attachment-note">
                    <strong>Detailed Analysis:</strong> Complete technical metrics, including individual RSI/MACD values, signal specifics, and fundamental screening criteria are provided in the attached CSV file for further analysis and due diligence.
                </div>
        """
    else:
        html_body += """
                <div class="warning">
                    <h3>Market Conditions Assessment</h3>
                    <p>Current market scan indicates no securities meeting the specified RSI oversold/overbought thresholds (&lt;20 / &gt;80) or MACD crossover criteria within the analyzed universe. This may indicate a consolidating market environment.</p>
                </div>
        """
    
    html_body += """
                <div class="parameters">
                    <h3>Technical Analysis Parameters</h3>
                    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                            <h4 style="margin: 0 0 10px 0; color: #495057;">RSI Configuration</h4>
                            <ul style="margin: 0; padding-left: 15px;">
                                <li>Period: 14 trading sessions</li>
                                <li>Oversold threshold: &lt; 20</li>
                                <li>Overbought threshold: &gt; 80</li>
                            </ul>
                        </div>
                        <div>
                            <h4 style="margin: 0 0 10px 0; color: #495057;">MACD Configuration</h4>
                            <ul style="margin: 0; padding-left: 15px;">
                                <li>Fast EMA: 12 periods</li>
                                <li>Slow EMA: 26 periods</li>
                                <li>Signal line: 9-period EMA</li>
                            </ul>
                        </div>
                    </div>
                    <div style="margin-top: 15px;">
                        <h4 style="margin: 0 0 10px 0; color: #495057;">Screening Criteria</h4>
                        <ul style="margin: 0; padding-left: 15px;">
                            <li>Minimum market capitalization: ₹500 crores</li>
                            <li>Minimum daily trading volume: ₹1 crore</li>
                        </ul>
                    </div>
                </div>
                
                <div class="disclaimer">
                    <p><strong>Important Disclaimer:</strong> This technical analysis is provided for informational and educational purposes only. It should not be construed as investment advice, recommendation, or solicitation to buy or sell any securities. Past performance does not guarantee future results. Please consult with qualified financial advisors and conduct your own due diligence before making any investment decisions. Technical indicators are tools for analysis and should be used in conjunction with fundamental analysis and risk management strategies.</p>
                </div>
            </div>
        </div>
    </body>
    </html>
    """
    
    return html_body


def send_email_report(companies_with_signals: List[Dict[str, Any]], data_source: str, total_analyzed: int) -> bool:
    """
    Send email report with CSV attachment using concurrent processing
    
    Args:
        companies_with_signals: List of analysis results with trading signals
        data_source: Source of the data
        total_analyzed: Total number of stocks analyzed
    
    Returns:
        bool: True if email sent successfully, False otherwise
    """
    try:
        # Validate email configuration
        if not config.EMAIL_SENDER or not config.EMAIL_PASSWORD:
            logger.error("Email credentials not configured")
            return False
        
        if not config.EMAIL_RECIPIENTS:
            logger.error("No email recipients configured")
            return False
        
        # Use threading to prepare CSV and email body concurrently
        with ThreadPoolExecutor(max_workers=2) as executor:
            # Submit both tasks concurrently
            csv_future = executor.submit(create_csv_report, companies_with_signals, data_source)
            html_future = executor.submit(create_email_body, companies_with_signals, data_source, total_analyzed)
            
            # Get results
            csv_path = csv_future.result()
            html_body = html_future.result()
        
        if not csv_path:
            logger.error("Failed to create CSV report")
            return False
        
        # Create email content
        subject = f"NSE Technical Analysis Report - {datetime.now().strftime('%Y-%m-%d')} ({len(companies_with_signals)} signals)"
        
        # Create message
        msg = MIMEMultipart('alternative')
        msg['From'] = config.EMAIL_SENDER
        msg['To'] = ', '.join(config.EMAIL_RECIPIENTS)
        msg['Subject'] = subject
        
        # Add HTML body
        html_part = MIMEText(html_body, 'html')
        msg.attach(html_part)
        
        # Add CSV attachment
        try:
            with open(csv_path, 'rb') as attachment:
                part = MIMEBase('application', 'octet-stream')
                part.set_payload(attachment.read())
                
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename= {os.path.basename(csv_path)}'
            )
            msg.attach(part)
            
        except Exception as e:
            logger.error(f"Error attaching CSV file: {str(e)}")
            # Continue without attachment rather than failing completely
        
        # Send email
        logger.info("Connecting to SMTP server...")
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        
        text = msg.as_string()
        server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENTS, text)
        server.quit()
        
        logger.info(f"Email sent successfully to {len(config.EMAIL_RECIPIENTS)} recipients")
        
        # Clean up temporary CSV file
        try:
            os.remove(csv_path)
            logger.debug(f"Temporary CSV file removed: {csv_path}")
        except Exception as e:
            logger.warning(f"Could not remove temporary CSV file: {str(e)}")
        
        return True
        
    except smtplib.SMTPAuthenticationError:
        logger.error("SMTP authentication failed. Check email credentials.")
        return False
    except smtplib.SMTPException as e:
        logger.error(f"SMTP error occurred: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error sending email: {str(e)}")
        return False


def test_email_configuration() -> bool:
    """
    Test email configuration by sending a test email
    
    Returns:
        bool: True if test email sent successfully, False otherwise
    """
    try:
        # Create test message
        msg = MIMEMultipart()
        msg['From'] = config.EMAIL_SENDER
        msg['To'] = ', '.join(config.EMAIL_RECIPIENTS)
        msg['Subject'] = "NSE Technical Analysis - Email Configuration Test"
        
        body = """
        <html>
        <body>
            <h2>✅ Email Configuration Test</h2>
            <p>This is a test email to verify that your email configuration is working correctly.</p>
            <p><strong>Timestamp:</strong> {}</p>
            <p>If you receive this email, your NSE Technical Analysis tool is properly configured to send reports.</p>
        </body>
        </html>
        """.format(datetime.now().strftime('%Y-%m-%d %H:%M:%S IST'))
        
        msg.attach(MIMEText(body, 'html'))
        
        # Send test email
        server = smtplib.SMTP(config.SMTP_SERVER, config.SMTP_PORT)
        server.starttls()
        server.login(config.EMAIL_SENDER, config.EMAIL_PASSWORD)
        
        text = msg.as_string()
        server.sendmail(config.EMAIL_SENDER, config.EMAIL_RECIPIENTS, text)
        server.quit()
        
        logger.info("Test email sent successfully")
        return True
        
    except Exception as e:
        logger.error(f"Test email failed: {str(e)}")
        return False
