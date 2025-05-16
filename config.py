# config.py
import os
from dotenv import load_dotenv

load_dotenv()

# Configuration AWS
AWS_ACCESS_KEY = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY = os.getenv('AWS_SECRET_KEY')
AWS_REGION = os.getenv('AWS_REGION', 'eu-west-3')

# Configuration de l'application
FLASK_SECRET_KEY = os.getenv('FLASK_SECRET_KEY', 'default_secret_key_for_development')
WHISPER_MODEL = os.getenv('WHISPER_MODEL', 'base')
SOURCE_LANGUAGE = os.getenv('SOURCE_LANGUAGE', 'fr')

# Langues supportées
SUPPORTED_LANGUAGES = {
    'fr': 'Français (original)',
    'en': 'English',
    'es': 'Español',
    'de': 'Deutsch',
    'it': 'Italiano'
}