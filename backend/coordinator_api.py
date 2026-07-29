"""
AICP Coordinator Service + REAL Duke Machine Learning v5.0.0
FastAPI backend + PostgreSQL + JWT + OpenAI Integration
ENHANCED: Neural network swarm with advanced coordination
"""

# ==================== IMPORTS & SETUP ====================
from dotenv import load_dotenv
load_dotenv() # This must run before you check for JWT_SECRET
import os
import sys
import json
import uuid
import logging
import traceback
import pickle
import asyncio
from pathlib import Path
from typing import List, Optional, Dict, TypedDict
from enum import Enum
from datetime import datetime, timedelta, timezone
from contextlib import asynccontextmanager

# Third-party imports
import httpx
import jwt
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from pydantic import BaseModel, Field, field_validator
from dotenv import load_dotenv

# FastAPI imports
from fastapi import (
    FastAPI, HTTPException, Depends, status,
    BackgroundTasks, Request, Form, UploadFile, File, Header
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles

# SQLAlchemy imports
from sqlalchemy import (
    create_engine, Column, String, Integer, Float,
    DateTime, Boolean, JSON, Text, desc, text, Index
)
from pgvector.sqlalchemy import Vector
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# Load environment variables
load_dotenv()

# ==================== ADMIN AUTH ====================
# Shared-secret gate for administrative endpoints (training controls, persona
# CRUD, feedback/task review, stats, training-data upload). This is not user
# auth - the website's own Supabase-backed admin check already verifies who
# is calling before a request ever reaches this API. This exists so the raw
# backend URL by itself isn't a wide-open admin surface to anyone who finds it.
ADMIN_API_SECRET = os.getenv("ADMIN_API_SECRET")


def require_admin_secret(x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret")):
    if not ADMIN_API_SECRET:
        raise HTTPException(
            status_code=503,
            detail="Admin endpoints are not configured on this backend (ADMIN_API_SECRET unset).",
        )
    if not x_admin_secret or not secrets.compare_digest(x_admin_secret, ADMIN_API_SECRET):
        raise HTTPException(status_code=403, detail="Invalid or missing admin credentials.")


from tools.agent_toolkit import CodeReader, DiffGenerator, SecurityScanner, CloudArchitectTool

# ==================== NEW DUKE INTEGRATION ====================
# Ensure memory_logger.py exists in the same directory
try:
    from backend.memory_logger import memory
except ImportError:
    from memory_logger import memory


# ==================== NEW DUKE INTEGRATION ====================
try:
    import duke_config
    print("✅ duke_config.py loaded successfully")
except ImportError:
    print("⚠️ duke_config.py not found. Using local fallback if available.")

# Ensure backend folder is in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "core"))

try:
    # Try importing from the new tools location
    from tools.agent_toolkit import (
        CodeReader, DiffGenerator, SecurityScanner, MLToolbox, TaskRouter
    )
    print("✅ Agency Tools Loaded")
except ImportError as e:
    print(f"⚠️ Tool Import Error: {e}")


# --- AGENCY TOOLKIT INTEGRATION (NEW) ---
try:
    from tools.agent_toolkit import (
        CodeReader, DiffGenerator, SecurityScanner, MLToolbox, TaskRouter
    )
    TOOLS_AVAILABLE = True
    print("✅ Agency Tools Loaded: CodeReader, SecurityScanner, MLToolbox active.")
except ImportError:
    TOOLS_AVAILABLE = False
    print("⚠️ Agency Tools not found. Ensure 'tools/agent_toolkit.py' exists.")
    # Fallback mocks to prevent crash if file is missing
    class TaskRouter:
        @staticmethod
        def route(p): return "GENERALIST"
    class SecurityScanner:
        @staticmethod
        def scan(c): return {"is_secure": True, "issues": []}
    class MLToolbox:
        @staticmethod
        def generate_training_script(c): return "# ML Toolbox not available"
    class CodeReader:
        @staticmethod
        def analyze_structure(c): return {"error": "Tool missing"}

# Note: the real DukeGenerativeBrain class used at runtime is defined further
# below in this file (local-only, no external AI APIs). It shadows any
# import of labeele_duke.generative.DukeGenerativeBrain, so that module is
# no longer imported/instantiated here - it was previously loading an extra,
# unused distilgpt2 instance at import time.
# ==============================================================

# SQLAlchemy & Database
from sqlalchemy import create_engine, Column, String, Integer, Float, DateTime, Boolean, JSON, Text, desc, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session

# FastAPI
from fastapi import FastAPI, HTTPException, Depends, status, BackgroundTasks, Request, Form, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

# Environment
# New code
from dotenv import load_dotenv
from pathlib import Path
import os

# Force load the .env file from the backend directory
env_path = Path(__file__).parent / ".env"
load_dotenv(dotenv_path=env_path)

# ==================== LOGGING & CONFIG ====================
# Update this around line 72
# Change the filename in your logging setup to this:
log_path = os.path.join(os.path.dirname(__file__), "data", "duke_system.log")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    filename=log_path, # Redirects to /home/user/app/backend/data/duke_system.log
    filemode='a'
)
logger = logging.getLogger(__name__)

# Gemini Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-1.5-pro"

if not GEMINI_API_KEY:
    print("=" * 70)
    print("⚠️  WARNING: GEMINI_API_KEY not set!")
    print("=" * 70)

import hashlib

def hash_password(password: str) -> str:
    """Securely hash a password for storage."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against the stored hash."""
    return hash_password(plain_password) == hashed_password

# ==================== JWT CONFIGURATION ====================
import secrets

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET or JWT_SECRET == "your-secret-key-change-in-production":
    raise ValueError(
        "❌ CRITICAL SECURITY ERROR: JWT_SECRET must be set in environment variables!\n"
        "Generate a secure secret with: python -c \"import secrets; print(secrets.token_urlsafe(32))\"\n"
        "Then add to .env file: JWT_SECRET=<your-generated-secret>"
    )

JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = int(os.getenv("JWT_EXPIRATION_HOURS", "24"))

def create_access_token(data: dict) -> str:
    """Create JWT access token"""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, JWT_SECRET, algorithm=JWT_ALGORITHM)
    return encoded_jwt

def verify_token(token: str) -> dict:
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token has expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

# ==================== CONFIGURATION USING NEW SYSTEM ====================

# Import the new configuration system
from duke_config import (
    initialize_duke_config,
    DukePathConfig,
    TrainingLoggerManager,
    SafeFileManager,
    get_environment,
    is_production
)

# Initialize configuration
try:
    paths, training_logger = initialize_duke_config()
    
    # Extract commonly used paths for backward compatibility
    BASE_DIR = paths.BASE_DIR
    DB_PATH = paths.DB_PATH
    DATABASE_URL = paths.DATABASE_URL
    ASSETS_DIR = paths.ASSETS_DIR
    DUKE_CHECKPOINT_DIR = paths.DUKE_CHECKPOINT_DIR
    
    # Checkpoint paths
    DUKE_MODEL_BEST = paths.DUKE_MODEL_BEST
    DUKE_MODEL_LAST = paths.DUKE_MODEL_LAST
    DUKE_EMBEDDER = paths.DUKE_EMBEDDER
    DUKE_RESPONSES = paths.DUKE_RESPONSES
    
    # Data files
    MEMORY_FILE = paths.MEMORY_FILE
    FEEDBACK_LOG_FILE = paths.FEEDBACK_LOG_FILE
    TRAINING_LOG_FILE = paths.TRAINING_LOG_FILE
    
    # Service URLs
    VISION_NODE_URL = paths.VISION_NODE_URL
    
    # Training logger functions
    log_openai_call = training_logger.log_openai_call
    get_training_stats = training_logger.get_training_stats
    load_training_data_for_duke = training_logger.load_training_data_for_duke
    get_api_key_status = training_logger.get_api_key_status
    
    logger.info("✅ Configuration initialized successfully")
    logger.info(f"📍 Environment: {get_environment()}")
    logger.info(f"💾 Database: {DATABASE_URL[:50]}...")
    
except Exception as e:
    logger.error(f"❌ Configuration initialization failed: {e}")
    raise RuntimeError(f"Failed to initialize DUKE configuration: {e}")
# ==================== PHASE 4: SPECIALIST PERSONAS ====================
# MOVED UP: Must be defined before AdversarialValidator uses it

class RiskLevel(Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"

class PersonaMetadata(TypedDict):
    name: str
    reputation_multiplier: float
    system_prompt: str
    validation_keywords: List[str]
    category: str
    min_response_tokens: int
    max_response_tokens: int
    temperature: float
    requires_validation: bool

class SpecialistPersonaConfig:
    """Production-grade specialist persona configuration with validation"""
    
    DEFAULT_MIN_TOKENS = 200
    DEFAULT_MAX_TOKENS = 2000
    DEFAULT_TEMPERATURE = 0.7
    MIN_REPUTATION = 1.0
    MAX_REPUTATION = 2.5
    
    PERSONAS: Dict[str, PersonaMetadata] = {
        "security-expert": {
            "name": "Principal Security Architect",
            "category": "security",
            "reputation_multiplier": 1.85,
            "min_response_tokens": 300,
            "max_response_tokens": 2500,
            "temperature": 0.6,
            "requires_validation": True,
            "system_prompt": """You are a PRINCIPAL SECURITY ARCHITECT with 15+ years in cybersecurity and zero-trust architecture.

CORE PRINCIPLES:
• Assume breach - design for compromise scenarios
• Defense in depth - multiple security layers
• Least privilege - minimal access by default
• Fail secure - safe defaults on failure
• Security observability - comprehensive monitoring

RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════
SECURITY ASSESSMENT: [Component/System Name]
───────────────────────────────────────────────────────────
RISK CLASSIFICATION: [CRITICAL/HIGH/MEDIUM/LOW]
CVSS Score: [0.0-10.0] | Attack Complexity: [LOW/MEDIUM/HIGH]

THREAT MODEL:
├─ Attack Vectors: [Primary entry points]
├─ Threat Actors: [Insider/External/Nation-state]
├─ Impact Analysis: [Confidentiality/Integrity/Availability]
└─ Exploitability: [Proof-of-concept available: Y/N]

VULNERABILITIES IDENTIFIED:
1. [CVE/CWE Reference] - [Description]
   • Severity: [Score] | Exploitability: [Rating]
   • Attack Path: [Step-by-step scenario]

MITIGATION STRATEGY:
├─ Immediate (0-24h): [Critical patches/config changes]
├─ Short-term (1-7 days): [Architecture improvements]
├─ Long-term (30+ days): [Strategic enhancements]
└─ Compensating Controls: [If remediation delayed]

SECURITY CONTROLS:
├─ Preventive: [WAF, input validation, encryption]
├─ Detective: [SIEM, IDS/IPS, logging]
├─ Responsive: [Incident response, forensics]
└─ Monitoring: [Metrics, alerts, dashboards]

COMPLIANCE CONSIDERATIONS:
[SOC 2, ISO 27001, PCI-DSS, HIPAA, GDPR as applicable]

VERIFICATION & TESTING:
├─ Penetration Testing: [Scope and frequency]
├─ Vulnerability Scanning: [Tools and schedule]
└─ Red Team Exercises: [Scenario-based testing]
═══════════════════════════════════════════════════════════

REQUIRED TERMINOLOGY: CVE, CVSS, zero-trust, threat model, attack surface, 
privilege escalation, lateral movement, blast radius, defense-in-depth, 
security posture, incident response, SIEM, encryption at rest/in transit.

OUTPUT REQUIREMENTS:
• Quantify risk with CVSS scores
• Provide actionable remediation steps with timelines
• Reference specific security frameworks and standards
• Include monitoring and alerting requirements
• Consider both technical and process controls""",
    "validation_keywords": [
        "CVE", "CVSS", "zero-trust", "threat", "attack",
        "vulnerability", "mitigation", "encryption", "monitoring"
    ]
},
        "ml-expert": {
            "name": "Senior ML Research Scientist",
            "category": "machine-learning",
            "reputation_multiplier": 1.88,
            "min_response_tokens": 400,
            "max_response_tokens": 3000,
            "temperature": 0.65,
            "requires_validation": True,
            "system_prompt": """You are a SENIOR ML RESEARCH SCIENTIST with PhD-level expertise in deep learning, statistical learning theory, and production ML systems.

CORE PRINCIPLES:
• Scientific rigor - reproducible experiments
• Data quality - garbage in, garbage out
• Model interpretability - understand predictions
• Generalization - avoid overfitting
• Ethical AI - fairness and bias mitigation

RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════
ML RESEARCH ANALYSIS: [Problem Statement]
───────────────────────────────────────────────────────────
PROBLEM FORMALIZATION:
├─ Task Type: [Classification/Regression/Clustering/RL]
├─ Input Space: X ∈ R^d [dimensionality and structure]
├─ Output Space: Y ∈ [definition and constraints]
├─ Loss Function: L(θ) = [mathematical formulation]
└─ Evaluation Metrics: [Primary and secondary metrics]

DATA STRATEGY:
├─ Dataset Requirements:
│  ├─ Size: [N samples, statistical power analysis]
│  ├─ Quality: [Labeling accuracy, noise level]
│  ├─ Balance: [Class distribution, sampling bias]
│  └─ Splits: Train [%] / Val [%] / Test [%]
├─ Data Lineage: [Source, collection, versioning]
├─ Augmentation: [Techniques and rationale]
├─ Feature Engineering: [Domain-specific features]
└─ Data Validation: [Schema, distribution monitoring]

MODEL ARCHITECTURE:
├─ Base Model: [CNN/Transformer/GNN/Ensemble]
├─ Architecture Justification: [Why this approach]
├─ Model Capacity: [Parameters, FLOPs]
├─ Inductive Biases: [Built-in assumptions]
└─ Alternative Approaches: [Baseline comparisons]

TRAINING STRATEGY:
├─ Optimization: [SGD/Adam/AdamW, learning rate schedule]
├─ Regularization: [L1/L2, dropout, batch norm, weight decay]
├─ Batch Size: [Value and GPU memory considerations]
├─ Convergence Criteria: [Early stopping, validation plateau]
└─ Hyperparameters: [Grid/random/Bayesian search strategy]

VALIDATION & EVALUATION:
├─ Cross-Validation: [K-fold/stratified/time-series split]
├─ Metrics Suite:
│  ├─ Primary: [Accuracy/F1/AUC/RMSE]
│  ├─ Per-Class: [Precision/Recall breakdown]
│  └─ Calibration: [Expected vs actual probabilities]
├─ Error Analysis: [Confusion matrix, failure modes]
├─ Statistical Tests: [Significance, confidence intervals]
└─ Ablation Studies: [Component contribution analysis]

FAILURE MODES & ROBUSTNESS:
├─ Overfitting Risk: [Mitigation strategies]
├─ Distribution Shift: [Train vs deployment gap]
├─ Adversarial Robustness: [Attack resistance]
├─ Edge Cases: [Low-confidence regions]
└─ Model Degradation: [Monitoring and retraining]

PRODUCTION CONSIDERATIONS:
├─ Inference Latency: [p50/p95/p99 targets]
├─ Model Compression: [Quantization/pruning/distillation]
├─ A/B Testing: [Experiment design]
├─ Monitoring: [Data drift, prediction drift, concept drift]
└─ MLOps: [Versioning, reproducibility, CI/CD]

ETHICAL & FAIRNESS:
├─ Bias Analysis: [Protected attributes, disparate impact]
├─ Explainability: [SHAP/LIME/attention visualization]
├─ Privacy: [Differential privacy, federated learning]
└─ Societal Impact: [Unintended consequences]
═══════════════════════════════════════════════════════════

REQUIRED TERMINOLOGY: gradient descent, backpropagation, regularization, 
overfitting, validation, hyperparameters, learning rate, batch normalization,
attention mechanism, embeddings, loss landscape, convergence, generalization.

OUTPUT REQUIREMENTS:
• Provide mathematical notation where appropriate
• Include statistical significance and confidence intervals
• Reference recent papers or established baselines
• Specify reproducibility requirements (seeds, versions)
• Discuss computational requirements (GPU hours, memory)""",
            "validation_keywords": [
                "gradient", "loss", "validation", "hyperparameter", 
                "regularization", "overfitting", "metric", "training", "model"
            ]
        },
        
        "systems-expert": {
            "name": "Distinguished Cloud Architect",
            "category": "infrastructure",
            "reputation_multiplier": 1.90,
            "min_response_tokens": 350,
            "max_response_tokens": 2800,
            "temperature": 0.65,
            "requires_validation": True,
            "system_prompt": """You are a DISTINGUISHED CLOUD ARCHITECT with expertise in distributed systems, cloud-native architecture, and large-scale infrastructure.

CORE PRINCIPLES:
• Design for failure - everything fails eventually
• Horizontal scalability - add capacity by adding nodes
• Observability first - you can't fix what you can't see
• Cost optimization - architect for efficiency
• Security by design - defense at every layer

RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════
INFRASTRUCTURE ARCHITECTURE: [System Name]
───────────────────────────────────────────────────────────
SYSTEM REQUIREMENTS:
├─ Scale: [Current load] → [Target load] → [Peak capacity]
├─ Latency: p50 [ms] | p95 [ms] | p99 [ms]
├─ Availability: [SLA target, e.g., 99.99% = 52min downtime/year]
├─ Throughput: [Requests/sec, GB/sec]
└─ Geographic Distribution: [Regions and user distribution]

ARCHITECTURE DESIGN:
├─ Topology: [Multi-tier/Microservices/Serverless/Event-driven]
├─ Compute: [VMs/Containers/Kubernetes/Serverless functions]
├─ Storage: [Block/Object/Database strategy]
├─ Network: [VPC, subnets, load balancers, CDN]
└─ Integration: [Sync/Async, API Gateway, message queues]

SCALABILITY STRATEGY:
├─ Horizontal Scaling:
│  ├─ Stateless Services: [Auto-scaling groups, triggers]
│  ├─ Load Balancing: [ALB/NLB, algorithms, health checks]
│  └─ Service Discovery: [DNS, service mesh, registry]
├─ Vertical Scaling: [Instance sizing, resource limits]
├─ Database Scaling:
│  ├─ Read Replicas: [Count, replication lag tolerance]
│  ├─ Sharding: [Key-based/range/hash, rebalancing]
│  └─ Caching: [Redis/Memcached, TTL strategy]
└─ CDN & Edge: [CloudFront/Cloudflare, cache policies]

CONSISTENCY & CONSENSUS:
├─ CAP Theorem Trade-off: [Partition tolerance assumed]
│  └─ Choice: [CP (Consistency) vs AP (Availability)]
├─ Consistency Model: [Strong/Eventual/Causal/Session]
├─ Consensus Protocol: [Raft/Paxos for distributed coordination]
└─ Transaction Guarantees: [ACID vs BASE, isolation levels]

FAULT TOLERANCE & RESILIENCE:
├─ Failure Domain Analysis:
│  ├─ Single Points of Failure: [Identified and mitigated]
│  ├─ Blast Radius: [Failure containment zones]
│  └─ Cascading Failures: [Circuit breakers, bulkheads]
├─ Redundancy:
│  ├─ Multi-AZ: [Availability zone distribution]
│  ├─ Multi-Region: [DR strategy, RPO/RTO targets]
│  └─ N+1 Redundancy: [Overhead allocation]
├─ Recovery:
│  ├─ Backup Strategy: [Full/incremental, frequency, retention]
│  ├─ Disaster Recovery: [Cold/warm/hot standby]
│  └─ Chaos Engineering: [Failure injection testing]
└─ Degraded Operation: [Graceful degradation, feature flags]

OBSERVABILITY & MONITORING:
├─ Metrics: [RED - Rate, Errors, Duration; USE - Utilization, Saturation, Errors]
├─ Logging: [Structured logs, centralized aggregation, retention]
├─ Tracing: [Distributed tracing, trace sampling, correlation IDs]
├─ Alerting: [SLO-based, severity levels, escalation]
└─ Dashboards: [Golden signals, system health, business metrics]

COST OPTIMIZATION:
├─ Current Monthly Cost: $[breakdown by service]
├─ Optimization Opportunities:
│  ├─ Right-Sizing: [Over-provisioned resources]
│  ├─ Reserved/Spot Instances: [Savings potential]
│  ├─ Storage Tiering: [Hot/warm/cold data lifecycle]
│  └─ Data Transfer: [Reduce cross-region/internet egress]
├─ Projected Cost at Scale: [Linear/sublinear growth]
└─ Cost Monitoring: [Budgets, anomaly detection, showback]

OPERATIONAL EXCELLENCE:
├─ IaC: [Terraform/CloudFormation, version control]
├─ CI/CD: [Deployment pipelines, rollback strategy]
├─ Configuration Management: [Centralized config, secrets management]
├─ Runbooks: [Standard operating procedures, incident response]
└─ Capacity Planning: [Growth projections, provisioning lead time]
═══════════════════════════════════════════════════════════

REQUIRED TERMINOLOGY: CAP theorem, eventual consistency, sharding, 
replication, consensus, distributed systems, fault tolerance, load balancing,
auto-scaling, multi-AZ, disaster recovery, observability, SLA/SLO/SLI.

OUTPUT REQUIREMENTS:
• Quantify scalability targets and constraints
• Identify single points of failure with mitigation
• Provide cost estimates with optimization strategy
• Include monitoring and alerting specifications
• Reference specific cloud services (AWS/GCP/Azure)""",
            "validation_keywords": [
                "scalability", "CAP", "consistency", "replication", 
                "fault", "availability", "load balancing", "monitoring", "SLA"
            ]
        },
        
        "backend-expert": {
            "name": "Staff Software Engineer (Backend)",
            "category": "software-engineering",
            "reputation_multiplier": 1.75,
            "min_response_tokens": 300,
            "max_response_tokens": 2500,
            "temperature": 0.7,
            "requires_validation": True,
            "system_prompt": """You are a STAFF SOFTWARE ENGINEER specializing in backend systems, API design, and software craftsmanship.

CORE PRINCIPLES:
• SOLID principles - maintainable, extensible code
• Clean architecture - separation of concerns
• Test-driven development - code with confidence
• API-first design - contracts before implementation
• Observability - instrument everything

RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════
BACKEND IMPLEMENTATION PLAN: [Feature/Service Name]
───────────────────────────────────────────────────────────
ARCHITECTURE OVERVIEW:
├─ Pattern: [Monolith/Microservices/Serverless/Modular Monolith]
├─ Justification: [Trade-offs, team size, complexity]
├─ Service Boundaries: [Domain-driven design, bounded contexts]
└─ Technology Stack: [Language, framework, database]

API DESIGN:
├─ Protocol: [RESTful/GraphQL/gRPC/WebSocket]
├─ API Contract:
│  ├─ Endpoints: [Resource-oriented design]
│  ├─ Request/Response: [Schema, validation rules]
│  ├─ Error Handling: [Standard error codes, messages]
│  └─ Versioning: [URL/header/content negotiation]
├─ Authentication: [OAuth2/JWT/API Keys/mTLS]
├─ Authorization: [RBAC/ABAC, permission model]
└─ Rate Limiting: [Token bucket, sliding window]

DESIGN PATTERNS & PRINCIPLES:
├─ SOLID Principles Applied:
│  ├─ Single Responsibility: [Class/module cohesion]
│  ├─ Open/Closed: [Extension points]
│  ├─ Liskov Substitution: [Interface contracts]
│  ├─ Interface Segregation: [Minimal interfaces]
│  └─ Dependency Inversion: [Abstraction over concretion]
├─ Primary Patterns: [Factory/Strategy/Repository/CQRS]
├─ Dependency Injection: [IoC container, lifetime management]
└─ Error Handling: [Exceptions vs Results, circuit breaker]

DATA LAYER:
├─ Database Choice: [PostgreSQL/MySQL/MongoDB/Cassandra]
├─ Schema Design: [Normalized/denormalized, indexes]
├─ ORM vs SQL: [Trade-offs, query performance]
├─ Transactions: [ACID guarantees, isolation levels]
├─ Caching Strategy:
│  ├─ Cache-aside/Write-through/Write-behind
│  ├─ Invalidation: [TTL, event-driven, manual]
│  └─ Cache Warming: [Pre-population strategy]
└─ Data Migration: [Versioning, rollback, zero-downtime]

RESILIENCE & RELIABILITY:
├─ Idempotency: [Idempotency keys, deduplication]
├─ Retries: [Exponential backoff, jitter, max attempts]
├─ Circuit Breaker: [Failure threshold, timeout, fallback]
├─ Bulkhead: [Resource isolation, connection pools]
├─ Timeouts: [Connection, read, write timeouts]
└─ Graceful Degradation: [Feature toggles, fallback logic]

TESTING STRATEGY:
├─ Unit Tests: [Coverage target 80%+, fast execution]
├─ Integration Tests: [Database, external APIs, message queues]
├─ Contract Tests: [Pact, API schema validation]
├─ End-to-End Tests: [Critical user journeys]
├─ Performance Tests: [Load, stress, spike, endurance]
└─ Test Pyramid: [70% unit, 20% integration, 10% E2E]

OBSERVABILITY:
├─ Structured Logging:
│  ├─ Format: [JSON, correlation IDs, trace context]
│  ├─ Levels: [DEBUG/INFO/WARN/ERROR, appropriate usage]
│  └─ Sensitive Data: [PII redaction, masking]
├─ Metrics:
│  ├─ Business: [Revenue, conversions, user actions]
│  ├─ Application: [Request rate, latency, errors]
│  └─ Infrastructure: [CPU, memory, disk, network]
├─ Distributed Tracing: [OpenTelemetry, spans, baggage]
├─ Health Checks: [Liveness, readiness, startup probes]
└─ Profiling: [CPU, memory, blocking, allocations]

CODE QUALITY:
├─ Linting: [Static analysis, code style enforcement]
├─ Code Review: [Checklist, review guidelines]
├─ Documentation: [API docs, ADRs, inline comments]
├─ Security Scanning: [SAST, dependency vulnerabilities]
└─ Technical Debt: [Tracking, prioritization, paydown]

DEPLOYMENT & OPERATIONS:
├─ Blue/Green Deployment: [Zero-downtime strategy]
├─ Feature Flags: [Progressive rollout, kill switches]
├─ Database Migrations: [Expand-contract pattern]
├─ Rollback Plan: [Automated, time-bounded]
└─ Runbooks: [Common issues, troubleshooting steps]
═══════════════════════════════════════════════════════════

REQUIRED TERMINOLOGY: SOLID, design patterns, API contract, idempotency,
circuit breaker, repository pattern, dependency injection, unit testing,
observability, microservices, RESTful, rate limiting, caching.

OUTPUT REQUIREMENTS:
• Provide code examples for critical components
• Specify test coverage expectations and strategy
• Include API endpoint specifications with examples
• Discuss trade-offs between architectural choices
• Reference specific frameworks and libraries""",
            "validation_keywords": [
                "SOLID", "API", "testing", "pattern", "idempotency",
                "circuit breaker", "observability", "microservices", "cache"
            ]
        },
        
        "devops-expert": {
            "name": "Principal DevOps Engineer",
            "category": "devops",
            "reputation_multiplier": 1.80,
            "min_response_tokens": 300,
            "max_response_tokens": 2500,
            "temperature": 0.65,
            "requires_validation": True,
            "system_prompt": """You are a PRINCIPAL DEVOPS ENGINEER with expertise in CI/CD, infrastructure automation, and platform engineering.

CORE PRINCIPLES:
• Infrastructure as Code - version everything
• Automate everything - eliminate toil
• Shift left - catch issues early
• Continuous improvement - measure and optimize
• Blameless culture - learn from failures

RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════
DEVOPS IMPLEMENTATION: [Pipeline/Platform Name]
───────────────────────────────────────────────────────────
CI/CD PIPELINE:
├─ Source Control: [Git workflow, branching strategy]
├─ Build Stage:
│  ├─ Build Tools: [Maven/Gradle/npm/Docker]
│  ├─ Artifact Management: [Nexus/Artifactory, versioning]
│  └─ Build Time: [Target < 10 min, parallelization]
├─ Test Stage:
│  ├─ Unit Tests: [Parallel execution, coverage gates]
│  ├─ Integration Tests: [Test containers, mocking]
│  ├─ Security Scans: [SAST, dependency check, secrets]
│  └─ Quality Gates: [SonarQube, coverage thresholds]
├─ Deployment Stage:
│  ├─ Strategy: [Blue/green, canary, rolling]
│  ├─ Environments: [Dev → Staging → Production]
│  ├─ Approval Gates: [Manual/automated, stakeholders]
│  └─ Rollback: [Automated on failure, < 5 min]
└─ Pipeline as Code: [Jenkinsfile/GitLab CI/.github/actions]

INFRASTRUCTURE AS CODE:
├─ Tools: [Terraform/Pulumi/CloudFormation/Ansible]
├─ State Management: [Remote backend, locking, versioning]
├─ Module Design: [Reusable, composable, versioned]
├─ Secrets Management: [Vault/AWS Secrets/Azure KeyVault]
└─ Drift Detection: [Scheduled checks, reconciliation]

CONTAINER & ORCHESTRATION:
├─ Containerization:
│  ├─ Base Images: [Minimal, security-hardened]
│  ├─ Multi-stage Builds: [Build vs runtime separation]
│  ├─ Image Scanning: [Trivy/Clair, vulnerability thresholds]
│  └─ Registry: [Private registry, image promotion]
├─ Kubernetes:
│  ├─ Cluster Architecture: [Control plane HA, node pools]
│  ├─ Workload Resources: [Deployments, StatefulSets, Jobs]
│  ├─ Networking: [CNI, service mesh, ingress]
│  ├─ Storage: [PV/PVC, storage classes, backup]
│  └─ Security: [RBAC, pod security, network policies]
└─ GitOps: [ArgoCD/Flux, declarative deployments]

MONITORING & OBSERVABILITY:
├─ Metrics: [Prometheus/Datadog, custom metrics]
├─ Logging: [ELK/Splunk, log aggregation, retention]
├─ Tracing: [Jaeger/Zipkin, sampling strategy]
├─ Dashboards: [Grafana, service health, SLIs]
└─ Alerting: [Alert manager, on-call rotation, runbooks]

RELIABILITY & PERFORMANCE:
├─ SLO/SLI Definition: [Availability, latency, throughput]
├─ Load Testing: [JMeter/k6, baseline performance]
├─ Chaos Engineering: [Chaos Monkey, game days]
├─ Incident Management: [PagerDuty, post-mortems]
└─ Capacity Planning: [Resource utilization, growth]

SECURITY & COMPLIANCE:
├─ Secret Rotation: [Automated, frequency]
├─ Vulnerability Management: [Scan, patch, verify]
├─ Compliance: [SOC 2, PCI, audit trails]
├─ Access Control: [Least privilege, MFA, SSO]
└─ Network Security: [Segmentation, firewalls, zero trust]
═══════════════════════════════════════════════════════════

REQUIRED TERMINOLOGY: CI/CD, infrastructure as code, GitOps, Kubernetes,
Docker, pipeline, deployment strategy, monitoring, observability, SLO/SLI.

OUTPUT REQUIREMENTS:
• Provide pipeline configuration examples
• Include rollback and disaster recovery procedures
• Specify monitoring and alerting thresholds
• Document security and compliance measures""",
            "validation_keywords": [
                "CI/CD", "pipeline", "Kubernetes", "Docker", "infrastructure",
                "GitOps", "monitoring", "deployment", "automation"
            ]
        },
        
            "advanced-expert": {
            "name": "Emerging Technology Strategist",
            "category": "innovation",
            "reputation_multiplier": 1.60,
            "min_response_tokens": 250,
            "max_response_tokens": 2200,
            "temperature": 0.75,
            "requires_validation": True,
            "system_prompt": """You are an EMERGING TECHNOLOGY STRATEGIST with expertise in evaluating and adopting cutting-edge technologies.

CORE PRINCIPLES:
• Technology radar - track maturity lifecycle
• Risk assessment - balance innovation and stability
• ROI analysis - justify adoption with metrics
• Vendor evaluation - avoid lock-in
• Continuous learning - stay ahead of curve

RESPONSE STRUCTURE:
═══════════════════════════════════════════════════════════
TECHNOLOGY EVALUATION: [Technology Name]
───────────────────────────────────────────────────────────
TECHNOLOGY OVERVIEW:
├─ Category: [Quantum/Blockchain/Web3/Edge/AI/XR]
├─ Key Capabilities: [Core features and differentiators]
├─ Vendor Landscape: [Major players, open-source options]
└─ Standards: [Emerging standards, consortiums]

MATURITY ASSESSMENT:
├─ Gartner Hype Cycle: [Innovation trigger → Plateau]
├─ Technology Readiness Level: [TRL 1-9]
├─ Adoption Phase: [Innovators/Early adopters/Early majority]
├─ Production Readiness:
│  ├─ Performance: [Benchmarks vs established tech]
│  ├─ Reliability: [Failure rates, support quality]
│  ├─ Tooling: [Development, debugging, monitoring]
│  └─ Talent: [Skill availability, learning curve]
└─ Risk Factors: [Technical debt, vendor viability]

USE CASE ANALYSIS:
├─ Problem Fit: [Why this tech vs alternatives]
├─ Value Proposition: [Unique benefits, competitive advantage]
├─ Applicability: [Where it works well, where it doesn't]
├─ Prerequisites: [Infrastructure, skills, data requirements]
└─ Success Metrics: [KPIs, ROI calculation]

IMPLEMENTATION ROADMAP:
├─ Phase 1 - Exploration (1-3 months):
│  ├─ Proof of Concept: [Scope, success criteria]
│  ├─ Risk Assessment: [Technical, business, security]
│  └─ Team Training: [Skills gap, learning resources]
├─ Phase 2 - Pilot (3-6 months):
│  ├─ Limited Production: [Scope, monitoring]
│  ├─ Integration: [Existing systems, data flows]
│  └─ Performance Validation: [Benchmarks, scaling]
├─ Phase 3 - Scale (6-12 months):
│  ├─ Production Deployment: [Rollout strategy]
│  ├─ Operational Excellence: [SLAs, support]
│  └─ Continuous Optimization: [Tuning, updates]
└─ Phase 4 - Optimization (12+ months):
   ├─ Advanced Features: [Leverage full capabilities]
   └─ Knowledge Sharing: [Internal expertise, best practices]

COMPETITIVE ANALYSIS:
├─ Alternatives: [Established technologies]
├─ Trade-offs: [Innovation vs stability vs cost]
├─ Migration Path: [If technology doesn't pan out]
└─ Lock-in Risk: [Vendor dependency, standards]

COST-BENEFIT ANALYSIS:
├─ Initial Investment: [Licenses, infrastructure, training]
├─ Ongoing Costs: [Maintenance, scaling, support]
├─ Expected Benefits: [Quantified improvements]
├─ Payback Period: [Time to positive ROI]
└─ Opportunity Cost: [Alternative investments]

RISK MITIGATION:
├─ Technical Risks: [Immaturity, bugs, performance]
├─ Business Risks: [Vendor viability, support]
├─ Security Risks: [Vulnerabilities, compliance]
├─ Mitigation Strategies: [Contingency plans]
└─ Exit Strategy: [Migration path if needed]
═══════════════════════════════════════════════════════════

REQUIRED TERMINOLOGY: maturity model, proof of concept, pilot, adoption,
innovation, emerging technology, roadmap, ROI, risk assessment.

OUTPUT REQUIREMENTS:
• Provide realistic timelines for each phase
• Include specific use cases and success criteria
• Quantify expected benefits and costs
• Identify risks with mitigation strategies
• Compare with established alternatives""",
            "validation_keywords": [
                "maturity", "adoption", "roadmap", "ROI", "pilot",
                "emerging", "innovation", "risk", "use case"
            ]
        },
            "vision-expert": {
            "name": "Computer Vision Specialist",
            "category": "vision",
            "reputation_multiplier": 2.0,
            "min_response_tokens": 250,
            "max_response_tokens": 3000,
            "temperature": 0.65,
            "requires_validation": True,
            "system_prompt": """You are a COMPUTER VISION SPECIALIST with expertise in image analysis, object detection, and visual reasoning.

CORE PRINCIPLES:
- Precise visual observation
- Technical accuracy in descriptions  
- Spatial relationship awareness
- Color and composition analysis
- Object recognition expertise

RESPONSE STRUCTURE:
Provide detailed visual analysis with specific observations about objects, colors, spatial relationships, lighting, and composition.""",
            "validation_keywords": [
                "image", "visual", "object", "color", "composition",
                "lighting", "perspective", "spatial", "texture"
            ]
        }

        }

    @classmethod
    def get_persona(cls, persona_id: str) -> Optional[PersonaMetadata]:
        """Retrieve a persona by ID with validation."""
        try:
            if not isinstance(cls.PERSONAS, dict):
                logger.error(f"PERSONAS is {type(cls.PERSONAS)}, expected dict!")
                return None

            persona = cls.PERSONAS.get(persona_id)
            if persona is None:
                logger.warning(f"Persona '{persona_id}' not found in {list(cls.PERSONAS.keys())}")
                return None

            if not cls._validate_persona(persona):
                logger.error(f"Persona '{persona_id}' failed validation")
                return None

            return persona
        except Exception as e:
            logger.error(f"get_persona error: {e}")
            return None

    @classmethod
    def _validate_persona(cls, persona: PersonaMetadata) -> bool:
        """Validate persona configuration"""
        try:
            required_fields = [
                "name", "category", "reputation_multiplier",
                "system_prompt", "validation_keywords"
            ]
            for field in required_fields:
                if field not in persona:
                    logger.error(f"Missing required field: {field}")
                    return False

            rep = persona["reputation_multiplier"]
            if not (cls.MIN_REPUTATION <= rep <= cls.MAX_REPUTATION):
                logger.error(f"Invalid reputation: {rep}")
                return False

            if not persona.get("validation_keywords") or len(persona.get("validation_keywords", [])) < 3:
                logger.error("Insufficient validation keywords")
                return False

            if persona.get("min_response_tokens", 0) > persona.get("max_response_tokens", float('inf')):
                logger.error("Invalid token limits")
                return False

            return True
        except Exception as e:
            logger.error(f"Persona validation error: {e}")
            return False

    @classmethod
    def list_personas(cls) -> List[Dict[str, any]]:
        """List all available personas with metadata"""
        return [
            {
                "id": pid,
                "name": p["name"],
                "category": p["category"],
                "reputation_multiplier": p["reputation_multiplier"]
            }
            for pid, p in cls.PERSONAS.items()
        ]

    @classmethod
    def get_by_category(cls, category: str) -> List[str]:
        """Get all persona IDs in a category"""
        return [
            pid for pid, p in cls.PERSONAS.items() if p.get("category") == category
        ]

    @classmethod
    def validate_response(cls, persona_id: str, response: str) -> bool:
        """Validate that a response contains expected keywords for the persona"""
        persona = cls.get_persona(persona_id)
        if not persona:
            return False

        if not persona.get("requires_validation", False):
            return True

        response_lower = response.lower()
        keywords = persona.get("validation_keywords", [])
        keywords_found = sum(1 for kw in keywords if kw.lower() in response_lower)

        threshold = max(2, int(len(keywords) * 0.3))
        return keywords_found >= threshold

SPECIALIST_PERSONAS = SpecialistPersonaConfig.PERSONAS

# ==================== ITERATIVE ADVERSARIAL CRITIQUE (IAC) SYSTEM ====================
# Fixed and Enabled

class AdversarialValidator:
    """
    COMPLETE FIXED IAC Validator (Gemini Powered)
    - Uses google-genai SDK
    - Uses gemini-1.5-flash to avoid 429 Errors
    - Removes all OpenAI dependencies
    """
    
    CRITIC_PROMPTS = {
        "security-expert": """You are a cynical Security Architect reviewing code for vulnerabilities.
        Focus ONLY on:
        1. Remote Code Execution (RCE)
        2. SQL/Command Injection
        3. Hardcoded Credentials
        4. Privilege Escalation
        
        If the code is safe or standard practice, mark as PASS.
        OUTPUT FORMAT (JSON only): {"verdict": "PASS"/"FAIL", "confidence": 0.0-1.0, "fatal_flaws": [], "minor_issues": [], "reasoning": "", "risk_level": "CRITICAL/HIGH/MEDIUM/LOW"}""",

        "ml-expert": """You are a Senior ML Researcher reviewing training logic.
        Focus ONLY on:
        1. Data leakage (training on test data)
        2. NaN/Infinity propagation
        3. Memory leaks in training loops
        4. Invalid tensor shapes
        
        Standard training loops should PASS.
        OUTPUT FORMAT (JSON only): {"verdict": "PASS"/"FAIL", "confidence": 0.0-1.0, "fatal_flaws": [], "minor_issues": [], "reasoning": "", "risk_level": "CRITICAL/HIGH/MEDIUM/LOW"}""",

        "general": """You are reviewing an AI response for safety and quality.
        IMPORTANT: Use CRITICAL risk level ONLY for genuinely dangerous content:
        - Security vulnerabilities that would cause immediate breaches
        - Completely incorrect technical information that would break systems
        - Harmful medical/legal advice
        - Malicious code or exploits

        For everything else, use HIGH/MEDIUM/LOW and mark as PASS if it's helpful.
        OUTPUT FORMAT (JSON only): {"verdict": "PASS"/"FAIL", "confidence": 0.0-1.0, "fatal_flaws": [], "minor_issues": [], "reasoning": "", "risk_level": "CRITICAL/HIGH/MEDIUM/LOW"}"""
    }

    def __init__(self, max_refinement_iterations=1, min_confidence_threshold=0.7, auto_reject_critical_risk=True, training_mode=True):
        self.max_refinement_iterations = max_refinement_iterations
        self.min_confidence_threshold = min_confidence_threshold
        self.auto_reject_critical_risk = auto_reject_critical_risk
        self.training_mode = training_mode
        self.logger = logging.getLogger(f"{__name__}.AdversarialValidator")
        
        # Initialize Gemini Client
        try:
            from google import genai
            self.client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
            self.model_id = "gemini-1.5-flash" # Stable model to avoid 429
        except Exception as e:
            self.logger.error(f"Failed to init Gemini Client for Validator: {e}")
            self.client = None

    async def _call_gemini(self, system_prompt: str, user_prompt: str) -> Optional[str]:
        """Helper to call Gemini 1.5 Flash using the SDK"""
        if not self.client: 
            self.logger.error("Gemini client not initialized")
            return None
            
        try:
            from google.genai import types
            
            combined_content = f"SYSTEM INSTRUCTION:\n{system_prompt}\n\nUSER REQUEST:\n{user_prompt}"
            
            response = self.client.models.generate_content(
                model=self.model_id,
                contents=combined_content,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=1500
                )
            )
            return response.text
        except Exception as e:
            self.logger.error(f"Gemini IAC Error: {e}")
            return None

    def _parse_critique(self, critique_text: str) -> dict:
        try:
            if "```json" in critique_text:
                json_start = critique_text.find("```json") + 7
                json_end = critique_text.find("```", json_start)
                critique_text = critique_text[json_start:json_end].strip()
            elif "```" in critique_text:
                json_start = critique_text.find("```") + 3
                json_end = critique_text.find("```", json_start)
                critique_text = critique_text[json_start:json_end].strip()
            
            critique = json.loads(critique_text)
            
            required_fields = ["verdict", "confidence", "fatal_flaws", "reasoning", "risk_level"]
            for field in required_fields:
                if field not in critique:
                    critique[field] = "UNKNOWN" if field in ["verdict", "risk_level"] else 0.5 if field == "confidence" else []
            
            return critique
            
        except json.JSONDecodeError as e:
            self.logger.error(f"Failed to parse critique: {e}")
            return {
                "verdict": "PASS" if self.training_mode else "FAIL",
                "confidence": 0.7 if self.training_mode else 0.0,
                "fatal_flaws": [] if self.training_mode else ["Critic malformed"],
                "minor_issues": [],
                "reasoning": "Parsing failed - defaulting to PASS for training",
                "risk_level": "MEDIUM" if self.training_mode else "HIGH"
            }

    async def _generate_draft(self, prompt: str, persona_type: str) -> Optional[str]:
        if 'get_safe_persona' in globals():
            resolved_type, persona = get_safe_persona(persona_type)
        else:
            persona = SPECIALIST_PERSONAS.get(persona_type, SPECIALIST_PERSONAS.get("advanced-expert"))
            
        if not persona:
            self.logger.error(f"❌ No persona config available (requested: {persona_type})")
            return None
        
        system_prompt = persona["system_prompt"]
        persona_name = persona["name"]
        
        self.logger.info(f"🎨 Generating draft with persona: {persona_type} ({persona_name})")
        
        # Use new helper
        draft = await self._call_gemini(system_prompt, prompt)
        
        if draft:
            self.logger.info(f"✅ Draft generated ({len(draft)} chars)")
        else:
            self.logger.error("❌ Draft generation failed")
        
        return draft

    async def _critique_draft(self, prompt: str, draft: str, domain: str) -> dict:
        critic_prompt = self.CRITIC_PROMPTS.get(domain, self.CRITIC_PROMPTS["general"])
        
        self.logger.info(f"🔍 Critiquing draft (domain: {domain})")
        
        user_content = f"ORIGINAL QUERY:\n{prompt}\n\nDRAFT RESPONSE:\n{draft}\n\nProvide JSON critique."
        
        # Use new helper (Replacing OpenAI call)
        critique_text = await self._call_gemini(critic_prompt, user_content)
        
        if not critique_text:
            return {
                "verdict": "FAIL",
                "confidence": 0.0,
                "fatal_flaws": ["Critic API failed"],
                "minor_issues": [],
                "risk_level": "HIGH"
            }
        
        return self._parse_critique(critique_text)

    async def validate_and_refine(self, prompt: str, persona_type: str, complexity: int) -> dict:
        """Unified validation logic handling training mode."""
        self.logger.info(f"🚀 IAC validation started (training_mode={self.training_mode})")
        
        # 1. Generate
        draft = await self._generate_draft(prompt, persona_type)
        if not draft:
            return {"success": False, "response": None, "final_verdict": "FAIL", "reason": "Draft generation failed"}
        
        # 2. Critique
        domain = "general"
        if "security" in persona_type: domain = "security-expert"
        if "ml" in persona_type or "training" in persona_type: domain = "ml-expert"
        
        critique = await self._critique_draft(prompt, draft, domain)
        
        verdict = critique.get("verdict", "FAIL").upper()
        risk_level = critique.get("risk_level", "UNKNOWN")
        fatal_flaws = critique.get("fatal_flaws", [])
        
        # 3. Decision Logic
        should_accept = False
        reason = ""

        if verdict == "PASS":
            should_accept = True
            reason = "Passed critique"
        elif self.training_mode and risk_level != "CRITICAL":
            should_accept = True
            reason = f"Training Mode Bypass: Accepted {risk_level} risk"
            self.logger.info("✅ Training mode bypass active")
        elif risk_level == "CRITICAL" and not fatal_flaws:
            should_accept = True
            reason = "False positive CRITICAL (no flaws listed)"
        else:
            should_accept = False
            reason = f"Rejected: {risk_level} risk with flaws: {fatal_flaws}"

        if should_accept:
            return {
                "success": True,
                "response": draft,
                "iterations": 1,
                "critiques": [critique],
                "final_verdict": "PASS",
                "reason": reason
            }
        else:
            return {
                "success": False,
                "response": None,
                "iterations": 1,
                "critiques": [critique],
                "final_verdict": "FAIL",
                "reason": reason
            }

# ==================== GLOBAL INSTANCE ====================
adversarial_validator = AdversarialValidator(
    max_refinement_iterations=1,
    min_confidence_threshold=0.7,
    auto_reject_critical_risk=True,
    training_mode=True  # Enable lenient mode for training
)

# ==================== SAFE PERSONA RESOLVER ====================
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

# ==================== DATABASE CONFIGURATION ====================
engine = create_engine(DATABASE_URL, pool_size=20, max_overflow=40)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Define get_db here to ensure it's available for all dependencies
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

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

# ==================== REAL DUKE MODEL CLASSES ====================

class SimpleDukeModel(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=512):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim)
        )
    def forward(self, x): return self.network(x)

import torch
import torch.nn as nn
import logging

logger = logging.getLogger("LabeleeDuke")

class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim=512):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )
    def forward(self, x): return x + self.block(x)

class EnhancedDukeModel(nn.Module):
    """
    Labelee Duke Model V2.0
    Now utilizes EnhancedModelConfig for modular initialization.
    Integrates the CrossModalBridge and TrustScoringHead.
    """
    def __init__(self, config):
        super().__init__()
        self.config = config
        
        # Perception layers (Input dimensions from config)
        self.input_proj = nn.Linear(config.embed_dim, config.embed_dim)
        
        # V2.0 Feature: Bi-Directional Cross-Modal Bridge
        # Note: In a full multimodal setup, you'd pass visual and text dims separately.
        # For the coordinator's flattened input, we use the bridge to refine representations.
        self.bridge = nn.MultiheadAttention(config.embed_dim, num_heads=8, batch_first=True)
        
        self.residual_blocks = nn.Sequential(
            *[ResidualBlock(config.embed_dim) for _ in range(4)]
        )
        
        # Final Output Projection
        self.output_proj = nn.Sequential(
            nn.Linear(config.embed_dim, config.embed_dim),
            nn.LayerNorm(config.embed_dim),
            nn.ReLU(),
            nn.Linear(config.embed_dim, config.embed_dim)
        )
        
        # V2.0 Upgrade: LABEELE AI Trust System Head
        if config.use_trust_head:
            self.trust_head = nn.Sequential(
                nn.Linear(config.embed_dim, config.embed_dim // 4),
                nn.ReLU(),
                nn.Linear(config.embed_dim // 4, 1),
                nn.Sigmoid()
            )
            logger.info("🛡️ TrustScoringHead Online for V2.0 Pipeline")

    def forward(self, x):
        # 1. Initial Projection
        x = self.input_proj(x)
        
        # 2. Refinement via Attention (Self-Attention here as x is fused)
        # Using the bridge logic: x attends to itself to find internal correlations
        attn_out, _ = self.bridge(x, x, x)
        x = x + attn_out
        
        # 3. Non-linear depth
        x = self.residual_blocks(x)
        
        # 4. Generate Main Embedding
        embedding = self.output_proj(x)
        
        # 5. Generate Trust Score (V2.0 Exclusive)
        trust_score = torch.tensor([0.95]) # Default fallback
        if self.config.use_trust_head:
            trust_score = self.trust_head(embedding)
            
        return embedding, trust_score

class TextEmbedder:
    def __init__(self, embedding_dim=512):
        self.embedding_dim = embedding_dim
        self.vocab = {}
        self.vocab_size = 0
    
    def build_vocab(self, texts):
        all_words = set()
        for text in texts:
            words = text.lower().split()
            all_words.update(words)
        self.vocab = {word: idx for idx, word in enumerate(sorted(all_words))}
        self.vocab_size = len(self.vocab)
        logger.info(f"📚 Built vocabulary with {self.vocab_size} words")
    
    def embed(self, text: str):
        words = text.lower().split()
        bow = np.zeros(self.embedding_dim)
        for word in words:
            if word in self.vocab:
                idx = self.vocab[word]
                if idx < self.embedding_dim:
                    bow[idx] = 1
        if bow.sum() > 0: bow = bow / bow.sum()
        if len(bow) < self.embedding_dim: bow = np.pad(bow, (0, self.embedding_dim - len(bow)))
        return bow

class ResponseGenerator:
    def __init__(self):
        self.response_database = []
        self.min_similarity_threshold = 0.3
        self.response_truncation = 1500
    
    def add_response(self, embedding, response: str, metadata: dict = None):
        if not response or len(response) < 20: return False
        self.response_database.append({
            "embedding": embedding,
            "response": response,
            "metadata": metadata or {},
            "length": len(response),
            "added_at": datetime.now().isoformat(),
        })
        return True
    
    def generate(self, output_embedding, complexity: int = None, fallback_mode: bool = False):
        if not self.response_database: return self._get_fallback(complexity)
        
        similarities = []
        for item in self.response_database:
            dot_product = np.dot(output_embedding, item["embedding"])
            norm_product = (np.linalg.norm(output_embedding) * np.linalg.norm(item["embedding"]))
            similarity = dot_product / (norm_product + 1e-8)
            
            if complexity and "complexity" in item["metadata"]:
                complexity_match = 1 - abs(complexity - item["metadata"]["complexity"]) / 10
                similarity *= (0.7 + 0.3 * complexity_match)
                
            similarities.append({"score": similarity, "response": item["response"]})
        
        similarities.sort(key=lambda x: x["score"], reverse=True)
        best_match = similarities[0]
        
        if best_match["score"] > self.min_similarity_threshold:
            return best_match["response"]
        return self._get_fallback(complexity)

    def _get_fallback(self, complexity: int = None):
        return "Duke ML is continuously learning. Check back soon!"

    def get_stats(self):
        if not self.response_database: return {}
        lengths = [item["length"] for item in self.response_database]
        return {
            "total_responses": len(self.response_database),
            "avg_response_length": int(np.mean(lengths)),
            "max_response_length": max(lengths),
            "min_response_length": min(lengths),
        }

class EnhancedModelConfig:
    """
    Centralized Configuration for Labelee Duke Model V2.0
    Created by Immanuel Olajuyigbe
    """
    def __init__(self):
        # --- Core Architecture ---
        self.model_name = "Labelee Duke Model"
        self.vision_backbone = "vit_base_patch16_224" 
        self.text_backbone = "sentence-transformers/all-MiniLM-L6-v2"
        self.embed_dim = 768  
        self.latent_dim = 512 
        
        # --- MISSING ATTRIBUTES ADDED HERE ---
        self.use_trust_head = True      # Required for the V2 Trust Scoring logic
        self.dropout_rate = 0.1         # Standard regularization
        self.num_heads = 8              # For cross-modal attention layers
        self.use_bottleneck = True      # For latent space compression
        
        # --- Training Hyperparameters ---
        self.learning_rate = 1e-4
        self.batch_size = 32
        self.epochs = 20
        self.weight_decay = 0.01
        self.warmup_steps = 500
        
        # --- LoRA / PEFT Settings ---
        self.use_lora = True
        self.lora_rank = 8
        self.lora_alpha = 16
        self.lora_dropout = 0.05
        
        # --- Loss Balancing (Multi-Task) ---
        self.recon_weight = 1.0     
        self.trust_weight = 0.1     
        self.contrastive_weight = 0.5 
        
        # --- Path Configuration ---
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.checkpoint_dir = os.path.join(self.base_dir, "duke_checkpoints")
        self.weights_dir = os.path.join(self.base_dir, "labeele_duke", "fine_tuned_weights_v2")
        
        # Ensure directories exist
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        os.makedirs(self.weights_dir, exist_ok=True)

    def to_dict(self):
        """Export config for logging or serialization"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
class RealDukeMLPipeline:
    def __init__(self):
        # 1. Initialize V2 Configuration
        self.config = EnhancedModelConfig()
        
        # ✅ GPU Detection with Fallback
        if torch.cuda.is_available():
            torch.cuda.empty_cache()  
            self.device = torch.device("cuda")
            print(f"✅ GPU ENABLED: {torch.cuda.get_device_name(0)}")
        elif torch.backends.mps.is_available():
            self.device = torch.device("mps")
            print("✅ APPLE SILICON GPU (MPS) ENABLED")
        else:
            self.device = torch.device("cpu")
            print("⚠️ GPU NOT AVAILABLE - Using CPU (slower)")

        # Initialize core components
        self.model = None
        # embedding_dim must match EnhancedModelConfig.embed_dim (768) - TextEmbedder's
        # own default (512) silently mismatched this, so every real training run threw
        # a matrix-shape RuntimeError the moment EnhancedDukeModel's input_proj layer
        # (Linear(768, 768)) received a 512-dim tensor. This is why retrain-agents
        # always failed once there was enough real data to actually reach training.
        self.embedder = TextEmbedder(embedding_dim=self.config.embed_dim)
        self.generator = ResponseGenerator()
        self.brain = None  
        self.model_version = 0
        self.stats = {
            "samples_processed": 0,
            "total_inferences": 0,
            "recent_loss": 0.0,
            "last_training_time": None,
            "avg_trust_score": 0.0 
        }
        
        # Ensure path variables are accessible (Assumes these are in duke_config)
        try:
            from duke_config import DukePathConfig
            path_cfg = DukePathConfig()
            self.checkpoint_dir = path_cfg.DUKE_CHECKPOINT_DIR
        except ImportError:
            self.checkpoint_dir = Path("./duke_checkpoints")
            
        logger.info(f"🚀 Initializing Real Duke ML Pipeline V2.0 on {self.device}")
        
        # Load the checkpoints
        self.load_checkpoint()

    def load_checkpoint(self):
        """Fixes the loading logic to ensure EnhancedDukeModel is used correctly."""
        try:
            # Check for specific weights file in v2 directory
            weights_v2_path = Path(self.config.weights_dir) / "duke_model_best.pth"
            
            if weights_v2_path.exists():
                logger.info(f"📦 Loading model V2 from {weights_v2_path}")
                self.model = EnhancedDukeModel(self.config).to(self.device)
                checkpoint = torch.load(weights_v2_path, map_location=self.device)
                self.model.load_state_dict(checkpoint)
                self.model.eval()
            else:
                logger.info("ℹ️ Initializing fresh V2 model - weights not found.")
                self.model = EnhancedDukeModel(self.config).to(self.device)

            # Rest of your loading logic...
            # (Embedder and Generator loading remains same)
            
        except Exception as e:
            logger.error(f"❌ Error loading V2 checkpoints: {e}")

    def save_checkpoint(self):
        try:
            if self.model: torch.save(self.model.state_dict(), DUKE_MODEL_LAST)
            if self.embedder: 
                with DUKE_EMBEDDER.open("wb") as f: pickle.dump(self.embedder, f)
            if self.generator:
                with DUKE_RESPONSES.open("wb") as f: pickle.dump(self.generator, f)
            logger.info("✅ All Duke V2 checkpoints saved successfully")
        except Exception as e:
            logger.error(f"❌ V2 Save failed: {e}")

    async def process_with_duke(self, task_description: str, complexity: int) -> dict:
        """
        Upgraded Inference: Now returns dual-output (Response + Trust Score).
        """
        # Strategy 1: Generative Brain (Novelty)
        if self.brain and complexity > 7:
            try:
                logger.info("🧠 Duke Brain generating NOVEL response...")
                resp = self.brain.generate_novel_response("duke-core", task_description)
                return {"response": resp, "trust_score": 0.88} # Brain default
            except Exception as e:
                logger.error(f"⚠️ Brain failed, falling back: {e}")

        # Strategy 2: V2 Retrieval + Trust Scoring
        if not self.model: raise Exception("Duke model not trained yet")
        
        task_embedding = self.embedder.embed(task_description)
        x = torch.FloatTensor(task_embedding).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            # V2 Model returns tuple: (embedding, trust_score)
            output_embedding, trust_tensor = self.model(x)
        
        output_np = output_embedding.cpu().numpy()[0]
        trust_val = float(trust_tensor.cpu().item())
        
        response = self.generator.generate(output_np, complexity=complexity)
        
        # Update Stats
        self.stats["total_inferences"] += 1
        self.stats["avg_trust_score"] = (self.stats["avg_trust_score"] + trust_val) / 2
        
        return {"response": response, "trust_score": trust_val}

    def _load_low_rated_task_ids(self, min_rating: int = 3) -> set:
        """
        Reads the feedback log (populated by POST /feedback/submit) and returns
        the set of task/request ids rated below min_rating (out of 5), so
        train_model() can exclude examples a human already flagged as bad.
        Previously this feedback was collected but never actually used by
        training - it only sat in a JSONL file.
        """
        low_rated = set()
        try:
            if not os.path.exists(FEEDBACK_LOG_FILE):
                return low_rated
            with open(FEEDBACK_LOG_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        entry = json.loads(line)
                        if entry.get("rating", 5) < min_rating and entry.get("request_id"):
                            low_rated.add(entry["request_id"])
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.warning(f"⚠️ Could not read feedback log for training filter: {e}")
        return low_rated

    async def train_model(self, db: Session) -> dict:
        """
        V2 Rigorous Training: LoRA injection, feedback-aware data curation, a
        real train/validation split, and early stopping.

        Replaces the previous version, which trained on 100% of raw
        TrainingData rows (including literal "Error: ..." responses),
        for a fixed 20 epochs with no validation set at all, and then
        stored a hardcoded validation_accuracy=0.96 regardless of what the
        model actually did. That accuracy number was never real - anyone
        looking at /model/status was seeing a fabricated metric.
        """
        import random

        try:
            training_data = db.query(TrainingData).all()

            # 1. Data-quality filtering: drop error/placeholder responses,
            # too-short responses, and exact-duplicate descriptions.
            ERROR_MARKERS = ("error:", "not initialized", "completely unavailable", "no response received")
            low_rated_ids = self._load_low_rated_task_ids()

            seen_descriptions = set()
            quality_samples = []
            skipped_error = skipped_short = skipped_duplicate = skipped_low_rated = 0

            for td in training_data:
                try:
                    inp = json.loads(td.input_data) if isinstance(td.input_data, str) else td.input_data
                    out = json.loads(td.output_data) if isinstance(td.output_data, str) else td.output_data
                except Exception:
                    continue

                description = str(inp.get("description", inp)).strip()
                result = str(out.get("result", out)).strip()

                if td.task_id in low_rated_ids:
                    skipped_low_rated += 1
                    continue
                if any(marker in result.lower() for marker in ERROR_MARKERS):
                    skipped_error += 1
                    continue
                if len(result) < 20:
                    skipped_short += 1
                    continue
                dedup_key = description.lower()
                if dedup_key in seen_descriptions:
                    skipped_duplicate += 1
                    continue

                seen_descriptions.add(dedup_key)
                quality_samples.append((description, result))

            logger.info(
                f"🧹 Data curation: {len(quality_samples)} usable / {len(training_data)} total "
                f"(skipped {skipped_error} error-responses, {skipped_short} too-short, "
                f"{skipped_duplicate} duplicates, {skipped_low_rated} low-rated)"
            )

            if len(quality_samples) < 10:
                logger.warning(f"⚠️ Not enough quality samples: {len(quality_samples)} (need 10+)")
                return {
                    "status": "skipped",
                    "reason": "insufficient_quality_samples",
                    "usable_samples": len(quality_samples),
                    "total_samples": len(training_data),
                }

            logger.info(f"🧠 DUKE V2.0 TRAINING STARTING with {len(quality_samples)} quality samples")

            # 2. Train/validation split (85/15, shuffled) - the previous version
            # trained and "validated" on the exact same data, which can't
            # actually detect overfitting.
            random.shuffle(quality_samples)
            split_idx = max(1, int(len(quality_samples) * 0.85))
            train_set = quality_samples[:split_idx]
            val_set = quality_samples[split_idx:] or quality_samples[-1:]

            self.embedder.build_vocab([desc for desc, _ in quality_samples])

            def encode(subset):
                X, Y = [], []
                for desc, result in subset:
                    x_emb = self.embedder.embed(desc)
                    y_emb = self.embedder.embed(result)
                    X.append(x_emb)
                    Y.append(y_emb)
                    if len(result) > 50:
                        self.generator.add_response(x_emb, result, metadata={"complexity": 10})
                return (
                    torch.FloatTensor(np.array(X)).to(self.device),
                    torch.FloatTensor(np.array(Y)).to(self.device),
                )

            X_train, Y_train = encode(train_set)
            X_val, Y_val = encode(val_set)

            # 3. LoRA Injection & Model Setup
            self.model = EnhancedDukeModel(self.config).to(self.device)
            optimizer = torch.optim.AdamW(
                self.model.parameters(),
                lr=self.config.learning_rate,
                weight_decay=self.config.weight_decay,
            )
            criterion = nn.SmoothL1Loss()
            trust_criterion = nn.BCELoss()  # For the Trust Head

            # 4. Training loop with early stopping on validation loss, instead
            # of a fixed epoch count that ignores whether the model is
            # actually still improving.
            best_val_loss = float("inf")
            best_state = None
            patience, patience_counter = 5, 0
            max_epochs = 40
            epochs_run = 0

            for epoch in range(max_epochs):
                epochs_run = epoch + 1
                self.model.train()
                optimizer.zero_grad()

                embeddings, trust_scores = self.model(X_train)
                recon_loss = criterion(embeddings, Y_train)
                target_trust = torch.ones_like(trust_scores)  # Real data = high trust
                trust_loss = trust_criterion(trust_scores, target_trust)

                total_loss = recon_loss + (self.config.trust_weight * trust_loss)
                total_loss.backward()
                optimizer.step()
                self.stats["recent_loss"] = total_loss.item()

                self.model.eval()
                with torch.no_grad():
                    val_embeddings, _ = self.model(X_val)
                    val_loss = criterion(val_embeddings, Y_val).item()

                if val_loss < best_val_loss - 1e-4:
                    best_val_loss = val_loss
                    best_state = {k: v.clone() for k, v in self.model.state_dict().items()}
                    patience_counter = 0
                else:
                    patience_counter += 1
                    if patience_counter >= patience:
                        logger.info(f"⏹️ Early stopping at epoch {epochs_run} (no val improvement for {patience} epochs)")
                        break

            # Restore the checkpoint with the best validation loss, not
            # necessarily whichever epoch happened to run last.
            if best_state is not None:
                self.model.load_state_dict(best_state)
            self.model.eval()

            # 5. Real validation metric: mean cosine similarity between
            # predicted and target embeddings on the held-out validation
            # set, mapped from [-1, 1] to a [0, 1] "accuracy-like" score.
            # This replaces the previous hardcoded validation_accuracy=0.96.
            with torch.no_grad():
                val_embeddings, _ = self.model(X_val)
                cos_sim = F.cosine_similarity(val_embeddings, Y_val, dim=-1)
                validation_accuracy = float(((cos_sim.mean() + 1) / 2).clamp(0, 1).item())

            self.model_version += 1
            self.save_checkpoint()

            model_version = ModelVersionBase(
                id=str(uuid.uuid4()),
                version_number=self.model_version,
                training_samples=len(quality_samples),
                validation_accuracy=validation_accuracy,
                is_production=True,
                model_info={
                    "vocab": self.embedder.vocab_size,
                    "peft_enabled": True,
                    "epochs_run": epochs_run,
                    "train_samples": len(train_set),
                    "val_samples": len(val_set),
                    "best_val_loss": best_val_loss,
                    "total_samples_considered": len(training_data),
                    "skipped_error": skipped_error,
                    "skipped_short": skipped_short,
                    "skipped_duplicate": skipped_duplicate,
                    "skipped_low_rated": skipped_low_rated,
                },
            )
            db.add(model_version)
            db.commit()

            logger.info(
                f"✅ Duke V2.0 TRAINED & DEPLOYED (LoRA Rank: {self.config.lora_rank}, "
                f"epochs: {epochs_run}, val_accuracy: {validation_accuracy:.3f})"
            )

            return {
                "status": "success",
                "model_version": self.model_version,
                "epochs_run": epochs_run,
                "train_samples": len(train_set),
                "val_samples": len(val_set),
                "validation_accuracy": validation_accuracy,
                "best_val_loss": best_val_loss,
                "total_samples_considered": len(training_data),
                "skipped_error": skipped_error,
                "skipped_short": skipped_short,
                "skipped_duplicate": skipped_duplicate,
                "skipped_low_rated": skipped_low_rated,
            }

        except Exception as e:
            logger.error(f"❌ V2 Training failed: {e}")
            raise

# Initialize Duke Pipeline Global
duke_pipeline = RealDukeMLPipeline()

# ==================== SYSTEM METRICS HELPERS (V2 Enhanced) ====================

def get_gpu_metrics():
    """Get GPU metrics using GPUtil or safe fallback"""
    if not torch.cuda.is_available():
        import random
        return {
            "gpu_utilization": random.uniform(5, 15), # Simulated idle
            "gpu_memory_used": 0,
            "gpu_memory_total": 0,
            "gpu_temperature": 35.0,
        }

    try:
        import GPUtil
        gpus = GPUtil.getGPUs()
        if not gpus: return {"gpu_utilization": 0, "gpu_memory_used": 0, "gpu_memory_total": 0, "gpu_temperature": 0}
        
        gpu = gpus[0]
        return {
            "gpu_utilization": gpu.load * 100,
            "gpu_memory_used": gpu.memoryUsed / 1024,
            "gpu_memory_total": gpu.memoryTotal / 1024,
            "gpu_temperature": gpu.temperature,
        }
    except:
        return {"gpu_utilization": 45.0, "gpu_memory_used": 2.1, "gpu_memory_total": 8.0, "gpu_temperature": 55.0}

def get_system_metrics():
    """Get CPU and memory metrics"""
    import psutil
    try:
        cpu_percent = psutil.cpu_percent(interval=0.1)
        mem = psutil.virtual_memory()
        return {
            "cpu_utilization": cpu_percent,
            "system_memory_used": mem.used / (1024**3),
            "system_memory_total": mem.total / (1024**3),
        }
    except Exception:
        return {"cpu_utilization": 15.0, "system_memory_used": 4.5, "system_memory_total": 16.0}

# ==================== TRUST & MATCHING ENGINE (PHASE 3) ====================

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


# --- INSERT THIS CLASS BEFORE 'app = FastAPI()' ---

from transformers import AutoTokenizer, AutoModelForCausalLM

import os
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM

import os
from tenacity import retry, stop_after_attempt, wait_random_exponential
from google import genai

# The SDK automatically checks for os.environ.get("GOOGLE_API_KEY") 
# or os.environ.get("GEMINI_API_KEY"). 
# Initializing without arguments works if the env var is set.
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

@retry(
    wait=wait_random_exponential(min=1, max=60), 
    stop=stop_after_attempt(5),
    reraise=True  # Recommended so you can see the final error if it fails 5 times
)
def safe_generate(prompt: str):
    """
    Generates content using Gemini 2.0 Flash Lite with exponential backoff.
    """
    response = client.models.generate_content(
        model='gemini-2.0-flash-lite',
        contents=prompt
    )
    return response.text

# Example usage:
# print(safe_generate("Explain quantum entanglement like I'm five."))

from transformers import AutoTokenizer, AutoModelForCausalLM

import os
import torch
import pickle
from pathlib import Path
from transformers import AutoTokenizer, AutoModelForCausalLM
from google import genai
import re

class DukeGenerativeBrain:
    def __init__(self, model_name="distilgpt2"):
        # 1. Hardware Detection
        self.device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"🧠 Initializing Duke's Generative Brain on {self.device}...")

        self.mode = "student"  # Default mode

        # Local-only brain: fine-tuned TinyLlama, no external AI APIs.
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.model_path = os.path.join(base_dir, "labeele_duke", "duke_chat_brain")
        self.model = None
        self.tokenizer = None
        self._initialize_local_model(model_name)

    def _initialize_local_model(self, model_name):
        """Load the fine-tuned Duke chat model, falling back to the base model if untrained."""
        has_weights = os.path.exists(self.model_path) and len(os.listdir(self.model_path)) > 0

        # On a fresh deploy (e.g. the HF Space) the 2.2GB checkpoint won't be
        # in the git-based deploy - it's pulled from the dedicated weights
        # repo instead, matching the existing 'origin' remote convention.
        if not has_weights:
            try:
                from huggingface_hub import snapshot_download
                print("📥 No local checkpoint - downloading Duke Brain from LABEELEA1/Duke-Weights-Internal...")
                downloaded = snapshot_download(
                    repo_id="LABEELEA1/Duke-Weights-Internal",
                    allow_patterns=["duke_chat_brain/*"],
                    token=os.getenv("HF_TOKEN"),
                )
                candidate = os.path.join(downloaded, "duke_chat_brain")
                if os.path.exists(candidate) and len(os.listdir(candidate)) > 0:
                    self.model_path = candidate
                    has_weights = True
                    print(f"✅ Downloaded Duke Brain to {candidate}")
            except Exception as e:
                print(f"⚠️ Could not download Duke Brain checkpoint ({e}). Using base model.")

        load_path = self.model_path if has_weights else "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

        try:
            print(f"📦 Loading Duke Brain from {load_path}")
            self.tokenizer = AutoTokenizer.from_pretrained(load_path)
            if self.tokenizer.pad_token is None:
                self.tokenizer.pad_token = self.tokenizer.eos_token

            self.model = AutoModelForCausalLM.from_pretrained(
                load_path,
                torch_dtype=torch.bfloat16 if self.device == "cuda" else torch.float32
            ).to(self.device)
            self.model.eval()
            self.mode = "graduate" if has_weights else "student"

        except Exception as e:
            print(f"❌ Critical Local Load Error: {e}")
            try:
                self.tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
                self.model = AutoModelForCausalLM.from_pretrained("distilgpt2").to(self.device)
                self.mode = "student"
            except Exception:
                self.model = None
                self.mode = "unavailable"

    # A small local LLM has no clock and no internet - it will confidently
    # hallucinate a plausible-looking wrong date if asked directly, since
    # nothing in training ever taught it "today". Date/time questions are
    # answered deterministically instead of trusting the model to know.
    DATE_TIME_PATTERN = re.compile(
        r"\b(what'?s?\s+(is\s+)?(the\s+)?(current\s+|today'?s\s+)?(date|day|time)\b|"
        r"what\s+(day|date|time)\s+is\s+it|current\s+date|current\s+time)",
        re.IGNORECASE
    )

    def generate_response(self, prompt, max_length=256):
        if not self.model or not self.tokenizer:
            return "Duke Brain is currently offline or initializing."

        if self.DATE_TIME_PATTERN.search(prompt):
            now = datetime.now()
            return f"Today's date is {now.strftime('%Y-%m-%d')} ({now.strftime('%A')}), current time {now.strftime('%H:%M')}."

        try:
            # Ground the model in the real date so date-adjacent answers
            # (e.g. "how many days until...") aren't computed from whatever
            # date happened to show up in training data.
            today_str = datetime.now().strftime('%Y-%m-%d')
            chat_prompt = f"<|user|>\nToday's date is {today_str}.\n{prompt}</s>\n<|assistant|>\n"
            inputs = self.tokenizer(chat_prompt, return_tensors="pt").to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    max_new_tokens=300,
                    temperature=0.7,
                    top_p=0.9,
                    do_sample=True,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # Only decode the newly generated tokens, not the echoed prompt
            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            decoded = self.tokenizer.decode(new_tokens, skip_special_tokens=True)
            answer = decoded.strip()

            self._log_training_data(prompt, answer)
            return answer

        except Exception as e:
            print(f"❌ Generation Error: {e}")
            return "Duke is currently processing internal neural updates..."

    def _log_training_data(self, prompt, answer):
        """Append real Q&A traffic to duke_training_memory.json as future fine-tuning data."""
        try:
            base_dir = os.path.dirname(os.path.abspath(__file__))
            memory_path = os.path.join(base_dir, "duke_training_memory.json")

            data = []
            if os.path.exists(memory_path):
                try:
                    with open(memory_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = []  # Corrupt file - reset rather than crash logging

            data.append({
                "timestamp": datetime.now().isoformat(),
                "instruction": prompt,
                "output": answer
            })

            with open(memory_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)

        except Exception as e:
            print(f"⚠️ Could not log training data: {e}")
# ==================== APP INITIALIZATION ====================

# Initialize the Brain immediately
duke_brain = None  # Initialize as None globally

async def generate_periodic_logs():
    """Generate system logs periodically"""
    while True:
        await asyncio.sleep(30)
        write_log(f"INFO: System health check - {len(active_connections)} active connections")

async def periodic_metrics_log():
    """Log system metrics periodically"""
    while True:
        await asyncio.sleep(60)
        try:
            cpu = psutil.cpu_percent()
            mem = psutil.virtual_memory()
            write_log(f"METRICS: CPU: {cpu:.1f}% | RAM: {mem.percent:.1f}% | Connections: {len(active_connections)}")
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
    # We use the global variable defined earlier to ensure it persists
    global duke_brain
    try:
        logger.info("🧠 Waking up Duke Generative Brain...")
        duke_brain = DukeGenerativeBrain() # Loads local fine-tuned model weights
        logger.info(f"✅ Duke Brain: ONLINE (Local Mode, {duke_brain.mode})")
    except Exception as e:
        logger.error(f"⚠️ Brain init failed (continuing in lightweight mode): {e}")
        duke_brain = None

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


app = FastAPI(title="AICP Coordinator", lifespan=lifespan)
# ==================== CORS CONFIGURATION (FIXED) ====================
from fastapi.middleware.cors import CORSMiddleware

# Define all trusted origins (Local + Production)
origins = [
    "http://localhost:3000",                # Your local frontend (React)
    "http://127.0.0.1:3000",                # Alternate local address
    "https://www.labeele.ai",               # Your production domain
    "https://labeele.ai",                   # Root domain
    "https://labeele-ai-web.vercel.app",    # Vercel deployments
    "https://huggingface.co",               # Hugging Face internal calls
    "*"                                     # TEMPORARY: Allow all to ensure it works
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,   # Use the list above
    allow_credentials=True,
    allow_methods=["*"],     # Allow all methods (GET, POST, OPTIONS, etc.)
    allow_headers=["*"],     # Allow all headers (Authorization, etc.)
)
# ====================================================================

app.mount("/assets", StaticFiles(directory=ASSETS_DIR), name="assets")


@app.get("/api/metrics/system")
async def get_system_metrics():
    """Get real-time system performance metrics"""
    try:
        # CPU metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        
        # Memory metrics
        memory = psutil.virtual_memory()
        memory_used_gb = memory.used / (1024**3)
        memory_total_gb = memory.total / (1024**3)
        
        # GPU metrics
        try:
            gpus = GPUtil.getGPUs()
            if gpus:
                gpu = gpus[0]  # Get first GPU
                gpu_utilization = gpu.load * 100
                gpu_memory_used = gpu.memoryUsed / 1024  # Convert to GB
                gpu_memory_total = gpu.memoryTotal / 1024
                gpu_temperature = gpu.temperature
            else:
                gpu_utilization = 0
                gpu_memory_used = 0
                gpu_memory_total = 0
                gpu_temperature = 0
        except:
            gpu_utilization = 0
            gpu_memory_used = 0
            gpu_memory_total = 8.55  # Default from logs
            gpu_temperature = 0
        
        metrics = {
            "cpu_utilization": cpu_percent,
            "system_memory_used": memory_used_gb,
            "system_memory_total": memory_total_gb,
            "gpu_utilization": gpu_utilization,
            "gpu_memory_used": gpu_memory_used,
            "gpu_memory_total": gpu_memory_total,
            "gpu_temperature": gpu_temperature,
            "requests_per_sec": len(active_connections) * 0.5,  # Simulated
            "timestamp": datetime.now().isoformat()
        }
        
        # Log metrics periodically
        if int(datetime.now().timestamp()) % 30 == 0:  # Every 30 seconds
            write_log(f"INFO: GPU: {gpu_utilization:.1f}% | RAM: {memory_used_gb:.1f}GB | CPU: {cpu_percent:.1f}%")
        
        return metrics
        
    except Exception as e:
        write_log(f"ERROR: Failed to fetch system metrics: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {str(e)}")

import asyncio
from fastapi.responses import StreamingResponse

# Log file path
LOG_FILE = "duke_system.log"

# Ensure log file exists
if not os.path.exists(LOG_FILE):
    with open(LOG_FILE, "w") as f:
        f.write(f"[{datetime.now().isoformat()}] INFO: Duke System Log initialized\n")

# Active connections tracking
active_connections = set()

# Helper function to write logs
def write_log(message: str):
    """Write log message to file"""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] {message}\n"
    with open(LOG_FILE, "a") as f:
        f.write(log_line)


@app.get("/api/logs/stream")
async def stream_logs(request: Request):
    """Server-Sent Events endpoint for real-time logs"""
    
    async def log_generator():
        connection_id = id(asyncio.current_task())
        active_connections.add(connection_id)
        
        # Send initial connection message
        yield f"data: [SYSTEM] Neural stream connected (ID: {connection_id})\n\n"
        write_log(f"INFO: Client {connection_id} connected to Neural Stream")
        
        try:
            # Open log file and seek to end
            with open(LOG_FILE, "r") as f:
                f.seek(0, 2)  # Go to end of file
                
                while True:
                    # CRITICAL: Check if client is still connected
                    if await request.is_disconnected():
                       # Silent disconnected - this is normal, don't log it
                        pass
                    
                    # Read new lines
                    line = f.readline()
                    if not line:
                        # No new data, send heartbeat and wait
                        yield ": heartbeat\n\n"
                        await asyncio.sleep(1.0)
                        continue
                    
                    # Send the log line
                    yield f"data: {line.strip()}\n\n"
                    
        except asyncio.CancelledError:
            # Client disconnected - this is normal, don't log it
            pass
        except Exception as e:
            write_log(f"ERROR: Stream error for client {connection_id}: {str(e)}")
            print(f"❌ Stream error: {e}")
        finally:
            # Cleanup
            active_connections.discard(connection_id)
    
    return StreamingResponse(
        log_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # Disable nginx buffering
        }
    )
# ==================== JWT & AUTH ====================
from pydantic import BaseModel
from typing import Optional

# JWT_SECRET is already defined above (line ~192) with a fail-closed startup
# guard - this used to redefine it with an insecure hardcoded fallback and no
# guard, silently overwriting that safety check for every JWT operation in
# this file. Removed (security audit); JWT_ALGORITHM kept for the functions below.
JWT_ALGORITHM = "HS256"

class AuthRequest(BaseModel):
    username: str
    password: str

class TaskCreate(BaseModel):
    description: str
    task: Optional[str] = None
    complexity: Optional[int] = 5

def create_token(username: str):
    """Create JWT token"""
    payload = {
        "sub": username,
        "exp": datetime.utcnow() + timedelta(hours=24)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def verify_token(token: str):
    """Verify JWT token"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload.get("sub")
    except:
        return None

# ==================== JWT & AUTH FIXED ====================
class UserRegister(BaseModel):
    username: str
    password: str

from pydantic import BaseModel

class UserRegister(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    password: str

class LoginRequest(BaseModel):
    username: str
    password: str

# coordinator_api.py

@app.post("/api/auth/register", tags=["auth"])
async def register(request: Request, db: Session = Depends(get_db)):
    try:
        body = await request.json()
        username = body.get("username")
        password = body.get("password")
        # Fix: Ensure email is handled even if missing
        email = body.get("email") or f"{username}@labeele.ai"

        if not username or not password:
            raise HTTPException(status_code=400, detail="Missing username or password")

        existing_user = db.query(User).filter(User.username == username).first()
        if existing_user:
            raise HTTPException(status_code=400, detail="Username already exists")

        # Create user
        new_user = User(
            username=username,
            email=email,
            password_hash=hash_password(password),
            is_active=True
        )
        
        db.add(new_user)
        db.commit()
        db.refresh(new_user)

        return {"message": "User registered successfully", "status": "success"}
    except Exception as e:
        db.rollback()
        logger.error(f"Registration Error: {e}")
        # Return 500 but with JSON so frontend doesn't just crash
        return JSONResponse(status_code=500, content={"detail": str(e)})
    
import bcrypt

from pydantic import BaseModel

@app.post("/api/auth/login", tags=["auth"])
async def login(request: LoginRequest, db: Session = Depends(get_db)):
    # SEARCH BY USERNAME
    user = db.query(User).filter(User.username == request.username).first()
    
    if not user or not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    # Generate JWT token
    token = create_access_token(data={"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}

# ✅ CREATE TASK ENDPOINT
@app.post("/api/tasks")
async def create_task(task: TaskCreate, request: Request):
    """Create task - requires JWT token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token")
    
    token = auth_header.split(" ")[1]
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    return {
        "id": str(uuid.uuid4()),
        "result": {
            "response": f"Task processed: {task.description}",
            "confidence": 0.95
        },
        "status": "completed",
        "created_by": username
    }

# ✅ DEPLOY AGENT ENDPOINT
@app.post("/api/agents/{agent_id}/deploy")
async def deploy_agent(agent_id: str, task: TaskCreate, request: Request):
    """Deploy specialist agent - requires JWT token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")
    
    token = auth_header.split(" ")[1]
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    write_log(f"INFO: Deploying agent '{agent_id}' for user '{username}'")
    
    # Agent-specific responses
    agents = {
        "security-expert": f"🔐 Security Analysis: Performing comprehensive security audit for: {task.description}",
        "ml-expert": f"🧠 ML Perspective: Analyzing machine learning approach for: {task.description}",
        "systems-expert": f"⚙️ Systems Analysis: Evaluating architecture and scalability for: {task.description}",
        "backend-expert": f"💻 Backend Design: Designing robust backend solution for: {task.description}",
        "devops-expert": f"🚀 DevOps Approach: Planning deployment strategy for: {task.description}",
        "vision-expert": f"👁️ Visual Analysis: Processing visual data for: {task.description}",
    }
    
    response_text = agents.get(agent_id, f"Processing task with {agent_id}")
    
    # Simulate processing
    await asyncio.sleep(0.5)
    
    task_id = str(uuid.uuid4())
    result = {
        "id": task_id,
        "agent": agent_id,
        "result": {
            "response": response_text,
            "confidence": 0.95
        },
        "status": "completed",
        "created_by": username,
        "complexity": task.complexity,
        "cost": task.complexity * 0.15,
        "timestamp": datetime.now().isoformat()
    }
    
    write_log(f"SUCCESS: Agent '{agent_id}' deployed successfully (Task: {task_id})")
    
    return result

# ==================== END AUTH ====================

# ==================== PYDANTIC MODELS ====================

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

class FeedbackSubmission(BaseModel):
    request_id: str
    rating: int  # 1 (Bad) to 5 (Good)
    comment: str = ""
    agent_name: str

class BuyerLoginRequest(BaseModel):
    buyer_id: str
    password: str

# ==================== API ENDPOINTS ====================

# ==================== CORE AGENCY ENDPOINTS (NEW) ====================

@app.post("/agency/dispatch")
async def agency_dispatch(req: DispatchRequest, db: Session = Depends(get_db)):
    """
    The Generalist (Traffic Controller) Endpoint.
    Analyzes the prompt via TaskRouter and dispatches to Tools OR Agents.
    """
    try:
        # 1. Determine Intent using the Toolkit Router
        target_persona = TaskRouter.route(req.prompt)
        
        # 2. Prepare Response
        response = {
            "assigned_agent": target_persona,
            "action_type": "tool_execution",
            "reply": "",
            "data": None,
            "tools_used": []
        }

        # 3. Execution Logic based on Persona & Intent
        
        # --- SECURITY PATH ---
        if target_persona == "SECURITY_EXPERT":
            if req.context_code and len(req.context_code) > 10:
                scan_result = SecurityScanner.scan(req.context_code)
                response["data"] = scan_result
                response["tools_used"].append("StaticSecurityScanner")
                if scan_result["is_secure"]:
                    response["reply"] = f"✅ Security Scan Passed. No critical issues found in {len(req.context_code.splitlines())} lines."
                else:
                    response["reply"] = f"🚨 CRITICAL ALERT: Found {len(scan_result['issues'])} potential vulnerabilities."
            else:
                response["action_type"] = "conversation"
                response["reply"] = "I am ready to secure your infrastructure. Please provide code or logs to analyze."

        # --- ML PATH ---
        elif target_persona == "ML_SPECIALIST":
            if any(k in req.prompt.lower() for k in ["script", "code", "generate", "loop"]):
                # Generate Training Script
                script = MLToolbox.generate_training_script({})
                response["data"] = {"code": script, "language": "python"}
                response["tools_used"].append("TrainingScriptGenerator")
                response["reply"] = "I have generated a PyTorch training loop optimized for the DUKE architecture."
            else:
                response["action_type"] = "conversation"
                response["reply"] = "I can help with training loops, loss functions, and gradients. What do you need?"

        # --- BACKEND/DEV PATH ---
        elif target_persona == "BACKEND_DEV":
            if "diff" in req.prompt.lower() and req.context_code:
                response["reply"] = "Diff tool ready. Please provide original and modified source."
            else:
                response["action_type"] = "conversation"
                response["reply"] = "I'm ready to architect your API. Do you need a FastAPI scaffold or a DB migration plan?"

        # --- CV PATH ---
        elif target_persona == "CV_SPECIALIST":
            response["action_type"] = "conversation"
            response["reply"] = "Visual perception systems online. Upload an image to generate saliency maps."

        # --- GENERALIST / FALLBACK ---
        else:
            response["action_type"] = "conversation"
            response["reply"] = f"I've analyzed your request. Routing to {target_persona} for specialized assistance."

        return response

    except Exception as e:
        logger.error(f"Dispatch Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/tools/analyze_code")
async def tool_analyze_code(req: ToolRequest):
    """Direct access to CodeReader tool"""
    return CodeReader.analyze_structure(req.code)

@app.post("/tools/security_scan")
async def tool_security_scan(req: ToolRequest):
    """Direct access to SecurityScanner tool"""
    return SecurityScanner.scan(req.code)

@app.post("/tools/generate_train_script")
async def tool_gen_script(config: TrainConfigRequest):
    """Direct access to MLToolbox"""
    return {"code": MLToolbox.generate_training_script(config.dict())}

@app.get("/")
async def root():
    return {
        "service": "AICP Coordinator",
        "version": "5.0.0",
        "features": ["Real Duke ML", "Trust Scoring", "Semantic Matching"],
        "dashboard": "http://localhost:3000/dashboard"
    }

@app.get("/health")
async def health():
    return {"status": "ok", "service": "AICP Coordinator"}

import psutil
try:
    import GPUtil
    GPU_AVAILABLE = True
except ImportError:
    GPU_AVAILABLE = False
    print("⚠️ GPUtil not installed. Install with: pip install gputil")


# NOTE: /auth/buyer/login and /auth/agent/login were removed (security audit).
# Both accepted a hardcoded literal password ("securepassword123") for ANY
# buyer_id/agent_name, auto-created a User row with the plaintext password
# copied into password_hash, and signed the resulting JWT with a second
# hardcoded string ("your-secret-key") completely independent of the real,
# properly-configured JWT_SECRET - i.e. a permanent, unrotatable auth bypass
# sitting in this file's source, which is public on GitHub. Unused by the
# frontend (confirmed via search - real auth is Supabase, see frontend/lib/supabase).

# --- MATCHING & TRUST ENDPOINTS ---

@app.post("/matching/find")
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
        
        write_log(f"🎯 Agent Matching: {selected_agent} (Score: {match_score:.2f})")
        
        return {
            "selected_agent": selected_agent,
            "match_score": match_score,
            "confidence": match_score,
            "reason": reason,
            "all_matches": matches[:3]  # Top 3
        }
        
    except Exception as e:
        write_log(f"ERROR: Agent matching failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))
    
@app.get("/agents/{agent_id}/trust-score")
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

@app.post("/admin/recalc-scores", dependencies=[Depends(require_admin_secret)])
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

@app.post("/tasks/submit")
async def submit_task(
    task_data: TaskSubmission, 
    background_tasks: BackgroundTasks, 
    db: Session = Depends(get_db)
):
    """
    Processes a task using the local Duke Brain only - no external AI APIs.
    """
    try:
        logger.info(f"📥 RECEIVED TASK: {task_data.description[:60]}...")

        target_agent = task_data.target_agent

        # 1. Matching Engine (Auto-Router)
        if not target_agent or target_agent == "Auto-Router":
            try:
                # Simple keyword matching if full MatchingEngine isn't available
                matcher = MatchingEngine(db)
                match_result = matcher.find_best_agent(task_data.description, task_data.complexity)
                if match_result:
                    target_agent = match_result["agent"].name
                    logger.info(f"🎯 Auto-Matched Agent: {target_agent} (Score: {match_result['match_score']})")
                else:
                    target_agent = "duke-ml"
            except Exception as e:
                logger.warning(f"⚠️ Router failed, defaulting to duke-ml: {e}")
                target_agent = "duke-ml"

        # 2. Execution Logic (Memory -> Duke)
        final_response = None
        response_source = "unknown"

        # A. Check Cache first
        try:
            # CAST(...AS TEXT), not a bare "=", because input_data is a json column -
            # Postgres rejects json = text directly ("operator does not exist: json =
            # unknown"), unlike SQLite which allowed it silently. CAST works on both.
            query = text("SELECT output_data FROM training_data WHERE CAST(input_data AS TEXT) = :prompt LIMIT 1")
            exact_prompt = json.dumps({"description": task_data.description, "complexity": task_data.complexity})
            result = db.execute(query, {"prompt": exact_prompt}).fetchone()
            if result:
                data = json.loads(result[0]) if isinstance(result[0], str) else result[0]
                if isinstance(data, str): data = json.loads(data)
                final_response = data.get("result")
                response_source = "cache"
                logger.info("✅ Found EXACT cached response")
        except Exception as cache_error:
            # A failed query leaves a Postgres transaction "aborted" until rolled back -
            # every later query on this same session would fail too without this.
            logger.warning(f"⚠️ Cache lookup failed, continuing without it: {cache_error}")
            db.rollback()

        # B. Local Duke Brain
        if not final_response:
            logger.info(f"🧠 Asking LOCAL DUKE BRAIN for {target_agent}")
            try:
                # Persona system prompt (DB-backed via get_safe_persona, previously never
                # called here at all) + retrieved knowledge (per-agent + DUKE-global,
                # see backend/knowledge.py) replace the old bare "Persona: X\nTask: Y"
                # string - this is the actual RAG wiring for the knowledge system.
                _, persona = get_safe_persona(target_agent)
                prompt = persona["system_prompt"]

                try:
                    chunks = knowledge_lib.retrieve_relevant_chunks(db, KnowledgeChunk, target_agent, task_data.description)
                    if chunks:
                        context_block = "\n\n".join(f"[Reference {i+1}]\n{c.content}" for i, c in enumerate(chunks))
                        prompt += f"\n\nRelevant reference material:\n{context_block}"
                except Exception as retrieval_error:
                    logger.warning(f"⚠️ Knowledge retrieval failed, continuing without it: {retrieval_error}")

                prompt += f"\n\nTask: {task_data.description}"
                if len(prompt) > 6000:
                    prompt = prompt[:6000]

                if duke_brain and duke_brain.model is not None:
                    raw_response = duke_brain.generate_response(prompt)
                    final_response = f"⚡ [DUKE-LOCAL]: {raw_response}"
                    response_source = "duke_local"
                    logger.info("🧠 Duke processed task successfully on Local/GPU.")
                else:
                    final_response = "Error: Duke Brain is not initialized."
            except Exception as duke_error:
                logger.error(f"❌ Duke Brain failed: {duke_error}")
                final_response = "Error: System completely unavailable."

        # 3. Save to Database
        agent_record = db.query(Agent).filter(Agent.name == target_agent).first()
        reputation = agent_record.reputation_multiplier if agent_record else 1.0
        price = int(task_data.complexity * 1_000_000 * reputation)
        
        task_id = str(uuid.uuid4())
        new_task = Task(
            id=task_id,
            description=task_data.description,
            agent_name=target_agent,
            status="completed",
            result=final_response,
            complexity=task_data.complexity,
            price_satoshis=price,
            completed_at=datetime.now(timezone.utc),
            buyer_id=task_data.buyer_id or "anon"
        )
        db.add(new_task)
        
        # Save Training Data
        td = TrainingData(
            id=str(uuid.uuid4()),
            task_id=task_id,
            input_data=json.dumps({"description": task_data.description, "complexity": task_data.complexity}),
            output_data=json.dumps({"result": final_response, "agent": target_agent}),
            success=True,
            agent_name=target_agent,
            persona_type=target_agent
        )
        db.add(td)
        
        if agent_record:
            agent_record.total_tasks_completed += 1
            agent_record.balance_satoshis += price
        
        db.commit()

        # === 4. MEMORY HARVESTING (Training Data Save) ===
        if final_response and response_source == "gemini_cloud":
            try:
                import os
                force_memory_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "duke_training_memory.json")
                
                entry = {
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "instruction": f"Persona: {target_agent}\nTask: {task_data.description}",
                    "output": final_response
                }

                current_data = []
                if os.path.exists(force_memory_path):
                    try:
                        with open(force_memory_path, "r", encoding="utf-8") as f:
                            current_data = json.load(f)
                    except: current_data = [] 
                
                current_data.append(entry)
                with open(force_memory_path, "w", encoding="utf-8") as f:
                    json.dump(current_data, f, indent=2)

                logger.info(f"📝 [MEMORY] Saved to {force_memory_path} | Count: {len(current_data)}")
            except Exception as log_err:
                logger.error(f"⚠️ Memory save failed: {log_err}")

        # 5. Return Result
        confidence_map = {
            "cache": 0.98,
            "gemini_cloud": 0.95,
            "duke_local": 0.75,
            "unknown": 0.5
        }
        confidence_score = confidence_map.get(response_source, 0.5)

        return {
            "response": final_response,
            "confidence": confidence_score,
            "agent_name": target_agent,
            "request_id": task_id,
            "status": "completed",
            "price_satoshis": price
        }

    except Exception as e:
        logger.error(f"❌ TASK ERROR: {str(e)}")
        # Return a clean JSON error instead of crashing
        return JSONResponse(status_code=500, content={"message": f"Task processing failed: {str(e)}"})

@app.post("/feedback/submit", dependencies=[Depends(require_admin_secret)])
async def submit_feedback(feedback: FeedbackSubmission):
    """
    Receives human feedback (RLHF) to improve the Duke Model.
    """
    logger.info(f"📝 Received feedback for {feedback.request_id}: Rating {feedback.rating}/5")
    
    # Structure the training sample
    training_sample = {
        "timestamp": datetime.utcnow().isoformat(),
        "request_id": feedback.request_id,
        "agent": feedback.agent_name,
        "rating": feedback.rating,
        "user_comment": feedback.comment,
        "weight": feedback.rating / 5.0  # Normalize to 0.0 - 1.0 for training
    }
    
    # Save to a JSON Lines file (High-speed append, no DB locking)
    # Ensure directory exists
    os.makedirs(os.path.dirname(FEEDBACK_LOG_FILE), exist_ok=True)
    
    with open(FEEDBACK_LOG_FILE, "a") as f:
        f.write(json.dumps(training_sample) + "\n")
        
    return {
        "status": "received", 
        "message": "Feedback integrated into continual learning pipeline."
    }

# REPLACE THE ENTIRE call_openai_for_persona FUNCTION WITH THIS:

# REPLACE THE ENTIRE call_openai_for_persona FUNCTION WITH THIS:

async def call_gemini_for_persona(description: str, complexity: int, persona_type: str = "duke-ml") -> str:
    """
    Directly calls Gemini 1.5 Flash for specialized persona tasks.
    Replaces the old OpenAI logic.
    """
    try:
        # 1. Get the Persona System Prompt
        resolved_type, persona = get_safe_persona(persona_type)
        system_instruction = persona.get("system_prompt", "You are a helpful AI assistant.")
        
        # 2. Prepare the Client
        from google import genai
        from google.genai import types
        import os
        
        # Initialize client
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        # 3. Construct the Request
        combined_prompt = f"""
        SYSTEM INSTRUCTION:
        {system_instruction}
        
        USER TASK:
        {description}
        
        Perform the task above, adhering strictly to the system instruction.
        """
        
        # 4. Generate Content using the STABLE model
        # CHANGED FROM 'gemini-2.0-flash-lite' TO 'gemini-1.5-flash' TO FIX 429 ERROR
        response = client.models.generate_content(
            model='gemini-1.5-flash',
            contents=combined_prompt,
            config=types.GenerateContentConfig(
                temperature=0.7,
                max_output_tokens=2000
            )
        )
        
        return response.text

    except Exception as e:
        logger.error(f"❌ Gemini Persona Error: {e}")
        return f"Error generating response: {str(e)}"

@app.get("/tasks", dependencies=[Depends(require_admin_secret)])
async def get_tasks(limit: int = 20, db: Session = Depends(get_db)):
    tasks = db.query(Task).order_by(desc(Task.created_at)).limit(limit).all()
    return [{"id": t.id, "description": t.description, "status": t.status, "agent_name": t.agent_name, "result": t.result, "price_satoshis": t.price_satoshis, "complexity": t.complexity} for t in tasks]

@app.get("/learning/status")
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

@app.get("/model/status")
async def get_model_status(db: Session = Depends(get_db)):
    ver = db.query(ModelVersionBase).order_by(desc(ModelVersionBase.created_at)).first()
    return {
        "status": "ready" if ver and ver.is_production else "training",
        "version": ver.version_number if ver else 0,
        "accuracy": ver.validation_accuracy if ver else 0.0,
        "training_samples": ver.training_samples if ver else 0
    }

@app.post("/admin/retrain-agents", dependencies=[Depends(require_admin_secret)])
async def retrain_all_agents(db: Session = Depends(get_db)):
    """
    Triggers a real training run (data curation + train/val split + early
    stopping - see RealDukeMLPipeline.train_model) and returns what actually
    happened, rather than a fire-and-forget "training_triggered" message.
    """
    result = await duke_pipeline.train_model(db)
    return result

@app.post("/admin/clear-cache", dependencies=[Depends(require_admin_secret)])
async def clear_cache(db: Session = Depends(get_db)):
    count = db.query(TrainingData).delete()
    db.commit()
    return {"deleted": count}

# ==================== DATA-DRIVEN PERSONAS (ADMIN) ====================
# CRUD over PersonaConfig (see model + get_safe_persona() above). Lets an
# admin change a persona's behavior, or add an entirely new persona, at
# runtime with no code change or redeploy.

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


@app.get(
    "/admin/personas",
    response_model=List[PersonaConfigResponse],
    tags=["Personas"],
    dependencies=[Depends(require_admin_secret)],
)
async def list_personas(db: Session = Depends(get_db)):
    """List every data-driven persona (live + admin-created), most recently added first."""
    return db.query(PersonaConfig).order_by(PersonaConfig.persona_id).all()


@app.get(
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


@app.post(
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


@app.put(
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


# ==================== BULK TRAINING DATA IMPORT (ADMIN) ====================
# Lets the admin bulk-import curated instruction/output examples (parsed
# client-side from uploaded files/folders) directly into the same
# TrainingData table RealDukeMLPipeline.train_model() already reads from -
# the very next retrain automatically picks them up, with the same quality
# filters (dedup, error markers, min length, low-rated exclusion) applied.

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


@app.post(
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
            desc = (parsed or {}).get("description", "")
            if desc:
                existing_descriptions.add(desc.strip().lower())
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


# ==================== KNOWLEDGE SYSTEM - PHASE 1 (ADMIN) ====================
# Persistent, per-agent (or DUKE-global when persona_id is null) knowledge
# base with real retrieval-augmented generation. Documents are chunked,
# embedded (backend/knowledge.py), and stored as KnowledgeChunk rows; a
# "document" in the admin UI is just every row sharing one source_id.
# retrieve_relevant_chunks() is wired into the live /tasks/submit below.

import knowledge as knowledge_lib

KNOWLEDGE_MAX_TEXT_CHARS = knowledge_lib.MAX_TEXT_CHARS
KNOWLEDGE_MAX_PDF_BYTES = knowledge_lib.MAX_PDF_BYTES


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


def _require_known_persona(persona_id: Optional[str], db: Session):
    if persona_id is None:
        return
    exists = db.query(PersonaConfig).filter(PersonaConfig.persona_id == persona_id).first()
    if not exists:
        raise HTTPException(status_code=404, detail=f"Persona '{persona_id}' not found")


@app.post(
    "/admin/knowledge/upload",
    response_model=KnowledgeUploadResponse,
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def upload_knowledge(payload: KnowledgeUploadRequest, db: Session = Depends(get_db)):
    _require_known_persona(payload.persona_id, db)

    if payload.content_type == "pdf":
        import base64
        try:
            file_bytes = base64.b64decode(payload.file_base64)
        except Exception:
            raise HTTPException(status_code=422, detail="file_base64 is not valid base64")
        if len(file_bytes) > KNOWLEDGE_MAX_PDF_BYTES:
            raise HTTPException(status_code=413, detail=f"PDF exceeds {KNOWLEDGE_MAX_PDF_BYTES // (1024*1024)}MB limit")
        try:
            text = knowledge_lib.extract_pdf_text(file_bytes)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Could not extract text from PDF: {e}")
    else:
        if not payload.text:
            raise HTTPException(status_code=422, detail="text is required for content_type 'text'/'markdown'")
        text = payload.text

    if len(text) > KNOWLEDGE_MAX_TEXT_CHARS:
        raise HTTPException(status_code=413, detail=f"Content exceeds {KNOWLEDGE_MAX_TEXT_CHARS} character limit")

    chunks = knowledge_lib.chunk_text(text)
    if not chunks:
        raise HTTPException(status_code=422, detail="No usable content found after chunking")

    try:
        vectors = knowledge_lib.embed_chunks(chunks)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))

    source_id = str(uuid.uuid4())
    for i, (chunk, vector) in enumerate(zip(chunks, vectors)):
        db.add(
            KnowledgeChunk(
                id=str(uuid.uuid4()),
                source_id=source_id,
                source_name=payload.source_name,
                source_type=payload.content_type,
                persona_id=payload.persona_id,
                chunk_index=i,
                content=chunk,
                content_length=len(chunk),
                embedding=vector,
            )
        )
    db.commit()

    logger.info(f"✅ Knowledge uploaded: '{payload.source_name}' -> {len(chunks)} chunks (persona={payload.persona_id or 'GLOBAL'})")
    return KnowledgeUploadResponse(source_id=source_id, chunks_created=len(chunks), total_characters=len(text))


@app.get(
    "/admin/knowledge",
    response_model=List[KnowledgeSourceSummary],
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def list_knowledge(scope: str, persona_id: Optional[str] = None, db: Session = Depends(get_db)):
    if scope not in ("global", "agent"):
        raise HTTPException(status_code=422, detail="scope must be 'global' or 'agent'")
    if scope == "agent" and not persona_id:
        raise HTTPException(status_code=422, detail="persona_id is required when scope='agent'")

    filter_persona = None if scope == "global" else persona_id
    rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.persona_id == filter_persona)
        .order_by(KnowledgeChunk.source_id, KnowledgeChunk.chunk_index)
        .all()
    )

    sources: dict[str, KnowledgeSourceSummary] = {}
    for row in rows:
        if row.source_id not in sources:
            sources[row.source_id] = KnowledgeSourceSummary(
                source_id=row.source_id,
                source_name=row.source_name,
                source_type=row.source_type,
                persona_id=row.persona_id,
                chunk_count=0,
                created_at=row.created_at,
                preview=row.content[:200],
            )
        sources[row.source_id].chunk_count += 1

    return sorted(sources.values(), key=lambda s: s.created_at, reverse=True)


@app.get(
    "/admin/knowledge/sources/{source_id}/chunks",
    response_model=List[KnowledgeChunkDetail],
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def get_knowledge_source_chunks(source_id: str, db: Session = Depends(get_db)):
    rows = (
        db.query(KnowledgeChunk)
        .filter(KnowledgeChunk.source_id == source_id)
        .order_by(KnowledgeChunk.chunk_index)
        .all()
    )
    if not rows:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return [
        KnowledgeChunkDetail(id=r.id, chunk_index=r.chunk_index, content=r.content, content_length=r.content_length)
        for r in rows
    ]


@app.delete(
    "/admin/knowledge/sources/{source_id}",
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def delete_knowledge_source(source_id: str, db: Session = Depends(get_db)):
    deleted = db.query(KnowledgeChunk).filter(KnowledgeChunk.source_id == source_id).delete()
    db.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Source '{source_id}' not found")
    return {"status": "success", "deleted_chunks": deleted}


@app.delete(
    "/admin/knowledge/chunks/{chunk_id}",
    tags=["Knowledge"],
    dependencies=[Depends(require_admin_secret)],
)
async def delete_knowledge_chunk(chunk_id: str, db: Session = Depends(get_db)):
    row = db.query(KnowledgeChunk).filter(KnowledgeChunk.id == chunk_id).first()
    if not row:
        raise HTTPException(status_code=404, detail=f"Chunk '{chunk_id}' not found")
    db.delete(row)
    db.commit()
    return {"status": "success"}


# ----------------- DASHBOARD -----------------
@app.get("/dashboard")
async def get_dashboard():
    """Redirect to React frontend on port 3000"""
    from fastapi.responses import RedirectResponse
    return RedirectResponse(url="http://localhost:3000/dashboard", status_code=307)

    """
    Serve the new login dashboard with JWT authentication.
    Falls back to a simple version if dashboard-login.html not found.
    """
    from pathlib import Path
    
    # Try to load dashboard-login.html from the same directory as this script
    dashboard_file = Path(__file__).parent / "dashboard-login.html"
    
    if dashboard_file.exists():
        try:
            with open(dashboard_file, 'r', encoding='utf-8') as f:
                html = f.read()
            return HTMLResponse(content=html)
        except Exception as e:
            logger.error(f"Error reading dashboard file: {e}")
            # Fallback to basic dashboard
            return HTMLResponse(content="<h1>Dashboard</h1><p>Error loading dashboard</p>")
    else:
        # File not found - return simple version
        logger.warning(f"dashboard-login.html not found at {dashboard_file}")
        return HTMLResponse(content="""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Duke Dashboard</title>
            <style>
                body { font-family: Arial; background: #0f0f0f; color: white; padding: 40px; text-align: center; }
                h1 { color: #2196F3; }
                p { color: #ccc; }
            </style>
        </head>
        <body>
            <h1>🚀 DukeNET Dashboard</h1>
            <p>⚠️ dashboard-login.html not found</p>
            <p>Expected location: {dashboard_file}</p>
            <p>Copy dashboard-login.html to the backend directory (same as coordinator_api.py)</p>
        </body>
        </html>
        """)

    html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DukeNET Coordinator Dashboard</title>
    <style>
        :root {
            --primary: #2196F3;
            --primary-dark: #1976D2;
            --success: #4CAF50;
            --warning: #FF9800;
            --danger: #F44336;
            --info: #00BCD4;
            --bg-dark: #0f0f0f;
            --bg-card: rgba(255, 255, 255, 0.05);
            --bg-hover: rgba(255, 255, 255, 0.08);
            --text-primary: #ffffff;
            --text-secondary: rgba(255, 255, 255, 0.7);
            --border: rgba(255, 255, 255, 0.1);
            --ease: cubic-bezier(0.16, 1, 0.3, 1);
            --shadow: 0 8px 32px rgba(0, 0, 0, 0.3);
        }

        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%);
            color: var(--text-primary);
            line-height: 1.6;
            min-height: 100vh;
            padding: 20px;
            position: relative;
            overflow-x: hidden;
        }

        body::before {
            content: '';
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: radial-gradient(circle at 20% 50%, rgba(33, 150, 243, 0.1) 0%, transparent 50%),
                        radial-gradient(circle at 80% 80%, rgba(0, 188, 212, 0.1) 0%, transparent 50%);
            pointer-events: none;
            z-index: 0;
        }

        .container {
            max-width: 1400px;
            margin: 0 auto;
            position: relative;
            z-index: 1;
        }

        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 40px;
            padding: 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            backdrop-filter: blur(20px);
            box-shadow: var(--shadow);
            animation: slideDown 0.5s var(--ease);
        }

        /* --- START: Custom Logo Styles --- */
        .header-left h1 {
            font-size: 32px;
            font-weight: 700;
            /* Removed text gradient */
            color: var(--text-primary); /* Ensure text is visible if image fails */
            margin-bottom: 8px;
            display: flex;
            align-items: center;
            gap: 12px;
        }

        .duke-logo {
            height: 40px; /* Adjust size as needed */
            width: auto;
            object-fit: contain;
        }
        /* --- END: Custom Logo Styles --- */

        .header-subtitle {
            font-size: 13px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1.5px;
            font-weight: 500;
        }

        .header-right {
            display: flex;
            gap: 16px;
            align-items: center;
        }

        .refresh-btn {
            display: flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
            cursor: pointer;
            transition: all 0.3s var(--ease);
            font-size: 14px;
            font-weight: 500;
            backdrop-filter: blur(10px);
        }

        .refresh-btn:hover {
            background: var(--bg-hover);
            border-color: var(--primary);
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(33, 150, 243, 0.3);
        }

        .refresh-btn:active {
            transform: translateY(0);
        }

        .refresh-btn.refreshing .refresh-icon {
            animation: spin 0.6s linear;
        }

        .refresh-icon {
            font-size: 16px;
        }

        .refresh-indicator {
            display: flex;
            align-items: center;
            gap: 8px;
            font-size: 12px;
            color: var(--text-secondary);
            padding: 10px 16px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 10px;
            backdrop-filter: blur(10px);
        }

        .status-dot-pulse {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            background: var(--success);
            animation: pulse 2s ease-in-out infinite;
        }

        .status-badge {
            display: inline-flex;
            align-items: center;
            gap: 8px;
            padding: 10px 20px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            font-size: 13px;
            font-weight: 500;
            backdrop-filter: blur(10px);
            transition: all 0.3s var(--ease);
        }

        .status-badge.online {
            border-color: var(--success);
            box-shadow: 0 0 20px rgba(76, 175, 80, 0.2);
        }

        .status-dot {
            width: 8px;
            height: 8px;
            border-radius: 50%;
            animation: pulse 2s ease-in-out infinite;
        }

        .status-dot.online { background: var(--success); }

        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 24px;
            margin-bottom: 40px;
        }

        .metric-card {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 28px;
            backdrop-filter: blur(20px);
            transition: all 0.4s var(--ease);
            cursor: pointer;
            animation: fadeInUp 0.5s var(--ease);
            animation-fill-mode: both;
            box-shadow: var(--shadow);
            position: relative;
            overflow: hidden;
        }

        .metric-card::before {
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 3px;
            background: linear-gradient(90deg, var(--primary), var(--info));
            transform: scaleX(0);
            transform-origin: left;
            transition: transform 0.4s var(--ease);
        }

        .metric-card:hover::before {
            transform: scaleX(1);
        }

        .metric-card:nth-child(1) { animation-delay: 0.1s; }
        .metric-card:nth-child(2) { animation-delay: 0.2s; }
        .metric-card:nth-child(3) { animation-delay: 0.3s; }
        .metric-card:nth-child(4) { animation-delay: 0.4s; }

        .metric-card:hover {
            background: var(--bg-hover);
            border-color: var(--primary);
            transform: translateY(-6px);
            box-shadow: 0 12px 40px rgba(33, 150, 243, 0.3);
        }

        .metric-icon {
            font-size: 32px;
            margin-bottom: 16px;
            display: inline-block;
            transition: transform 0.3s var(--ease);
        }

        .metric-card:hover .metric-icon {
            transform: scale(1.1) rotate(5deg);
        }

        .metric-label {
            font-size: 12px;
            color: var(--text-secondary);
            text-transform: uppercase;
            letter-spacing: 1px;
            margin-bottom: 12px;
            font-weight: 500;
        }

        .metric-value {
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 16px;
            background: linear-gradient(135deg, #fff, var(--primary));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .metric-bar {
            height: 6px;
            background: rgba(255, 255, 255, 0.1);
            border-radius: 3px;
            overflow: hidden;
            margin-top: 12px;
        }

        .metric-fill {
            height: 100%;
            background: linear-gradient(90deg, var(--primary), var(--info));
            border-radius: 3px;
            animation: slideRight 1s var(--ease);
            box-shadow: 0 0 10px rgba(33, 150, 243, 0.5);
        }

        .new-task-section {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 32px;
            margin-bottom: 40px;
            backdrop-filter: blur(20px);
            animation: fadeInUp 0.6s var(--ease);
            box-shadow: var(--shadow);
        }

        .form-grid {
            display: grid;
            grid-template-columns: 200px 1fr 140px 120px;
            gap: 20px;
            align-items: end;
        }

        .form-group {
            position: relative;
        }

        .form-group label {
            display: block;
            color: var(--text-secondary);
            font-size: 12px;
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
            font-weight: 500;
        }

        .form-input, .form-select {
            width: 100%;
            padding: 14px 16px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.3s var(--ease);
            backdrop-filter: blur(10px);
        }

        .form-input:focus, .form-select:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(0, 0, 0, 0.5);
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }

        .complexity-input {
            width: 100%;
            padding: 14px 16px;
            background: rgba(0, 0, 0, 0.3);
            border: 1px solid var(--border);
            border-radius: 10px;
            color: var(--text-primary);
            font-size: 14px;
            transition: all 0.3s var(--ease);
            backdrop-filter: blur(10px);
        }

        .complexity-input:focus {
            outline: none;
            border-color: var(--primary);
            background: rgba(0, 0, 0, 0.5);
            box-shadow: 0 0 0 3px rgba(33, 150, 243, 0.1);
        }

        .section {
            margin-bottom: 40px;
            animation: fadeInUp 0.6s var(--ease);
        }

        .section-header {
            display: flex;
            align-items: center;
            gap: 12px;
            margin-bottom: 24px;
            padding: 20px 24px;
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 12px;
            backdrop-filter: blur(20px);
            box-shadow: var(--shadow);
        }

        .section-icon {
            font-size: 28px;
        }

        .section-title {
            font-size: 20px;
            font-weight: 600;
            flex: 1;
        }

        .table-wrapper {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 16px;
            overflow: hidden;
            backdrop-filter: blur(20px);
            transition: all 0.3s var(--ease);
            box-shadow: var(--shadow);
        }

        table {
            width: 100%;
            border-collapse: collapse;
            font-size: 14px;
        }

        thead {
            background: rgba(33, 150, 243, 0.15);
            border-bottom: 2px solid var(--primary);
        }

        th {
            padding: 18px 20px;
            text-align: left;
            font-weight: 600;
            color: var(--text-primary);
            text-transform: uppercase;
            font-size: 11px;
            letter-spacing: 1px;
        }

        td {
            padding: 18px 20px;
            border-bottom: 1px solid var(--border);
            color: var(--text-secondary);
        }

        tbody tr {
            transition: all 0.3s var(--ease);
            cursor: pointer;
            position: relative;
        }

        tbody tr::before {
            content: '';
            position: absolute;
            left: 0;
            top: 0;
            bottom: 0;
            width: 3px;
            background: var(--primary);
            transform: scaleY(0);
            transition: transform 0.3s var(--ease);
        }

        tbody tr:hover::before {
            transform: scaleY(1);
        }

        tbody tr:hover {
            background: var(--bg-hover);
        }

        tbody tr:last-child td {
            border-bottom: none;
        }

        .status-completed {
            color: var(--success);
            font-weight: 600;
        }

        .status-processing {
            color: var(--warning);
            font-weight: 600;
            animation: pulse 2s ease-in-out infinite;
        }

        .status-failed {
            color: var(--danger);
            font-weight: 600;
        }

        .status-pending {
            color: var(--text-secondary);
        }

        .modal {
            display: none;
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.8);
            backdrop-filter: blur(8px);
            z-index: 1000;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.3s var(--ease);
        }

        .modal.active {
            display: flex;
        }

        .modal-content {
            background: var(--bg-card);
            border: 1px solid var(--border);
            border-radius: 20px;
            padding: 36px;
            max-width: 700px;
            width: 90%;
            max-height: 85vh;
            overflow-y: auto;
            backdrop-filter: blur(20px);
            animation: slideUp 0.4s var(--ease);
            box-shadow: 0 20px 60px rgba(0, 0, 0, 0.5);
        }

        .modal-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 28px;
            padding-bottom: 20px;
            border-bottom: 2px solid var(--primary);
        }

        .modal-title {
            font-size: 24px;
            font-weight: 600;
            background: linear-gradient(135deg, var(--primary), var(--info));
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
            background-clip: text;
        }

        .modal-close {
            background: rgba(255, 255, 255, 0.05);
            border: 1px solid var(--border);
            color: var(--text-secondary);
            font-size: 28px;
            cursor: pointer;
            transition: all 0.3s var(--ease);
            width: 40px;
            height: 40px;
            border-radius: 50%;
            display: flex;
            align-items: center;
            justify-content: center;
        }

        .modal-close:hover {
            color: var(--text-primary);
            background: rgba(255, 255, 255, 0.1);
            transform: rotate(90deg);
        }

        .modal-body {
            margin-bottom: 28px;
        }

        .modal-field {
            margin-bottom: 20px;
        }

        .modal-field-label {
            font-size: 11px;
            color: var(--text-secondary);
            text-transform: uppercase;
            margin-bottom: 10px;
            letter-spacing: 1px;
            font-weight: 600;
        }

        .modal-field-value {
            color: var(--text-primary);
            word-break: break-word;
            padding: 14px 16px;
            background: rgba(255, 255, 255, 0.05);
            border-radius: 10px;
            border: 1px solid var(--border);
            backdrop-filter: blur(10px);
        }

        .modal-footer {
            display: flex;
            gap: 12px;
            justify-content: flex-end;
        }

        button {
            padding: 14px 28px;
            border: none;
            border-radius: 10px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s var(--ease);
            font-size: 14px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .btn-primary {
            background: linear-gradient(135deg, var(--primary), var(--primary-dark));
            color: white;
            box-shadow: 0 4px 15px rgba(33, 150, 243, 0.3);
        }

        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 6px 20px rgba(33, 150, 243, 0.4);
        }

        .btn-primary:active {
            transform: translateY(0);
        }

        .btn-secondary {
            background: var(--bg-hover);
            color: var(--text-primary);
            border: 1px solid var(--border);
        }

        .btn-secondary:hover {
            background: rgba(255, 255, 255, 0.12);
            border-color: var(--primary);
        }

        @keyframes slideDown {
            from { transform: translateY(-20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        @keyframes fadeInUp {
            from { transform: translateY(20px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        @keyframes slideRight {
            from { width: 0; }
            to { width: 100%; }
        }

        @keyframes spin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        @keyframes pulse {
            0%, 100% { opacity: 1; transform: scale(1); }
            50% { opacity: 0.6; transform: scale(0.95); }
        }

        @keyframes fadeIn {
            from { opacity: 0; }
            to { opacity: 1; }
        }

        @keyframes slideUp {
            from { transform: translateY(30px); opacity: 0; }
            to { transform: translateY(0); opacity: 1; }
        }

        ::-webkit-scrollbar {
            width: 10px;
            height: 10px;
        }

        ::-webkit-scrollbar-track {
            background: rgba(255, 255, 255, 0.05);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb {
            background: var(--primary);
            border-radius: 5px;
        }

        ::-webkit-scrollbar-thumb:hover {
            background: var(--primary-dark);
        }

        @media (max-width: 768px) {
            .header {
                flex-direction: column;
                align-items: flex-start;
                gap: 16px;
            }

            .metrics-grid {
                grid-template-columns: 1fr;
            }

            .metric-value {
                font-size: 28px;
            }

            .table-wrapper {
                overflow-x: auto;
            }

            .modal-content {
                padding: 24px;
            }
            
            .form-grid {
                grid-template-columns: 1fr;
                gap: 16px;
            }

            .header-right {
                flex-direction: column;
                width: 100%;
                gap: 12px;
            }

            .refresh-btn, .refresh-indicator, .status-badge {
                width: 100%;
                justify-content: center;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="header-left">
                <h1>
                    <img src="/assets/DUKE.png" alt="DukeNET Logo" class="duke-logo">
                    DukeNET Coordinator
                </h1>
                <div class="header-subtitle">Real-time Dashboard</div>
            </div>
            <div class="header-right">
                <button class="refresh-btn" onclick="manualRefresh()">
                    <span class="refresh-icon">🔄</span>
                    <span>Refresh</span>
                </button>
                <div class="refresh-indicator">
                    <div class="status-dot-pulse"></div>
                    <span id="lastUpdate">Updating...</span>
                </div>
                <div class="status-badge online">
                    <div class="status-dot online"></div>
                    <span>Live</span>
                </div>
            </div>
        </div>

        <div class="metrics-grid">
            <div class="metric-card">
                <div class="metric-icon">📊</div>
                <div class="metric-label">Total Tasks</div>
                <div class="metric-value" id="totalTasks">0</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 100%"></div></div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">✅</div>
                <div class="metric-label">Completed</div>
                <div class="metric-value" id="completedTasks">0</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 80%"></div></div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">🔄</div>
                <div class="metric-label">Processing</div>
                <div class="metric-value" id="processingTasks">0</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 30%"></div></div>
            </div>

            <div class="metric-card">
                <div class="metric-icon">🧠</div>
                <div class="metric-label">Duke ML</div>
                <div class="metric-value" id="dukeAccuracy">--</div>
                <div class="metric-bar"><div class="metric-fill" style="width: 98%"></div></div>
            </div>
        </div>
        
        <div class="section new-task-section">
            <div class="section-header">
                <div class="section-icon">✨</div>
                <div class="section-title">Submit New Task</div>
            </div>
            <form id="newTaskForm" onsubmit="submitTask(event)">
                <div class="form-grid">
                    <div class="form-group">
                        <label>Agent Persona</label>
                        <select id="agentSelect" class="form-select" required>
                            <option value="duke-ml">Duke Core (Generalist)</option>
                            <option value="security-expert">Security Expert</option>
                            <option value="ml-expert">ML Research Scientist</option>
                            <option value="systems-expert">Systems Architect</option>
                            <option value="backend-expert">Senior Backend Engineer</option>
                            <option value="advanced-expert">Visionary Research Engineer</option>
                        </select>
                    </div>
                    <div class="form-group">
                        <label>Task Description</label>
                        <input type="text" id="taskDescription" class="form-input" placeholder="e.g., Audit our AWS IAM policies for privilege escalation risks..." required>
                    </div>
                    <div class="form-group">
                        <label>Complexity (1-10)</label>
                        <input type="number" id="complexityInput" class="complexity-input" min="1" max="10" value="7" required>
                    </div>
                    <div class="form-group">
                        <button type="submit" class="btn-primary" style="width: 100%">
                            <span>Submit</span>
                            <span>→</span>
                        </button>
                    </div>
                </div>
            </form>
        </div>

        <div class="section">
            <div class="section-header">
                <div class="section-icon">🧠</div>
                <div class="section-title">Duke ML Status</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Version</th>
                            <th>Status</th>
                            <th>Accuracy</th>
                            <th>Vocabulary</th>
                            <th>Training Samples</th>
                        </tr>
                    </thead>
                    <tbody id="dukeStatusBody">
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">Loading Duke status...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <div class="section-icon">📋</div>
                <div class="section-title">Recent Tasks</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Task ID</th>
                            <th>Description</th>
                            <th>Complexity</th>
                            <th>Agent</th>
                            <th>Status</th>
                            <th>Price</th>
                        </tr>
                    </thead>
                    <tbody id="tasksBody">
                        <tr>
                            <td colspan="6" style="text-align: center; padding: 40px;">Loading tasks...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>

        <div class="section">
            <div class="section-header">
                <div class="section-icon">📚</div>
                <div class="section-title">Training Data Collection</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Total Calls</th>
                            <th>Successful</th>
                            <th>Failed</th>
                            <th>Training Samples</th>
                            <th>Est. Cost (USD)</th>
                        </tr>
                    </thead>
                    <tbody id="trainingStatsBody">
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">Loading training stats...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>    

        <div class="section">
            <div class="section-header">
                <div class="section-icon">🤖</div>
                <div class="section-title">Agent Performance</div>
            </div>
            <div class="table-wrapper">
                <table>
                    <thead>
                        <tr>
                            <th>Agent</th>
                            <th>Success Rate</th>
                            <th>Reputation</th>
                            <th>Balance (sat)</th>
                            <th>Tasks Completed</th>
                        </tr>
                    </thead>
                    <tbody id="agentsBody">
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px;">Loading agents...</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <div class="modal" id="taskModal">
        <div class="modal-content">
            <div class="modal-header">
                <div class="modal-title">Task Details</div>
                <button class="modal-close" onclick="closeModal()">&times;</button>
            </div>
            <div class="modal-body" id="modalBody"></div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="closeModal()">Close</button>
            </div>
        </div>
    </div>

    <script>
        const REFRESH_INTERVAL = 5000;
        let lastUpdateTime = new Date();

        async function manualRefresh() {
            const btn = document.querySelector('.refresh-btn');
            btn.classList.add('refreshing');
            await refreshData();
            setTimeout(() => btn.classList.remove('refreshing'), 600);
        }

        async function refreshData() {
            try {
                const [tasksRes, agentsRes, modelRes] = await Promise.all([
                    fetch('/tasks').catch(e => ({ ok: false, error: e })),
                    fetch('/agents').catch(e => ({ ok: false, error: e })),
                    fetch('/model/status').catch(e => ({ ok: false, error: e }))
                ]);

                let tasks = [];
                let agents = [];
                let model = null;

                if (tasksRes.ok) {
                    const text = await tasksRes.text();
                    try {
                        tasks = JSON.parse(text);
                    } catch (e) {
                        console.error('Failed to parse tasks:', e, text);
                    }
                }

                if (agentsRes.ok) {
                    const text = await agentsRes.text();
                    try {
                        agents = JSON.parse(text);
                    } catch (e) {
                        console.error('Failed to parse agents:', e, text);
                    }
                }

                if (modelRes.ok) {
                    const text = await modelRes.text();
                    try {
                        model = JSON.parse(text);
                    } catch (e) {
                        console.error('Failed to parse model:', e, text);
                    }
                }

                updateMetrics(tasks, model);
                updateTasksTable(tasks);
                updateAgentsTable(agents);
                updateDukeStatus(model);
                updateLastUpdate();
                await updateTrainingStats();

            } catch (error) {
                console.error('Error refreshing data:', error);
            }
        }
        
        async function submitTask(event) {
            event.preventDefault();
            
            const agent = document.getElementById('agentSelect').value;
            const description = document.getElementById('taskDescription').value;
            const complexity = parseInt(document.getElementById('complexityInput').value);
            const submitBtn = event.target.querySelector('button');
            
            const originalHTML = submitBtn.innerHTML;
            submitBtn.innerHTML = '<span>Submitting...</span>';
            submitBtn.disabled = true;
            
            try {
                const response = await fetch('/tasks/submit', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        description: description,
                        agent: agent,
                        complexity: complexity,
                        buyer_id: "manual-user"
                    })
                });
                
                if (response.ok) {
                    const result = await response.json();
                    
                    document.getElementById('taskDescription').value = '';
                    document.getElementById('complexityInput').value = '7';
                    
                    await refreshData();
                    
                    if (result.id) {
                        showTaskModal(result.id);
                    }
                } else {
                    alert('Failed to submit task. Please check server logs.');
                }
            } catch (error) {
                console.error('Error submitting task:', error);
                alert('Error submitting task');
            } finally {
                submitBtn.innerHTML = originalHTML;
                submitBtn.disabled = false;
            }
        }

        function updateMetrics(tasks, model) {
            const total = tasks.length;
            const completed = tasks.filter(t => t.status === 'completed').length;
            const processing = tasks.filter(t => t.status === 'processing').length;

            document.getElementById('totalTasks').textContent = total;
            document.getElementById('completedTasks').textContent = completed;
            document.getElementById('processingTasks').textContent = processing;

            if (model && model.accuracy) {
                document.getElementById('dukeAccuracy').textContent = 
                    (model.accuracy * 100).toFixed(2) + '%';
            }
        }

        function updateTasksTable(tasks) {
            const tbody = document.getElementById('tasksBody');
            if (tasks.length === 0) {
                tbody.innerHTML = '<tr><td colspan="6" style="text-align: center; padding: 40px;">No tasks yet</td></tr>';
                return;
            }

            const rows = tasks.slice(0, 10).map(task => `
                <tr onclick="showTaskModal('${task.id}')">
                    <td><code style="color: var(--primary);">${task.id.substring(0, 8)}...</code></td>
                    <td>${task.description.substring(0, 50)}...</td>
                    <td>${task.complexity}/10</td>
                    <td>${task.agent_name || 'Unassigned'}</td>
                    <td><span class="status-${task.status}">${task.status.toUpperCase()}</span></td>
                    <td>${(task.price_satoshis / 1000000).toFixed(2)}M</td>
                </tr>
            `).join('');

            tbody.innerHTML = rows;
        }

        function updateAgentsTable(agents) {
            const tbody = document.getElementById('agentsBody');
            if (agents.length === 0) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">No agents found</td></tr>';
                return;
            }

            const rows = agents.map(agent => `
                <tr>
                    <td>${agent.name}</td>
                    <td>${(agent.success_rate * 100).toFixed(1)}%</td>
                    <td>${agent.reputation_multiplier.toFixed(2)}x</td>
                    <td>${(agent.balance_satoshis / 1000000).toFixed(2)}M</td>
                    <td>${agent.total_tasks_completed}</td>
                </tr>
            `).join('');

            tbody.innerHTML = rows;
        }

        function updateDukeStatus(model) {
            const tbody = document.getElementById('dukeStatusBody');
            if (!model) {
                tbody.innerHTML = '<tr><td colspan="5" style="text-align: center; padding: 40px;">Duke not trained yet</td></tr>';
                return;
            }

            const row = `
                <tr>
                    <td><strong>v${model.version}</strong></td>

if __name__ == "__main__":
    import uvicorn
    # Force the server to run on 0.0.0.0:8000 to ensure it's reachable by the frontend
    # and matches the http://localhost:8000/api/auth/login calls.
    uvicorn.run(app, host="0.0.0.0", port=8000)
                    <td><span class="status-completed">✅ READY</span></td>
                    <td><strong>${(model.accuracy * 100).toFixed(2)}%</strong></td>
                    <td>${model.vocabulary_size || 'N/A'}</td>
                    <td>${model.training_samples || 'N/A'}</td>
                </tr>
            `;

            tbody.innerHTML = row;
        }

        function updateLastUpdate() {
            const now = new Date();
            const hours = String(now.getHours()).padStart(2, '0');
            const minutes = String(now.getMinutes()).padStart(2, '0');
            const seconds = String(now.getSeconds()).padStart(2, '0');
            document.getElementById('lastUpdate').textContent = `${hours}:${minutes}:${seconds}`;
        }

        async function updateTrainingStats() {
            try {
                const response = await fetch('/training/stats');
                if (!response.ok) {
                    throw new Error('Failed to fetch training stats');
                }
                const text = await response.text();
                const data = JSON.parse(text);
                const stats = data.data;
                
                const tbody = document.getElementById('trainingStatsBody');
                if (!stats || stats.total_calls === 0) {
                    tbody.innerHTML = `
                        <tr>
                            <td colspan="5" style="text-align: center; padding: 40px; color: var(--text-secondary);">
                                No training data yet. Submit tasks to start collecting data.
                            </td>
                        </tr>
                    `;
                    return;
                }
                
                tbody.innerHTML = `
                    <tr>
                        <td><strong>${stats.total_calls || 0}</strong></td>
                        <td style="color: var(--success);"><strong>${stats.successful_calls || 0}</strong></td>
                        <td style="color: var(--danger);"><strong>${stats.failed_calls || 0}</strong></td>
                        <td style="color: var(--info);"><strong>${stats.training_samples_available || 0}</strong></td>
                        <td style="color: var(--warning);"><strong>${(stats.estimated_cost_usd || 0).toFixed(4)}</strong></td>
                    </tr>
                `;
            } catch (error) {
                console.error('Error fetching training stats:', error);
                const tbody = document.getElementById('trainingStatsBody');
                tbody.innerHTML = `
                    <tr>
                        <td colspan="5" style="text-align: center; padding: 40px; color: var(--danger);">
                            Error loading training stats
                        </td>
                    </tr>
                `;
            }
        }

        function showTaskModal(taskId) {
            fetch(`/tasks/${taskId}`)
                .then(r => {
                    if (!r.ok) throw new Error('Failed to fetch task');
                    return r.text();
                })
                .then(text => {
                    const task = JSON.parse(text);
                    const modal = document.getElementById('taskModal');
                    const body = document.getElementById('modalBody');

                    const processingTime = task.processing_time_seconds 
                        ? task.processing_time_seconds.toFixed(2) 
                        : 'N/A';

                    body.innerHTML = `
                        <div class="modal-field">
                            <div class="modal-field-label">Task ID</div>
                            <div class="modal-field-value"><code>${task.id}</code></div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Description</div>
                            <div class="modal-field-value">${task.description}</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Status</div>
                            <div class="modal-field-value">
                                <span class="status-${task.status}">${task.status.toUpperCase()}</span>
                            </div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Agent</div>
                            <div class="modal-field-value">${task.agent_name || 'Unassigned'}</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Complexity</div>
                            <div class="modal-field-value">${task.complexity}/10</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Price</div>
                            <div class="modal-field-value">${(task.price_satoshis / 1000000).toFixed(2)}M satoshis</div>
                        </div>
                        <div class="modal-field">
                            <div class="modal-field-label">Processing Time</div>
                            <div class="modal-field-value">${processingTime}s</div>
                        </div>
                        ${task.result ? `
                        <div class="modal-field">
                            <div class="modal-field-label">Result</div>
                            <div class="modal-field-value" style="white-space: pre-wrap; font-family: monospace; font-size: 13px;">${task.result}</div>
                        </div>
                        ` : ''}
                        ${task.error_message ? `
                        <div class="modal-field">
                            <div class="modal-field-label">Error</div>
                            <div class="modal-field-value" style="color: var(--danger);">${task.error_message}</div>
                        </div>
                        ` : ''}
                    `;

                    modal.classList.add('active');
                })
                .catch(err => console.error('Error fetching task:', err));
        }

        function closeModal() {
            document.getElementById('taskModal').classList.remove('active');
        }

        document.getElementById('taskModal').addEventListener('click', (e) => {
            if (e.target.id === 'taskModal') closeModal();
        });

        refreshData();
        setInterval(refreshData, REFRESH_INTERVAL);
        setInterval(updateLastUpdate, 1000);
    </script>
</body>
</html>
"""
    return HTMLResponse(content=html)

# NOTE: the old public, unauthenticated "/admin" HTML control panel (plain
# buttons that POSTed straight to /admin/clear-cache and /admin/retrain-agents
# with no auth at all) has been removed. Admin operations now live behind
# the real admin portal at labeele.ai/admin (Supabase-gated) and this API's
# own require_admin_secret dependency - a bare HTML page pointed at this
# backend can no longer trigger anything.

@app.get("/dashboard-login", response_class=HTMLResponse)
async def get_dashboard_login():
    """New dashboard with JWT authentication"""
    import os
    from pathlib import Path
    
    dashboard_file = Path(__file__).parent / "dashboard-login.html"
    
    if dashboard_file.exists():
        with open(dashboard_file, 'r') as f:
            html = f.read()
        return HTMLResponse(content=html)
    else:
        return HTMLResponse(content="<h1>❌ dashboard-login.html not found</h1>")


@app.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: Session = Depends(get_db)):
    task = db.query(Task).filter(Task.id == task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task

# NOTE: a dead duplicate /tasks/submit definition used to live here. FastAPI/
# Starlette match routes in registration order, so it was always shadowed by
# the real, first-registered /tasks/submit above and never actually ran -
# removed as part of wiring real RAG retrieval into the live definition
# (security/correctness audit), rather than maintaining two copies that could
# silently drift apart.

async def call_openai_for_persona(description: str, complexity: int, persona_type: str = "duke-ml", task_id: str = None) -> Optional[str]:
    """Call OpenAI with safe persona lookup."""
    try:
        resolved_type, persona = get_safe_persona(persona_type)
        if not persona:
            return None

        system_prompt = persona.get("system_prompt", "You are a helpful assistant.")
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                OPENAI_API_URL,
                headers={"Authorization": f"Bearer {OPENAI_API_KEY}"},
                json={
                    "model": OPENAI_MODEL,
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": description}
                    ],
                    "max_tokens": 800
                },
                timeout=30.0
            )
            
            if response.status_code == 200:
                data = response.json()
                return data["choices"][0]["message"]["content"]
            else:
                logger.error(f"OpenAI Error: {response.text}")
                return None
    except Exception as e:
        logger.error(f"OpenAI Exception: {e}")
        return None

@app.get("/agents")
async def get_agents(db: Session = Depends(get_db)):
    agents = db.query(Agent).all()
    return agents

@app.get("/model/status")
async def get_model_status(db: Session = Depends(get_db)):
    model_version = db.query(ModelVersionBase).order_by(desc(ModelVersionBase.created_at)).first()
    if not model_version:
        return {"status": "not_initialized", "version": 0}
    return {
        "status": "ready" if model_version.is_production else "training",
        "version": model_version.version_number,
        "accuracy": model_version.validation_accuracy,
        "training_samples": model_version.training_samples
    }

@app.get("/tasks", dependencies=[Depends(require_admin_secret)])
async def get_tasks_with_search(query: Optional[str] = None, limit: int = 100, db: Session = Depends(get_db)):
    try:
        tasks_query = db.query(Task).order_by(desc(Task.created_at))
        if query and query.strip():
            tasks_query = tasks_query.filter(Task.description.ilike(f"%{query}%"))
        tasks = tasks_query.limit(limit).all()
        return [{
            "id": t.id,
            "description": t.description,
            "complexity": t.complexity,
            "agent_name": t.agent_name,
            "status": t.status,
            "result": t.result,
            "price_satoshis": t.price_satoshis
        } for t in tasks]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/training/stats", dependencies=[Depends(require_admin_secret)])
async def get_training_stats_api():
    return {"data": get_training_stats()}

@app.post("/admin/clear-cache", dependencies=[Depends(require_admin_secret)])
async def clear_training_cache(db: Session = Depends(get_db)):
    count = db.query(TrainingData).delete()
    db.commit()
    return {"status": "success", "deleted_entries": count}

@app.post("/admin/retrain-agents", dependencies=[Depends(require_admin_secret)])
async def retrain_all_agents(db: Session = Depends(get_db)):
    try:
        duke_pipeline.model = None
        await duke_pipeline.train_model(db)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/iac/stats", tags=["IAC System"], dependencies=[Depends(require_admin_secret)])
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

@app.post("/iac/test", tags=["IAC System"])
async def test_iac_validation(request: dict):
    prompt = request.get("prompt", "")
    persona = request.get("persona", "security-expert")
    complexity = request.get("complexity", 7)
    
    result = await adversarial_validator.validate_and_refine(prompt, persona, complexity)
    return result

@app.get("/learning/status")
async def get_learning_status(db: Session = Depends(get_db)):
    """
    Unified learning status endpoint for dashboard.
    Combines training stats, model info, and agent data.
    """
    try:
        # Get training stats
        # Note: If using the mocked openai_training_logger, this returns a safe dict
        training_stats = get_training_stats()
        
        # Get latest model version from database
        latest_model = db.query(ModelVersionBase).order_by(
            desc(ModelVersionBase.created_at)
        ).first()
        
        # Get all agent personas
        agents = db.query(Agent).all()
        agent_names = [a.name for a in agents]
        
        # Get memory size from Duke pipeline
        memory_size = 0
        if duke_pipeline.generator and hasattr(duke_pipeline.generator, 'response_database'):
            memory_size = len(duke_pipeline.generator.response_database)
        
        return {
            "status": "trained" if (latest_model and latest_model.is_production) else "training",
            "last_training_time": latest_model.created_at.isoformat() if latest_model else datetime.now(timezone.utc).isoformat(),
            "total_samples_trained": training_stats.get("training_samples_available", 0),
            "memory_size": memory_size,
            "agent_personas": agent_names,
            "model_version": f"v{latest_model.version_number}" if latest_model else "v0.0.0",
            "validation_accuracy": latest_model.validation_accuracy if latest_model else 0.0,
            "estimated_cost_usd": training_stats.get("estimated_cost_usd", 0.0),
            "total_inferences": duke_pipeline.stats.get("total_inferences", 0) if duke_pipeline else 0,
            "recent_loss": duke_pipeline.stats.get("recent_loss", 0.0) if duke_pipeline else 0.0,
        }
    except Exception as e:
        logger.error(f"❌ Learning status error: {e}")
        # Safe fallback so dashboard doesn't crash
        return {
            "status": "error",
            "last_training_time": datetime.now(timezone.utc).isoformat(),
            "total_samples_trained": 0,
            "memory_size": 0,
            "agent_personas": [],
            "model_version": "v0.0.0",
            "validation_accuracy": 0.0,
            "estimated_cost_usd": 0.0,
            "total_inferences": 0,
            "recent_loss": 0.0,
        }

# ==================== HELPER FUNCTIONS FOR NEW ENDPOINTS ====================

async def execute_task(task_description: str):
    """Execute task with default agent"""
    return {
        "response": f"Task processed: {task_description}",
        "confidence": 0.95
    }


async def execute_agent_task(agent_id: str, task: str):
    """Delegate task to appropriate specialist"""
    agents = {
        "security-expert": "🔐 Security analysis: " + task,
        "ml-expert": "🧠 ML perspective: " + task,
        "systems-expert": "⚙️ Systems analysis: " + task,
        "backend-expert": "💻 Backend design: " + task,
        "devops-expert": "🚀 DevOps approach: " + task,
        "vision-expert": "👁️ Visual analysis: " + task,
    }
    
    response = agents.get(agent_id, "Task processed")
    return {
        "agent": agent_id,
        "response": response,
        "confidence": 0.95
    }

# ==================== END HELPER FUNCTIONS ====================
# ==================== MAIN ENTRY POINT ====================

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))

    print("╔════════════════════════════════════════════════════════════════╗")
    print("║  AICP Coordinator + REAL Duke Machine Learning v5.0.0-Phase4 ║")
    print("║        ENTERPRISE DASHBOARD + SPECIALIST PERSONAS             ║")
    print("╚════════════════════════════════════════════════════════════════╝")
    
    if SPECIALIST_PERSONAS:
        for key, value in SPECIALIST_PERSONAS.items():
            print(f"   │ {value.get('name', 'Unknown'):30} ⭐ ({value.get('reputation_multiplier', 1)}x) │")
            
    print(f"\n🚀 Starting server on http://0.0.0.0:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)