"""
core/accounts_security.py - password hashing (bcrypt) and session-token
helpers for the website's own local account system (signup/login/session).

Reuses JWT_SECRET/JWT_ALGORITHM from core/security.py so only one secret has
to be configured, but tags every token with "kind": ACCOUNT_TOKEN_KIND so
these session tokens can never be confused with the unrelated buyer JWTs
verify_token() in core/security.py already handles for tasks.py.
"""
from datetime import datetime, timedelta, timezone
from typing import Optional

import bcrypt
import jwt

from coordinator_API.core.security import JWT_SECRET, JWT_ALGORITHM

ACCOUNT_TOKEN_KIND = "account_session"
ACCOUNT_TOKEN_EXPIRY_DAYS = 30

# bcrypt itself (not passlib - passlib 1.7.4's bcrypt backend self-test
# raises on bcrypt>=4.1, a known version-compatibility break). bcrypt also
# hard-caps input at 72 bytes; silently truncating is the standard practice
# (no real password is that long).


def hash_account_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:72], bcrypt.gensalt()).decode("utf-8")


def verify_account_password(plain_password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8")[:72], password_hash.encode("utf-8"))
    except Exception:
        return False


def create_account_token(account_id: str, email: str, is_admin: bool) -> str:
    """is_admin is baked into the token so middleware can gate /admin by
    verifying the token locally (no network round trip to this backend on
    every request). Promoting/demoting an admin takes effect on that
    person's next login, not instantly - an accepted simplification."""
    expire = datetime.now(timezone.utc) + timedelta(days=ACCOUNT_TOKEN_EXPIRY_DAYS)
    payload = {
        "sub": account_id,
        "email": email,
        "is_admin": is_admin,
        "kind": ACCOUNT_TOKEN_KIND,
        "exp": expire,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_account_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        if payload.get("kind") != ACCOUNT_TOKEN_KIND:
            return None
        return payload
    except Exception:
        return None
