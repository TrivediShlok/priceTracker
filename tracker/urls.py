"""
URL configuration for the tracker application.

This module defines the URL patterns for the Price Tracker application,
including views for products, alerts, and user management.
"""

from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Dashboard and main views
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('profile/', views.profile, name='profile'),
    
    # Product management
    path('product/add/', views.ProductCreateView.as_view(), name='product_add'),
    path('product/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='product_edit'),
    path('product/<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='product_delete'),
    path('product/<uuid:product_id>/update-price/', views.update_price_manual, name='update_price_manual'),
    
    # Alert management
    path('product/<uuid:product_id>/add-alert/', views.add_alert, name='add_alert'),
    path('alert/<int:alert_id>/delete/', views.delete_alert, name='delete_alert'),
    
    # Product actions
    path('product/<uuid:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
    
    # Data export
    path('export/', views.export_data, name='export_data'),
    
    # User registration
    path('register/', views.register, name='register'),
    
    # API endpoints
    path('api/products/', views.api_products, name='api_products'),
    path('api/products/<uuid:product_id>/predictions/', views.api_product_predictions, name='api_product_predictions'),
]
