import os
import difflib
import logging
import ast
import re
import torch
from pathlib import Path
from typing import List, Dict, Any, Optional

# Standard Labelee Logging
logger = logging.getLogger("duke_toolkit")

class TaskRouter:
    """Specialist Persona: Routes complex tasks to the correct Duke Sub-module."""
    def __init__(self):
        self.routes = {
            "security": "Principal Security Architect",
            "ml": "Senior ML Research Scientist",
            "cloud": "Distinguished Cloud Architect",
            "code": "Staff Software Engineer",
            "vision": "Computer Vision Specialist"
        }

    def route_task(self, description: str) -> str:
        desc = description.lower()
        for key, persona in self.routes.items():
            if key in desc:
                return persona
        return "Emerging Technology Strategist"

class CodeReader:
    """Staff Software Engineer Tool: Advanced file system traversal and source extraction."""
    def __init__(self, base_path: str = "."):
        self.base_path = Path(base_path)

    def read_file(self, file_path: str) -> str:
        """Reads a file safely with encoding fallback."""
        full_path = self.base_path / file_path
        if not full_path.exists():
            return f"❌ Error: File {file_path} does not exist."
        
        try:
            return full_path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            return full_path.read_text(encoding='latin-1')
        except Exception as e:
            return f"❌ Critical Read Error: {str(e)}"

    def list_structure(self, dir_path: str = ".") -> List[str]:
        """Maps directory structure for AI context."""
        try:
            return [str(p.relative_to(self.base_path)) for p in Path(dir_path).rglob('*') 
                    if "__pycache__" not in str(p) and ".git" not in str(p)]
        except Exception as e:
            return [f"Error mapping directory: {e}"]

class DiffGenerator:
    """Backend Engineer Tool: Generates Git-style diffs for code updates."""
    def generate_diff(self, old_code: str, new_code: str, filename: str = "duke_update.py") -> str:
        if old_code == new_code:
            return "✅ No changes detected."
            
        old_lines = old_code.splitlines(keepends=True)
        new_lines = new_code.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            old_lines, new_lines, 
            fromfile=f"a/{filename}", 
            tofile=f"b/{filename}"
        )
        return "".join(diff)

class SecurityScanner:
    """Principal Security Architect Tool: Static Application Security Testing (SAST)."""
    def __init__(self):
        # Comprehensive pattern list from the original script
        self.forbidden_patterns = {
            r"eval\(": "High: Dynamic code execution (eval)",
            r"exec\(": "High: Dynamic code execution (exec)",
            r"subprocess\.Popen\(.*shell=True\)": "Critical: Shell injection risk",
            r"os\.system\(": "High: Command injection risk",
            r"yaml\.load\(": "Medium: Unsafe YAML loading",
        }

    def scan_source(self, code: str) -> Dict[str, Any]:
        """Scans code using regex and AST parsing for vulnerabilities."""
        findings = []
        lines = code.splitlines()
        
        # Regex Scan
        for pattern, risk in self.forbidden_patterns.items():
            for i, line in enumerate(lines):
                if re.search(pattern, line):
                    findings.append({"line": i+1, "issue": risk, "content": line.strip()})
        
        # AST Scan for hardcoded secrets (Enhanced Logic)
        try:
            tree = ast.parse(code)
            for node in ast.walk(tree):
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        # Check for sensitive variable names
                        if isinstance(target, ast.Name) and any(x in target.id.lower() for x in ['key', 'secret', 'token', 'password']):
                            # Look for string constants longer than 8 chars
                            if isinstance(node.value, (ast.Constant, ast.Str)):
                                val = getattr(node.value, 'value', getattr(node.value, 's', ""))
                                if isinstance(val, str) and len(val) > 8:
                                    findings.append({
                                        "line": node.lineno, 
                                        "issue": "Warning: Hardcoded secret suspect", 
                                        "content": target.id
                                    })
        except SyntaxError:
            return {"status": "error", "message": "Syntax error in code; scan incomplete."}

        return {"status": "complete", "threat_count": len(findings), "findings": findings}

class MLToolbox:
    """Senior ML Research Scientist: Model weight and tensor analysis."""
    def __init__(self):
        # Optimized Device Detection (MPS for your Mac, CUDA for servers, CPU fallback)
        if torch.backends.mps.is_available():
            self.device = "mps"
        elif torch.cuda.is_available():
            self.device = "cuda"
        else:
            self.device = "cpu"

    def inspect_weights(self, weights_path: str) -> Dict[str, Any]:
        """Analyzes weight distribution for Labelee Duke Model layers."""
        try:
            # Map location ensures loading works across different hardware setups
            data = torch.load(weights_path, map_location=self.device)
            summary = {}
            for k, v in data.items():
                if hasattr(v, 'shape'):
                    summary[k] = {
                        "shape": list(v.shape),
                        "mean": float(v.mean()) if v.is_floating_point() else "N/A",
                        "std": float(v.std()) if v.is_floating_point() else "N/A"
                    }
            return summary
        except Exception as e:
            return {"error": str(e)}

class CloudArchitectTool:
    """Distinguished Cloud Architect: Infrastructure and environment validation."""
    def validate_env(self) -> Dict[str, str]:
        # Full validation suite including JWT_SECRET from your original script
        results = {
            "DATABASE_URL": "✅ Configured" if os.getenv("DATABASE_URL") else "❌ Missing",
            "GEMINI_API_KEY": "✅ Configured" if os.getenv("GEMINI_API_KEY") else "❌ Missing",
            "JWT_SECRET": "✅ Configured" if os.getenv("JWT_SECRET") else "⚠️ Missing",
            "MPS_AVAILABLE": "✅ Yes" if torch.backends.mps.is_available() else "⚠️ No"
        }
        return results

# --- Unified Toolkit Export ---
# Mapped to match specialist personas in coordinator_api.py
agency_tools = {
    "TaskRouter": TaskRouter(),
    "CodeReader": CodeReader(),
    "DiffGenerator": DiffGenerator(),
    "SecurityScanner": SecurityScanner(),
    "MLToolbox": MLToolbox(),
    "CloudArchitectTool": CloudArchitectTool()
}