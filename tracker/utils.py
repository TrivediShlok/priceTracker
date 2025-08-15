"""
Utility functions for the Price Tracker application.

This module contains functions for web scraping, data processing,
machine learning predictions, and visualization.
"""

import requests
import time
import logging
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional, Dict, List, Tuple
import re

# Web scraping imports
from bs4 import BeautifulSoup
from fake_useragent import UserAgent

# Data processing imports
from django.utils import timezone
from django.conf import settings

# Django imports
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils.html import strip_tags

# Local imports
from .models import Product, PriceHistory, DemandPrediction, PriceAlert, ScrapingLog

# Configure logging
logger = logging.getLogger(__name__)


class WebScraper:
    """Web scraping utility class for extracting product prices."""
    
    def __init__(self):
        """Initialize the scraper with configuration."""
        self.session = requests.Session()
        self.ua = UserAgent()
        self.session.headers.update({
            'User-Agent': self.ua.random,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Accept-Encoding': 'gzip, deflate',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        })
    
    def scrape_amazon_price(self, url: str) -> Optional[Decimal]:
        """Scrape price from Amazon product page."""
        try:
            time.sleep(settings.SCRAPING_DELAY)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Common Amazon price selectors
            price_selectors = [
                'span.a-price-whole',
                'span.a-offscreen',
                'span.a-price span.a-offscreen',
                'span#priceblock_ourprice',
                'span#priceblock_dealprice',
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_match = re.search(r'[\d,]+\.?\d*', price_text.replace(',', ''))
                    if price_match:
                        return Decimal(price_match.group())
            
            return None
            
        except Exception as e:
            logger.error(f"Error scraping Amazon price from {url}: {str(e)}")
            return None
    
    def scrape_flipkart_price(self, url: str) -> Optional[Decimal]:
        """Scrape price from Flipkart product page."""
        try:
            time.sleep(settings.SCRAPING_DELAY)
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Common Flipkart price selectors
            price_selectors = [
                'div._30jeq3._16Jk6d',
                'div._1vC4OE._3qQ9m1',
                'div._30jeq3',
            ]
            
            for selector in price_selectors:
                price_element = soup.select_one(selector)
                if price_element:
                    price_text = price_element.get_text().strip()
                    price_match = re.search(r'[\d,]+', price_text.replace(',', ''))
                    if price_match:
                        return Decimal(price_match.group())
            
            return None
            
        except Exception as e:
            logger.error(f"Error scraping Flipkart price from {url}: {str(e)}")
            return None
    
    def scrape_price(self, product: Product) -> Tuple[Optional[Decimal], str]:
        """Scrape price for a given product."""
        start_time = time.time()
        log_entry = ScrapingLog.objects.create(
            product=product,
            status='failed',
            started_at=timezone.now()
        )
        
        try:
            url = product.url.lower()
            
            if 'amazon' in url:
                price = self.scrape_amazon_price(product.url)
            elif 'flipkart' in url:
                price = self.scrape_flipkart_price(product.url)
            else:
                price = None
            
            # Update log entry
            log_entry.status = 'success' if price else 'failed'
            log_entry.scraped_price = price
            log_entry.response_time = time.time() - start_time
            log_entry.completed_at = timezone.now()
            log_entry.save()
            
            return price, log_entry.status
            
        except Exception as e:
            log_entry.error_message = str(e)
            log_entry.response_time = time.time() - start_time
            log_entry.completed_at = timezone.now()
            log_entry.save()
            return None, 'failed'


class DataProcessor:
    """Data processing utility class for cleaning and analyzing price data."""
    
    @staticmethod
    def get_price_history_dataframe(product: Product, days: int = 30):
        """Get price history as a list of dictionaries."""
        end_date = timezone.now()
        start_date = end_date - timedelta(days=days)
        
        history = PriceHistory.objects.filter(
            product=product,
            recorded_at__gte=start_date,
            is_valid=True
        ).order_by('recorded_at')
        
        if not history.exists():
            return []
        
        data = []
        for record in history:
            data.append({
                'date': record.recorded_at.date(),
                'price': float(record.price),
                'timestamp': record.recorded_at
            })
        
        return data
    
    @staticmethod
    def calculate_moving_averages(data, windows: List[int] = [7, 14, 30]):
        """Calculate moving averages for price trends."""
        if not data:
            return data
        
        result = data.copy()
        
        for window in windows:
            if len(result) >= window:
                for i in range(window - 1, len(result)):
                    window_data = result[i - window + 1:i + 1]
                    avg_price = sum(item['price'] for item in window_data) / len(window_data)
                    result[i][f'ma_{window}'] = avg_price
        
        return result
    
    @staticmethod
    def clean_price_data(data):
        """Clean price data by removing outliers and invalid values."""
        if not data:
            return data
        
        # Remove negative prices
        cleaned_data = [item for item in data if item['price'] > 0]
        
        # Remove duplicate dates (keep latest)
        seen_dates = set()
        unique_data = []
        for item in reversed(cleaned_data):
            if item['date'] not in seen_dates:
                seen_dates.add(item['date'])
                unique_data.append(item)
        
        return list(reversed(unique_data))


def calculate_price_change_percentage(product: Product, days: int = 30) -> Optional[float]:
    """Calculate the percentage change in price over a specified period."""
    data = DataProcessor.get_price_history_dataframe(product, days)
    
    if len(data) < 2:
        return None
    
    current_price = data[-1]['price']
    past_price = data[0]['price']
    
    if past_price == 0:
        return None
    
    return ((current_price - past_price) / past_price) * 100


def check_alert_conditions(alert: PriceAlert) -> bool:
    """Check if alert conditions are met and trigger if necessary."""
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
        # Update alert status
        alert.status = 'triggered'
        alert.triggered_at = timezone.now()
        alert.save()
        
        # Send notifications
        send_alert_notification(alert)
        
        return True
    
    return False


def send_alert_notification(alert: PriceAlert):
    """Send alert notifications via email and web."""
    product = alert.product
    user = alert.user
    
    # Prepare email content
    subject = f'Price Alert: {product.name}'
    
    context = {
        'user': user,
        'product': product,
        'alert': alert,
        'current_price': product.current_price,
        'threshold': alert.threshold_value,
    }
    
    html_message = render_to_string('tracker/email/price_alert.html', context)
    plain_message = strip_tags(html_message)
    
    # Send email notification
    if alert.email_notification and user.email:
        try:
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False,
            )
            logger.info(f"Alert email sent to {user.email} for product {product.name}")
        except Exception as e:
            logger.error(f"Failed to send alert email: {str(e)}")


def update_product_prices():
    """Update prices for all active products."""
    scraper = WebScraper()
    active_products = Product.objects.filter(is_active=True)
    
    updated_count = 0
    failed_count = 0
    
    for product in active_products:
        try:
            price, status = scraper.scrape_price(product)
            
            if price and status == 'success':
                # Update product price
                product.current_price = price
                product.last_scraped = timezone.now()
                product.save()
                
                # Create price history record
                PriceHistory.objects.create(
                    product=product,
                    price=price,
                    currency=product.currency,
                    source='scraper'
                )
                
                updated_count += 1
                logger.info(f"Updated price for {product.name}: {price}")
            else:
                failed_count += 1
                logger.warning(f"Failed to update price for {product.name}")
                
        except Exception as e:
            failed_count += 1
            logger.error(f"Error updating price for {product.name}: {str(e)}")
    
    logger.info(f"Price update completed: {updated_count} updated, {failed_count} failed")
    return updated_count, failed_count
