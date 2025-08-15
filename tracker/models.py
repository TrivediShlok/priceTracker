"""
Django models for the Price Tracker application.

This module defines the database models for tracking products, price history,
and demand predictions.
"""

from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator, URLValidator
from django.utils import timezone
import uuid


class Product(models.Model):
    """
    Model to store product information for price tracking.
    
    This model represents a product that users want to track for price changes.
    It stores basic product information and tracking preferences.
    """
    
    # Product identification
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200, help_text="Product name")
    url = models.URLField(validators=[URLValidator()], help_text="Product URL from Amazon/Flipkart")
    
    # Current price information
    current_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Current price of the product"
    )
    currency = models.CharField(max_length=3, default='INR', help_text="Currency code")
    
    # Tracking preferences
    alert_threshold = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Price threshold for alerts"
    )
    is_active = models.BooleanField(default=True, help_text="Whether to track this product")
    
    # Metadata
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    last_scraped = models.DateTimeField(null=True, blank=True)
    
    # User relationship
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='products')
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Product"
        verbose_name_plural = "Products"
    
    def __str__(self):
        return f"{self.name} - {self.current_price} {self.currency}"
    
    @property
    def price_change_percentage(self):
        """Calculate the percentage change in price over the last 30 days."""
        from .utils import calculate_price_change_percentage
        return calculate_price_change_percentage(self)
    
    @property
    def is_price_dropped(self):
        """Check if current price is below alert threshold."""
        if self.alert_threshold and self.current_price:
            return self.current_price < self.alert_threshold
        return False


class PriceHistory(models.Model):
    """
    Model to store historical price data for products.
    
    This model tracks price changes over time, enabling trend analysis
    and price prediction using machine learning algorithms.
    """
    
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='price_history')
    
    # Price data
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='INR')
    
    # Timestamp
    recorded_at = models.DateTimeField(default=timezone.now)
    
    # Additional metadata
    source = models.CharField(max_length=50, default='scraper', help_text="Source of price data")
    is_valid = models.BooleanField(default=True, help_text="Whether this price data is valid")
    
    class Meta:
        ordering = ['-recorded_at']
        verbose_name = "Price History"
        verbose_name_plural = "Price History"
        # Ensure unique price records per product per day
        unique_together = ['product', 'recorded_at']
    
    def __str__(self):
        return f"{self.product.name} - {self.price} {self.currency} at {self.recorded_at}"
    
    @property
    def date(self):
        """Return just the date part of the timestamp."""
        return self.recorded_at.date()


class DemandPrediction(models.Model):
    """
    Model to store demand predictions for products.
    
    This model stores machine learning predictions for future demand
    and price trends, helping users make informed decisions.
    """
    
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='demand_predictions')
    
    # Prediction data
    predicted_demand = models.FloatField(help_text="Predicted demand score")
    predicted_price = models.DecimalField(
        max_digits=10, 
        decimal_places=2, 
        null=True, 
        blank=True,
        help_text="Predicted price"
    )
    confidence_score = models.FloatField(
        default=0.0,
        validators=[MinValueValidator(0.0)],
        help_text="Confidence score for the prediction (0-1)"
    )
    
    # Prediction period
    prediction_date = models.DateField(help_text="Date for which prediction is made")
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Model metadata
    model_type = models.CharField(
        max_length=50, 
        default='linear_regression',
        help_text="Type of ML model used for prediction"
    )
    model_version = models.CharField(max_length=20, default='1.0')
    
    class Meta:
        ordering = ['-prediction_date']
        verbose_name = "Demand Prediction"
        verbose_name_plural = "Demand Predictions"
        unique_together = ['product', 'prediction_date', 'model_type']
    
    def __str__(self):
        return f"{self.product.name} - {self.predicted_demand:.2f} demand on {self.prediction_date}"


class PriceAlert(models.Model):
    """
    Model to store user price alerts and notifications.
    
    This model manages user alerts for price drops and sends
    notifications when conditions are met.
    """
    
    ALERT_TYPES = [
        ('price_drop', 'Price Drop'),
        ('price_increase', 'Price Increase'),
        ('demand_spike', 'Demand Spike'),
    ]
    
    STATUS_CHOICES = [
        ('active', 'Active'),
        ('triggered', 'Triggered'),
        ('disabled', 'Disabled'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='alerts')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='alerts')
    
    # Alert configuration
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='price_drop')
    threshold_value = models.DecimalField(max_digits=10, decimal_places=2)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='active')
    
    # Notification settings
    email_notification = models.BooleanField(default=True)
    web_notification = models.BooleanField(default=True)
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    triggered_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-created_at']
        verbose_name = "Price Alert"
        verbose_name_plural = "Price Alerts"
    
    def __str__(self):
        return f"{self.user.username} - {self.product.name} {self.alert_type} alert"
    
    def check_and_trigger(self):
        """Check if alert conditions are met and trigger if necessary."""
        from .utils import check_alert_conditions
        return check_alert_conditions(self)


class ScrapingLog(models.Model):
    """
    Model to log scraping activities and errors.
    
    This model helps track scraping performance, errors, and
    provides debugging information for web scraping operations.
    """
    
    STATUS_CHOICES = [
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial Success'),
    ]
    
    id = models.BigAutoField(primary_key=True)
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='scraping_logs')
    
    # Scraping results
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    scraped_price = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    error_message = models.TextField(blank=True, null=True)
    
    # Performance metrics
    response_time = models.FloatField(null=True, blank=True, help_text="Response time in seconds")
    retry_count = models.IntegerField(default=0)
    
    # Timestamps
    started_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    
    class Meta:
        ordering = ['-started_at']
        verbose_name = "Scraping Log"
        verbose_name_plural = "Scraping Logs"
    
    def __str__(self):
        return f"{self.product.name} - {self.status} at {self.started_at}"
    
    @property
    def duration(self):
        """Calculate scraping duration."""
        if self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None
