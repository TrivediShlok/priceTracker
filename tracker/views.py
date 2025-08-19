"""
Django views for the Price Tracker application with all missing functions.
"""

import json
import csv
from datetime import datetime, timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse, Http404
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Avg, Max, Min
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.cache import cache_page
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib import messages
from django.urls import reverse
import logging

# Local imports
from .models import Product, PriceHistory, DemandPrediction, PriceAlert, ScrapingLog
from .forms import ProductForm, AlertForm, UserRegistrationForm, ProductSearchForm, ExportForm
from .utils import (
    WebScraper, DataProcessor, ChartGenerator, MLPredictor,
    calculate_price_change_percentage, update_product_prices,
    generate_predictions_for_product
)

logger = logging.getLogger(__name__)


class DashboardView(LoginRequiredMixin, ListView):
    """Enhanced dashboard view with comprehensive analytics."""
    
    model = Product
    template_name = 'tracker/dashboard.html'
    context_object_name = 'products'
    paginate_by = 10
    
    def get_queryset(self):
        """Get products for the current user with annotations."""
        queryset = Product.objects.filter(user=self.request.user).annotate(
            price_history_count=Count('price_history'),
            avg_price=Avg('price_history__price'),
            latest_price_date=Max('price_history__recorded_at')
        )
        
        # Apply search filters
        search_form = ProductSearchForm(self.request.GET)
        if search_form.is_valid():
            search_query = search_form.cleaned_data.get('search_query')
            min_price = search_form.cleaned_data.get('min_price')
            max_price = search_form.cleaned_data.get('max_price')
            currency = search_form.cleaned_data.get('currency')
            is_active = search_form.cleaned_data.get('is_active')
            
            if search_query:
                queryset = queryset.filter(
                    Q(name__icontains=search_query) | 
                    Q(url__icontains=search_query)
                )
            
            if min_price:
                queryset = queryset.filter(current_price__gte=min_price)
            
            if max_price:
                queryset = queryset.filter(current_price__lte=max_price)
            
            if currency:
                queryset = queryset.filter(currency=currency)
            
            if is_active:
                is_active_bool = is_active == 'True'
                queryset = queryset.filter(is_active=is_active_bool)
        
        return queryset.order_by('-created_at')
    
    def get_context_data(self, **kwargs):
        """Add comprehensive context data."""
        context = super().get_context_data(**kwargs)
        
        # Add search form
        context['search_form'] = ProductSearchForm(self.request.GET)
        
        # Get user products for statistics
        user_products = Product.objects.filter(user=self.request.user)
        context['total_products'] = user_products.count()
        context['active_products'] = user_products.filter(is_active=True).count()
        
        # Fixed alert counting
        products_with_alerts = user_products.filter(
            alerts__status='active'
        ).distinct().count()
        context['products_with_alerts'] = products_with_alerts
        
        # Get recent price changes
        recent_changes = []
        for product in user_products.filter(current_price__isnull=False)[:5]:
            change = calculate_price_change_percentage(product, days=7)
            if change is not None:
                recent_changes.append({
                    'product': product,
                    'change_percentage': change,
                    'is_positive': change > 0,
                    'abs_change': abs(change)
                })
        
        context['recent_changes'] = sorted(
            recent_changes, 
            key=lambda x: x['abs_change'], 
            reverse=True
        )
        
        # Add scraping statistics
        today = timezone.now().date()
        context['today_scrapes'] = ScrapingLog.objects.filter(
            product__user=self.request.user,
            started_at__date=today
        ).count()
        
        context['successful_scrapes'] = ScrapingLog.objects.filter(
            product__user=self.request.user,
            started_at__date=today,
            status='success'
        ).count()
        
        return context


class ProductDetailView(LoginRequiredMixin, DetailView):
    """Product detail view with comprehensive analytics."""
    
    model = Product
    template_name = 'tracker/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # Get price history
        context['price_history'] = PriceHistory.objects.filter(
            product=product,
            is_valid=True
        ).order_by('-recorded_at')[:30]
        
        # Calculate basic statistics
        if context['price_history']:
            prices = [float(ph.price) for ph in context['price_history']]
            context['min_price'] = min(prices)
            context['max_price'] = max(prices)
            context['avg_price'] = sum(prices) / len(prices)
            context['price_volatility'] = calculate_price_change_percentage(product, days=30)
        else:
            context['min_price'] = 0
            context['max_price'] = 0
            context['avg_price'] = 0
            context['price_volatility'] = None
        
        # Get active alerts
        context['active_alerts'] = PriceAlert.objects.filter(
            product=product,
            status='active'
        )
        
        # Get recent scraping logs
        context['recent_scrapes'] = ScrapingLog.objects.filter(
            product=product
        ).order_by('-started_at')[:10]
        
        # Get recent predictions
        context['recent_predictions'] = DemandPrediction.objects.filter(
            product=product
        ).order_by('-prediction_date')[:7]
        
        # Generate charts
        try:
            chart_generator = ChartGenerator()
            context['price_chart'] = chart_generator.generate_price_trend_chart(product)
        except Exception as e:
            logger.error(f"Error generating price chart: {str(e)}")
            context['price_chart'] = None
        
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    """View for creating new products."""
    
    model = Product
    form_class = ProductForm
    template_name = 'tracker/product_form.html'
    success_url = reverse_lazy('tracker:dashboard')
    
    def form_valid(self, form):
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        messages.success(
            self.request, 
            f'Product "{form.instance.name}" added successfully! '
            'Use the "Update Price" button to fetch the current price.'
        )
        
        return response


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """View for updating existing products."""
    
    model = Product
    form_class = ProductForm
    template_name = 'tracker/product_form.html'
    
    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        return reverse_lazy('tracker:product_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        response = super().form_valid(form)
        messages.success(self.request, f'Product "{form.instance.name}" updated successfully.')
        return response


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """View for deleting products."""
    
    model = Product
    template_name = 'tracker/product_confirm_delete.html'
    success_url = reverse_lazy('tracker:dashboard')
    
    def get_queryset(self):
        return Product.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        product = self.get_object()
        messages.success(request, f'Product "{product.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def update_price_manual(request, product_id):
    """Manual price update with proper parameter name."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST':
        try:
            scraper = WebScraper()
            old_price = product.current_price
            
            messages.info(
                request, 
                f'Starting price update for "{product.name}". Please wait...'
            )
            
            price, status = scraper.scrape_price(product)
            
            if price and status == 'success':
                with transaction.atomic():
                    product.current_price = price
                    product.last_scraped = timezone.now()
                    product.save()
                    
                    PriceHistory.objects.create(
                        product=product,
                        price=price,
                        currency=product.currency,
                        source='manual_update'
                    )
                    
                    change_msg = ""
                    if old_price:
                        change = ((price - old_price) / old_price) * 100
                        change_msg = f" ({change:+.1f}% change)"
                    
                    messages.success(
                        request, 
                        f'Price updated successfully: {price} {product.currency}{change_msg}'
                    )
                    
                    logger.info(f"Manual price update successful for {product.name}: {price}")
            else:
                messages.error(
                    request, 
                    f'Failed to update price for "{product.name}". '
                    'The website might be blocking requests or the product page structure has changed.'
                )
                logger.warning(f"Manual price update failed for {product.name}")
                        
        except Exception as e:
            logger.error(f"Error in manual price update: {str(e)}")
            messages.error(request, f'Error updating price: {str(e)}')
    
    return redirect('tracker:product_detail', pk=product_id)


@login_required
def bulk_update_prices(request):
    """Bulk update prices for all user's active products."""
    if request.method == 'POST':
        user_products = Product.objects.filter(user=request.user, is_active=True)
        
        if not user_products.exists():
            messages.warning(request, 'No active products to update.')
            return redirect('tracker:dashboard')
        
        updated_count = 0
        failed_count = 0
        scraper = WebScraper()
        
        messages.info(
            request, 
            f'Starting bulk update for {user_products.count()} products. This may take a few minutes...'
        )
        
        for product in user_products:
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
                        source='bulk_update'
                    )
                    
                    updated_count += 1
                    logger.info(f"Bulk update successful for {product.name}: {price}")
                else:
                    failed_count += 1
                    logger.warning(f"Bulk update failed for {product.name}")
                    
                import time
                time.sleep(2)
                    
            except Exception as e:
                failed_count += 1
                logger.error(f"Error in bulk update for {product.name}: {str(e)}")
        
        if updated_count > 0:
            messages.success(
                request, 
                f'Bulk update completed! {updated_count} products updated successfully.'
            )
        
        if failed_count > 0:
            messages.warning(
                request, 
                f'{failed_count} products failed to update. Check the logs for details.'
            )
        
        logger.info(f"Bulk update completed: {updated_count} updated, {failed_count} failed")
    
    return redirect('tracker:dashboard')


@login_required
def generate_predictions(request, product_id):
    """Manual prediction generation endpoint."""
    try:
        product = get_object_or_404(Product, id=product_id, user=request.user)
        
        prediction_count = generate_predictions_for_product(product)
        
        if prediction_count > 0:
            messages.success(
                request, 
                f'Generated {prediction_count} new predictions for {product.name}.'
            )
        else:
            messages.warning(
                request, 
                f'Could not generate predictions for {product.name}. '
                'Make sure the product has sufficient price history.'
            )
    
    except Exception as e:
        logger.error(f"Error generating predictions: {str(e)}")
        messages.error(request, f'Error generating predictions: {str(e)}')
    
    return redirect('tracker:product_detail', pk=product_id)


@login_required
@require_POST
def delete_alert(request, alert_id):
    """AJAX endpoint to delete a price alert."""
    try:
        alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
        product_name = alert.product.name
        alert.delete()
        
        return JsonResponse({
            'status': 'success',
            'message': f'Alert for "{product_name}" deleted successfully.'
        })
        
    except Exception as e:
        logger.error(f"Error deleting alert: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to delete alert.'
        }, status=500)


@login_required
@require_POST
def toggle_product_status(request, product_id):
    """AJAX endpoint to toggle product status."""
    try:
        product = get_object_or_404(Product, id=product_id, user=request.user)
        
        product.is_active = not product.is_active
        product.save()
        
        status = 'activated' if product.is_active else 'deactivated'
        
        return JsonResponse({
            'status': 'success',
            'is_active': product.is_active,
            'message': f'Product {status} successfully.'
        })
        
    except Exception as e:
        logger.error(f"Error toggling product status: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Failed to update product status.'
        }, status=500)


@login_required
def chart_data_api(request, product_id):
    """API endpoint for getting chart data in JSON format."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    days = int(request.GET.get('days', 30))
    
    try:
        chart_data_json = DataProcessor.get_chart_data_json(product, days)
        return JsonResponse(json.loads(chart_data_json))
    except Exception as e:
        logger.error(f"Error getting chart data: {str(e)}")
        return JsonResponse({'error': 'Failed to get chart data'}, status=500)


@login_required
def add_alert(request, product_id):
    """View for adding price alerts to products."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            try:
                alert = form.save(commit=False)
                alert.user = request.user
                alert.product = product
                alert.save()
                
                messages.success(
                    request, 
                    f'Alert created successfully for {product.name}!'
                )
                return redirect('tracker:product_detail', pk=product_id)
            except ValidationError as e:
                messages.error(request, f'Error creating alert: {str(e)}')
        else:
            messages.error(request, 'Please correct the errors below.')
    else:
        form = AlertForm()
    
    return render(request, 'tracker/alert_form.html', {
        'form': form,
        'product': product
    })


@login_required
def export_data(request):
    """Data export view."""
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            export_format = form.cleaned_data['export_format']
            
            products = Product.objects.filter(user=request.user)
            
            if export_format == 'csv':
                return export_to_csv(request, products)
            elif export_format == 'json':
                return export_to_json(request, products)
    else:
        form = ExportForm()
    
    return render(request, 'tracker/export.html', {'form': form})


def export_to_csv(request, products):
    """Export product data to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="products_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    writer.writerow(['Product ID', 'Name', 'URL', 'Current Price', 'Currency', 'Is Active', 'Created At'])
    
    for product in products:
        writer.writerow([
            product.id,
            product.name,
            product.url,
            product.current_price,
            product.currency,
            product.is_active,
            product.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ])
    
    return response


def export_to_json(request, products):
    """Export product data to JSON format."""
    data = []
    
    for product in products:
        product_data = {
            'id': str(product.id),
            'name': product.name,
            'url': product.url,
            'current_price': float(product.current_price) if product.current_price else None,
            'currency': product.currency,
            'is_active': product.is_active,
            'created_at': product.created_at.isoformat(),
        }
        data.append(product_data)
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="products_{timezone.now().strftime("%Y%m%d")}.json"'
    
    return response


def register(request):
    """User registration view."""
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save()
                login(request, user)
                messages.success(request, 'Account created successfully!')
                return redirect('tracker:dashboard')
            except Exception as e:
                logger.error(f"Registration error: {str(e)}")
                messages.error(request, 'Registration failed. Please try again.')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'tracker/register.html', {'form': form})


@login_required
def profile(request):
    """User profile view with statistics."""
    user = request.user
    
    user_products = Product.objects.filter(user=user)
    context = {
        'user': user,
        'total_products': user_products.count(),
        'active_products': user_products.filter(is_active=True).count(),
    }
    
    return render(request, 'tracker/profile.html', context)


# API views
@login_required
def api_products(request):
    """REST API endpoint for getting user's products."""
    products = Product.objects.filter(user=request.user)
    
    data = []
    for product in products:
        data.append({
            'id': str(product.id),
            'name': product.name,
            'current_price': float(product.current_price) if product.current_price else None,
            'currency': product.currency,
            'is_active': product.is_active,
            'created_at': product.created_at.isoformat(),
        })
    
    return JsonResponse({'products': data})


@login_required
def api_product_predictions(request, product_id):
    """REST API endpoint for getting product predictions."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    predictions = DemandPrediction.objects.filter(
        product=product
    ).order_by('-prediction_date')[:7]
    
    data = []
    for pred in predictions:
        data.append({
            'date': pred.prediction_date.isoformat(),
            'predicted_demand': pred.predicted_demand,
            'predicted_price': float(pred.predicted_price) if pred.predicted_price else None,
            'confidence_score': pred.confidence_score,
            'model_type': pred.model_type,
        })
    
    return JsonResponse({'predictions': data})

@login_required
def update_price_manual(request, product_id):
    """Manual price update with proper parameter name."""
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST':
        try:
            scraper = WebScraper()
            old_price = product.current_price
            
            messages.info(
                request, 
                f'Starting price update for "{product.name}". Please wait...'
            )
            
            price, status = scraper.scrape_price(product)
            
            if price and status == 'success':
                with transaction.atomic():
                    product.current_price = price
                    product.last_scraped = timezone.now()
                    product.save()
                    
                    # Create price history record
                    PriceHistory.objects.create(
                        product=product,
                        price=price,
                        currency=product.currency,
                        source='manual_update'
                    )
                    
                    change_msg = ""
                    if old_price:
                        change = ((price - old_price) / old_price) * 100
                        change_msg = f" ({change:+.1f}% change)"
                    
                    messages.success(
                        request, 
                        f'Price updated successfully: {price} {product.currency}{change_msg}'
                    )
                    
                    logger.info(f"Manual price update successful for {product.name}: {price}")
            else:
                messages.error(
                    request, 
                    f'Failed to update price for "{product.name}". '
                    'Please try again later.'
                )
                logger.warning(f"Manual price update failed for {product.name}")
                        
        except Exception as e:
            logger.error(f"Error in manual price update: {str(e)}")
            messages.error(request, f'Error updating price: Please try again.')
    
    return redirect('tracker:product_detail', pk=product_id)
