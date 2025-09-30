# backend/src/db/database.py
import os
from sqlalchemy import create_engine, MetaData
from sqlalchemy.orm import sessionmaker, DeclarativeBase

# --------------------------------------------------------------------
# Database URL (from environment)
# Example: postgresql+psycopg2://user:password@localhost:5432/poker_analytics
# --------------------------------------------------------------------
DATABASE_URL = os.getenv("DATABASE_URL")

# --------------------------------------------------------------------
# Naming convention helps Alembic generate stable migration diffs
# --------------------------------------------------------------------
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}

# --------------------------------------------------------------------
# Base class with metadata (used by models.py)
# --------------------------------------------------------------------
class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)

# --------------------------------------------------------------------
# Engine and Session factory
# --------------------------------------------------------------------
engine = create_engine(
    DATABASE_URL,
    future=True,
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20,
    pool_recycle=3600,
    pool_timeout=30,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
    expire_on_commit=False,
    future=True,
)
