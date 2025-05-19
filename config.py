# config.py
import os
from dotenv import load_dotenv

load_dotenv()

AWS_ACCESS_KEY    = os.getenv('AWS_ACCESS_KEY')
AWS_SECRET_KEY    = os.getenv('AWS_SECRET_KEY')
AWS_REGION        = os.getenv('AWS_REGION', 'eu-west-3')

FLASK_SECRET_KEY  = os.getenv('FLASK_SECRET_KEY')
WHISPER_MODEL     = os.getenv('WHISPER_MODEL', 'large-v3')
SOURCE_LANGUAGE   = os.getenv('SOURCE_LANGUAGE', 'fr')

SUPPORTED_LANGUAGES = {
    'fr': 'Français',
    'en': 'English',
    'es': 'Español'
}

RECORDINGS_DIR    = os.getenv('RECORDINGS_DIR', 'recordings')
