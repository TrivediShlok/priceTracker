# Price Fluctuation Tracker with Demand Prediction

A comprehensive Django web application that tracks product prices from e-commerce sites, predicts price fluctuations and demand trends, and provides a user dashboard with alerts.

## Features

-   **Web Scraping**: Automatically scrape prices from Amazon and Flipkart
-   **Data Processing**: Clean and process price data using Pandas and NumPy
-   **Machine Learning**: Predict price trends and demand using Scikit-learn and Prophet
-   **Visualization**: Interactive charts showing price history and predictions
-   **Alerts**: Email notifications for price drops
-   **User Dashboard**: Track multiple products with detailed analytics
-   **REST API**: Simple API endpoints for data access

## Technology Stack

-   **Backend**: Django 4.2.7
-   **Web Scraping**: BeautifulSoup4, Requests, Selenium
-   **Data Processing**: Pandas, NumPy
-   **Machine Learning**: Scikit-learn, Prophet
-   **Visualization**: Matplotlib, Seaborn
-   **Database**: SQLite (configurable for PostgreSQL)
-   **Task Queue**: Celery (optional)

## Installation

1. **Clone the repository**

    ```bash
    git clone <repository-url>
    cd price_tracker
    ```

2. **Create a virtual environment**

    ```bash
    python -m venv venv

    # On Windows
    venv\Scripts\activate

    # On macOS/Linux
    source venv/bin/activate
    ```

3. **Install dependencies**

    ```bash
    pip install -r requirements.txt
    ```

4. **Set up environment variables**
   Create a `.env` file in the root directory:

    ```
    SECRET_KEY=your-secret-key-here
    DEBUG=True
    EMAIL_HOST=smtp.gmail.com
    EMAIL_PORT=587
    EMAIL_USE_TLS=True
    EMAIL_HOST_USER=your-email@gmail.com
    EMAIL_HOST_PASSWORD=your-app-password
    ```

5. **Run database migrations**

    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

6. **Create a superuser (optional)**

    ```bash
    python manage.py createsuperuser
    ```

7. **Run the development server**

    ```bash
    python manage.py runserver
    ```

8. **Access the application**
    - Main application: http://127.0.0.1:8000/
    - Admin panel: http://127.0.0.1:8000/admin/

## Usage

### Adding Products

1. Go to the dashboard
2. Click "Add Product"
3. Enter product name and URL (Amazon/Flipkart)
4. Set price alert threshold
5. Save the product

### Running Price Updates

To manually update prices and predictions:

```bash
python manage.py update_prices
```

### Setting up Automated Updates

For production, set up a cron job or use Celery:

```bash
# Add to crontab (runs daily at 2 AM)
0 2 * * * cd /path/to/price_tracker && python manage.py update_prices
```

## Project Structure

```
price_tracker/
├── manage.py
├── requirements.txt
├── README.md
├── price_tracker/          # Django settings
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
└── tracker/               # Main application
    ├── migrations/
    ├── templates/
    ├── static/
    ├── management/
    │   └── commands/
    │       └── update_prices.py
    ├── admin.py
    ├── apps.py
    ├── models.py
    ├── views.py
    ├── forms.py
    ├── utils.py
    └── tests.py
```

## API Endpoints

-   `GET /api/products/` - List all products
-   `GET /api/products/{id}/` - Get product details
-   `GET /api/products/{id}/predictions/` - Get demand predictions

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

This project is licensed under the MIT License.

## Troubleshooting

### Common Issues

1. **Prophet installation issues**: On Windows, you might need to install Microsoft Visual C++ Build Tools
2. **Selenium issues**: Make sure you have the appropriate webdriver installed
3. **Email not working**: Check your email credentials and enable 2-factor authentication with app passwords

### Support

For issues and questions, please open an issue on GitHub.
