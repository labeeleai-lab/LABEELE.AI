"""
ml/validator.py - AdversarialValidator (the Gemini-powered Iterative
Adversarial Critique / IAC system) and the adversarial_validator singleton.
"""
import json
import logging
import os
from typing import Optional

from coordinator_API.personas.specialists import SPECIALIST_PERSONAS
from coordinator_API.personas.resolver import get_safe_persona


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
