"""
routers/admin_personas.py - GET /admin/personas, GET /admin/personas/{persona_id},
POST /admin/personas, PUT /admin/personas/{persona_id}.

CRUD over PersonaConfig (see models/orm.py + personas/resolver.get_safe_persona()).
Lets an admin change a persona's behavior, or add an entirely new persona, at
runtime with no code change or redeploy.
"""
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger
from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.orm import PersonaConfig
from coordinator_API.models.schemas import (
    PersonaConfigResponse, PersonaConfigCreate, PersonaConfigUpdate,
)

router = APIRouter()


@router.get(
    "/admin/personas",
    response_model=List[PersonaConfigResponse],
    tags=["Personas"],
    dependencies=[Depends(require_admin_secret)],
)
async def list_personas(db: Session = Depends(get_db)):
    """List every data-driven persona (live + admin-created), most recently added first."""
    return db.query(PersonaConfig).order_by(PersonaConfig.persona_id).all()


@router.get(
    "/admin/personas/{persona_id}",
    response_model=PersonaConfigResponse,
    tags=["Personas"],
    dependencies=[Depends(require_admin_secret)],
)
async def get_persona(persona_id: str, db: Session = Depends(get_db)):
    row = db.query(PersonaConfig).filter(PersonaConfig.persona_id == persona_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")
    return row


@router.post(
    "/admin/personas",
    response_model=PersonaConfigResponse,
    status_code=201,
    tags=["Personas"],
    dependencies=[Depends(require_admin_secret)],
)
async def create_persona(payload: PersonaConfigCreate, db: Session = Depends(get_db)):
    """Create a brand new persona - e.g. a roadmap persona going live for the first time."""
    existing = db.query(PersonaConfig).filter(PersonaConfig.persona_id == payload.persona_id).first()
    if existing:
        raise HTTPException(status_code=409, detail=f"Persona '{payload.persona_id}' already exists")

    row = PersonaConfig(
        persona_id=payload.persona_id,
        name=payload.name,
        category=payload.category,
        reputation_multiplier=payload.reputation_multiplier,
        min_response_tokens=payload.min_response_tokens,
        max_response_tokens=payload.max_response_tokens,
        temperature=payload.temperature,
        requires_validation=payload.requires_validation,
        system_prompt=payload.system_prompt,
        validation_keywords=payload.validation_keywords,
        is_active=True,
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    logger.info(f"✅ Created new persona via admin API: {payload.persona_id}")
    return row


@router.put(
    "/admin/personas/{persona_id}",
    response_model=PersonaConfigResponse,
    tags=["Personas"],
    dependencies=[Depends(require_admin_secret)],
)
async def update_persona(persona_id: str, payload: PersonaConfigUpdate, db: Session = Depends(get_db)):
    """Edit any field of an existing persona - most importantly system_prompt. Takes effect
    on the very next query, since get_safe_persona() reads this table live."""
    row = db.query(PersonaConfig).filter(PersonaConfig.persona_id == persona_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")

    updates = payload.model_dump(exclude_unset=True)

    new_min = updates.get("min_response_tokens", row.min_response_tokens)
    new_max = updates.get("max_response_tokens", row.max_response_tokens)
    if new_max < new_min:
        raise HTTPException(status_code=422, detail="max_response_tokens must be >= min_response_tokens")

    for field, value in updates.items():
        setattr(row, field, value)
    row.updated_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(row)
    logger.info(f"✅ Updated persona via admin API: {persona_id}")
    return row
