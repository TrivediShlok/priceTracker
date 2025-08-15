"""
Django views for the Price Tracker application.

This module contains views for handling user requests, displaying
product information, and managing user interactions.
"""

from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.http import JsonResponse, HttpResponse
from django.views.generic import ListView, DetailView, CreateView, UpdateView, DeleteView
from django.urls import reverse_lazy
from django.db.models import Q, Count, Avg
from django.utils import timezone
from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth import login, authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
import json
import csv
from datetime import datetime, timedelta

# Local imports
from .models import Product, PriceHistory, DemandPrediction, PriceAlert, ScrapingLog
from .forms import ProductForm, AlertForm, UserRegistrationForm, ProductSearchForm, ExportForm
from .utils import WebScraper, DataProcessor, calculate_price_change_percentage, update_product_prices


class DashboardView(LoginRequiredMixin, ListView):
    """
    Dashboard view showing user's products with summary statistics.
    
    This view displays a comprehensive dashboard with product overview,
    price trends, and quick actions for the authenticated user.
    """
    
    model = Product
    template_name = 'tracker/dashboard.html'
    context_object_name = 'products'
    paginate_by = 10
    
    def get_queryset(self):
        """Get products for the current user with annotations."""
        queryset = Product.objects.filter(user=self.request.user).annotate(
            price_history_count=Count('price_history'),
            avg_price=Avg('price_history__price')
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
        """Add additional context data for the dashboard."""
        context = super().get_context_data(**kwargs)
        
        # Add search form
        context['search_form'] = ProductSearchForm(self.request.GET)
        
        # Add summary statistics
        user_products = Product.objects.filter(user=self.request.user)
        context['total_products'] = user_products.count()
        context['active_products'] = user_products.filter(is_active=True).count()
        context['products_with_alerts'] = user_products.filter(alerts__status='active').distinct().count()
        
        # Add recent price changes
        recent_changes = []
        for product in user_products[:5]:
            change = calculate_price_change_percentage(product, days=7)
            if change is not None:
                recent_changes.append({
                    'product': product,
                    'change_percentage': change,
                    'is_positive': change > 0
                })
        
        context['recent_changes'] = sorted(recent_changes, key=lambda x: abs(x['change_percentage']), reverse=True)
        
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
    """
    Detailed view for a single product with price history and predictions.
    
    This view shows comprehensive information about a product including
    price trends, predictions, and alert settings.
    """
    
    model = Product
    template_name = 'tracker/product_detail.html'
    context_object_name = 'product'
    
    def get_queryset(self):
        """Ensure users can only view their own products."""
        return Product.objects.filter(user=self.request.user)
    
    def get_context_data(self, **kwargs):
        """Add additional context data for product details."""
        context = super().get_context_data(**kwargs)
        product = self.get_object()
        
        # Get price history
        price_history = PriceHistory.objects.filter(
            product=product,
            is_valid=True
        ).order_by('-recorded_at')[:30]
        
        context['price_history'] = price_history
        
        # Get recent predictions
        recent_predictions = DemandPrediction.objects.filter(
            product=product
        ).order_by('-prediction_date')[:7]
        
        context['recent_predictions'] = recent_predictions
        
        # Calculate price statistics
        if price_history.exists():
            prices = [float(ph.price) for ph in price_history]
            context['min_price'] = min(prices)
            context['max_price'] = max(prices)
            context['avg_price'] = sum(prices) / len(prices)
            context['price_volatility'] = calculate_price_change_percentage(product, days=30)
        
        # Get active alerts
        context['active_alerts'] = PriceAlert.objects.filter(
            product=product,
            status='active'
        )
        
        # Get recent scraping logs
        context['recent_scrapes'] = ScrapingLog.objects.filter(
            product=product
        ).order_by('-started_at')[:10]
        
        return context


class ProductCreateView(LoginRequiredMixin, CreateView):
    """
    View for creating new products.
    
    This view handles the creation of new products with form validation
    and automatic price scraping.
    """
    
    model = Product
    form_class = ProductForm
    template_name = 'tracker/product_form.html'
    success_url = reverse_lazy('tracker:dashboard')
    
    def form_valid(self, form):
        """Handle form submission and create product."""
        form.instance.user = self.request.user
        response = super().form_valid(form)
        
        # Try to scrape initial price
        try:
            scraper = WebScraper()
            price, status = scraper.scrape_price(form.instance)
            
            if price:
                form.instance.current_price = price
                form.instance.last_scraped = timezone.now()
                form.instance.save()
                
                # Create price history record
                PriceHistory.objects.create(
                    product=form.instance,
                    price=price,
                    currency=form.instance.currency,
                    source='initial_scrape'
                )
                
                messages.success(self.request, f'Product "{form.instance.name}" added successfully with initial price: {price} {form.instance.currency}')
            else:
                messages.warning(self.request, f'Product "{form.instance.name}" added successfully, but could not fetch initial price.')
                
        except Exception as e:
            messages.warning(self.request, f'Product "{form.instance.name}" added successfully, but price scraping failed.')
        
        return response


class ProductUpdateView(LoginRequiredMixin, UpdateView):
    """
    View for updating existing products.
    
    This view allows users to modify product information and settings.
    """
    
    model = Product
    form_class = ProductForm
    template_name = 'tracker/product_form.html'
    
    def get_queryset(self):
        """Ensure users can only update their own products."""
        return Product.objects.filter(user=self.request.user)
    
    def get_success_url(self):
        """Redirect to product detail page after update."""
        return reverse_lazy('tracker:product_detail', kwargs={'pk': self.object.pk})
    
    def form_valid(self, form):
        """Handle form submission and update product."""
        response = super().form_valid(form)
        messages.success(self.request, f'Product "{form.instance.name}" updated successfully.')
        return response


class ProductDeleteView(LoginRequiredMixin, DeleteView):
    """
    View for deleting products.
    
    This view handles product deletion with confirmation.
    """
    
    model = Product
    template_name = 'tracker/product_confirm_delete.html'
    success_url = reverse_lazy('tracker:dashboard')
    
    def get_queryset(self):
        """Ensure users can only delete their own products."""
        return Product.objects.filter(user=self.request.user)
    
    def delete(self, request, *args, **kwargs):
        """Handle product deletion."""
        product = self.get_object()
        messages.success(request, f'Product "{product.name}" deleted successfully.')
        return super().delete(request, *args, **kwargs)


@login_required
def add_alert(request, product_id):
    """
    View for adding price alerts to products.
    
    This view handles the creation of new price alerts for products.
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST':
        form = AlertForm(request.POST)
        if form.is_valid():
            alert = form.save(commit=False)
            alert.user = request.user
            alert.product = product
            alert.save()
            
            messages.success(request, f'Alert created successfully for {product.name}.')
            return redirect('tracker:product_detail', pk=product_id)
    else:
        form = AlertForm()
    
    return render(request, 'tracker/alert_form.html', {
        'form': form,
        'product': product
    })


@login_required
def update_price_manual(request, product_id):
    """
    Manual price update view.
    
    This view allows users to manually trigger price updates for specific products.
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    if request.method == 'POST':
        try:
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
                    source='manual_update'
                )
                
                messages.success(request, f'Price updated successfully: {price} {product.currency}')
            else:
                messages.error(request, 'Failed to update price. Please try again later.')
                
        except Exception as e:
            messages.error(request, f'Error updating price: {str(e)}')
    
    return redirect('tracker:product_detail', pk=product_id)


@login_required
def export_data(request):
    """
    Data export view.
    
    This view allows users to export their product data in various formats.
    """
    if request.method == 'POST':
        form = ExportForm(request.POST)
        if form.is_valid():
            export_format = form.cleaned_data['export_format']
            export_type = form.cleaned_data['export_type']
            include_history = form.cleaned_data['include_price_history']
            include_predictions = form.cleaned_data['include_predictions']
            date_from = form.cleaned_data['date_from']
            date_to = form.cleaned_data['date_to']
            
            # Get products based on export type
            products = Product.objects.filter(user=request.user)
            
            if export_type == 'active':
                products = products.filter(is_active=True)
            elif export_type == 'with_history':
                products = products.filter(price_history__isnull=False).distinct()
            elif export_type == 'with_predictions':
                products = products.filter(demand_predictions__isnull=False).distinct()
            
            # Apply date filters
            if date_from:
                products = products.filter(created_at__gte=date_from)
            if date_to:
                products = products.filter(created_at__lte=date_to)
            
            if export_format == 'csv':
                return export_to_csv(request, products, include_history, include_predictions)
            elif export_format == 'json':
                return export_to_json(request, products, include_history, include_predictions)
    
    else:
        form = ExportForm()
    
    return render(request, 'tracker/export.html', {'form': form})


def export_to_csv(request, products, include_history, include_predictions):
    """Export product data to CSV format."""
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="products_{timezone.now().strftime("%Y%m%d")}.csv"'
    
    writer = csv.writer(response)
    
    # Write header
    header = ['Product ID', 'Name', 'URL', 'Current Price', 'Currency', 'Alert Threshold', 'Is Active', 'Created At']
    if include_history:
        header.extend(['Price History Count'])
    if include_predictions:
        header.extend(['Prediction Count'])
    
    writer.writerow(header)
    
    # Write data
    for product in products:
        row = [
            product.id,
            product.name,
            product.url,
            product.current_price,
            product.currency,
            product.alert_threshold,
            product.is_active,
            product.created_at.strftime('%Y-%m-%d %H:%M:%S')
        ]
        
        if include_history:
            row.append(product.price_history.count())
        
        if include_predictions:
            row.append(product.demand_predictions.count())
        
        writer.writerow(row)
    
    return response


def export_to_json(request, products, include_history, include_predictions):
    """Export product data to JSON format."""
    data = []
    
    for product in products:
        product_data = {
            'id': str(product.id),
            'name': product.name,
            'url': product.url,
            'current_price': float(product.current_price) if product.current_price else None,
            'currency': product.currency,
            'alert_threshold': float(product.alert_threshold) if product.alert_threshold else None,
            'is_active': product.is_active,
            'created_at': product.created_at.isoformat(),
            'updated_at': product.updated_at.isoformat(),
        }
        
        if include_history:
            history_data = []
            for ph in product.price_history.all()[:50]:  # Limit to last 50 records
                history_data.append({
                    'price': float(ph.price),
                    'currency': ph.currency,
                    'recorded_at': ph.recorded_at.isoformat(),
                    'source': ph.source
                })
            product_data['price_history'] = history_data
        
        if include_predictions:
            predictions_data = []
            for pred in product.demand_predictions.all()[:30]:  # Limit to last 30 predictions
                predictions_data.append({
                    'predicted_demand': pred.predicted_demand,
                    'predicted_price': float(pred.predicted_price) if pred.predicted_price else None,
                    'confidence_score': pred.confidence_score,
                    'prediction_date': pred.prediction_date.isoformat(),
                    'model_type': pred.model_type
                })
            product_data['predictions'] = predictions_data
        
        data.append(product_data)
    
    response = HttpResponse(json.dumps(data, indent=2), content_type='application/json')
    response['Content-Disposition'] = f'attachment; filename="products_{timezone.now().strftime("%Y%m%d")}.json"'
    
    return response


def register(request):
    """
    User registration view.
    
    This view handles new user registration with form validation.
    """
    if request.method == 'POST':
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'Account created successfully! Welcome to Price Tracker.')
            return redirect('tracker:dashboard')
    else:
        form = UserRegistrationForm()
    
    return render(request, 'tracker/register.html', {'form': form})


@login_required
def profile(request):
    """
    User profile view.
    
    This view displays user profile information and statistics.
    """
    user = request.user
    
    # Get user statistics
    total_products = Product.objects.filter(user=user).count()
    active_products = Product.objects.filter(user=user, is_active=True).count()
    total_alerts = PriceAlert.objects.filter(user=user).count()
    active_alerts = PriceAlert.objects.filter(user=user, status='active').count()
    
    # Get recent activity
    recent_products = Product.objects.filter(user=user).order_by('-created_at')[:5]
    recent_alerts = PriceAlert.objects.filter(user=user).order_by('-created_at')[:5]
    
    context = {
        'user': user,
        'total_products': total_products,
        'active_products': active_products,
        'total_alerts': total_alerts,
        'active_alerts': active_alerts,
        'recent_products': recent_products,
        'recent_alerts': recent_alerts,
    }
    
    return render(request, 'tracker/profile.html', context)


@login_required
@require_POST
def toggle_product_status(request, product_id):
    """
    Toggle product active/inactive status.
    
    This view allows users to quickly enable or disable product tracking.
    """
    product = get_object_or_404(Product, id=product_id, user=request.user)
    
    product.is_active = not product.is_active
    product.save()
    
    status = 'activated' if product.is_active else 'deactivated'
    messages.success(request, f'Product "{product.name}" {status} successfully.')
    
    return JsonResponse({'status': 'success', 'is_active': product.is_active})


@login_required
@require_POST
def delete_alert(request, alert_id):
    """
    Delete a price alert.
    
    This view allows users to remove price alerts.
    """
    alert = get_object_or_404(PriceAlert, id=alert_id, user=request.user)
    product_name = alert.product.name
    alert.delete()
    
    messages.success(request, f'Alert for "{product_name}" deleted successfully.')
    
    return JsonResponse({'status': 'success'})


@login_required
def api_products(request):
    """
    API endpoint for getting user's products.
    
    This view provides a simple API for accessing product data.
    """
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
    """
    API endpoint for getting product predictions.
    
    This view provides predictions for a specific product.
    """
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
