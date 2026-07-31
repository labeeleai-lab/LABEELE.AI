"""
routers/iac.py - GET /iac/stats, POST /iac/test (Iterative Adversarial
Critique system stats + manual test trigger).
"""
import json

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.orm import TrainingData
from coordinator_API.ml.validator import adversarial_validator

router = APIRouter()


@router.get("/iac/stats", tags=["IAC System"], dependencies=[Depends(require_admin_secret)])
async def get_iac_statistics(db: Session = Depends(get_db)):
    try:
        all_training = db.query(TrainingData).all()
        iac_validated = 0
        for entry in all_training:
            try:
                out = json.loads(entry.output_data) if isinstance(entry.output_data, str) else entry.output_data
                if out.get("iac_validated"): iac_validated += 1
            except: pass
        return {
            "status": "active",
            "total": len(all_training),
            "validated": iac_validated
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/iac/test", tags=["IAC System"])
async def test_iac_validation(request: dict):
    prompt = request.get("prompt", "")
    persona = request.get("persona", "security-expert")
    complexity = request.get("complexity", 7)

    result = await adversarial_validator.validate_and_refine(prompt, persona, complexity)
    return result
