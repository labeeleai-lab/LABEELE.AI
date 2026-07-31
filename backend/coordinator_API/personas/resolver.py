"""
personas/resolver.py - get_safe_persona(): the safe persona lookup used
everywhere a persona config is needed. Checks the database first
(PersonaConfig - admin-editable at runtime via /admin/personas, including
personas that don't exist in the hardcoded dict at all), then falls back to
SPECIALIST_PERSONAS.
"""
import logging

from coordinator_API.core.db import SessionLocal
from coordinator_API.models.orm import PersonaConfig
from coordinator_API.personas.specialists import SPECIALIST_PERSONAS

logger = logging.getLogger(__name__)


def _persona_row_to_dict(row) -> dict:
    """Shape a PersonaConfig DB row exactly like a SPECIALIST_PERSONAS[...] entry."""
    return {
        "name": row.name,
        "category": row.category,
        "reputation_multiplier": row.reputation_multiplier,
        "min_response_tokens": row.min_response_tokens,
        "max_response_tokens": row.max_response_tokens,
        "temperature": row.temperature,
        "requires_validation": row.requires_validation,
        "system_prompt": row.system_prompt,
        "validation_keywords": row.validation_keywords or [],
    }


def get_safe_persona(persona_type: str) -> tuple[str, dict]:
    """
    SAFE lookup - NEVER raises KeyError on missing persona.

    Checks the database first (PersonaConfig - admin-editable at runtime via
    /admin/personas, including personas that don't exist in the hardcoded
    dict at all), then falls back to the hardcoded SPECIALIST_PERSONAS dict
    below exactly as before. The hardcoded dict is intentionally never
    removed, so a DB outage or empty table can't take personas offline.
    """
    # Priority 0: Database override / DB-only persona
    try:
        db = SessionLocal()
        try:
            row = (
                db.query(PersonaConfig)
                .filter(PersonaConfig.persona_id == persona_type, PersonaConfig.is_active == True)
                .first()
            )
            if row:
                return persona_type, _persona_row_to_dict(row)
        finally:
            db.close()
    except Exception as e:
        logger.warning(f"⚠️ PersonaConfig DB lookup failed for '{persona_type}', falling back to hardcoded: {e}")

    # Priority 1: Exact match
    if persona_type in SPECIALIST_PERSONAS:
        return persona_type, SPECIALIST_PERSONAS[persona_type]

    logger.warning(f"⚠️ Persona '{persona_type}' not found in SPECIALIST_PERSONAS")

    # Priority 2: Fall back to "duke-ml" if available
    if "duke-ml" in SPECIALIST_PERSONAS:
        logger.warning(f"⚠️ Using 'duke-ml' fallback instead of '{persona_type}'")
        return "duke-ml", SPECIALIST_PERSONAS["duke-ml"]

    # Priority 3: Use first available persona
    if SPECIALIST_PERSONAS:
        fallback_id = next(iter(SPECIALIST_PERSONAS.keys()))
        logger.warning(f"⚠️ Using '{fallback_id}' fallback ('{persona_type}' not found, 'duke-ml' not available)")
        return fallback_id, SPECIALIST_PERSONAS[fallback_id]

    # Priority 4: Catastrophic failure (should never happen)
    logger.error("❌ CRITICAL: No personas defined at all!")
    return persona_type, {}
