"""
API URL configuration for the tracker application.

This module defines the REST API URL patterns for the Price Tracker application,
providing programmatic access to product data and predictions.
"""

from django.urls import path
from . import views

app_name = 'tracker_api'

urlpatterns = [
    # Product API endpoints
    path('products/', views.api_products, name='products'),
    path('products/<uuid:product_id>/predictions/', views.api_product_predictions, name='product_predictions'),
]
