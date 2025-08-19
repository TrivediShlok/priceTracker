"""URL patterns for the tracker app."""

from django.urls import path
from . import views

app_name = 'tracker'

urlpatterns = [
    # Dashboard and main views
    path('', views.DashboardView.as_view(), name='dashboard'),
    path('product/<uuid:pk>/', views.ProductDetailView.as_view(), name='product_detail'),
    path('product/add/', views.ProductCreateView.as_view(), name='add_product'),
    path('product/<uuid:pk>/edit/', views.ProductUpdateView.as_view(), name='edit_product'),
    path('product/<uuid:pk>/delete/', views.ProductDeleteView.as_view(), name='delete_product'),
    
    # Price update endpoints
    path('product/<uuid:product_id>/update-price/', views.update_price_manual, name='update_price_manual'),
    path('bulk-update-prices/', views.bulk_update_prices, name='bulk_update_prices'),
    
    # Alert management
    path('product/<uuid:product_id>/alert/add/', views.add_alert, name='add_alert'),
    path('alert/<int:alert_id>/delete/', views.delete_alert, name='delete_alert'),
    
    # AJAX endpoints
    path('product/<uuid:product_id>/toggle-status/', views.toggle_product_status, name='toggle_product_status'),
    
    # Chart and data APIs
    path('api/product/<uuid:product_id>/chart-data/', views.chart_data_api, name='chart_data_api'),
    path('api/products/', views.api_products, name='api_products'),
    
    # User management
    path('register/', views.register, name='register'),
    path('profile/', views.profile, name='profile'),
    path('export/', views.export_data, name='export_data'),
]
