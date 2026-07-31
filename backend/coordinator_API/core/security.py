"""
core/security.py - admin shared-secret gate, password hashing, and JWT helpers.

verify_token: the original file had two colliding definitions. The first
(module top, raised HTTPException, returned the full decoded payload) was
never actually reachable - the later definition below silently shadowed it
in the module namespace, and only the later one is what every real call site
(register/login/create_task/deploy_agent handlers) resolves to at runtime.
Per the approved cleanup plan, only the reachable version is kept here.
"""
import os
import secrets
import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

import jwt
from fastapi import HTTPException, Header

# ==================== ADMIN AUTH ====================
# Shared-secret gate for administrative endpoints (training controls, persona
# CRUD, feedback/task review, stats, training-data upload). This is not user
# auth - the website's own Supabase-backed admin check already verifies who
# is calling before a request ever reaches this API. This exists so the raw
# backend URL by itself isn't a wide-open admin surface to anyone who finds it.
ADMIN_API_SECRET = os.getenv("ADMIN_API_SECRET")


def require_admin_secret(x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret")):
    if not ADMIN_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints are not configured on this backend (ADMIN_API_SECRET unset).",
        )
    if not x_admin_secret or not secrets.compare_digest(x_admin_secret, ADMIN_API_SECRET):
        raise HTTPException(status_code=403, detail="Invalid or missing admin credentials.")


# ==================== PASSWORD HASHING ====================
def hash_password(password: str) -> str:
    """Securely hash a password for storage."""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored hash."""
    return hash_password(plain_password) == hashed_password


# ==================== JWT CONFIGURATION ====================
JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or JWT_SECRET == "your-secret-key-change-in-production":
    raise ValueError(
        "❌ CRITICAL SECURITY ERROR: JWT_SECRET must be set in environment variables!\n"
        "Generate a secure secret with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
        "Then add to .env file: JWT_SECRET=<your-generated-secret>"
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))


def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt


def verify_token(token: str):
    """Verify JWT token. Returns the 'sub' claim, or None if invalid/expired.

    This is the reachable definition (previously at line ~2248, in the
    "JWT & AUTH" section) - the only one used by register/login/create_task/
    deploy_agent. It deliberately swallows exceptions and returns None rather
    than raising, matching that existing call-site contract.
    """
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except:
        return None


def create_token(username: str):
    """Create JWT token. DEAD CODE - never called anywhere in the original
    file (superseded by create_access_token). Relocated as-is per the
    approved cleanup plan (dead functions are moved, not deleted)."""
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)
