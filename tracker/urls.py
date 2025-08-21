"""
URL configuration for the Price Tracker application.
"""

from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Dashboard and main views
    path('', views.DashboardView.as_view(), name='dashboard'),
    
    # Product management
    path('product/add/', views.ProductCreateView.as_view(), name='add_product'),
    path('product/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='edit_product'),
    path('product/<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='delete_product'),
    
    # Price management
    path('product/<uuid:product_id>/update-price/', views.update_price_manual, name='update_price_manual'),
    path('bulk-update-prices/', views.bulk_update_prices, name='bulk_update_prices'),
    
    # Alerts
    path('product/<uuid:product_id>/add-alert/', views.add_alert, name='add_alert'),
    path('alert/<int:alert_id>/delete/', views.delete_alert, name='delete_alert'),
    
    # Predictions
    path('product/<uuid:product_id>/generate-predictions/', views.generate_predictions, name='generate_predictions'),
    
    # AJAX endpoints
    path('product/<uuid:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
    path('api/product/<uuid:product_id>/chart-data/', views.chart_data_api, name='chart_data_api'),
    
    # Data export
    path('export/', views.export_data, name='export_data'),
    
    # User management
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    
    # API endpoints
    path('api/products/', views.api_products, name='api_products'),
    path('api/product/<uuid:product_id>/predictions/', views.api_product_predictions, name='api_product_predictions'),
]
