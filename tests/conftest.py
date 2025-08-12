import sys
import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient
from main import app
from db.init_engine import Base, get_db

# Add project root to sys.path if needed
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# SQLite in-memory database URL for testing
SQLALCHEMY_DATABASE_URL = "sqlite://"

# Create engine with StaticPool for in-memory persistence during test
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

# Create session factory bound to this engine
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables in test database
Base.metadata.create_all(bind=engine)

# Dependency override: use test DB session instead of production one
def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

@pytest.fixture(scope="function")
def db():
    """
    Creates a clean database session for each test,
    clearing all tables before yielding the session.
    """
    db = TestingSessionLocal()
    try:
        # Clear all tables before each test
        for table in reversed(Base.metadata.sorted_tables):
            db.execute(table.delete())
        db.commit()
        yield db
    finally:
        db.close()

@pytest.fixture(scope="function")
def client():
    """
    Provides a TestClient instance for API calls.
    """
    yield TestClient(app)
