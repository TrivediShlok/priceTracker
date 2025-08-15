"""
Django admin configuration for the Price Tracker application.

This module configures the Django admin interface for managing
products, price history, predictions, and alerts.
"""

from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils.safestring import mark_safe
from .models import Product, PriceHistory, DemandPrediction, PriceAlert, ScrapingLog


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    """Admin interface for Product model."""
    
    list_display = [
        'name', 
        'user', 
        'current_price', 
        'currency', 
        'price_change_percentage_display',
        'is_active', 
        'created_at'
    ]
    list_filter = ['is_active', 'currency', 'created_at', 'user']
    search_fields = ['name', 'user__username', 'user__email']
    readonly_fields = ['id', 'created_at', 'updated_at', 'last_scraped']
    list_editable = ['is_active']
    
    fieldsets = (
        ('Product Information', {
            'fields': ('id', 'name', 'url', 'user')
        }),
        ('Price Information', {
            'fields': ('current_price', 'currency', 'last_scraped')
        }),
        ('Tracking Settings', {
            'fields': ('alert_threshold', 'is_active')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def price_change_percentage_display(self, obj):
        """Display price change percentage with color coding."""
        change = obj.price_change_percentage
        if change is None:
            return "N/A"
        
        if change > 0:
            color = 'red'
            symbol = '+'
        elif change < 0:
            color = 'green'
            symbol = ''
        else:
            color = 'black'
            symbol = ''
        
        return format_html(
            '<span style="color: {};">{}{:.2f}%</span>',
            color, symbol, change
        )
    price_change_percentage_display.short_description = 'Price Change %'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user')


@admin.register(PriceHistory)
class PriceHistoryAdmin(admin.ModelAdmin):
    """Admin interface for PriceHistory model."""
    
    list_display = ['product', 'price', 'currency', 'recorded_at', 'source', 'is_valid']
    list_filter = ['currency', 'source', 'is_valid', 'recorded_at']
    search_fields = ['product__name']
    readonly_fields = ['id', 'recorded_at']
    date_hierarchy = 'recorded_at'
    
    fieldsets = (
        ('Price Information', {
            'fields': ('product', 'price', 'currency')
        }),
        ('Metadata', {
            'fields': ('recorded_at', 'source', 'is_valid')
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('product')


@admin.register(DemandPrediction)
class DemandPredictionAdmin(admin.ModelAdmin):
    """Admin interface for DemandPrediction model."""
    
    list_display = [
        'product', 
        'predicted_demand', 
        'predicted_price', 
        'confidence_score_display',
        'prediction_date', 
        'model_type'
    ]
    list_filter = ['model_type', 'prediction_date', 'created_at']
    search_fields = ['product__name']
    readonly_fields = ['id', 'created_at']
    date_hierarchy = 'prediction_date'
    
    fieldsets = (
        ('Product & Prediction', {
            'fields': ('product', 'predicted_demand', 'predicted_price', 'prediction_date')
        }),
        ('Model Information', {
            'fields': ('confidence_score', 'model_type', 'model_version')
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def confidence_score_display(self, obj):
        """Display confidence score as a colored bar."""
        score = obj.confidence_score
        if score >= 0.8:
            color = 'green'
        elif score >= 0.6:
            color = 'orange'
        else:
            color = 'red'
        
        return format_html(
            '<span style="color: {};">{:.2f}</span>',
            color, score
        )
    confidence_score_display.short_description = 'Confidence'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('product')


@admin.register(PriceAlert)
class PriceAlertAdmin(admin.ModelAdmin):
    """Admin interface for PriceAlert model."""
    
    list_display = [
        'user', 
        'product', 
        'alert_type', 
        'threshold_value', 
        'status', 
        'created_at'
    ]
    list_filter = ['alert_type', 'status', 'email_notification', 'web_notification', 'created_at']
    search_fields = ['user__username', 'product__name']
    readonly_fields = ['id', 'created_at']
    list_editable = ['status']
    
    fieldsets = (
        ('Alert Configuration', {
            'fields': ('user', 'product', 'alert_type', 'threshold_value', 'status')
        }),
        ('Notification Settings', {
            'fields': ('email_notification', 'web_notification')
        }),
        ('Timestamps', {
            'fields': ('created_at', 'triggered_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('user', 'product')


@admin.register(ScrapingLog)
class ScrapingLogAdmin(admin.ModelAdmin):
    """Admin interface for ScrapingLog model."""
    
    list_display = [
        'product', 
        'status', 
        'scraped_price', 
        'response_time_display',
        'retry_count', 
        'started_at'
    ]
    list_filter = ['status', 'started_at']
    search_fields = ['product__name', 'error_message']
    readonly_fields = ['id', 'started_at', 'completed_at', 'duration_display']
    
    fieldsets = (
        ('Scraping Results', {
            'fields': ('product', 'status', 'scraped_price', 'error_message')
        }),
        ('Performance Metrics', {
            'fields': ('response_time', 'retry_count', 'duration_display')
        }),
        ('Timestamps', {
            'fields': ('started_at', 'completed_at'),
            'classes': ('collapse',)
        }),
    )
    
    def response_time_display(self, obj):
        """Display response time in a readable format."""
        if obj.response_time:
            return f"{obj.response_time:.2f}s"
        return "N/A"
    response_time_display.short_description = 'Response Time'
    
    def duration_display(self, obj):
        """Display duration in a readable format."""
        duration = obj.duration
        if duration:
            return f"{duration:.2f}s"
        return "N/A"
    duration_display.short_description = 'Duration'
    
    def get_queryset(self, request):
        """Optimize queryset with related fields."""
        return super().get_queryset(request).select_related('product')


# Customize admin site
admin.site.site_header = "Price Tracker Administration"
admin.site.site_title = "Price Tracker Admin"
admin.site.index_title = "Welcome to Price Tracker Administration"
