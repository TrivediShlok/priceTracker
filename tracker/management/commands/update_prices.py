"""
Django management command for updating product prices and predictions.

This command can be run manually or scheduled to automatically update
prices for all active products and generate new predictions.
"""

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from django.db import transaction
import logging

from tracker.models import Product, PriceHistory, DemandPrediction
from tracker.utils import update_product_prices, WebScraper, DataProcessor

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    """Management command for updating product prices and predictions."""
    
    help = 'Update prices for all active products and generate predictions'
    
    def add_arguments(self, parser):
        """Add command line arguments."""
        parser.add_argument(
            '--force',
            action='store_true',
            help='Force update even if recently updated',
        )
        parser.add_argument(
            '--product-id',
            type=str,
            help='Update specific product by ID',
        )
        parser.add_argument(
            '--skip-predictions',
            action='store_true',
            help='Skip generating predictions',
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be updated without making changes',
        )
    
    def handle(self, *args, **options):
        """Execute the command."""
        self.stdout.write(
            self.style.SUCCESS('Starting price update process...')
        )
        
        # Get products to update
        if options['product_id']:
            try:
                products = Product.objects.filter(
                    id=options['product_id'],
                    is_active=True
                )
                if not products.exists():
                    raise CommandError(f'Product with ID {options["product_id"]} not found or not active')
            except Exception as e:
                raise CommandError(f'Invalid product ID: {e}')
        else:
            products = Product.objects.filter(is_active=True)
            
            # Skip recently updated products unless forced
            if not options['force']:
                recent_threshold = timezone.now() - timezone.timedelta(hours=6)
                products = products.filter(
                    last_scraped__lt=recent_threshold
                )
        
        if not products.exists():
            self.stdout.write(
                self.style.WARNING('No products to update.')
            )
            return
        
        self.stdout.write(f'Found {products.count()} products to update.')
        
        if options['dry_run']:
            self.stdout.write('DRY RUN - No changes will be made.')
            for product in products:
                self.stdout.write(f'  - {product.name} (ID: {product.id})')
            return
        
        # Update prices
        updated_count, failed_count = self._update_prices(products)
        
        # Generate predictions (if not skipped)
        if not options['skip_predictions']:
            prediction_count = self._generate_predictions(products)
        else:
            prediction_count = 0
        
        # Summary
        self.stdout.write(
            self.style.SUCCESS(
                f'Update completed: {updated_count} prices updated, '
                f'{failed_count} failed, {prediction_count} predictions generated.'
            )
        )
    
    def _update_prices(self, products):
        """Update prices for the given products."""
        self.stdout.write('Updating product prices...')
        
        updated_count = 0
        failed_count = 0
        
        for product in products:
            try:
                self.stdout.write(f'  Updating {product.name}...')
                
                with transaction.atomic():
                    # Use the utility function
                    scraper = WebScraper()
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
                            source='management_command'
                        )
                        
                        updated_count += 1
                        self.stdout.write(
                            self.style.SUCCESS(f'    ✓ Updated: {price} {product.currency}')
                        )
                    else:
                        failed_count += 1
                        self.stdout.write(
                            self.style.ERROR(f'    ✗ Failed to update price')
                        )
                        
            except Exception as e:
                failed_count += 1
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Error: {str(e)}')
                )
                logger.error(f'Error updating price for {product.name}: {str(e)}')
        
        return updated_count, failed_count
    
    def _generate_predictions(self, products):
        """Generate predictions for products with sufficient data."""
        self.stdout.write('Generating predictions...')
        
        prediction_count = 0
        
        for product in products:
            try:
                # Check if product has enough price history
                price_history = PriceHistory.objects.filter(
                    product=product,
                    is_valid=True
                ).count()
                
                if price_history < 10:  # Minimum data points for prediction
                    self.stdout.write(f'  Skipping {product.name} - insufficient data ({price_history} records)')
                    continue
                
                self.stdout.write(f'  Generating predictions for {product.name}...')
                
                # Simple prediction based on recent trend
                recent_prices = PriceHistory.objects.filter(
                    product=product,
                    is_valid=True
                ).order_by('-recorded_at')[:7]
                
                if recent_prices.count() >= 3:
                    prices = [float(ph.price) for ph in recent_prices]
                    avg_price = sum(prices) / len(prices)
                    
                    # Simple trend calculation
                    if len(prices) >= 2:
                        trend = (prices[0] - prices[-1]) / len(prices)
                        
                        # Generate predictions for next 7 days
                        for i in range(1, 8):
                            predicted_date = timezone.now().date() + timezone.timedelta(days=i)
                            predicted_price = max(0, avg_price + (trend * i))
                            
                            # Create or update prediction
                            prediction, created = DemandPrediction.objects.update_or_create(
                                product=product,
                                prediction_date=predicted_date,
                                model_type='simple_trend',
                                defaults={
                                    'predicted_demand': 0.5,  # Placeholder
                                    'predicted_price': predicted_price,
                                    'confidence_score': 0.6,
                                    'model_version': '1.0'
                                }
                            )
                            
                            if created:
                                prediction_count += 1
                        
                        self.stdout.write(
                            self.style.SUCCESS(f'    ✓ Generated 7 predictions')
                        )
                    else:
                        self.stdout.write(
                            self.style.WARNING(f'    - Insufficient data for trend calculation')
                        )
                else:
                    self.stdout.write(
                        self.style.WARNING(f'    - Insufficient recent price data')
                    )
                    
            except Exception as e:
                self.stdout.write(
                    self.style.ERROR(f'    ✗ Error generating predictions: {str(e)}')
                )
                logger.error(f'Error generating predictions for {product.name}: {str(e)}')
        
        return prediction_count
