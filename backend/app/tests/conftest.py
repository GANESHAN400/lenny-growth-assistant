"""Shared test fixtures and configuration for Lenny Growth Assistant test suite."""
import os
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

# Use an in-memory SQLite database for tests
os.environ.setdefault("DATABASE_URL", "sqlite+pysqlite:///./test_lenny.db")
os.environ.setdefault("DEFAULT_PROVIDER", "ollama")
os.environ.setdefault("LOG_LEVEL", "WARNING")

from app.database.base import Base


@pytest.fixture(scope="session")
def test_engine():
    """Create a test database engine with an in-memory SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite:///./test_lenny.db",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="session")
def test_session_factory(test_engine):
    """Create a session factory bound to the test engine."""
    return sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture
def db_session(test_session_factory):
    """Provide a transactional database session that rolls back after each test."""
    session = test_session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@pytest.fixture(scope="session")
def client(test_engine):
    """FastAPI TestClient with test database overrides."""
    from app.main import app
    from app.database import get_db

    TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)

    def override_get_db():
        db = TestSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

    app.dependency_overrides.clear()
