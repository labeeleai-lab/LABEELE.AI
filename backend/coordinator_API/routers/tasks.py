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
import re
import os
import time
import uuid
from datetime import datetime, timezone
from typing import Optional

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, Header, HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy import desc, text
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger, APP_DIR, FEEDBACK_LOG_FILE
from coordinator_API.core.db import SessionLocal, get_db
from coordinator_API.core.security import require_admin_secret, verify_token
from coordinator_API.core import math_solver, grounding, web_fetch, document_qa, extractive_qa
import coordinator_API.core.state as state
from coordinator_API.models.orm import Agent, Task, TrainingData, PersonaConfig, KnowledgeChunk
from coordinator_API.models.schemas import TaskCreate, TaskSubmission, TaskResponse, FeedbackSubmission, SimplifyRequest
from coordinator_API.personas.specialists import SPECIALIST_PERSONAS
from coordinator_API.personas.resolver import get_safe_persona
from coordinator_API.ml.matching import MatchingEngine

import knowledge as knowledge_lib

router = APIRouter()


# Generation runs in a worker thread (asyncio.to_thread) - calling the model
# directly inside the async handler froze the whole server for the length of
# every answer, so concurrent /health, /agents and dashboard polls hung until
# the Vercel proxies timed out with 502s. state.model_lock keeps generation
# from running mid fine-tune (ml/finetune.py); returns None if the model stays
# busy past the wait, well inside the /api/duke proxy's 90s timeout.
GENERATION_LOCK_WAIT_SECONDS = 30


def _generate_with_lock(prompt: str, system_prompt: Optional[str] = None, on_text=None,
                        wait_seconds: float = GENERATION_LOCK_WAIT_SECONDS, on_start=None, examples=None):
    """Returns (answer, hit_token_limit), or (None, False) if the model
    stayed busy past the wait. on_start runs once the model is ours."""
    if not state.model_lock.acquire(timeout=wait_seconds):
        return None, False
    try:
        if on_start:
            on_start()
        answer = state.duke_brain.generate_response(prompt, system_prompt=system_prompt, on_text=on_text, examples=examples)
        return answer, bool(getattr(state.duke_brain, "last_hit_token_limit", False))
    finally:
        state.model_lock.release()


BUSY_MESSAGE = ("Error: DUKE is busy right now (most likely a training run is in "
                "progress). Please try again in a few minutes.")
LIMIT_NOTE = ("\n\n*This answer reached DUKE's maximum length and may be incomplete - "
              "ask a narrower follow-up question for the rest.*")


# ---- Streamed answers ----------------------------------------------------
# A complete answer on this CPU deployment can take minutes - longer than a
# single HTTP request can safely stay open behind the Vercel proxy. With
# stream=true, /tasks/submit starts generation in the background and returns
# a job_id immediately; the client polls GET /tasks/jobs/{job_id}, which
# reports the text written so far until the job is done. In-memory is fine:
# one replica, and a job only needs to outlive its own answer.
_JOBS: dict = {}
_JOB_TTL_SECONDS = 30 * 60
# Background jobs aren't bound by an HTTP timeout, so they queue behind
# whatever DUKE is writing instead of failing after 30s. Status is "queued"
# until the model is theirs, then "generating".
JOB_LOCK_WAIT_SECONDS = 10 * 60


def _new_job(**fields) -> str:
    now = time.time()
    for jid in [j for j, v in _JOBS.items() if now - v["created"] > _JOB_TTL_SECONDS]:
        _JOBS.pop(jid, None)
    job_id = str(uuid.uuid4())
    _JOBS[job_id] = {"status": "queued", "text": "", "done": False, "created": now, **fields}
    return job_id


def _record_task(db, task_data, target_agent, final_response, training_response):
    """Persist a finished answer (Task + TrainingData + agent stats).
    Returns (task_id, price). Shared by the synchronous and streamed paths."""
    agent_record = db.query(Agent).filter(Agent.name == target_agent).first()
    reputation = agent_record.reputation_multiplier if agent_record else 1.0
    price = int(task_data.complexity * 1_000_000 * reputation)

    task_id = str(uuid.uuid4())
    db.add(Task(
        id=task_id,
        description=task_data.description,
        agent_name=target_agent,
        status="completed",
        result=final_response,
        complexity=task_data.complexity,
        price_satoshis=price,
        completed_at=datetime.now(timezone.utc),
        buyer_id=task_data.buyer_id or "anon"
    ))
    db.add(TrainingData(
        id=str(uuid.uuid4()),
        task_id=task_id,
        input_data=json.dumps({"description": task_data.description, "complexity": task_data.complexity}),
        output_data=json.dumps({"result": training_response or final_response, "agent": target_agent}),
        success=True,
        agent_name=target_agent,
        persona_type=target_agent
    ))
    if agent_record:
        agent_record.total_tasks_completed += 1
        agent_record.balance_satoshis += price
    db.commit()
    return task_id, price


async def _run_answer_job(job_id, prompt, system_prompt, used_chunks, task_data, target_agent):
    job = _JOBS[job_id]

    def on_text(t):
        job["text"] += t

    def on_start():
        job["status"] = "generating"

    try:
        raw, hit_limit = await asyncio.to_thread(
            _generate_with_lock, prompt, system_prompt, on_text, JOB_LOCK_WAIT_SECONDS, on_start
        )
        training_response = None
        if raw is None:
            final_response, response_source = BUSY_MESSAGE, "unknown"
        else:
            final_response = f"⚡ [DUKE-LOCAL]: {raw}"
            training_response = final_response
            if hit_limit:
                final_response += LIMIT_NOTE
            final_response += _citation_footer(used_chunks)
            response_source = "duke_local"

        # The request's own DB session is long closed by now - use a fresh one
        db = SessionLocal()
        try:
            task_id, price = _record_task(db, task_data, target_agent, final_response, training_response)
        finally:
            db.close()
        job.update(done=True, status="completed", response=final_response,
                   response_source=response_source, request_id=task_id, price_satoshis=price)
    except Exception as e:
        logger.error(f"❌ Streamed answer failed: {e}")
        job.update(done=True, status="error", error="DUKE couldn't finish this answer. Please try again.")


# Plain-language rewrite prompt, tuned against the real model on a real
# long answer: explicit structure rules plus one worked example (unrelated
# topic, so no facts carry over) moved this small model from lightly
# reworded jargon to genuinely everyday language.
SIMPLIFY_SYSTEM = (
    "You explain technical topics to people with no technical background, like a patient teacher "
    "talking to a smart friend who has never worked in technology. You are clear, warm, and accurate, "
    "and you never invent facts."
)
SIMPLIFY_PROMPT = """Rewrite the answer below so that someone with no technical background can fully understand it.

Rules:
- Start with one or two sentences that explain the main idea in everyday words. An everyday comparison is welcome if it truly fits.
- Then list the key points or steps as a bulleted list, one short bullet each, in the same order as the original.
- Every technical term must either be replaced with plain words, or be followed right away by a short plain explanation in parentheses. For example: "validation data (practice questions the model has never seen)".
- Keep every important point from the original. Do not add new facts. Do not mention that this is a rewrite.

Answer to rewrite:
{text}"""
SIMPLIFY_EXAMPLE = (
    SIMPLIFY_PROMPT.format(text=(
        "To reduce latency, deploy a CDN so static assets are cached at edge locations, and enable "
        "HTTP/2 multiplexing so multiple requests share one TCP connection."
    )),
    "Your website feels slow because every file travels a long way to reach each visitor. Two fixes help:\n\n"
    "- **Keep copies close to your visitors.** A content delivery network (a set of servers spread around "
    "the world) stores copies of your images and files near the people using them, so they load faster.\n"
    "- **Send many files through one connection.** A newer web standard (HTTP/2) lets the browser download "
    "many files at once over a single connection, instead of opening a new one for each file.",
)


async def _run_simplify_job(job_id, text):
    job = _JOBS[job_id]

    def on_text(t):
        job["text"] += t

    prompt = SIMPLIFY_PROMPT.format(text=text)

    def on_start():
        job["status"] = "generating"

    try:
        raw, hit_limit = await asyncio.to_thread(
            _generate_with_lock, prompt, SIMPLIFY_SYSTEM, on_text, JOB_LOCK_WAIT_SECONDS, on_start, [SIMPLIFY_EXAMPLE]
        )
        if raw is None:
            job.update(done=True, status="error", error=BUSY_MESSAGE.removeprefix("Error: "))
            return
        job.update(done=True, status="completed", response=raw + (LIMIT_NOTE if hit_limit else ""))
    except Exception as e:
        logger.error(f"❌ Simplify failed: {e}")
        job.update(done=True, status="error", error="DUKE couldn't simplify this answer. Please try again.")


# Total characters of knowledge-base passages placed in front of the model.
# Four ~1,000-1,600 char passages fit; the old flat 6,000-char cap on the
# whole prompt (persona text included) silently chopped the last passage.
MAX_REFERENCE_CHARS = 6000

# Citation tiers, calibrated on the 80-question scorecard (backend/evals,
# after-2026-09-29): BGE similarities are compressed, so irrelevant passages
# still score 0.58-0.67. At >= 0.68 none of the 5 no-answer "honesty"
# questions cite anything while 60/75 book questions keep their sources.
#   >= CITE_MIN_SIMILARITY          -> "Sources:" line
#   between the two                 -> no footer (loosely related material)
#   < NOT_FOUND_BELOW or no passage -> honest "not in my knowledge base" note
CITE_MIN_SIMILARITY = 0.68
NOT_FOUND_BELOW = 0.55

_PART_SUFFIX = re.compile(r"\s*\(part \d+ of \d+\)\s*$", re.IGNORECASE)


def _source_title(source_name: str) -> str:
    """Knowledge-base uploads of long books are split into
    "Title (part 3 of 17)" - users should see just the book's title."""
    return _PART_SUFFIX.sub("", source_name or "").strip()


def _persona_label(persona_id):
    if persona_id is None:
        return "DUKE Global knowledge base"
    return SPECIALIST_PERSONAS.get(persona_id, {}).get("name", persona_id)


def _citation_footer(chunks) -> str:
    """Sources line built by code from what retrieval actually returned -
    never written by the model, so it can't cite a book that wasn't used.
    With no strong match, says so honestly instead."""
    titles = []
    best = max((getattr(c, "similarity", 0.0) for c in chunks), default=0.0)
    for c in chunks:
        if getattr(c, "similarity", 0.0) >= CITE_MIN_SIMILARITY:
            t = _source_title(c.source_name)
            if t and t not in titles:
                titles.append(t)
    if titles:
        return "\n\n📚 Sources: " + "; ".join(titles)
    if best < NOT_FOUND_BELOW:
        return ("\n\nℹ️ I couldn't find this in my knowledge base, so this answer is based on "
                "general knowledge - please double-check anything important.")
    return ""


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
    db: Session = Depends(get_db),
    x_admin_secret: Optional[str] = Header(default=None, alias="X-Admin-Secret"),
):
    """
    Processes a task using the local Duke Brain only - no external AI APIs.
    """
    if task_data.eval_mode:
        require_admin_secret(x_admin_secret)  # raises 403/503 - scorecard mode is admin-only
    retrieved_sources = []
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
        training_response = None
        response_source = "unknown"

        # A. Check Cache first (never in eval mode - a scorecard must measure
        # the current brain, not replay an answer an older model gave)
        try:
            if task_data.eval_mode:
                raise LookupError("cache skipped in eval mode")
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
        except LookupError:
            pass
        except Exception as cache_error:
            # A failed query leaves a Postgres transaction "aborted" until rolled back -
            # every later query on this same session would fail too without this.
            logger.warning(f"⚠️ Cache lookup failed, continuing without it: {cache_error}")
            db.rollback()

        # A2. Deterministic math - the local model has no real arithmetic
        # ability and will confidently guess wrong answers for basic math
        # (proven live: "what's 15% of 240?" -> hallucinated 45 instead of
        # 36). Simple, unambiguous arithmetic questions are solved exactly
        # instead of asking the model to guess.
        if not final_response:
            math_answer = math_solver.try_solve(task_data.description)
            if math_answer:
                final_response = math_answer
                response_source = "math_solver"
                logger.info("🧮 Answered with deterministic math solver")

        # A3. Deterministic date/time/weather - same reasoning as A2: the
        # local model has no clock and no live internet access, so date,
        # time, and weather questions are answered from a real clock/timezone
        # and a live weather API instead of letting the model guess (proven
        # live: it reported raw server UTC as "the current time" for a
        # Lavon, TX question - hours off from actual local time - and
        # silently dropped the weather half of the question entirely).
        if not final_response:
            try:
                grounded_answer = grounding.try_ground(task_data.description)
                if grounded_answer:
                    final_response = grounded_answer
                    response_source = "grounding"
                    logger.info("🌎 Answered with deterministic date/time/weather grounding")
            except Exception as grounding_error:
                logger.warning(f"⚠️ Grounding failed, falling back to the model: {grounding_error}")

        # A4/A5. Attached document / linked web page - answered by finding
        # the actual most-relevant excerpt (see core/extractive_qa.py) and
        # returning it directly, NOT by handing the text to the local model
        # and asking it to summarize/reason over it. Live testing proved
        # that doesn't work with this model: given a one-line test document
        # ("The secret code is 4471") and asked what the code was, it
        # invented an unrelated answer about backend architecture instead of
        # using the text it was given - same result with a real fetched web
        # page and a real multi-sentence document. A hard failure
        # (unreadable file, unsafe or unreachable URL) is reported directly
        # rather than silently continuing without it.
        if not final_response and task_data.attachment_base64 and task_data.attachment_name:
            doc_text, doc_error = document_qa.extract_attachment_text(
                task_data.attachment_base64, task_data.attachment_name
            )
            if doc_error:
                final_response = f"I couldn't use the attached file \"{task_data.attachment_name}\" - {doc_error}."
                response_source = "attachment_error"
            else:
                excerpt = extractive_qa.find_best_excerpt(task_data.description, doc_text)
                final_response = f"From the attached file \"{task_data.attachment_name}\":\n\n{excerpt}"
                response_source = "document_extract"

        if not final_response:
            linked_url = web_fetch.find_url(task_data.description)
            if linked_url:
                page_text, page_error = web_fetch.fetch_page_text(linked_url)
                if page_error:
                    final_response = f"I couldn't read that link - {page_error}."
                    response_source = "web_fetch_error"
                else:
                    excerpt = extractive_qa.find_best_excerpt(task_data.description, page_text)
                    final_response = f"From {linked_url}:\n\n{excerpt}"
                    response_source = "web_fetch_extract"

        # B. Local Duke Brain
        if not final_response:
            logger.info(f"🧠 Asking LOCAL DUKE BRAIN for {target_agent}")
            try:
                # Persona system prompt (DB-backed via get_safe_persona, previously never
                # called here at all) + retrieved knowledge (per-agent + DUKE-global,
                # see backend/knowledge.py) replace the old bare "Persona: X\nTask: Y"
                # string - this is the actual RAG wiring for the knowledge system.
                _, persona = get_safe_persona(target_agent)
                system_prompt = persona["system_prompt"]
                chunks = []

                try:
                    is_duke = target_agent == "duke"
                    chunks = knowledge_lib.retrieve_relevant_chunks(
                        db, KnowledgeChunk, target_agent, task_data.description,
                        top_k=4,
                        cross_agent=is_duke,
                    )
                    retrieved_sources = [
                        {"source": c.source_name, "persona_id": c.persona_id,
                         "similarity": round(getattr(c, "similarity", 0.0), 3)}
                        for c in chunks
                    ]
                except Exception as retrieval_error:
                    logger.warning(f"⚠️ Knowledge retrieval failed, continuing without it: {retrieval_error}")

                # The question goes last and is never the part that gets cut -
                # reference passages are added whole, best match first, only
                # while they fit the budget (a passage chopped mid-sentence
                # is worse than no passage).
                question_block = (
                    f"\n\nQuestion: {task_data.description}\n\n"
                    "Answer the question accurately and completely. When the reference "
                    "material above is relevant, base your answer on it - use its facts "
                    "and terminology directly. If the question asks for specific facts "
                    "that are not in the reference material and that you could not know "
                    "(for example this company's private or internal data, credentials, "
                    "people, or live numbers), say plainly that you don't have that "
                    "information instead of guessing."
                )
                used_chunks, blocks, budget = [], [], MAX_REFERENCE_CHARS
                for c in chunks:
                    label = f"[{_source_title(c.source_name)}]"
                    if target_agent == "duke":
                        label += f" (from the {_persona_label(c.persona_id)})"
                    block = f"{label}\n{c.content}"
                    if len(block) > budget:
                        continue
                    blocks.append(block)
                    used_chunks.append(c)
                    budget -= len(block)
                if blocks:
                    prompt = "Reference material from your knowledge base:\n\n" + "\n\n".join(blocks) + question_block
                else:
                    prompt = question_block.lstrip()

                if state.duke_brain and state.duke_brain.model is not None and task_data.stream and not task_data.eval_mode:
                    job_id = _new_job(agent_name=target_agent, sources=retrieved_sources)
                    asyncio.create_task(_run_answer_job(job_id, prompt, system_prompt, used_chunks, task_data, target_agent))
                    return {
                        "job_id": job_id,
                        "status": "streaming",
                        "agent_name": target_agent,
                        "sources": retrieved_sources,
                        "response_source": "duke_local",
                    }
                if state.duke_brain and state.duke_brain.model is not None:
                    raw_response, hit_limit = await asyncio.to_thread(_generate_with_lock, prompt, system_prompt)
                    if raw_response is None:
                        final_response = BUSY_MESSAGE
                    else:
                        final_response = f"⚡ [DUKE-LOCAL]: {raw_response}"
                        # Training data keeps the model's own words only - the
                        # footer below is added by code, and the model must not
                        # learn to write (and invent) citation lines itself.
                        training_response = final_response
                        if hit_limit:
                            final_response += LIMIT_NOTE
                        final_response += _citation_footer(used_chunks)
                        response_source = "duke_local"
                        logger.info("🧠 Duke processed task successfully on Local/GPU.")
                else:
                    final_response = "Error: Duke Brain is not initialized."
            except Exception as duke_error:
                logger.error(f"❌ Duke Brain failed: {duke_error}")
                final_response = "Error: System completely unavailable."

        if task_data.eval_mode:
            return {
                "response": final_response,
                "response_source": response_source,
                "agent_name": target_agent,
                "sources": retrieved_sources,
                "status": "completed",
            }

        # 3. Save to Database
        task_id, price = _record_task(db, task_data, target_agent, final_response, training_response)

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
            "math_solver": 0.99,
            "grounding": 0.97,
            "gemini_cloud": 0.95,
            "duke_local": 0.75,
            "attachment_error": 0.9,
            "web_fetch_error": 0.9,
            "document_extract": 0.95,
            "web_fetch_extract": 0.95,
            "unknown": 0.5
        }
        confidence_score = confidence_map.get(response_source, 0.5)

        return {
            "response": final_response,
            "confidence": confidence_score,
            "agent_name": target_agent,
            "request_id": task_id,
            "status": "completed",
            "price_satoshis": price,
            "sources": retrieved_sources,
            "response_source": response_source,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"❌ TASK ERROR: {str(e)}")
        # Return a clean JSON error instead of crashing
        return JSONResponse(status_code=500, content={"message": f"Task processing failed: {str(e)}"})


@router.get("/tasks/jobs/{job_id}")
async def get_task_job(job_id: str):
    """Progress of a streamed answer or simplification: text written so far,
    and the final response once done."""
    job = _JOBS.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Unknown or expired job - it may have been lost in a restart.")
    return {k: v for k, v in job.items() if k != "created"}


@router.post("/tasks/simplify")
async def simplify_answer(req: SimplifyRequest):
    """Start a plain-language rewrite of an answer (the dashboard's "Simple
    explanation" toggle). Streamed like answers; never saved as training
    data - it's a presentation of an existing answer, not a new one."""
    if not state.duke_brain or state.duke_brain.model is None:
        raise HTTPException(status_code=503, detail="Duke Brain is not initialized.")
    job_id = _new_job()
    asyncio.create_task(_run_simplify_job(job_id, req.text))
    return {"job_id": job_id, "status": "streaming"}


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
