"""
core/db.py - SQLAlchemy engine, session factory, declarative base, and the
get_db() FastAPI dependency.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from coordinator_API.core.config import DATABASE_URL

# ==================== DATABASE CONFIGURATION ====================
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Define get_db here to ensure it's available for all dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
