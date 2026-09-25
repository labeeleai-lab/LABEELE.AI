"""
models/accounts_orm.py - ORM models for the local account system: Account,
ContactMessage, QueryHistoryEntry.

Kept separate from models/orm.py (which requires the pgvector extension and
a reachable Postgres DATABASE_URL) so signup/login/contact always work on
plain SQLite, regardless of the main database's availability.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, Column, DateTime, Index, String, Text

from coordinator_API.core.accounts_db import AccountsBase, accounts_engine


class Account(AccountsBase):
    __tablename__ = "accounts"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    email = Column(String, unique=True, index=True, nullable=False)
    full_name = Column(String, nullable=True)
    password_hash = Column(String, nullable=False)
    is_admin = Column(Boolean, default=False, nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class ContactMessage(AccountsBase):
    __tablename__ = "contact_messages"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    email = Column(String, nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))


class QueryHistoryEntry(AccountsBase):
    __tablename__ = "query_history"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    account_id = Column(String, index=True, nullable=False)
    agent_id = Column(String, nullable=False)
    query = Column(Text, nullable=False)
    response = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index("ix_query_history_account_created", "account_id", "created_at"),
    )


AccountsBase.metadata.create_all(bind=accounts_engine)
