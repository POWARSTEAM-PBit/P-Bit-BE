from sqlalchemy import create_engine, inspect
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

def init_db():
    """Initialize database tables"""
    from db import db_models
    
    inspector = inspect(engine)
    existing_tables = inspector.get_table_names()
    
    print(f"Existing tables: {existing_tables}")
    
    # Check if we need to create new tables
    required_tables = ['user', 'class', 'class_member']
    missing_tables = [table for table in required_tables if table not in existing_tables]
    
    if missing_tables:
        print(f"Creating missing tables: {missing_tables}")
        try:
            # Create all tables in the correct order
            Base.metadata.create_all(bind=engine)
            print("✅ Database tables created successfully")
        except Exception as e:
            print(f"❌ Error creating tables: {e}")
            # Try creating tables individually in order
            try:
                # Create user table first
                if 'user' not in existing_tables:
                    db_models.User.__table__.create(engine)
                    print("✅ User table created")
                
                # Create class table
                if 'class' not in existing_tables:
                    db_models.Class.__table__.create(engine)
                    print("✅ Class table created")
                
                # Create class_member table
                if 'class_member' not in existing_tables:
                    db_models.ClassMember.__table__.create(engine)
                    print("✅ ClassMember table created")
                    
            except Exception as e2:
                print(f"❌ Error creating tables individually: {e2}")
                raise e2
    else:
        print("✅ All required tables already exist")