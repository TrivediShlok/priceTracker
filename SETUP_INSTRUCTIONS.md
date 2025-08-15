# Price Tracker Setup Instructions

## 🚀 Quick Start

The Price Fluctuation Tracker with Demand Prediction is now ready to use! Here's how to get started:

### 1. Prerequisites

-   Python 3.10+ (tested with Python 3.12)
-   pip (Python package installer)

### 2. Installation Steps

#### Step 1: Install Dependencies

```bash
# Install core dependencies
pip install Django==4.2.7 python-decouple==3.8 beautifulsoup4==4.12.2 requests==2.31.0 fake-useragent

# Optional: Install additional ML libraries (if needed)
pip install numpy pandas matplotlib scikit-learn
```

#### Step 2: Set Up Environment Variables

Create a `.env` file in the project root with the following content:

```
SECRET_KEY=django-insecure-your-secret-key-here-change-in-production
DEBUG=True
ALLOWED_HOSTS=127.0.0.1,localhost
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
```

#### Step 3: Run Database Migrations

```bash
python manage.py makemigrations
python manage.py migrate
```

#### Step 4: Create Superuser (Optional)

```bash
python manage.py createsuperuser
```

#### Step 5: Start the Development Server

```bash
python manage.py runserver
```

### 3. Access the Application

-   **Main Application**: http://127.0.0.1:8000/
-   **Admin Panel**: http://127.0.0.1:1:8000/admin/
-   **Login**: Use the superuser credentials you created

## 📋 Features Available

### ✅ Core Features (Working)

-   **User Registration & Authentication**: Complete user management system
-   **Product Management**: Add, edit, delete products with URLs
-   **Price Tracking**: Manual price updates with web scraping
-   **Price History**: Track price changes over time
-   **Alerts System**: Set price drop alerts
-   **Dashboard**: Overview with statistics and recent changes
-   **Search & Filter**: Find products by name, price range, etc.
-   **Data Export**: Export data in CSV and JSON formats
-   **Admin Interface**: Full Django admin for data management

### 🔧 Management Commands

```bash
# Update all product prices
python manage.py update_prices

# Update specific product
python manage.py update_prices --product-id <product-id>

# Force update (ignore recent updates)
python manage.py update_prices --force

# Dry run (see what would be updated)
python manage.py update_prices --dry-run
```

### 📊 API Endpoints

-   `GET /api/products/` - List all products
-   `GET /api/products/{id}/predictions/` - Get demand predictions

## 🛠️ How to Use

### Adding Your First Product

1. Go to http://127.0.0.1:8000/
2. Click "Register" to create an account
3. Click "Add Product"
4. Enter product details:
    - **Name**: Product name
    - **URL**: Amazon or Flipkart product URL
    - **Alert Threshold**: Price at which you want alerts
    - **Currency**: INR, USD, EUR, or GBP
5. Click "Add Product"

### Setting Up Price Alerts

1. Go to a product's detail page
2. Click "Add Alert"
3. Choose alert type (Price Drop, Price Increase, Demand Spike)
4. Set threshold value
5. Choose notification methods (Email, Web)
6. Save the alert

### Manual Price Updates

1. Go to a product's detail page
2. Click "Update Price" button
3. The system will scrape the current price from the product URL

## 🔍 Testing the Application

Run the test script to verify everything works:

```bash
python test_app.py
```

## 📁 Project Structure

```
price_tracker/
├── manage.py                 # Django management script
├── requirements.txt          # Python dependencies
├── README.md                # Project documentation
├── test_app.py              # Test script
├── price_tracker/           # Django settings
│   ├── settings.py          # Application settings
│   ├── urls.py              # Main URL configuration
│   └── wsgi.py              # WSGI configuration
└── tracker/                 # Main application
    ├── models.py            # Database models
    ├── views.py             # View functions
    ├── forms.py             # Form definitions
    ├── admin.py             # Admin interface
    ├── utils.py             # Utility functions
    ├── urls.py              # App URL patterns
    ├── templates/           # HTML templates
    │   └── tracker/
    │       ├── base.html    # Base template
    │       ├── dashboard.html
    │       ├── product_form.html
    │       └── product_detail.html
    └── management/          # Management commands
        └── commands/
            └── update_prices.py
```

## 🐛 Troubleshooting

### Common Issues

1. **Import Errors**: Make sure all dependencies are installed

    ```bash
    pip install -r requirements.txt
    ```

2. **Database Errors**: Run migrations

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

3. **Static Files Warning**: Create static directory

    ```bash
    mkdir static
    ```

4. **Email Not Working**: Configure email settings in `.env` file

### Web Scraping Issues

-   Some websites may block automated requests
-   The scraper includes delays and user agent rotation
-   For production, consider using proxy services

## 🚀 Production Deployment

For production deployment:

1. **Set DEBUG=False** in settings
2. **Use PostgreSQL** instead of SQLite
3. **Configure proper email settings**
4. **Set up Celery** for background tasks
5. **Use a proper web server** (nginx + gunicorn)
6. **Set up SSL certificates**
7. **Configure logging**

## 📈 Future Enhancements

### Planned Features

-   **Advanced ML Models**: Prophet, ARIMA for better predictions
-   **Real-time Notifications**: WebSocket support
-   **Mobile App**: React Native companion app
-   **Advanced Analytics**: Price trend analysis, volatility metrics
-   **Multi-site Support**: More e-commerce platforms
-   **API Rate Limiting**: Protect against abuse
-   **Caching**: Redis for better performance

### Machine Learning Integration

To enable advanced ML features, install additional packages:

```bash
pip install prophet scikit-learn pandas numpy matplotlib seaborn
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License.

## 🆘 Support

For issues and questions:

1. Check the troubleshooting section
2. Review the Django documentation
3. Create an issue on GitHub

---

**Happy Price Tracking! 🎉**
