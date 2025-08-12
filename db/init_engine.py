from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from constants import DB_HOSTNAME, DB_PASSWORD, DB_PORT, DB_USER, DB_DATABASE

URL_DATABASE = f'mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOSTNAME}:{DB_PORT}/{DB_DATABASE}'

engine = create_engine(
    URL_DATABASE,
    poolclass=QueuePool,
    pool_size=5,               # Number of persistent connections
    max_overflow=10,           # Max connections beyond pool_size
    pool_timeout=30,           # Seconds to wait for a connection
    pool_recycle=3600,         # Recycle connections after 1 hour
    pool_pre_ping=True,        # Test connections before use
    connect_args={
        'connect_timeout': 10  # Connection timeout in seconds
    },
    echo=False,                # Set True to log SQL queries
    future=True,               # SQLAlchemy 2.0 compatibility
    isolation_level="REPEATABLE READ"  # MySQL default isolation level
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()