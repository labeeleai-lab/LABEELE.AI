"""
routers/admin_training.py - POST /admin/training-data/upload,
POST /admin/retrain-agents, POST /admin/clear-cache, GET /training/stats,
GET /learning/status, GET /model/status, GET /admin/training/history.

Duplicate-route cleanup (approved plan): POST /admin/retrain-agents and
POST /admin/clear-cache were each defined twice in the original file. Only
the later, real/currently-winning definitions are kept here - the earlier
ones (a `retrain_all_agents` that never reset duke_pipeline.model before
retraining, and a `clear_cache` returning a differently-shaped body) were
always shadowed by these and never actually reachable.
"""
import json
import uuid
from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger, get_training_stats
from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.orm import Agent, ModelVersionBase, TrainingData
from coordinator_API.models.schemas import (
    TrainingUploadRequest, TrainingUploadResponse, ModelVersionSummary,
)
from coordinator_API.ml.pipeline import duke_pipeline

router = APIRouter()


@router.post(
    "/admin/training-data/upload",
    response_model=TrainingUploadResponse,
    tags=["Training"],
    dependencies=[Depends(require_admin_secret)],
)
async def upload_training_data(payload: TrainingUploadRequest, db: Session = Depends(get_db)):
    """Bulk-insert admin-curated instruction/output pairs as TrainingData rows."""
    existing_descriptions = set()
    for row in db.query(TrainingData.input_data).all():
        try:
            parsed = json.loads(row[0]) if isinstance(row[0], str) else row[0]
            desc_ = (parsed or {}).get("description", "")
            if desc_:
                existing_descriptions.add(desc_.strip().lower())
        except Exception:
            continue

    inserted = 0
    skipped_duplicate = 0
    skipped_invalid = 0
    seen_this_batch = set()

    for example in payload.examples:
        instruction = example.instruction.strip()
        output = example.output.strip()
        if not instruction or not output:
            skipped_invalid += 1
            continue

        key = instruction.lower()
        if key in existing_descriptions or key in seen_this_batch:
            skipped_duplicate += 1
            continue
        seen_this_batch.add(key)

        agent = example.persona_id or "duke-ml"
        db.add(
            TrainingData(
                id=str(uuid.uuid4()),
                task_id=f"upload-{uuid.uuid4().hex[:12]}",
                input_data=json.dumps({"description": instruction, "complexity": 5}),
                output_data=json.dumps({"result": output, "agent": agent}),
                success=True,
                agent_name=agent,
                persona_type=agent,
            )
        )
        inserted += 1

    db.commit()
    logger.info(f"✅ Bulk training-data upload: {inserted} inserted, {skipped_duplicate} duplicate, {skipped_invalid} invalid")
    return TrainingUploadResponse(
        inserted=inserted,
        skipped_duplicate=skipped_duplicate,
        skipped_invalid=skipped_invalid,
        total_submitted=len(payload.examples),
    )


@router.get("/learning/status")
async def get_learning_status(db: Session = Depends(get_db)):
    try:
        training_stats = get_training_stats()
        latest_model = db.query(ModelVersionBase).order_by(desc(ModelVersionBase.created_at)).first()
        agents = db.query(Agent).all()
        agent_names = [a.name for a in agents]
        memory_size = len(duke_pipeline.generator.response_database) if duke_pipeline.generator else 0

        return {
            "status": "trained" if (latest_model and latest_model.is_production) else "training",
            "last_training_time": latest_model.created_at.isoformat() if latest_model else datetime.now(timezone.utc).isoformat(),
            "total_samples_trained": training_stats.get("training_samples_available", 0),
            "memory_size": memory_size,
            "agent_personas": agent_names,
            "model_version": f"v{latest_model.version_number}" if latest_model else "v0.0.0",
            "validation_accuracy": latest_model.validation_accuracy if latest_model else 0.0,
            "estimated_cost_usd": training_stats.get("estimated_cost_usd", 0.0),
            "total_inferences": duke_pipeline.stats.get("total_inferences", 0),
            "recent_loss": duke_pipeline.stats.get("recent_loss", 0.0),
        }
    except Exception as e:
        logger.error(f"❌ Learning status error: {e}")
        return {"status": "error", "model_version": "v0.0.0"}

@router.get("/model/status")
async def get_model_status(db: Session = Depends(get_db)):
    ver = db.query(ModelVersionBase).order_by(desc(ModelVersionBase.created_at)).first()
    return {
        "status": "ready" if ver and ver.is_production else "training",
        "version": ver.version_number if ver else 0,
        "accuracy": ver.validation_accuracy if ver else 0.0,
        "training_samples": ver.training_samples if ver else 0
    }

@router.get("/training/stats", dependencies=[Depends(require_admin_secret)])
async def get_training_stats_api():
    return {"data": get_training_stats()}

@router.post("/admin/clear-cache", dependencies=[Depends(require_admin_secret)])
async def clear_training_cache(db: Session = Depends(get_db)):
    count = db.query(TrainingData).delete()
    db.commit()
    return {"status": "success", "deleted_entries": count}

@router.post("/admin/retrain-agents", dependencies=[Depends(require_admin_secret)])
async def retrain_all_agents(db: Session = Depends(get_db)):
    try:
        duke_pipeline.model = None
        await duke_pipeline.train_model(db)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get(
    "/admin/training/history",
    response_model=List[ModelVersionSummary],
    tags=["Dashboard"],
    dependencies=[Depends(require_admin_secret)],
)
async def get_training_history(db: Session = Depends(get_db)):
    """Every training run ever recorded, oldest first - powers the real accuracy/loss trend chart."""
    return db.query(ModelVersionBase).order_by(ModelVersionBase.version_number).all()
