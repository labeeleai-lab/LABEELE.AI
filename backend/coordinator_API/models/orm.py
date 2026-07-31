"""
models/orm.py - all SQLAlchemy ORM models + the Base.metadata.create_all() call.
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    Column, String, Integer, Float,
    DateTime, Boolean, JSON, Text, Index
)
from pgvector.sqlalchemy import Vector

from coordinator_API.core.db import Base, engine

# ==================== DATABASE MODELS ====================

class Agent(Base):
    __tablename__ = "agents"
    id = Column(String, primary_key=True, index=True)
    name = Column(String, unique=True, index=True)
    success_rate = Column(Float)
    reputation_multiplier = Column(Float)
    balance_satoshis = Column(Integer, default=0)
    total_tasks_completed = Column(Integer, default=0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    last_active = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    category = Column(String, default="specialist")
    capabilities = Column(JSON, default=lambda: ["Analysis", "Processing", "Learning"])
    status = Column(String, default="idle")

# --- TRUST & CAPABILITY MODELS (NEW) ---
class Capability(Base):
    __tablename__ = "capabilities"
    id = Column(String, primary_key=True)
    name = Column(String, unique=True, index=True)
    description = Column(Text)
    category = Column(String)  # e.g., "Security", "ML", "DevOps"
    complexity_weight = Column(Float, default=1.0)

class AgentCapability(Base):
    __tablename__ = "agent_capabilities"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    agent_id = Column(String, index=True)
    capability_id = Column(String, index=True)
    proficiency = Column(Float, default=0.5)  # 0.0 to 1.0
    verified = Column(Boolean, default=False)
    verification_date = Column(DateTime)

class AgentScore(Base):
    __tablename__ = "agent_scores"
    agent_id = Column(String, primary_key=True)
    current_score = Column(Float, default=50.0)  # 0-100
    trust_tier = Column(String, default="Standard")  # Critical, High, Standard, Low
    volatility = Column(Float, default=0.0)
    last_updated = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class MatchingDecision(Base):
    __tablename__ = "matching_decisions"
    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    task_id = Column(String, index=True)
    selected_agent_id = Column(String)
    match_score = Column(Float)
    strategy_used = Column(String)  # "BestMatch", "Fallback", "Random"
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
# ----------------------------------------

class Task(Base):
    __tablename__ = "tasks"
    id = Column(String, primary_key=True, index=True)
    description = Column(Text)
    summary = Column(String(200), nullable=True)
    complexity = Column(Integer)
    buyer_id = Column(String, index=True)
    agent_name = Column(String, index=True)
    price_satoshis = Column(Integer)
    status = Column(String, index=True)
    result = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    processing_time_seconds = Column(Float, nullable=True)
    persona_used = Column(String, nullable=True)

class PersonaMetrics(Base):
    __tablename__ = "persona_metrics"
    id = Column(String, primary_key=True, index=True)
    persona_type = Column(String, index=True)
    tasks_completed = Column(Integer, default=0)
    average_complexity = Column(Float, default=0.0)
    success_rate = Column(Float, default=0.0)
    keyword_accuracy = Column(Float, default=0.0)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, index=True)
    email = Column(String, unique=True, index=True)
    password_hash = Column(String)
    is_active = Column(Boolean, default=True) # Add this line

class TrainingData(Base):
    __tablename__ = "training_data"
    id = Column(String, primary_key=True, index=True)
    task_id = Column(String, index=True)
    input_data = Column(JSON)
    output_data = Column(JSON)
    success = Column(Boolean, nullable=False)
    agent_name = Column(String)
    persona_type = Column(String, index=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

class ModelVersionBase(Base):
    __tablename__ = "model_versions"
    id = Column(String, primary_key=True, index=True)
    version_number = Column(Integer, nullable=False)
    model_name = Column(String, default="duke-ml")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    training_samples = Column(Integer)
    validation_accuracy = Column(Float)
    validation_f1 = Column(Float)
    is_production = Column(Boolean, default=False)
    model_info = Column(JSON)

class PersonaConfig(Base):
    """
    Data-driven persona definitions. Seeded from SPECIALIST_PERSONAS on first
    startup (see lifespan()), then admin-editable at runtime via
    GET/POST/PUT /admin/personas - no code change or redeploy needed to
    change a persona's behavior or add a new one. get_safe_persona() checks
    this table before falling back to the hardcoded SPECIALIST_PERSONAS
    dict, which is intentionally never removed as a safety net.
    """
    __tablename__ = "persona_configs"
    persona_id = Column(String, primary_key=True, index=True)
    name = Column(String, nullable=False)
    category = Column(String, nullable=False, default="specialist")
    reputation_multiplier = Column(Float, nullable=False, default=1.5)
    min_response_tokens = Column(Integer, nullable=False, default=200)
    max_response_tokens = Column(Integer, nullable=False, default=2000)
    temperature = Column(Float, nullable=False, default=0.7)
    requires_validation = Column(Boolean, nullable=False, default=True)
    system_prompt = Column(Text, nullable=False)
    validation_keywords = Column(JSON, nullable=False, default=list)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

KNOWLEDGE_EMBED_DIM = 384  # tied to sentence-transformers/all-MiniLM-L6-v2 - see backend/knowledge.py

class KnowledgeChunk(Base):
    """
    Persistent per-agent (or DUKE-global, when persona_id is NULL) knowledge
    used for retrieval-augmented generation. A "document" as seen in the admin
    UI is just every row sharing one source_id - there's no separate
    documents table. Chunked/embedded/stored via backend/knowledge.py,
    retrieved in /tasks/submit via retrieve_relevant_chunks().
    """
    __tablename__ = "knowledge_chunks"
    id = Column(String, primary_key=True, index=True)
    source_id = Column(String, nullable=False, index=True)
    source_name = Column(String, nullable=False)
    source_type = Column(String, nullable=False)  # "text" | "markdown" | "pdf"
    persona_id = Column(String, nullable=True, index=True)  # NULL = DUKE-global
    chunk_index = Column(Integer, nullable=False)
    content = Column(Text, nullable=False)
    content_length = Column(Integer, nullable=False)
    embedding = Column(Vector(KNOWLEDGE_EMBED_DIM), nullable=False)
    created_by = Column(String, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    __table_args__ = (
        Index(
            "ix_knowledge_chunks_embedding",
            "embedding",
            postgresql_using="hnsw",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

Base.metadata.create_all(bind=engine)
