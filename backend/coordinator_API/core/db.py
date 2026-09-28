"""
core/db.py - SQLAlchemy engine, session factory, declarative base, and the
get_db() FastAPI dependency.
"""
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from coordinator_API.core.config import DATABASE_URL

# ==================== DATABASE CONFIGURATION ====================
# pool_pre_ping + pool_recycle: found necessary live (2026-09) when a real
# LoRA fine-tuning run (ml/finetune.py) held its DB session for ~20 minutes
# of CPU-bound training and Neon closed the idle connection - the final
# bookkeeping write then failed with "SSL connection has been closed
# unexpectedly". pre_ping tests each pooled connection with a lightweight
# check before handing it out and transparently reconnects if it's dead;
# pool_recycle proactively retires connections older than 30 minutes so
# they're never left long enough to hit a managed provider's own idle
# timeout in the first place.
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40, pool_pre_ping=True, pool_recycle=1800)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# Define get_db here to ensure it's available for all dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
