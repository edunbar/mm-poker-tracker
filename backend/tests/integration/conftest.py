"""
Shared fixtures for integration tests.
"""
import pytest
from src.db.database import SessionLocal


@pytest.fixture
def db_session():
    """Provide a database session for tests."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()