"""
routers/admin_dashboard.py - GET /admin/system/resources,
GET /admin/dashboard/summary.

Real data only - see backend/knowledge.py and the security/training-pipeline
fixes earlier in this app's history for the reasoning. Anything without a
real backend source (GPU on this deployment, precision/recall/F1, per-agent
online/synchronizing states) is intentionally left out rather than faked -
the frontend surfaces those gaps explicitly instead of hiding or inventing them.
"""
from datetime import datetime, timezone

import torch
from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.orm import Agent, TrainingData, KnowledgeChunk, ModelVersionBase
from coordinator_API.models.schemas import SystemResourcesResponse, DashboardSummaryResponse

router = APIRouter()


@router.get(
    "/admin/system/resources",
    response_model=SystemResourcesResponse,
    tags=["Dashboard"],
    dependencies=[Depends(require_admin_secret)],
)
async def get_system_resources_admin():
    """
    Real psutil CPU/memory/disk. GPU fields stay null with gpu_available=false
    unless a real GPU is actually detected - never a hardcoded fallback number
    (this replaces an earlier, unused endpoint that did exactly that).
    """
    import psutil

    cpu_percent = psutil.cpu_percent(interval=0.1)
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")

    gpu_available = False
    gpu_utilization = None
    gpu_memory_used_gb = None
    gpu_memory_total_gb = None
    if torch.cuda.is_available():
        try:
            import GPUtil
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]
                gpu_available = True
                gpu_utilization = gpu.load * 100
                gpu_memory_used_gb = gpu.memoryUsed / 1024
                gpu_memory_total_gb = gpu.memoryTotal / 1024
        except Exception:
            pass

    return SystemResourcesResponse(
        cpu_percent=cpu_percent,
        memory_used_gb=mem.used / (1024 ** 3),
        memory_total_gb=mem.total / (1024 ** 3),
        memory_percent=mem.percent,
        disk_used_gb=disk.used / (1024 ** 3),
        disk_total_gb=disk.total / (1024 ** 3),
        disk_percent=disk.percent,
        gpu_available=gpu_available,
        gpu_utilization=gpu_utilization,
        gpu_memory_used_gb=gpu_memory_used_gb,
        gpu_memory_total_gb=gpu_memory_total_gb,
        timestamp=datetime.now(timezone.utc),
    )


@router.get(
    "/admin/dashboard/summary",
    response_model=DashboardSummaryResponse,
    tags=["Dashboard"],
    dependencies=[Depends(require_admin_secret)],
)
async def get_dashboard_summary(db: Session = Depends(get_db)):
    """One aggregate call for the dashboard's at-a-glance row - every field computed
    directly from real tables, replacing reliance on the permanently-fallback
    get_training_stats() (its dependency, openai_training_logger, doesn't exist)."""
    agents = db.query(Agent).all()
    total_tasks = sum(a.total_tasks_completed or 0 for a in agents)
    total_training_samples = db.query(TrainingData).count()

    knowledge_persona_ids = db.query(KnowledgeChunk.persona_id).all()
    knowledge_by_agent: dict = {}
    for (pid,) in knowledge_persona_ids:
        key = pid or "duke-global"
        knowledge_by_agent[key] = knowledge_by_agent.get(key, 0) + 1

    latest_model = db.query(ModelVersionBase).order_by(desc(ModelVersionBase.created_at)).first()

    return DashboardSummaryResponse(
        total_tasks_completed=total_tasks,
        total_training_samples=total_training_samples,
        total_knowledge_chunks=len(knowledge_persona_ids),
        knowledge_chunks_by_agent=knowledge_by_agent,
        latest_model_version=latest_model.version_number if latest_model else 0,
        latest_validation_accuracy=latest_model.validation_accuracy if latest_model else None,
        total_agents=len(agents),
    )
