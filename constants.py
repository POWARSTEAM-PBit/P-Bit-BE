import os
from dotenv import load_dotenv

load_dotenv()

# Database configuration - Amazon database
DB_HOSTNAME: str = os.environ.get('DB_HOSTNAME')
DB_PORT: str = os.environ.get('DB_PORT', '3306')
DB_USER: str = os.environ.get('DB_USER')
DB_PASSWORD: str = os.environ.get('DB_PASSWORD')
DB_DATABASE: str = os.environ.get('DB_DATABASE')

# JWT Configuration
SECRET_KEY: str = os.environ.get('SECRET_KEY', 'your-secret-key-here')
ALGORITHM: str = os.environ.get('ALGORITHM', 'HS256')
ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.environ.get('ACCESS_TOKEN_EXPIRE_MINUTES', '30'))