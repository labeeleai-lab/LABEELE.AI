"""
ml/matching.py - TrustScoringSystem (agent trust score formula) and
MatchingEngine (semantic task-to-agent matching, built on duke_pipeline's
embedder).
"""
import logging

import numpy as np
from sqlalchemy.orm import Session

from coordinator_API.models.orm import Agent, AgentScore
from coordinator_API.ml.pipeline import duke_pipeline

logger = logging.getLogger("LabeleeDuke")


class TrustScoringSystem:
    WEIGHTS = {"success_rate": 0.4, "reputation": 0.3, "consistency": 0.2, "volume": 0.1}

    @staticmethod
    def calculate_score(agent: Agent, db: Session) -> float:
        success_metric = agent.success_rate * 100
        rep_metric = min(100, max(0, (agent.reputation_multiplier - 1.0) / 1.5 * 100))
        consistency_metric = 95.0
        volume_metric = min(100, np.log1p(agent.total_tasks_completed) * 10)

        raw_score = (
            (success_metric * TrustScoringSystem.WEIGHTS["success_rate"]) +
            (rep_metric * TrustScoringSystem.WEIGHTS["reputation"]) +
            (consistency_metric * TrustScoringSystem.WEIGHTS["consistency"]) +
            (volume_metric * TrustScoringSystem.WEIGHTS["volume"])
        )
        return round(raw_score, 2)

    @staticmethod
    def get_tier(score: float) -> str:
        if score >= 90: return "Critical"
        if score >= 80: return "High"
        if score >= 60: return "Standard"
        return "Low"

class MatchingEngine:
    def __init__(self, db: Session):
        self.db = db
        self.embedder = duke_pipeline.embedder
        self.agent_vectors = {}
        self._precompute_agent_vectors()

    def _precompute_agent_vectors(self):
        if not self.embedder: return
        agents = self.db.query(Agent).all()
        for agent in agents:
            caps = ", ".join(agent.capabilities) if agent.capabilities else "Generalist"
            profile_text = f"{agent.name} specialized in {agent.category}. Capabilities: {caps}"
            self.agent_vectors[agent.id] = self.embedder.embed(profile_text)
        logger.info(f"🧠 Semantic vectors computed for {len(self.agent_vectors)} agents")

    def find_best_agent(self, task_description: str, complexity: int) -> dict:
        if not self.embedder or not self.agent_vectors:
            return self._fallback_keyword_match(task_description)

        task_vector = self.embedder.embed(task_description)
        candidates = []
        for agent in self.db.query(Agent).all():
            if agent.id not in self.agent_vectors: continue

            agent_vector = self.agent_vectors[agent.id]
            dot_product = np.dot(task_vector, agent_vector)
            norm_a = np.linalg.norm(task_vector)
            norm_b = np.linalg.norm(agent_vector)
            similarity = dot_product / ((norm_a * norm_b) + 1e-8)

            score_rec = self.db.query(AgentScore).filter(AgentScore.agent_id == agent.id).first()
            trust = score_rec.current_score if score_rec else 50.0

            penalty = 0
            if agent.reputation_multiplier * 4 < complexity: penalty = 15

            normalized_trust = trust / 100.0
            final_score = (similarity * 0.7) + (normalized_trust * 0.3)
            final_score = (final_score * 100) - penalty
            candidates.append({"agent": agent, "score": final_score, "similarity": similarity, "trust": trust})

        candidates.sort(key=lambda x: x["score"], reverse=True)
        if not candidates: return None

        best_match = candidates[0]
        return {
            "agent": best_match["agent"],
            "match_score": round(best_match["score"], 2),
            "reason": f"Semantic Match: {int(best_match['similarity']*100)}% | Trust: {int(best_match['trust'])}"
        }

    def _fallback_keyword_match(self, text: str) -> dict:
        agent = self.db.query(Agent).first()
        return {"agent": agent, "match_score": 50.0, "reason": "Fallback Routing"}
