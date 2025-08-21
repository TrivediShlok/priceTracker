"""
Forms for the Price Tracker application.
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator
from .models import Product, PriceAlert


class ProductForm(forms.ModelForm):
    """Form for creating and updating products."""
    
    class Meta:
        model = Product
        fields = ['name', 'url', 'currency', 'alert_threshold']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name',
                'maxlength': 200
            }),
            'url': forms.URLInput(attrs={
                'class': 'form-control',
                'placeholder': 'https://www.amazon.in/product-url or https://www.flipkart.com/product-url'
            }),
            'currency': forms.Select(attrs={
                'class': 'form-select'
            }, choices=[
                ('INR', 'Indian Rupee (₹)'),
                ('USD', 'US Dollar ($)'),
                ('EUR', 'Euro (€)'),
                ('GBP', 'British Pound (£)')
            ]),
            'alert_threshold': forms.NumberInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter target price',
                'step': '0.01',
                'min': '0'
            })
        }
    
    def clean_url(self):
        url = self.cleaned_data.get('url')
        if url:
            url = url.lower()
            supported_sites = ['amazon.in', 'amazon.com', 'flipkart.com']
            if not any(site in url for site in supported_sites):
                raise forms.ValidationError(
                    'Please enter a valid URL from Amazon or Flipkart.'
                )
        return self.cleaned_data.get('url')


class AlertForm(forms.ModelForm):
    """Form for creating price alerts."""
    
    class Meta:
        model = PriceAlert
        fields = ['alert_type', 'threshold_value', 'email_notification', 'web_notification']
        widgets = {
            'alert_type': forms.RadioSelect(attrs={
                'class': 'form-check-input'
            }),
            'threshold_value': forms.NumberInput(attrs={
                'class': 'form-control threshold-input',
                'placeholder': 'Enter target price',
                'step': '0.01',
                'min': '0'
            }),
            'email_notification': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'checked': True
            }),
            'web_notification': forms.CheckboxInput(attrs={
                'class': 'form-check-input',
                'checked': True
            })
        }
    
    def clean_threshold_value(self):
        threshold = self.cleaned_data.get('threshold_value')
        if threshold is not None and threshold <= 0:
            raise forms.ValidationError('Threshold value must be greater than 0.')
        return threshold


class UserRegistrationForm(UserCreationForm):
    """Enhanced user registration form."""
    
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': 'Enter your email address'
        })
    )
    
    first_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'First name'
        })
    )
    
    last_name = forms.CharField(
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Last name'
        })
    )
    
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'username', 'email', 'password1', 'password2')
        widgets = {
            'username': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Choose a username'
            }),
        }
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['password1'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Create a strong password'
        })
        self.fields['password2'].widget.attrs.update({
            'class': 'form-control',
            'placeholder': 'Confirm your password'
        })
    
    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data['email']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        if commit:
            user.save()
        return user


class ProductSearchForm(forms.Form):
    """Form for searching and filtering products."""
    
    search_query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Search products...'
        })
    )
    
    min_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Min price',
            'step': '0.01'
        })
    )
    
    max_price = forms.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
        validators=[MinValueValidator(0)],
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'placeholder': 'Max price',
            'step': '0.01'
        })
    )
    
    currency = forms.ChoiceField(
        choices=[
            ('', 'All Currencies'),
            ('INR', 'Indian Rupee (₹)'),
            ('USD', 'US Dollar ($)'),
            ('EUR', 'Euro (€)'),
            ('GBP', 'British Pound (£)')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )
    
    is_active = forms.ChoiceField(
        choices=[
            ('', 'All Products'),
            ('True', 'Active Only'),
            ('False', 'Inactive Only')
        ],
        required=False,
        widget=forms.Select(attrs={'class': 'form-select'})
    )


class ExportForm(forms.Form):
    """Form for exporting data."""
    
    EXPORT_FORMAT_CHOICES = [
        ('csv', 'CSV (Excel Compatible)'),
        ('json', 'JSON (Developer Friendly)')
    ]
    
    export_format = forms.ChoiceField(
        choices=EXPORT_FORMAT_CHOICES,
        initial='csv',
        widget=forms.Select(attrs={'class': 'form-select'})
    )
