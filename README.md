# 🧠 Job Scraper & Portal (Django + Selenium)

This project is a Django-based job scraping and search system that collects job listings from **Indeed**, **LinkedIn**, and **JobStreet** using Selenium and stores them in a PostgreSQL database.

## 🚀 Features

- 🔍 Scrapes jobs based on keyword and location
- 🌐 Extracts job title, company, location, employment type, remote option, seniority level, and posted date
- 📅 Auto-clears database before each run
- 🔧 Integrates with Django models and admin for easy access
- 💡 Proxy support with stealth anti-bot detection

## 📁 Project Structure
jobportal/ # Django app
jobsite/ # Django project settings
scraper_combined.py # Scraper script
requirements.txt # All Python dependencies
README.md # You're reading this!
manage.py


## 📦 Requirements

- Python 3.9+
- PostgreSQL
- Google Chrome
- ChromeDriver
- A Bright Data (Luminati) proxy account (optional)

## 🔧 Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/job-scraper.git
   cd job-scraper


2. Create a virtual environment and activate it:
   python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

3. Install dependencies:
   pip install -r requirements.txt

4. Configure database settings in jobsite/settings.py or use .env.

5. Run migrations:
   python manage.py makemigrations
   python manage.py migrate


To scrape jobs:
python scraper_combined.py

To run the Django server:
python manage.py runserver



