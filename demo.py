#!/usr/bin/env python
"""
Demo script for the Price Tracker application.
This script demonstrates the key features and functionality.
"""

import os
import sys
import django
from datetime import datetime, timedelta

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracker.settings')
django.setup()

from django.contrib.auth.models import User
from tracker.models import Product, PriceHistory, PriceAlert, DemandPrediction
from tracker.utils import WebScraper, DataProcessor, calculate_price_change_percentage

def create_demo_data():
    """Create demo data to showcase the application."""
    print("Creating demo data for Price Tracker...")
    print("=" * 60)
    
    # Create demo user
    demo_user, created = User.objects.get_or_create(
        username='demo_user',
        defaults={
            'email': 'demo@example.com',
            'first_name': 'Demo',
            'last_name': 'User'
        }
    )
    if created:
        demo_user.set_password('demo123')
        demo_user.save()
        print("✓ Created demo user: demo_user (password: demo123)")
    else:
        print("✓ Demo user already exists")
    
    # Create demo products
    demo_products = [
        {
            'name': 'iPhone 15 Pro',
            'url': 'https://amazon.in/iphone-15-pro',
            'currency': 'INR',
            'current_price': 129999.00,
            'alert_threshold': 119999.00
        },
        {
            'name': 'Samsung Galaxy S24',
            'url': 'https://flipkart.com/samsung-galaxy-s24',
            'currency': 'INR',
            'current_price': 89999.00,
            'alert_threshold': 84999.00
        },
        {
            'name': 'MacBook Air M2',
            'url': 'https://amazon.in/macbook-air-m2',
            'currency': 'INR',
            'current_price': 99999.00,
            'alert_threshold': 94999.00
        }
    ]
    
    created_products = []
    for product_data in demo_products:
        product, created = Product.objects.get_or_create(
            name=product_data['name'],
            user=demo_user,
            defaults=product_data
        )
        if created:
            print(f"✓ Created product: {product.name}")
        else:
            print(f"✓ Product already exists: {product.name}")
        created_products.append(product)
    
    # Create price history for each product
    for product in created_products:
        # Create price history over the last 30 days
        base_price = float(product.current_price)
        for i in range(30):
            date = datetime.now() - timedelta(days=30-i)
            # Simulate price fluctuations
            price_variation = (i % 7 - 3) * 0.02  # ±6% variation
            price = base_price * (1 + price_variation)
            
            PriceHistory.objects.get_or_create(
                product=product,
                recorded_at=date,
                defaults={
                    'price': price,
                    'currency': product.currency,
                    'source': 'demo'
                }
            )
        print(f"✓ Created price history for {product.name}")
    
    # Create some alerts
    for product in created_products[:2]:  # Create alerts for first 2 products
        alert, created = PriceAlert.objects.get_or_create(
            product=product,
            alert_type='price_drop',
            defaults={
                'user': demo_user,
                'threshold_value': product.alert_threshold,
                'email_notification': True,
                'web_notification': True
            }
        )
        if created:
            print(f"✓ Created price alert for {product.name}")
    
    # Create some predictions
    for product in created_products:
        for i in range(1, 8):  # Next 7 days
            pred_date = datetime.now().date() + timedelta(days=i)
            predicted_price = float(product.current_price) * (1 + (i * 0.01))  # Gradual increase
            
            DemandPrediction.objects.get_or_create(
                product=product,
                prediction_date=pred_date,
                model_type='simple_trend',
                defaults={
                    'predicted_demand': 0.7 + (i * 0.02),
                    'predicted_price': predicted_price,
                    'confidence_score': 0.8 - (i * 0.05),
                    'model_version': '1.0'
                }
            )
        print(f"✓ Created predictions for {product.name}")
    
    print("=" * 60)
    print("Demo data created successfully!")
    print("\nYou can now:")
    print("1. Start the server: python manage.py runserver")
    print("2. Go to http://127.0.0.1:8000/")
    print("3. Login with: demo_user / demo123")
    print("4. Explore the dashboard and features!")

def show_statistics():
    """Show current application statistics."""
    print("\nCurrent Application Statistics:")
    print("=" * 40)
    
    user_count = User.objects.count()
    product_count = Product.objects.count()
    price_history_count = PriceHistory.objects.count()
    alert_count = PriceAlert.objects.count()
    prediction_count = DemandPrediction.objects.count()
    
    print(f"Users: {user_count}")
    print(f"Products: {product_count}")
    print(f"Price History Records: {price_history_count}")
    print(f"Active Alerts: {alert_count}")
    print(f"Predictions: {prediction_count}")
    
    # Show recent price changes
    print("\nRecent Price Changes:")
    print("-" * 20)
    for product in Product.objects.all()[:3]:
        change = calculate_price_change_percentage(product, days=7)
        if change is not None:
            direction = "↗️" if change > 0 else "↘️" if change < 0 else "➡️"
            print(f"{direction} {product.name}: {change:+.2f}%")

if __name__ == '__main__':
    create_demo_data()
    show_statistics()
