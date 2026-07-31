"""
routers/tasks.py - POST /api/tasks, POST /api/agents/{agent_id}/deploy,
POST /tasks/submit, GET /tasks/{task_id}, GET /tasks, POST /feedback/submit.

POST /api/agents/{agent_id}/deploy isn't explicitly assigned to a router in
the modularization plan's file tree; it's placed here (a judgment call) as
the closest thematic and structural match - it's the other legacy-JWT
"deploy work to an agent" endpoint, immediately adjacent to POST /api/tasks
in the original file, sharing the same manual Authorization-header/
verify_token pattern.

Owns its own `import knowledge as knowledge_lib` for retrieve_relevant_chunks()
in submit_task - coordinator_API.routers.admin_knowledge is the "declared
owner" of the knowledge.py import per the plan, but importing an
already-loaded module from a second file is normal and cheap in Python.

Also carries call_gemini_for_persona/call_openai_for_persona/execute_task/
execute_agent_task - four DEAD functions (never called anywhere in the app),
relocated here as-is per the approved cleanup plan (closest thematic home:
persona-driven task response generation).
"""
import asyncio
import json
import os
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger, APP_DIR, FEEDBACK_LOG_FILE
from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret, verify_token
import coordinator_API.core.state as state
from coordinator_API.models.orm import Agent, Task, TrainingData, PersonaConfig, KnowledgeChunk
from coordinator_API.models.schemas import TaskCreate, TaskSubmission, TaskResponse, FeedbackSubmission
from coordinator_API.personas.specialists import SPECIALIST_PERSONAS
from coordinator_API.personas.resolver import get_safe_persona
from coordinator_API.ml.matching import MatchingEngine

import knowledge as knowledge_lib

router = APIRouter()


# ✅ CREATE TASK ENDPOINT (legacy JWT)
@router.post("/api/tasks")
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

# ✅ DEPLOY AGENT ENDPOINT (legacy JWT)
@router.post("/api/agents/{agent_id}/deploy")
async def deploy_agent(agent_id: str, task: TaskCreate, request: Request):
    """Deploy specialist agent - requires JWT token"""
    auth_header = request.headers.get("Authorization")
    if not auth_header or not auth_header.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="No token provided")

    token = auth_header.split(" ")[1]
    username = verify_token(token)
    if not username:
        raise HTTPException(status_code=401, detail="Invalid token")

    state.write_log(f"INFO: Deploying agent '{agent_id}' for user '{username}'")

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

    state.write_log(f"SUCCESS: Agent '{agent_id}' deployed successfully (Task: {task_id})")

    return result


@router.post("/tasks/submit")
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
        else:
            # Caller named a specific agent - it must actually exist (hardcoded
            # persona or an active admin-created one in PersonaConfig), otherwise
            # this silently fell back to a different persona's answer.
            is_known = target_agent in SPECIALIST_PERSONAS
            if not is_known:
                exists_in_db = (
                    db.query(PersonaConfig)
                    .filter(PersonaConfig.persona_id == target_agent, PersonaConfig.is_active == True)
                    .first()
                )
                is_known = exists_in_db is not None
            if not is_known:
                raise HTTPException(status_code=404, detail=f"Unknown agent '{target_agent}'")

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
                    is_duke = target_agent == "duke"
                    chunks = knowledge_lib.retrieve_relevant_chunks(
                        db, KnowledgeChunk, target_agent, task_data.description,
                        # Fewer chunks for DUKE, not more - this small local model has a
                        # strong tendency to paraphrase/echo whatever context it's given
                        # (likely a side effect of the retrieval-alignment training
                        # objective in RealDukeMLPipeline, which rewards output that's
                        # textually close to retrieved chunks) instead of reasoning about
                        # the actual question. Less material means less to latch onto.
                        top_k=4 if is_duke else 4,
                        cross_agent=is_duke,
                    )
                    if chunks:
                        # Plain-text labels, not bracketed markers - this small local model
                        # tends to echo bracket-wrapped headers verbatim (the same failure
                        # mode as the old bracket-template system prompts), so the RAG
                        # context needs the same plain-language treatment.
                        if is_duke:
                            # Cross-agent mode: attribute each chunk to the specialist it
                            # came from so DUKE has real structure to synthesize from,
                            # and the response can honestly reflect which specialists
                            # were actually consulted (not a fabricated summary).
                            def _label(pid):
                                if pid is None:
                                    return "DUKE Global"
                                return SPECIALIST_PERSONAS.get(pid, {}).get("name", pid)
                            context_block = "\n\n".join(
                                f"From the {_label(c.persona_id)}: {c.content}" for c in chunks
                            )
                        else:
                            context_block = "\n\n".join(c.content for c in chunks)
                        prompt += (
                            "\n\nBackground context - use only what is actually relevant to "
                            "the question below, in your own reasoning. Do not quote, list, "
                            f"summarize, or repeat this material or its labels:\n{context_block}"
                        )
                except Exception as retrieval_error:
                    logger.warning(f"⚠️ Knowledge retrieval failed, continuing without it: {retrieval_error}")

                prompt += f"\n\nAnswer this question directly, in your own words: {task_data.description}"
                if len(prompt) > 6000:
                    prompt = prompt[:6000]

                if state.duke_brain and state.duke_brain.model is not None:
                    raw_response = state.duke_brain.generate_response(prompt)
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
                # APP_DIR fix: was os.path.dirname(os.path.abspath(__file__)),
                # which assumed __file__ was coordinator_api.py's own location.
                force_memory_path = os.path.join(str(APP_DIR), "duke_training_memory.json")

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

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ TASK ERROR: {str(e)}")
        # Return a clean JSON error instead of crashing
        return JSONResponse(status_code=500, content={"message": f"Task processing failed: {str(e)}"})


@router.get("/tasks/{task_id}", response_model=TaskResponse)
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

@router.get("/tasks", dependencies=[Depends(require_admin_secret)])
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


@router.post("/feedback/submit", dependencies=[Depends(require_admin_secret)])
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


# ==================== DEAD CODE (relocated as-is) ====================

async def call_gemini_for_persona(description: str, complexity: int, persona_type: str = "duke-ml") -> str:
    """
    Directly calls Gemini 1.5 Flash for specialized persona tasks.
    DEAD CODE - never called anywhere in the app.
    """
    try:
        # 1. Get the Persona System Prompt
        resolved_type, persona = get_safe_persona(persona_type)
        system_instruction = persona.get("system_prompt", "You are a helpful AI assistant.")

        # 2. Prepare the Client
        from google import genai
        from google.genai import types

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


async def call_openai_for_persona(description: str, complexity: int, persona_type: str = "duke-ml", task_id: str = None) -> Optional[str]:
    """Call OpenAI with safe persona lookup. DEAD CODE - never called anywhere
    in the app (also references OPENAI_API_URL/OPENAI_API_KEY/OPENAI_MODEL,
    which are not defined anywhere in this app - relocated exactly as-is,
    not fixed, since it's unreachable)."""
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


async def execute_task(task_description: str):
    """Execute task with default agent. DEAD CODE - never called anywhere in the app."""
    return {
        "response": f"Task processed: {task_description}",
        "confidence": 0.95
    }


async def execute_agent_task(agent_id: str, task: str):
    """Delegate task to appropriate specialist. DEAD CODE - never called anywhere in the app."""
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
