"""
lifespan.py - the FastAPI lifespan context manager: DB table creation, Duke
Brain startup, agent/persona-config auto-heal & seeding.

Also carries generate_periodic_logs()/periodic_metrics_log(), two DEAD CODE
background loops (never scheduled via asyncio.create_task anywhere in the
app), relocated here as-is per the approved cleanup plan.

duke_brain staleness fix: this module mutates coordinator_API.core.state's
module-level `duke_brain` attribute directly (`state.duke_brain = ...`)
rather than rebinding a name imported into this module's own namespace, so
every consumer that does `import coordinator_API.core.state as state` and
reads `state.duke_brain` at call time sees the live value - never a stale
None captured at its own import time.
"""
import asyncio
import uuid
from contextlib import asynccontextmanager

import psutil
from fastapi import FastAPI

from coordinator_API.core.config import logger
from coordinator_API.core.db import engine, Base, SessionLocal
from coordinator_API.core import state
from coordinator_API.models.orm import Agent, PersonaConfig
from coordinator_API.personas.specialists import SPECIALIST_PERSONAS
from coordinator_API.ml.duke_brain import DukeGenerativeBrain


async def generate_periodic_logs():
    """Generate system logs periodically. DEAD CODE - never scheduled."""
    while True:
        await asyncio.sleep(30)
        state.write_log(f"INFO: System health check - {len(state.active_connections)} active connections")

async def periodic_metrics_log():
    """Log system metrics periodically. DEAD CODE - never scheduled."""
    while True:
        await asyncio.sleep(60)
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            state.write_log(f"METRICS: CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% | Connections: {len(state.active_connections)}")
        except:
            pass

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup Phase
    logger.info("🚀 Starting AICP Coordinator Service v5.0.0...")

    # 1. Initialize Database Tables
    try:
        Base.metadata.create_all(bind=engine)
        logger.info("✅ Database migration completed")
    except Exception as e:
        logger.error(f"❌ Database migration failed: {e}")

    # 2. Initialize Duke Brain (Optimized Startup)
    # Mutate coordinator_API.core.state's module attribute directly (see
    # module docstring - duke_brain staleness fix) instead of a locally
    # scoped `global duke_brain`.
    try:
        logger.info("🧠 Waking up Duke Generative Brain...")
        state.duke_brain = DukeGenerativeBrain() # Loads local fine-tuned model weights
        logger.info(f"✅ Duke Brain: ONLINE (Local Mode, {state.duke_brain.mode})")
    except Exception as e:
        logger.error(f"⚠️ Brain init failed (continuing in lightweight mode): {e}")
        state.duke_brain = None

    # 3. Initialize/Heal Agents in Database
    db = SessionLocal()
    try:
        # Get list of existing agent names in the DB
        existing_agent_names = {a.name for a in db.query(Agent).all()}

        # Check against the SPECIALIST_PERSONAS configuration
        added_count = 0

        if SPECIALIST_PERSONAS:
            for persona_id, meta in SPECIALIST_PERSONAS.items():
                if persona_id not in existing_agent_names:
                    logger.info(f"➕ Adding missing agent: {persona_id}")
                    new_agent = Agent(
                        id=str(uuid.uuid4()),
                        name=persona_id,
                        success_rate=0.95,
                        reputation_multiplier=meta.get("reputation_multiplier", 1.0),
                        total_tasks_completed=0,
                        category=meta.get("category", "specialist"),
                        capabilities=meta.get("validation_keywords", ["Processing", "Analysis"])[:4],
                        status="idle"
                    )
                    db.add(new_agent)
                    added_count += 1

        if added_count > 0:
            db.commit()
            logger.info(f"✅ Database auto-healed: {added_count} new agents added")
        else:
            logger.info("✅ All agents verified in database")
    except Exception as e:
        logger.error(f"❌ Error initializing agents: {e}")
    finally:
        db.close()

    # 4. Seed Persona Configs (data-driven personas - admin-editable at runtime
    # via /admin/personas once seeded; never overwrites an existing row, so
    # admin edits made after the first startup are never clobbered on restart)
    db3 = SessionLocal()
    try:
        existing_persona_ids = {p.persona_id for p in db3.query(PersonaConfig).all()}
        seeded_count = 0

        if SPECIALIST_PERSONAS:
            for persona_id, meta in SPECIALIST_PERSONAS.items():
                if persona_id not in existing_persona_ids:
                    logger.info(f"➕ Seeding persona config: {persona_id}")
                    db3.add(PersonaConfig(
                        persona_id=persona_id,
                        name=meta.get("name", persona_id),
                        category=meta.get("category", "specialist"),
                        reputation_multiplier=meta.get("reputation_multiplier", 1.5),
                        min_response_tokens=meta.get("min_response_tokens", 200),
                        max_response_tokens=meta.get("max_response_tokens", 2000),
                        temperature=meta.get("temperature", 0.7),
                        requires_validation=meta.get("requires_validation", True),
                        system_prompt=meta.get("system_prompt", ""),
                        validation_keywords=meta.get("validation_keywords", []),
                        is_active=True,
                    ))
                    seeded_count += 1

        if seeded_count > 0:
            db3.commit()
            logger.info(f"✅ Seeded {seeded_count} persona config(s) into the database")
        else:
            logger.info("✅ All persona configs already present in database")
    except Exception as e:
        logger.error(f"❌ Error seeding persona configs: {e}")
        db3.rollback()
    finally:
        db3.close()

    logger.info("✅ OpenAI API configured")
    logger.info("✅ REAL Duke Learning Pipeline enabled (PyTorch Neural Network)")
    logger.info("✅ Trust & Capability Platform enabled")
    logger.info("✅ Server ready! Dashboard: http://localhost:3000/dashboard")

    # Hand over control to the application
    yield

    # Shutdown Phase
    logger.info("🛑 Shutting down server...")
