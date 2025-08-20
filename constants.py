import os
from dotenv import load_dotenv

load_dotenv()

DB_HOSTNAME: str = os.environ.get('DB_HOSTNAME')
DB_PORT: str = os.environ.get('DB_PORT')
DB_USER: str = os.environ.get('DB_USER')
DB_PASSWORD: str = os.environ.get('DB_PASSWORD')
DB_DATABASE: str = os.environ.get('DB_DATABASE')

SECRET_KEY: str = os.environ.get('SECRET_KEY')
ALGORITHM: str = os.environ.get('ALGORITHM')
ACCESS_TOKEN_EXPIRE_MINUTES: str = os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES')