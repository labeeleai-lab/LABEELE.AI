"""
models/schemas.py - all Pydantic request/response models used by the routers.

UserRegister was defined twice, identically, back to back in the original
file - deduplicated to one copy here per the approved cleanup plan.
"""
from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator

# ==================== AUTH / TASK (legacy JWT endpoints) ====================

class AuthRequest(BaseModel):
    username: str
    password: str

class TaskCreate(BaseModel):
    description: str
    task: Optional[str] = None
    complexity: Optional[int] = 5

class UserRegister(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

# ==================== CORE PYDANTIC MODELS ====================

class TaskRequest(BaseModel):
    description: str
    complexity: int = Field(..., ge=1, le=10)
    buyer_id: str

class DispatchRequest(BaseModel):
    prompt: str
    context_code: Optional[str] = ""
    current_persona: Optional[str] = "GENERALIST"
    complexity: Optional[int] = 7

class ToolRequest(BaseModel):
    code: str
    language: Optional[str] = "python"

class TrainConfigRequest(BaseModel):
    epochs: int = 10
    lr: float = 0.001
    optimizer: str = "Adam"

class TaskResponse(BaseModel):
    id: str
    description: str
    complexity: int
    status: str
    agent_name: str
    price_satoshis: Optional[int] = 0
    result: Optional[str] = None
    error_message: Optional[str] = None
    created_at: datetime
    completed_at: Optional[datetime] = None
    processing_time_seconds: Optional[float] = None

class TaskSubmission(BaseModel):
    description: str
    complexity: int = Field(..., ge=1, le=10)
    buyer_id: Optional[str] = None
    target_agent: Optional[str] = Field(None, alias="agent")
    model_config = {"populate_by_name": True}

    @field_validator("description")
    @classmethod
    def description_not_blank(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("description must not be empty")
        return v

class FeedbackSubmission(BaseModel):
    request_id: str
    rating: int  # 1 (Bad) to 5 (Good)
    comment: str = ""
    agent_name: str

class BuyerLoginRequest(BaseModel):
    buyer_id: str
    password: str

# ==================== DATA-DRIVEN PERSONAS (ADMIN) ====================

class PersonaConfigResponse(BaseModel):
    persona_id: str
    name: str
    category: str
    reputation_multiplier: float
    min_response_tokens: int
    max_response_tokens: int
    temperature: float
    requires_validation: bool
    system_prompt: str
    validation_keywords: List[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PersonaConfigCreate(BaseModel):
    persona_id: str = Field(..., min_length=1, max_length=64, pattern=r"^[a-z0-9\-]+$")
    name: str = Field(..., min_length=1, max_length=100)
    category: str = Field(default="specialist", max_length=50)
    reputation_multiplier: float = Field(default=1.5, ge=1.0, le=2.5)
    min_response_tokens: int = Field(default=200, ge=1, le=8000)
    max_response_tokens: int = Field(default=2000, ge=1, le=8000)
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    requires_validation: bool = True
    system_prompt: str = Field(..., min_length=1)
    validation_keywords: List[str] = Field(default_factory=list)

    @field_validator("max_response_tokens")
    @classmethod
    def _max_gte_min(cls, v, info):
        min_tokens = info.data.get("min_response_tokens")
        if min_tokens is not None and v < min_tokens:
            raise ValueError("max_response_tokens must be >= min_response_tokens")
        return v


class PersonaConfigUpdate(BaseModel):
    name: Optional[str] = Field(default=None, min_length=1, max_length=100)
    category: Optional[str] = Field(default=None, max_length=50)
    reputation_multiplier: Optional[float] = Field(default=None, ge=1.0, le=2.5)
    min_response_tokens: Optional[int] = Field(default=None, ge=1, le=8000)
    max_response_tokens: Optional[int] = Field(default=None, ge=1, le=8000)
    temperature: Optional[float] = Field(default=None, ge=0.0, le=2.0)
    requires_validation: Optional[bool] = None
    system_prompt: Optional[str] = Field(default=None, min_length=1)
    validation_keywords: Optional[List[str]] = None
    is_active: Optional[bool] = None

# ==================== BULK TRAINING DATA IMPORT (ADMIN) ====================

class TrainingExampleIn(BaseModel):
    instruction: str = Field(..., min_length=1, max_length=20000)
    output: str = Field(..., min_length=1, max_length=20000)
    persona_id: Optional[str] = Field(default=None, max_length=64)


class TrainingUploadRequest(BaseModel):
    examples: List[TrainingExampleIn] = Field(..., min_length=1, max_length=2000)


class TrainingUploadResponse(BaseModel):
    inserted: int
    skipped_duplicate: int
    skipped_invalid: int
    total_submitted: int

# ==================== KNOWLEDGE SYSTEM - PHASE 1 (ADMIN) ====================

class KnowledgeUploadRequest(BaseModel):
    persona_id: Optional[str] = Field(default=None, max_length=64)
    source_name: str = Field(..., min_length=1, max_length=255)
    content_type: str = Field(..., pattern=r"^(text|markdown|pdf)$")
    text: Optional[str] = None
    file_base64: Optional[str] = None

    @field_validator("file_base64")
    @classmethod
    def _require_matching_payload(cls, v, info):
        content_type = info.data.get("content_type")
        if content_type == "pdf" and not v:
            raise ValueError("file_base64 is required when content_type is 'pdf'")
        return v


class KnowledgeUploadResponse(BaseModel):
    source_id: str
    chunks_created: int
    total_characters: int


class KnowledgeSourceSummary(BaseModel):
    source_id: str
    source_name: str
    source_type: str
    persona_id: Optional[str]
    chunk_count: int
    created_at: datetime
    preview: str


class KnowledgeChunkDetail(BaseModel):
    id: str
    chunk_index: int
    content: str
    content_length: int

# ==================== ADMIN DASHBOARD (Phase 1) ====================

class ModelVersionSummary(BaseModel):
    version_number: int
    created_at: datetime
    training_samples: Optional[int]
    validation_accuracy: Optional[float]
    is_production: bool
    model_info: Optional[dict]

    model_config = {"from_attributes": True}


class SystemResourcesResponse(BaseModel):
    cpu_percent: float
    memory_used_gb: float
    memory_total_gb: float
    memory_percent: float
    disk_used_gb: float
    disk_total_gb: float
    disk_percent: float
    gpu_available: bool
    gpu_utilization: Optional[float] = None
    gpu_memory_used_gb: Optional[float] = None
    gpu_memory_total_gb: Optional[float] = None
    timestamp: datetime


class DashboardSummaryResponse(BaseModel):
    total_tasks_completed: int
    total_training_samples: int
    total_knowledge_chunks: int
    knowledge_chunks_by_agent: dict
    latest_model_version: int
    latest_validation_accuracy: Optional[float]
    total_agents: int
