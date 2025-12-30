import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

# Telegram Bot Token
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')

# Database
# Railway может предоставить postgres://, но psycopg2 требует postgresql://
database_url = os.getenv('DATABASE_URL', '')
if database_url and database_url.startswith('postgres://'):
    database_url = database_url.replace('postgres://', 'postgresql://', 1)
DATABASE_URL = database_url

# Challenge settings
CHALLENGE_START_DATE = datetime.strptime(
    os.getenv('CHALLENGE_START_DATE', '2025-12-01'), 
    '%Y-%m-%d'
).date()
CHALLENGE_END_DATE = datetime.strptime(
    os.getenv('CHALLENGE_END_DATE', '2026-11-30'), 
    '%Y-%m-%d'
).date()
CHALLENGE_TARGET = int(os.getenv('CHALLENGE_TARGET', '18250'))

# Reminder settings
REMINDER_TIME = os.getenv('REMINDER_TIME', '09:00')

