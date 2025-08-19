"""
Utility functions for the Price Tracker application.
"""

import requests
import time
import logging
import re
import io
import base64
import signal
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Tuple, Any
import json

# Web scraping imports
from bs4 import BeautifulSoup
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

# Data processing imports
import numpy as np
import pandas as pd

# Machine Learning imports
from sklearn.linear_model import LinearRegression
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score

# Prophet for time series forecasting
try:
    from prophet import Prophet
    PROPHET_AVAILABLE = True
except ImportError:
    PROPHET_AVAILABLE = False
    logging.warning("Prophet not available. Using simple regression models only.")

# Visualization imports
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import seaborn as sns

# Django imports
from django.utils import timezone
from django.conf import settings
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Set up logging
logger = logging.getLogger(__name__)

# Configure matplotlib and seaborn
plt.style.use('default')
sns.set_palette("husl")
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['figure.dpi'] = 100
plt.rcParams['font.size'] = 10


class TimeoutError(Exception):
    """Custom timeout error for scraping operations."""
    pass


def timeout_handler(signum, frame):
    """Signal handler for timeout operations."""
    raise TimeoutError("Operation timed out")


class WebScraper:
    """Enhanced web scraping utility class with fixed logging."""
    
    def __init__(self):
        """Initialize the scraper with configuration and user agents."""
        self.session = requests.Session()
        
        try:
            self.ua = UserAgent()
            self.user_agent = self.ua.random
        except:
            # Fallback user agent if fake-useragent fails
            self.user_agent = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        
        self.session.headers.update({
            'User-Agent': self.user_agent,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
        
        # Chrome options for Selenium
        self.chrome_options = Options()
        self.chrome_options.add_argument('--headless')
        self.chrome_options.add_argument('--no-sandbox')
        self.chrome_options.add_argument('--disable-dev-shm-usage')
        self.chrome_options.add_argument('--disable-gpu')
        self.chrome_options.add_argument('--disable-extensions')
        self.chrome_options.add_argument('--disable-plugins')
        self.chrome_options.add_argument('--disable-images')
        self.chrome_options.add_argument('--window-size=1920,1080')
        self.chrome_options.add_argument(f'--user-agent={self.user_agent}')
    
    def scrape_amazon_price(self, url: str) -> Optional[Decimal]:
        """Scrape price from Amazon with timeout handling."""
        try:
            time.sleep(getattr(settings, 'SCRAPING_DELAY', 2))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_selectors = [
                'span.a-price-whole',
                'span.a-offscreen',
                'span.a-price span.a-offscreen',
                'span#priceblock_ourprice',
                'span#priceblock_dealprice',
                'span.a-price.a-text-price.a-size-medium.apexPriceToPay',
                'span.a-price-range',
                '.a-price-whole',
                '.a-offscreen',
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_clean = re.sub(r'[^\d.,]', '', price_text)
                    price_match = re.search(r'[\d,]+\.?\d*', price_clean.replace(',', ''))
                    if price_match:
                        return Decimal(price_match.group())
            
            return self._scrape_with_selenium(url, 'amazon')
            
        except Exception as e:
            logger.error(f"Error scraping Amazon price from {url}: {str(e)}")
            return None
    
    def scrape_flipkart_price(self, url: str) -> Optional[Decimal]:
        """Scrape price from Flipkart with timeout handling."""
        try:
            time.sleep(getattr(settings, 'SCRAPING_DELAY', 2))
            response = self.session.get(url, timeout=20)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            price_selectors = [
                'div._30jeq3._16Jk6d',
                'div._1vC4OE._3qQ9m1',
                'div._30jeq3',
                'div._25b18c',
                'div._1g0rzj',
                '._30jeq3',
                '._1vC4OE',
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_clean = re.sub(r'[^\d,]', '', price_text)
                    price_match = re.search(r'[\d,]+', price_clean.replace(',', ''))
                    if price_match:
                        return Decimal(price_match.group())
            
            return self._scrape_with_selenium(url, 'flipkart')
            
        except Exception as e:
            logger.error(f"Error scraping Flipkart price from {url}: {str(e)}")
            return None
    
    def _scrape_with_selenium(self, url: str, site_type: str) -> Optional[Decimal]:
        """Fallback scraping using Selenium with proper timeout handling."""
        driver = None
        try:
            try:
                from webdriver_manager.chrome import ChromeDriverManager
                service = Service(ChromeDriverManager().install())
                driver = webdriver.Chrome(service=service, options=self.chrome_options)
            except:
                driver = webdriver.Chrome(options=self.chrome_options)
            
            driver.set_page_load_timeout(30)
            driver.implicitly_wait(10)
            driver.get(url)
            
            wait = WebDriverWait(driver, 15)
            
            if site_type == 'amazon':
                price_selectors = [
                    "span.a-price-whole",
                    "span.a-offscreen",
                    "#priceblock_ourprice",
                    ".a-price-whole",
                    ".a-offscreen",
                ]
            else:  # flipkart
                price_selectors = [
                    "div._30jeq3._16Jk6d",
                    "div._1vC4OE._3qQ9m1",
                    "div._30jeq3",
                    "._30jeq3",
                    "._1vC4OE",
                ]
            
            for selector in price_selectors:
                try:
                    price_element = wait.until(
                        EC.presence_of_element_located((By.CSS_SELECTOR, selector))
                    )
                    price_text = price_element.text.strip()
                    price_clean = re.sub(r'[^\d.,]', '', price_text)
                    price_match = re.search(r'[\d,]+\.?\d*', price_clean.replace(',', ''))
                    if price_match:
                        return Decimal(price_match.group())
                except (TimeoutException, NoSuchElementException):
                    continue
            
            return None
            
        except Exception as e:
            logger.error(f"Error with Selenium scraping for {url}: {str(e)}")
            return None
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
    
    def scrape_price(self, product) -> Tuple[Optional[Decimal], str]:
        """Main method to scrape price with comprehensive error handling."""
        from .models import ScrapingLog
        
        start_time = time.time()
        
        # FIXED: Remove user parameter since it doesn't exist in ScrapingLog model
        log_entry = ScrapingLog.objects.create(
            product=product,
            status='failed',
            started_at=timezone.now()
        )
        
        try:
            url = product.url.lower()
            price = None
            error_message = ""
            
            if 'amazon' in url:
                price = self.scrape_amazon_price(product.url)
                if not price:
                    error_message = "Could not extract price from Amazon page"
            elif 'flipkart' in url:
                price = self.scrape_flipkart_price(product.url)
                if not price:
                    error_message = "Could not extract price from Flipkart page"
            else:
                error_message = "Unsupported e-commerce site"
            
            log_entry.status = 'success' if price else 'failed'
            log_entry.scraped_price = price
            log_entry.response_time = time.time() - start_time
            log_entry.completed_at = timezone.now()
            log_entry.error_message = error_message
            log_entry.save()
            
            return price, log_entry.status
            
        except Exception as e:
            log_entry.error_message = str(e)
            log_entry.response_time = time.time() - start_time
            log_entry.completed_at = timezone.now()
            log_entry.save()
            
            logger.error(f"Error scraping price for {product.name}: {str(e)}")
            return None, 'failed'


class DataProcessor:
    """Data processing utility class using Pandas and NumPy."""
    
    @staticmethod
    def get_price_history_dataframe(product, days: int = 30) -> pd.DataFrame:
        """Get price history as a Pandas DataFrame for analysis."""
        from .models import PriceHistory
        
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        history = PriceHistory.objects.filter(
            product=product,
            recorded_at__gte=start_date,
            is_valid=True
        ).order_by('recorded_at')
        
        if not history.exists():
            return pd.DataFrame()
        
        data = []
        for record in history:
            data.append({
                'date': record.recorded_at.date(),
                'datetime': record.recorded_at,
                'price': float(record.price),
                'source': record.source
            })
        
        df = pd.DataFrame(data)
        if not df.empty:
            df['datetime'] = pd.to_datetime(df['datetime'])
            df.set_index('datetime', inplace=True)
            df.sort_index(inplace=True)
        
        return df
    
    @staticmethod
    def calculate_moving_averages(df: pd.DataFrame, windows: List[int] = [7, 14, 30]) -> pd.DataFrame:
        """Calculate moving averages using Pandas."""
        if df.empty:
            return df
        
        result_df = df.copy()
        
        for window in windows:
            if len(result_df) >= window:
                result_df[f'ma_{window}'] = result_df['price'].rolling(
                    window=window, min_periods=1
                ).mean()
        
        return result_df
    
    @staticmethod
    def calculate_price_statistics(df: pd.DataFrame) -> Dict[str, float]:
        """Calculate comprehensive price statistics using NumPy."""
        if df.empty or 'price' not in df.columns:
            return {}
        
        prices = df['price'].values
        
        stats = {
            'mean': np.mean(prices),
            'median': np.median(prices),
            'std': np.std(prices),
            'min': np.min(prices),
            'max': np.max(prices),
            'range': np.max(prices) - np.min(prices),
            'coefficient_of_variation': np.std(prices) / np.mean(prices) if np.mean(prices) > 0 else 0,
        }
        
        if len(prices) > 1:
            price_changes = np.diff(prices)
            stats.update({
                'volatility': np.std(price_changes),
                'avg_daily_change': np.mean(price_changes),
                'max_daily_increase': np.max(price_changes),
                'max_daily_decrease': np.min(price_changes),
            })
        
        return stats
    
    @staticmethod
    def get_chart_data_json(product, days: int = 30) -> str:
        """Get price history data formatted for Chart.js."""
        df = DataProcessor.get_price_history_dataframe(product, days)
        
        if df.empty:
            return json.dumps({'labels': [], 'prices': []})
        
        labels = [date.strftime('%Y-%m-%d') for date in df.index.date]
        prices = df['price'].tolist()
        
        return json.dumps({
            'labels': labels,
            'prices': prices,
            'product_name': product.name,
            'currency': product.currency
        })


class MLPredictor:
    """Machine Learning utility class for price and demand prediction."""
    
    def __init__(self):
        """Initialize ML models and scalers."""
        self.linear_model = LinearRegression()
        self.rf_model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
    
    def prepare_features(self, df: pd.DataFrame) -> Tuple[np.ndarray, np.ndarray]:
        """Prepare features for machine learning models."""
        if df.empty or len(df) < 5:
            return np.array([]), np.array([])
        
        df_features = df.copy()
        df_features['price_lag_1'] = df_features['price'].shift(1)
        df_features['price_lag_2'] = df_features['price'].shift(2)
        df_features['price_lag_3'] = df_features['price'].shift(3)
        
        df_features['price_ma_3'] = df_features['price'].rolling(3).mean()
        df_features['price_ma_7'] = df_features['price'].rolling(7).mean()
        df_features['price_std_3'] = df_features['price'].rolling(3).std()
        
        df_features['day_of_week'] = df_features.index.dayofweek
        df_features['day_of_month'] = df_features.index.day
        df_features['month'] = df_features.index.month
        
        df_features = df_features.dropna()
        
        if len(df_features) < 3:
            return np.array([]), np.array([])
        
        feature_columns = [
            'price_lag_1', 'price_lag_2', 'price_lag_3',
            'price_ma_3', 'price_ma_7', 'price_std_3',
            'day_of_week', 'day_of_month', 'month'
        ]
        
        X = df_features[feature_columns].values
        y = df_features['price'].values
        
        return X, y
    
    def predict_linear_regression(self, product, days_ahead: int = 7) -> List[Dict]:
        """Predict future prices using Linear Regression."""
        try:
            df = DataProcessor.get_price_history_dataframe(product, days=60)
            if df.empty:
                return []
            
            X, y = self.prepare_features(df)
            if len(X) == 0:
                return []
            
            X_scaled = self.scaler.fit_transform(X)
            
            if len(X_scaled) > 10:
                X_train, X_test, y_train, y_test = train_test_split(
                    X_scaled, y, test_size=0.2, random_state=42
                )
            else:
                X_train, X_test, y_train, y_test = X_scaled, X_scaled, y, y
            
            self.linear_model.fit(X_train, y_train)
            
            if len(X_test) > 0:
                y_pred_test = self.linear_model.predict(X_test)
                r2 = r2_score(y_test, y_pred_test)
                confidence = max(0, min(1, r2))
            else:
                confidence = 0.5
            
            predictions = []
            current_price = float(df['price'].iloc[-1])
            
            for i in range(days_ahead):
                if len(df) >= 3:
                    recent_prices = df['price'].tail(3).values
                    trend = np.mean(np.diff(recent_prices))
                    pred_price = current_price + (trend * (i + 1))
                else:
                    pred_price = current_price
                
                pred_price = max(current_price * 0.5, min(current_price * 2.0, pred_price))
                
                prediction_date = timezone.now().date() + timedelta(days=i+1)
                
                predictions.append({
                    'date': prediction_date,
                    'predicted_price': round(pred_price, 2),
                    'confidence_score': confidence,
                    'model_type': 'linear_regression'
                })
            
            return predictions
            
        except Exception as e:
            logger.error(f"Error in linear regression prediction: {str(e)}")
            return []
    
    def predict_demand(self, product) -> float:
        """Predict demand score based on price trends and volatility."""
        try:
            df = DataProcessor.get_price_history_dataframe(product, days=30)
            if df.empty:
                return 0.5
            
            if len(df) >= 2:
                price_trend = (df['price'].iloc[-1] - df['price'].iloc[0]) / df['price'].iloc
                trend_factor = max(0, 1 - price_trend)
            else:
                trend_factor = 0.5
            
            if len(df) >= 3:
                volatility = np.std(df['price']) / np.mean(df['price'])
                volatility_factor = max(0, 1 - volatility)
            else:
                volatility_factor = 0.5
            
            demand_score = (trend_factor * 0.6 + volatility_factor * 0.4)
            return max(0.1, min(0.9, demand_score))
            
        except Exception as e:
            logger.error(f"Error predicting demand: {str(e)}")
            return 0.5


class ChartGenerator:
    """Chart generation utility class using Matplotlib."""
    
    def __init__(self):
        """Initialize chart styling."""
        plt.style.use('default')
        plt.rcParams['figure.figsize'] = (12, 6)
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['font.size'] = 10
    
    def generate_price_trend_chart(self, product) -> str:
        """Generate a price trend chart using Matplotlib."""
        try:
            df = DataProcessor.get_price_history_dataframe(product, days=60)
            if df.empty:
                return self._create_no_data_chart("No price history available")
            
            fig, ax = plt.subplots(figsize=(12, 6))
            
            ax.plot(df.index, df['price'], linewidth=2, color='#2E86AB', label='Price', marker='o', markersize=3)
            
            df_with_ma = DataProcessor.calculate_moving_averages(df, [7, 14])
            if 'ma_7' in df_with_ma.columns:
                ax.plot(df_with_ma.index, df_with_ma['ma_7'], 
                       linewidth=1, color='#A23B72', alpha=0.7, label='7-day MA')
            if 'ma_14' in df_with_ma.columns:
                ax.plot(df_with_ma.index, df_with_ma['ma_14'], 
                       linewidth=1, color='#F18F01', alpha=0.7, label='14-day MA')
            
            if product.alert_threshold:
                ax.axhline(y=float(product.alert_threshold), color='red', 
                          linestyle='--', alpha=0.5, label='Alert Threshold')
            
            ax.set_title(f'Price Trend - {product.name}', fontsize=14, fontweight='bold')
            ax.set_xlabel('Date')
            ax.set_ylabel(f'Price ({product.currency})')
            ax.legend()
            ax.grid(True, alpha=0.3)
            
            ax.xaxis.set_major_formatter(mdates.DateFormatter('%m/%d'))
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            return self._fig_to_base64(fig)
            
        except Exception as e:
            logger.error(f"Error generating price trend chart: {str(e)}")
            return self._create_error_chart("Error generating chart")
    
    def _fig_to_base64(self, fig) -> str:
        """Convert matplotlib figure to base64 string for web display."""
        buffer = io.BytesIO()
        fig.savefig(buffer, format='png', bbox_inches='tight', dpi=100)
        buffer.seek(0)
        image_png = buffer.getvalue()
        buffer.close()
        plt.close(fig)  # Important: close figure to free memory
        
        graphic = base64.b64encode(image_png)
        return graphic.decode('utf-8')
    
    def _create_no_data_chart(self, message: str) -> str:
        """Create a simple chart showing no data message."""
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return self._fig_to_base64(fig)
    
    def _create_error_chart(self, message: str) -> str:
        """Create a simple chart showing error message."""
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, message, ha='center', va='center', fontsize=14, color='red')
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        return self._fig_to_base64(fig)


# Utility functions
def calculate_price_change_percentage(product, days: int = 30) -> Optional[float]:
    """Calculate the percentage change in price over a specified period."""
    try:
        df = DataProcessor.get_price_history_dataframe(product, days)
        
        if df.empty or len(df) < 2:
            return None
        
        current_price = df['price'].iloc[-1]
        past_price = df['price'].iloc[0]
        
        if past_price == 0:
            return None
        
        return ((current_price - past_price) / past_price) * 100
        
    except Exception as e:
        logger.error(f"Error calculating price change: {str(e)}")
        return None


def check_alert_conditions(alert) -> bool:
    """Check if alert conditions are met and trigger notifications."""
    if alert.status != 'active':
        return False
    
    product = alert.product
    
    if not product.current_price:
        return False
    
    current_price = float(product.current_price)
    threshold = float(alert.threshold_value)
    
    triggered = False
    
    if alert.alert_type == 'price_drop' and current_price <= threshold:
        triggered = True
    elif alert.alert_type == 'price_increase' and current_price >= threshold:
        triggered = True
    
    if triggered:
        alert.status = 'triggered'
        alert.triggered_at = timezone.now()
        alert.save()
        
        send_alert_notification(alert)
        
        logger.info(f"Alert triggered for {product.name}: {alert.alert_type}")
        return True
    
    return False


def send_alert_notification(alert):
    """Send alert notifications via email."""
    product = alert.product
    user = alert.user
    
    try:
        subject = f'Price Alert: {product.name}'
        
        context = {
            'user': user,
            'product': product,
            'alert': alert,
            'current_price': product.current_price,
            'threshold': alert.threshold_value,
            'price_url': product.url,
        }
        
        try:
            html_message = render_to_string('tracker/email/price_alert.html', context)
            plain_message = strip_tags(html_message)
        except:
            plain_message = f"""
            Hello {user.first_name or user.username},
            
            Your price alert for "{product.name}" has been triggered!
            
            Alert Type: {alert.get_alert_type_display()}
            Current Price: {product.current_price} {product.currency}
            Your Threshold: {alert.threshold_value} {product.currency}
            
            View product: {product.url}
            
            Best regards,
            Price Tracker Team
            """
            html_message = None
        
        if alert.email_notification and user.email:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=getattr(settings, 'DEFAULT_FROM_EMAIL', 'noreply@example.com'),
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Alert email sent to {user.email} for product {product.name}")
            
    except Exception as e:
        logger.error(f"Failed to send alert notification: {str(e)}")


def update_product_prices():
    """Update prices for all active products."""
    from .models import Product, PriceHistory
    
    scraper = WebScraper()
    active_products = Product.objects.filter(is_active=True)
    
    updated_count = 0
    failed_count = 0
    
    logger.info(f"Starting price update for {active_products.count()} products")
    
    for product in active_products:
        try:
            price, status = scraper.scrape_price(product)
            
            if price and status == 'success':
                old_price = product.current_price
                product.current_price = price
                product.last_scraped = timezone.now()
                product.save()
                
                PriceHistory.objects.create(
                    product=product,
                    price=price,
                    currency=product.currency,
                    source='automated_scraper'
                )
                
                updated_count += 1
                logger.info(f"Updated price for {product.name}: {old_price} -> {price}")
                
                for alert in product.alerts.filter(status='active'):
                    check_alert_conditions(alert)
                    
            else:
                failed_count += 1
                logger.warning(f"Failed to update price for {product.name}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error updating price for {product.name}: {str(e)}")
    
    logger.info(f"Price update completed: {updated_count} updated, {failed_count} failed")
    return updated_count, failed_count


def generate_predictions_for_product(product):
    """Generate ML predictions for a specific product."""
    from .models import DemandPrediction
    
    try:
        predictor = MLPredictor()
        
        linear_predictions = predictor.predict_linear_regression(product, days_ahead=7)
        
        prediction_count = 0
        
        for pred in linear_predictions:
            demand_score = predictor.predict_demand(product)
            
            prediction, created = DemandPrediction.objects.update_or_create(
                product=product,
                prediction_date=pred['date'],
                model_type=pred['model_type'],
                defaults={
                    'predicted_demand': demand_score,
                    'predicted_price': pred['predicted_price'],
                    'confidence_score': pred['confidence_score'],
                    'model_version': '1.0'
                }
            )
            
            if created:
                prediction_count += 1
        
        logger.info(f"Generated {prediction_count} predictions for {product.name}")
        return prediction_count
        
    except Exception as e:
        logger.error(f"Error generating predictions for {product.name}: {str(e)}")
        return 0
