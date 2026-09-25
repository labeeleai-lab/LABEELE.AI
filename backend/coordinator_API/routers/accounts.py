"""
routers/accounts.py - the website's own local account system: signup, login,
profile, account deletion, dashboard query history, and the contact form.

Replaces the site's former dependency on Supabase Auth/Postgres for all of
this. Backed entirely by the dedicated SQLite database in core/accounts_db.py
- no external service required. Admin-only endpoints reuse the existing
require_admin_secret gate (same X-Admin-Secret header already used by the
other /admin/* endpoints in this API).
"""
import re
from typing import Optional

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from coordinator_API.core.accounts_db import get_accounts_db
from coordinator_API.core.accounts_security import (
    create_account_token,
    hash_account_password,
    verify_account_password,
    verify_account_token,
)
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.accounts_orm import Account, ContactMessage, QueryHistoryEntry

router = APIRouter()

# Deliberately not pydantic's EmailStr - that requires the extra
# email-validator dependency. A plain shape check is enough here.
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def _validate_email(v: str) -> str:
    v = v.strip().lower()
    if not _EMAIL_RE.match(v):
        raise ValueError("Enter a valid email address.")
    return v


# ==================== SCHEMAS ====================

class RegisterBody(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=200)
    full_name: Optional[str] = Field(default=None, max_length=100)

    _validate = field_validator("email")(_validate_email)


class LoginBody(BaseModel):
    email: str
    password: str

    _validate = field_validator("email")(_validate_email)


class UpdateMeBody(BaseModel):
    full_name: Optional[str] = Field(default=None, max_length=100)
    password: Optional[str] = Field(default=None, min_length=8, max_length=200)


class ContactBody(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    email: str
    message: str = Field(..., min_length=1, max_length=5000)

    _validate = field_validator("email")(_validate_email)


class HistoryCreateBody(BaseModel):
    agent_id: str = Field(..., max_length=100)
    query: str = Field(..., min_length=1)
    response: Optional[str] = None


class PromoteAdminBody(BaseModel):
    email: str

    _validate = field_validator("email")(_validate_email)


def _account_out(account: Account) -> dict:
    return {
        "id": account.id,
        "email": account.email,
        "full_name": account.full_name,
        "is_admin": account.is_admin,
    }


def get_current_account(
    authorization: Optional[str] = Header(default=None),
    db: Session = Depends(get_accounts_db),
) -> Account:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Not signed in.")

    token = authorization.split(" ", 1)[1].strip()
    payload = verify_account_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Session expired or invalid.")

    account = db.query(Account).filter(Account.id == payload.get("sub")).first()
    if not account or not account.is_active:
        raise HTTPException(status_code=401, detail="Account no longer exists.")

    return account


# ==================== AUTH ====================

@router.post("/api/accounts/register", tags=["accounts"])
async def register(body: RegisterBody, db: Session = Depends(get_accounts_db)):
    existing = db.query(Account).filter(Account.email == body.email.lower()).first()
    if existing:
        raise HTTPException(status_code=409, detail="An account with that email already exists.")

    account = Account(
        email=body.email.lower(),
        full_name=body.full_name,
        password_hash=hash_account_password(body.password),
    )
    db.add(account)
    db.commit()
    db.refresh(account)

    token = create_account_token(account.id, account.email, account.is_admin)
    return {"token": token, "user": _account_out(account)}


@router.post("/api/accounts/login", tags=["accounts"])
async def login(body: LoginBody, db: Session = Depends(get_accounts_db)):
    account = db.query(Account).filter(Account.email == body.email.lower()).first()
    if not account or not verify_account_password(body.password, account.password_hash):
        raise HTTPException(status_code=401, detail="Invalid email or password.")

    if not account.is_active:
        raise HTTPException(status_code=403, detail="This account has been disabled.")

    token = create_account_token(account.id, account.email, account.is_admin)
    return {"token": token, "user": _account_out(account)}


@router.get("/api/accounts/me", tags=["accounts"])
async def get_me(account: Account = Depends(get_current_account)):
    return _account_out(account)


@router.put("/api/accounts/me", tags=["accounts"])
async def update_me(
    body: UpdateMeBody,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_accounts_db),
):
    if body.full_name is not None:
        account.full_name = body.full_name
    if body.password:
        account.password_hash = hash_account_password(body.password)

    db.commit()
    db.refresh(account)
    return _account_out(account)


@router.delete("/api/accounts/me", tags=["accounts"])
async def delete_me(
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_accounts_db),
):
    db.query(QueryHistoryEntry).filter(QueryHistoryEntry.account_id == account.id).delete()
    db.delete(account)
    db.commit()
    return {"success": True}


# ==================== DASHBOARD QUERY HISTORY ====================

@router.get("/api/accounts/history", tags=["accounts"])
async def list_history(
    limit: int = 20,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_accounts_db),
):
    rows = (
        db.query(QueryHistoryEntry)
        .filter(QueryHistoryEntry.account_id == account.id)
        .order_by(QueryHistoryEntry.created_at.desc())
        .limit(min(limit, 100))
        .all()
    )
    return [
        {
            "id": row.id,
            "agent_id": row.agent_id,
            "query": row.query,
            "response": row.response,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post("/api/accounts/history", tags=["accounts"])
async def add_history(
    body: HistoryCreateBody,
    account: Account = Depends(get_current_account),
    db: Session = Depends(get_accounts_db),
):
    entry = QueryHistoryEntry(
        account_id=account.id,
        agent_id=body.agent_id,
        query=body.query,
        response=body.response,
    )
    db.add(entry)
    db.commit()
    return {"success": True}


# ==================== CONTACT FORM ====================

@router.post("/api/contact", tags=["contact"])
async def submit_contact(body: ContactBody, db: Session = Depends(get_accounts_db)):
    message = ContactMessage(name=body.name, email=body.email.lower(), message=body.message)
    db.add(message)
    db.commit()
    return {"success": True}


@router.get(
    "/api/accounts/admin/contact-messages",
    tags=["accounts-admin"],
    dependencies=[Depends(require_admin_secret)],
)
async def list_contact_messages(db: Session = Depends(get_accounts_db)):
    rows = db.query(ContactMessage).order_by(ContactMessage.created_at.desc()).all()
    return [
        {
            "id": row.id,
            "name": row.name,
            "email": row.email,
            "message": row.message,
            "is_read": row.is_read,
            "created_at": row.created_at.isoformat(),
        }
        for row in rows
    ]


@router.post(
    "/api/accounts/admin/contact-messages/{message_id}/read",
    tags=["accounts-admin"],
    dependencies=[Depends(require_admin_secret)],
)
async def mark_contact_message_read(message_id: str, db: Session = Depends(get_accounts_db)):
    message = db.query(ContactMessage).filter(ContactMessage.id == message_id).first()
    if not message:
        raise HTTPException(status_code=404, detail="Message not found.")
    message.is_read = True
    db.commit()
    return {"success": True}


# ==================== ADMIN: TEAM MANAGEMENT ====================

@router.get(
    "/api/accounts/admin/users",
    tags=["accounts-admin"],
    dependencies=[Depends(require_admin_secret)],
)
async def list_admin_users(db: Session = Depends(get_accounts_db)):
    rows = db.query(Account).filter(Account.is_admin == True).order_by(Account.created_at.asc()).all()  # noqa: E712
    return [
        {"email": row.email, "added_by": None, "created_at": row.created_at.isoformat()}
        for row in rows
    ]


@router.post(
    "/api/accounts/admin/users",
    tags=["accounts-admin"],
    dependencies=[Depends(require_admin_secret)],
)
async def promote_admin_user(body: PromoteAdminBody, db: Session = Depends(get_accounts_db)):
    account = db.query(Account).filter(Account.email == body.email.lower()).first()
    if not account:
        raise HTTPException(
            status_code=404,
            detail="No account found for that email - they need to sign up first.",
        )
    if account.is_admin:
        raise HTTPException(status_code=409, detail="That email is already an admin.")

    account.is_admin = True
    db.commit()
    return {"success": True}


@router.delete(
    "/api/accounts/admin/users/{email}",
    tags=["accounts-admin"],
    dependencies=[Depends(require_admin_secret)],
)
async def demote_admin_user(email: str, db: Session = Depends(get_accounts_db)):
    target_email = email.lower()
    admin_count = db.query(Account).filter(Account.is_admin == True).count()  # noqa: E712

    if admin_count <= 1:
        raise HTTPException(status_code=409, detail="Can't remove the last remaining admin.")

    account = db.query(Account).filter(Account.email == target_email).first()
    if not account or not account.is_admin:
        raise HTTPException(status_code=404, detail="That email is not an admin.")

    account.is_admin = False
    db.commit()
    return {"success": True}
