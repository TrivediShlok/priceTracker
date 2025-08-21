"""
Django admin configuration for the Price Tracker application.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Product, PriceHistory, DemandPrediction, PriceAlert, ScrapingLog


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Enhanced admin interface for Product model."""
    
    list_display = [
        'name', 
        'current_price_display', 
        'price_change_percentage_display', 
        'currency', 
        'is_active', 
        'last_scraped', 
        'user'
    ]
    list_filter = ['is_active', 'currency', 'created_at', 'user']
    search_fields = ['name', 'url', 'user__username']
    readonly_fields = ['id', 'created_at', 'updated_at', 'price_change_percentage_display']
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'url', 'user')
        }),
        ('Price Information', {
            'fields': ('current_price', 'currency', 'alert_threshold')
        }),
        ('Status', {
            'fields': ('is_active', 'last_scraped')
        }),
        ('Metadata', {
            'fields': ('id', 'created_at', 'updated_at', 'price_change_percentage_display'),
            'classes': ('collapse',)
        })
    )
    
    def current_price_display(self, obj):
        """Display current price with currency symbol."""
        if obj.current_price:
            return f"{obj.current_price} {obj.currency}"
        return "No price data"
    current_price_display.short_description = "Current Price"
    current_price_display.admin_order_field = 'current_price'
    
    def price_change_percentage_display(self, obj):
        """Display price change percentage with color coding."""
        try:
            # Get the price change percentage
            change_value = obj.price_change_percentage
            
            # Handle None case
            if change_value is None:
                return format_html('<span style="color: gray;">No data</span>')
            
            # Convert to float if it's not already
            if isinstance(change_value, str):
                # Remove any HTML tags and convert to float
                import re
                clean_value = re.sub(r'<[^>]+>', '', str(change_value))
                try:
                    change_float = float(clean_value.replace('%', ''))
                except (ValueError, AttributeError):
                    return format_html('<span style="color: gray;">No data</span>')
            else:
                try:
                    change_float = float(change_value)
                except (TypeError, ValueError):
                    return format_html('<span style="color: gray;">No data</span>')
            
            # Color code based on value
            if change_float > 0:
                color = '#10b981'  # Green
                icon = '↗'
            elif change_float < 0:
                color = '#ef4444'  # Red
                icon = '↘'
            else:
                color = '#6b7280'  # Gray
                icon = '→'
            
            return format_html(
                '<span style="color: {}; font-weight: bold;">{} {:.2f}%</span>',
                color,
                icon,
                abs(change_float)
            )
            
        except Exception as e:
            return format_html('<span style="color: gray;">Error: {}</span>', str(e))
    
    price_change_percentage_display.short_description = 'Price Change (30d)'
    price_change_percentage_display.allow_tags = True
    
    def get_queryset(self, request):
        """Optimize queryset with select_related."""
        return super().get_queryset(request).select_related('user')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PriceHistory model."""
    
    list_display = ['product', 'price_display', 'recorded_at', 'source', 'is_valid']
    list_filter = ['is_valid', 'source', 'currency', 'recorded_at']
    search_fields = ['product__name', 'product__user__username']
    readonly_fields = ['recorded_at']
    
    def price_display(self, obj):
        """Display price with currency."""
        return f"{obj.price} {obj.currency}"
    price_display.short_description = "Price"
    price_display.admin_order_field = 'price'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('product', 'product__user')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    """Admin interface for PriceAlert model."""
    
    list_display = ['user', 'product', 'alert_type', 'threshold_display', 'status', 'created_at']
    list_filter = ['alert_type', 'status', 'email_notification', 'created_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['created_at', 'triggered_at']
    
    def threshold_display(self, obj):
        """Display threshold with currency."""
        return f"{obj.threshold_value} {obj.product.currency}"
    threshold_display.short_description = "Threshold"
    threshold_display.admin_order_field = 'threshold_value'
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('user', 'product')


@admin.register(DemandPrediction)
class DemandPredictionAdmin(admin.ModelAdmin):
    """Admin interface for DemandPrediction model."""
    
    list_display = [
        'product', 
        'prediction_date', 
        'predicted_demand_display', 
        'predicted_price_display', 
        'confidence_display', 
        'model_type'
    ]
    list_filter = ['model_type', 'prediction_date', 'created_at']
    search_fields = ['product__name', 'product__user__username']
    readonly_fields = ['created_at']
    
    def predicted_demand_display(self, obj):
        """Display predicted demand with formatting."""
        try:
            demand_float = float(obj.predicted_demand)
            return f"{demand_float:.3f}"
        except (TypeError, ValueError):
            return "N/A"
    predicted_demand_display.short_description = "Predicted Demand"
    predicted_demand_display.admin_order_field = 'predicted_demand'
    
    def predicted_price_display(self, obj):
        """Display predicted price with currency."""
        if obj.predicted_price:
            try:
                price_float = float(obj.predicted_price)
                return f"{price_float:.2f} {obj.product.currency}"
            except (TypeError, ValueError):
                return "N/A"
        return "N/A"
    predicted_price_display.short_description = "Predicted Price"
    predicted_price_display.admin_order_field = 'predicted_price'
    
    def confidence_display(self, obj):
        """Display confidence score as percentage."""
        try:
            confidence_float = float(obj.confidence_score)
            confidence_percent = confidence_float * 100
            
            if confidence_percent >= 80:
                color = '#10b981'  # Green
            elif confidence_percent >= 60:
                color = '#f59e0b'  # Yellow
            else:
                color = '#ef4444'  # Red
                
            return format_html(
                '<span style="color: {}; font-weight: bold;">{:.1f}%</span>',
                color,
                confidence_percent
            )
        except (TypeError, ValueError):
            return "N/A"
    confidence_display.short_description = "Confidence"
    confidence_display.admin_order_field = 'confidence_score'
    confidence_display.allow_tags = True
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('product', 'product__user')


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    """Admin interface for ScrapingLog model."""
    
    list_display = [
        'product', 
        'status_display', 
        'scraped_price_display', 
        'response_time_display', 
        'started_at', 
        'retry_count'
    ]
    list_filter = ['status', 'started_at', 'retry_count']
    search_fields = ['product__name', 'product__user__username', 'error_message']
    readonly_fields = ['started_at', 'completed_at', 'duration']
    
    def status_display(self, obj):
        """Display status with color coding."""
        status_colors = {
            'success': '#10b981',  # Green
            'failed': '#ef4444',   # Red
            'partial': '#f59e0b'   # Yellow
        }
        color = status_colors.get(obj.status, '#6b7280')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.status.upper()
        )
    status_display.short_description = "Status"
    status_display.admin_order_field = 'status'
    status_display.allow_tags = True
    
    def scraped_price_display(self, obj):
        """Display scraped price with currency."""
        if obj.scraped_price:
            try:
                price_float = float(obj.scraped_price)
                return f"{price_float:.2f} {obj.product.currency}"
            except (TypeError, ValueError):
                return str(obj.scraped_price)
        return "N/A"
    scraped_price_display.short_description = "Scraped Price"
    scraped_price_display.admin_order_field = 'scraped_price'
    
    def response_time_display(self, obj):
        """Display response time in a readable format."""
        if obj.response_time:
            try:
                time_float = float(obj.response_time)
                return f"{time_float:.2f}s"
            except (TypeError, ValueError):
                return str(obj.response_time)
        return "N/A"
    response_time_display.short_description = "Response Time"
    response_time_display.admin_order_field = 'response_time'
    
    def duration(self, obj):
        """Calculate and display scraping duration."""
        if obj.completed_at:
            duration_seconds = (obj.completed_at - obj.started_at).total_seconds()
            return f"{duration_seconds:.2f}s"
        return "In progress"
    duration.short_description = "Duration"
    
    def get_queryset(self, request):
        """Optimize queryset."""
        return super().get_queryset(request).select_related('product', 'product__user')


# Customize admin site headers
admin.site.site_header = "Price Tracker Administration"
admin.site.site_title = "Price Tracker Admin"
admin.site.index_title = "Welcome to Price Tracker Administration"
