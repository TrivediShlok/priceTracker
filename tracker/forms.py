"""
Django forms for the Price Tracker application.

This module defines forms for user input validation and data collection
for products, alerts, and other user interactions.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import URLValidator, MinValueValidator
from django.utils.translation import gettext_lazy as _
from .models import Product, PriceAlert


class ProductForm(forms.ModelForm):
    """
    Form for adding and editing products.
    
    This form handles product creation and updates with validation
    for URLs and price thresholds.
    """
    
    class Meta:
        model = Product
        fields = ['name', 'url', 'alert_threshold', 'currency']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name',
                'maxlength': '200'
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://amazon.in/product-url or https://flipkart.com/product-url'
            }),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter price threshold for alerts',
                'min': '0',
                'step': '0.01'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-control'
            }, choices=[
                ('INR', 'Indian Rupee (₹)'),
                ('USD', 'US Dollar ($)'),
                ('EUR', 'Euro (€)'),
                ('GBP', 'British Pound (£)'),
            ])
        }
        labels = {
            'name': _('Product Name'),
            'url': _('Product URL'),
            'alert_threshold': _('Price Alert Threshold'),
            'currency': _('Currency'),
        }
        help_texts = {
            'url': _('Enter the product URL from Amazon, Flipkart, or other supported e-commerce sites.'),
            'alert_threshold': _('Set a price threshold to receive alerts when the price drops below this value.'),
        }
    
    def clean_url(self):
        """Validate that the URL is from a supported e-commerce site."""
        url = self.cleaned_data.get('url')
        if url:
            url_lower = url.lower()
            supported_domains = ['amazon.in', 'amazon.com', 'flipkart.com', 'flipkart.in']
            
            if not any(domain in url_lower for domain in supported_domains):
                raise forms.ValidationError(
                    _('Please enter a valid URL from Amazon or Flipkart.')
                )
        
        return url
    
    def clean_alert_threshold(self):
        """Validate that alert threshold is positive if provided."""
        threshold = self.cleaned_data.get('alert_threshold')
        if threshold is not None and threshold <= 0:
            raise forms.ValidationError(
                _('Alert threshold must be a positive number.')
            )
        return threshold


class AlertForm(forms.ModelForm):
    """
    Form for creating and editing price alerts.
    
    This form handles alert configuration with validation for
    threshold values and notification preferences.
    """
    
    class Meta:
        model = PriceAlert
        fields = ['alert_type', 'threshold_value', 'email_notification', 'web_notification']
        widgets = {
            'alert_type': forms.Select(attrs={
                'class': 'form-control'
            }),
            'threshold_value': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter threshold value',
                'min': '0',
                'step': '0.01'
            }),
            'email_notification': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
            'web_notification': forms.CheckboxInput(attrs={
                'class': 'form-check-input'
            }),
        }
        labels = {
            'alert_type': _('Alert Type'),
            'threshold_value': _('Threshold Value'),
            'email_notification': _('Email Notifications'),
            'web_notification': _('Web Notifications'),
        }
        help_texts = {
            'alert_type': _('Choose the type of alert you want to receive.'),
            'threshold_value': _('Set the price threshold that will trigger this alert.'),
            'email_notification': _('Receive alerts via email.'),
            'web_notification': _('Receive alerts on the website.'),
        }
    
    def clean_threshold_value(self):
        """Validate that threshold value is positive."""
        threshold = self.cleaned_data.get('threshold_value')
        if threshold <= 0:
            raise forms.ValidationError(
                _('Threshold value must be a positive number.')
            )
        return threshold
    
    def clean(self):
        """Ensure at least one notification method is selected."""
        cleaned_data = super().clean()
        email_notification = cleaned_data.get('email_notification')
        web_notification = cleaned_data.get('web_notification')
        
        if not email_notification and not web_notification:
            raise forms.ValidationError(
                _('Please select at least one notification method.')
            )
        
        return cleaned_data


class UserRegistrationForm(UserCreationForm):
    """
    Extended user registration form with additional fields.
    
    This form extends Django's built-in UserCreationForm to include
    email and other user preferences.
    """
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your first name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=True,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your last name'
        })
    )
    
    class Meta:
        model = User
        fields = ['username', 'first_name', 'last_name', 'email', 'password1', 'password2']
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def clean_email(self):
        """Ensure email is unique."""
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _('A user with this email address already exists.')
            )
        return email


class ProductSearchForm(forms.Form):
    """
    Form for searching products.
    
    This form provides search functionality for finding products
    by name, price range, or other criteria.
    """
    
    search_query = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    
    min_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'min': '0',
            'step': '0.01'
        })
    )
    
    max_price = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'min': '0',
            'step': '0.01'
        })
    )
    
    currency = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Currencies'),
            ('INR', 'Indian Rupee (₹)'),
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    is_active = forms.ChoiceField(
        required=False,
        choices=[
            ('', 'All Products'),
            ('True', 'Active Only'),
            ('False', 'Inactive Only'),
        ],
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    def clean(self):
        """Validate that min_price is less than max_price."""
        cleaned_data = super().clean()
        min_price = cleaned_data.get('min_price')
        max_price = cleaned_data.get('max_price')
        
        if min_price and max_price and min_price > max_price:
            raise forms.ValidationError(
                _('Minimum price cannot be greater than maximum price.')
            )
        
        return cleaned_data


class ExportForm(forms.Form):
    """
    Form for exporting product data.
    
    This form allows users to export their product data in various formats.
    """
    
    EXPORT_FORMATS = [
        ('csv', 'CSV'),
        ('json', 'JSON'),
        ('xlsx', 'Excel'),
    ]
    
    EXPORT_TYPES = [
        ('all', 'All Products'),
        ('active', 'Active Products Only'),
        ('with_history', 'Products with Price History'),
        ('with_predictions', 'Products with Predictions'),
    ]
    
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMATS,
        initial='csv',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    export_type = forms.ChoiceField(
        choices=EXPORT_TYPES,
        initial='all',
        widget=forms.Select(attrs={
            'class': 'form-control'
        })
    )
    
    include_price_history = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    include_predictions = forms.BooleanField(
        required=False,
        initial=True,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input'
        })
    )
    
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
    
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            'class': 'form-control',
            'type': 'date'
        })
    )
