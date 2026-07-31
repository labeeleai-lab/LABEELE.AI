"""
routers/agents.py - GET /agents, POST /matching/find, GET /agents/{agent_id}/trust-score,
POST /admin/recalc-scores.
"""
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
import coordinator_API.core.state as state
from coordinator_API.models.orm import Agent, AgentScore
from coordinator_API.models.schemas import TaskSubmission
from coordinator_API.ml.matching import TrustScoringSystem

router = APIRouter()


@router.get("/agents")
async def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return agents


@router.post("/matching/find")
async def find_agent_for_task(task: TaskSubmission):
    """Find best agent for task"""
    try:
        description_lower = task.description.lower()

        # Keyword matching with scoring
        matches = []

        agent_keywords = {
            "security-expert": ["security", "vulnerability", "encrypt", "auth", "penetration", "firewall"],
            "ml-expert": ["ml", "model", "train", "neural", "ai", "prediction", "learning"],
            "systems-expert": ["cloud", "aws", "azure", "scale", "infrastructure", "architecture"],
            "backend-expert": ["api", "backend", "database", "endpoint", "server", "rest"],
            "devops-expert": ["deploy", "ci/cd", "kubernetes", "docker", "pipeline", "jenkins"],
            "vision-expert": ["image", "vision", "detect", "visual", "opencv", "recognition"]
        }

        for agent, keywords in agent_keywords.items():
            score = sum(1 for keyword in keywords if keyword in description_lower)
            if score > 0:
                matches.append({
                    "agent": agent,
                    "score": score,
                    "keywords_matched": score
                })

        # Sort by score
        matches.sort(key=lambda x: x["score"], reverse=True)

        if not matches:
            selected_agent = "ml-expert"  # Default
            match_score = 0.5
            reason = "No specific keywords matched, using default ML expert"
        else:
            best_match = matches[0]
            selected_agent = best_match["agent"]
            match_score = min(0.95, 0.6 + (best_match["score"] * 0.1))
            reason = f"Matched {best_match['keywords_matched']} keywords"

        state.write_log(f"🎯 Agent Matching: {selected_agent} (Score: {match_score:.2f})")

        return {
            "selected_agent": selected_agent,
            "match_score": match_score,
            "confidence": match_score,
            "reason": reason,
            "all_matches": matches[:3]  # Top 3
        }

    except Exception as e:
        state.write_log(f"ERROR: Agent matching failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/agents/{agent_id}/trust-score")
async def get_agent_trust(agent_id: str, db: Session = Depends(get_db)):
    """Deliverable 4.1: Trust Score Detail"""
    agent = db.query(Agent).filter((Agent.id == agent_id) | (Agent.name == agent_id)).first()
    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    score_val = TrustScoringSystem.calculate_score(agent, db)
    return {
        "agent": agent.name,
        "score": score_val,
        "tier": TrustScoringSystem.get_tier(score_val),
        "metrics": {
            "success_rate": agent.success_rate,
            "tasks": agent.total_tasks_completed,
            "reputation": agent.reputation_multiplier
        }
    }

@router.post("/admin/recalc-scores", dependencies=[Depends(require_admin_secret)])
async def recalculate_all_scores(db: Session = Depends(get_db)):
    """Maintenance: Update all scores based on recent training"""
    agents = db.query(Agent).all()
    count = 0
    for agent in agents:
        score_val = TrustScoringSystem.calculate_score(agent, db)
        tier = TrustScoringSystem.get_tier(score_val)
        existing = db.query(AgentScore).filter(AgentScore.agent_id == agent.id).first()
        if existing:
            existing.current_score = score_val
            existing.trust_tier = tier
            existing.last_updated = datetime.now(timezone.utc)
        else:
            db.add(AgentScore(agent_id=agent.id, current_score=score_val, trust_tier=tier))
        count += 1
    db.commit()
    return {"status": "success", "updated": count}
