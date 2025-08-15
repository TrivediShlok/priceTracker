#!/usr/bin/env python
"""
Simple test script to verify the Price Tracker application works correctly.
"""

import os
import sys
import django

# Add the project directory to the Python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Set up Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'price_tracker.settings')
django.setup()

from django.contrib.auth.models import User
from tracker.models import Product, PriceHistory
from tracker.utils import WebScraper, DataProcessor

def test_basic_functionality():
    """Test basic application functionality."""
    print("Testing Price Tracker Application...")
    print("=" * 50)
    
    # Test 1: Check if superuser exists
    try:
        user = User.objects.filter(is_superuser=True).first()
        if user:
            print(f"✓ Superuser found: {user.username}")
        else:
            print("✗ No superuser found")
    except Exception as e:
        print(f"✗ Error checking superuser: {e}")
    
    # Test 2: Check if models can be created
    try:
        # Create a test user if none exists
        test_user, created = User.objects.get_or_create(
            username='testuser',
            defaults={'email': 'test@example.com'}
        )
        if created:
            test_user.set_password('testpass123')
            test_user.save()
            print("✓ Test user created")
        else:
            print("✓ Test user already exists")
        
        # Create a test product
        test_product, created = Product.objects.get_or_create(
            name='Test Product',
            user=test_user,
            defaults={
                'url': 'https://amazon.in/test-product',
                'currency': 'INR',
                'current_price': 1000.00,
                'alert_threshold': 800.00
            }
        )
        if created:
            print("✓ Test product created")
        else:
            print("✓ Test product already exists")
        
        # Create test price history
        price_record, created = PriceHistory.objects.get_or_create(
            product=test_product,
            price=1000.00,
            defaults={
                'currency': 'INR',
                'source': 'test'
            }
        )
        if created:
            print("✓ Test price history created")
        else:
            print("✓ Test price history already exists")
            
    except Exception as e:
        print(f"✗ Error creating test data: {e}")
    
    # Test 3: Test utility functions
    try:
        scraper = WebScraper()
        print("✓ WebScraper initialized")
        
        processor = DataProcessor()
        print("✓ DataProcessor initialized")
        
        # Test price change calculation
        change = DataProcessor.get_price_history_dataframe(test_product, days=30)
        print(f"✓ Price history data retrieved: {len(change)} records")
        
    except Exception as e:
        print(f"✗ Error testing utilities: {e}")
    
    # Test 4: Check database connection
    try:
        product_count = Product.objects.count()
        user_count = User.objects.count()
        print(f"✓ Database connection working - {product_count} products, {user_count} users")
    except Exception as e:
        print(f"✗ Database connection error: {e}")
    
    print("=" * 50)
    print("Test completed!")

if __name__ == '__main__':
    test_basic_functionality()
