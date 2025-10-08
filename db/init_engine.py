from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import QueuePool
from constants import DB_HOSTNAME, DB_PASSWORD, DB_PORT, DB_USER, DB_DATABASE

URL_DATABASE = f"mysql+pymysql://{DB_USER}:{DB_PASSWORD}@{DB_HOSTNAME}:{DB_PORT}/{DB_DATABASE}"

engine = create_engine(
    URL_DATABASE,
    poolclass=QueuePool,
    pool_size=5,
    max_overflow=10,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args={"connect_timeout": 10},
    echo=False,
    future=True,
    isolation_level="READ COMMITTED",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
