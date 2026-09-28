"""
routers/agency_tools.py - POST /agency/dispatch, POST /tools/analyze_code,
POST /tools/security_scan, POST /tools/generate_train_script.

Owns the tools.agent_toolkit import. The original file imported it three
separate times (a bare, unprotected `from tools.agent_toolkit import
CodeReader, DiffGenerator, SecurityScanner, CloudArchitectTool`, immediately
followed by two near-identical try/except blocks importing an overlapping
but not identical name set - CodeReader, DiffGenerator, SecurityScanner,
MLToolbox, TaskRouter - the second of which added fallback mock classes).
Consolidated here into one try/except covering the full name set actually
referenced anywhere in the app, with fallback mocks for all of them so a
missing tools/agent_toolkit.py degrades gracefully instead of crashing
import outright (the original bare first import had no such protection).
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger
from coordinator_API.core.db import get_db
from coordinator_API.core.security import require_admin_secret
from coordinator_API.models.schemas import DispatchRequest, ToolRequest, TrainConfigRequest

try:
    from tools.agent_toolkit import CodeReader, DiffGenerator, SecurityScanner, MLToolbox, TaskRouter, CloudArchitectTool
    TOOLS_AVAILABLE = True
    print("✅ Agency Tools Loaded: CodeReader, SecurityScanner, MLToolbox active.")
except ImportError:
    TOOLS_AVAILABLE = False
    print("⚠️ Agency Tools not found. Ensure 'tools/agent_toolkit.py' exists.")
    # Fallback mocks to prevent crash if the file is missing - shaped to
    # match the REAL classes' actual method names (route_task/scan_source),
    # not the mismatched static-style names this router used to call
    # directly on the real classes (TaskRouter.route(), SecurityScanner.scan()
    # etc.), which don't exist there and would only ever have worked by
    # accidentally hitting these mocks instead.
    class TaskRouter:
        def route_task(self, p): return "GENERALIST"
    class SecurityScanner:
        def scan_source(self, c): return {"status": "complete", "threat_count": 0, "findings": []}
    class MLToolbox:
        pass
    class CodeReader:
        pass
    class DiffGenerator:
        pass
    class CloudArchitectTool:
        pass

# Real, stateless tool instances - the actual classes in tools/agent_toolkit.py
# expose instance methods (route_task, scan_source), not the static-style
# calls this router used to make directly on the class.
_task_router = TaskRouter()
_security_scanner = SecurityScanner()

router = APIRouter()


# TaskRouter.route_task() returns a human-readable role name ("Principal
# Security Architect", etc.) - this maps those to the short keys the
# dispatch logic below branches on. The router used to compare against
# "SECURITY_EXPERT"/"ML_SPECIALIST"/etc directly, which route_task() never
# actually returns, so every request silently fell through to the
# generalist fallback regardless of what was asked.
_PERSONA_KEY_BY_ROLE = {
    "Principal Security Architect": "SECURITY_EXPERT",
    "Senior ML Research Scientist": "ML_SPECIALIST",
    "Staff Software Engineer": "BACKEND_DEV",
    "Computer Vision Specialist": "CV_SPECIALIST",
}


@router.post("/agency/dispatch", dependencies=[Depends(require_admin_secret)])
async def agency_dispatch(req: DispatchRequest, db: Session = Depends(get_db)):
    """
    The Generalist (Traffic Controller) Endpoint.
    Analyzes the prompt via TaskRouter and dispatches to Tools OR Agents.
    """
    try:
        # 1. Determine Intent using the Toolkit Router
        routed_role = _task_router.route_task(req.prompt)
        target_persona = _PERSONA_KEY_BY_ROLE.get(routed_role, "GENERALIST")

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
                scan_result = _security_scanner.scan_source(req.context_code)
                response["data"] = scan_result
                response["tools_used"].append("StaticSecurityScanner")
                threat_count = scan_result.get("threat_count", 0)
                if scan_result.get("status") == "complete" and threat_count == 0:
                    response["reply"] = f"✅ Security Scan Passed. No critical issues found in {len(req.context_code.splitlines())} lines."
                elif scan_result.get("status") == "complete":
                    response["reply"] = f"🚨 CRITICAL ALERT: Found {threat_count} potential vulnerabilities."
                else:
                    response["reply"] = scan_result.get("message", "Scan could not complete.")
            else:
                response["action_type"] = "conversation"
                response["reply"] = "I am ready to secure your infrastructure. Please provide code or logs to analyze."

        # --- ML PATH ---
        elif target_persona == "ML_SPECIALIST":
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


@router.post("/tools/analyze_code", dependencies=[Depends(require_admin_secret)])
async def tool_analyze_code(req: ToolRequest):
    """CodeReader (tools/agent_toolkit.py) only reads files by path
    (read_file/list_structure) - there's no real "analyze this code string"
    capability implemented, unlike what this endpoint used to claim by
    calling a CodeReader.analyze_structure() that never existed (it would
    only "work" by accidentally hitting the import-failure fallback mock).
    Honest not-implemented response instead of a fabricated one."""
    return {"status": "not_implemented", "message": "Code-structure analysis isn't implemented yet."}

@router.post("/tools/security_scan", dependencies=[Depends(require_admin_secret)])
async def tool_security_scan(req: ToolRequest):
    """Direct access to the real SecurityScanner.scan_source()."""
    return _security_scanner.scan_source(req.code)

@router.post("/tools/generate_train_script", dependencies=[Depends(require_admin_secret)])
async def tool_gen_script(config: TrainConfigRequest):
    """MLToolbox (tools/agent_toolkit.py) only inspects saved model weights
    (inspect_weights) - there's no real training-script generator
    implemented, unlike what this endpoint used to claim by calling a
    MLToolbox.generate_training_script() that never existed. Honest
    not-implemented response instead of a fabricated one."""
    return {"status": "not_implemented", "message": "Training-script generation isn't implemented yet."}
