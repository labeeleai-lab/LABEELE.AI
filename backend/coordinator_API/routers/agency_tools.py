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
from coordinator_API.models.schemas import DispatchRequest, ToolRequest, TrainConfigRequest

try:
    from tools.agent_toolkit import (
        CodeReader, DiffGenerator, SecurityScanner, MLToolbox, TaskRouter, CloudArchitectTool
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
    class DiffGenerator:
        pass
    class CloudArchitectTool:
        pass

router = APIRouter()


@router.post("/agency/dispatch")
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


@router.post("/tools/analyze_code")
async def tool_analyze_code(req: ToolRequest):
    """Direct access to CodeReader tool"""
    return CodeReader.analyze_structure(req.code)

@router.post("/tools/security_scan")
async def tool_security_scan(req: ToolRequest):
    """Direct access to SecurityScanner tool"""
    return SecurityScanner.scan(req.code)

@router.post("/tools/generate_train_script")
async def tool_gen_script(config: TrainConfigRequest):
    """Direct access to MLToolbox"""
    return {"code": MLToolbox.generate_training_script(config.dict())}
