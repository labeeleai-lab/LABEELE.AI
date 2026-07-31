"""
routers/auth.py - POST /api/auth/register, POST /api/auth/login.
"""
from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger
from coordinator_API.core.db import get_db
from coordinator_API.core.security import hash_password, verify_password, create_access_token
from coordinator_API.models.orm import User
from coordinator_API.models.schemas import LoginRequest

router = APIRouter()


@router.post("/api/auth/register", tags=["auth"])
async def register(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
        # Fix: Ensure email is handled even if missing
        email = body.get("email") or f"{username}@labeele.ai"

        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing username or password")

        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Create user
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True
        )

        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": "User registered successfully", "status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Registration Error: {e}")
        # Return 500 but with JSON so frontend doesn't just crash
        return JSONResponse(status_code=500, content={"detail": str(e)})


@router.post("/api/auth/login", tags=["auth"])
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # SEARCH BY USERNAME
    user = db.query(User).filter(User.username == request.username).first()

    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )

    # Generate JWT token
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}
