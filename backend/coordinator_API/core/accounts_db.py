"""
core/accounts_db.py - dedicated SQLite database for the local account system
(accounts, contact messages, dashboard query history).

Deliberately its own engine/file, completely independent of DATABASE_URL
(the pgvector-backed Postgres database used for knowledge_chunks etc., which
in production has historically pointed at a Supabase-hosted instance) - login,
signup, and the contact form must keep working even if that database or its
provider is unreachable.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from coordinator_API.core.config import APP_DIR

ACCOUNTS_DB_PATH = os.path.join(str(APP_DIR), "data", "accounts.db")
os.makedirs(os.path.dirname(ACCOUNTS_DB_PATH), exist_ok=True)

accounts_engine = create_engine(
    f"sqlite:///{ACCOUNTS_DB_PATH}", connect_args={"check_same_thread": False}
)
AccountsSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=accounts_engine)
AccountsBase = declarative_base()


def get_accounts_db():
    db = AccountsSessionLocal()
    try:
        yield db
    finally:
        db.close()
