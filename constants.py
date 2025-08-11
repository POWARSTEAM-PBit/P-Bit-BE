import os
from dotenv import load_dotenv

load_dotenv()

DB_HOSTNAME: str = os.environ.get('DB_HOSTNAME')
DB_PORT: str = os.environ.get('DB_PORT')
DB_USER: str = os.environ.get('DB_USER')
DB_PASSWORD: str = os.environ.get('DB_PASSWORD')
DB_DATABASE: str = os.environ.get('DB_DATABASE')