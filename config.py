# config.py
import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'secret_dev_key')
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL', 'sqlite:///travel.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    OPENWEATHER_API_KEY = os.environ.get('OPENWEATHER_API_KEY')
    AMADEUS_API_KEY = os.environ.get('AMADEUS_API_ID')
    AMADEUS_API_SECRET = os.environ.get('AMADEUS_API_SECRET')
    OPENROUTER_API_KEY = os.environ.get('OPENROUTER_API_KEY')
    SERP_API_KEY = os.environ.get('SERP_API_KEY')
