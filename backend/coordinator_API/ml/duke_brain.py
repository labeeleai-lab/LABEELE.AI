"""
ml/duke_brain.py - DukeGenerativeBrain (the local, fine-tuned generative
model - no external AI APIs), instantiated by lifespan.py at startup.

Also carries safe_generate() and its module-level Gemini `client`, both
DEAD CODE (safe_generate is never called anywhere in the app) relocated
here as-is per the approved cleanup plan - this is the closest existing
home, immediately adjacent to DukeGenerativeBrain in the original file.

BUG FIX (found during Step 1, fixed here as directed): the original module
level statement was an *unconditional*
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
which raises and crashes import outright whenever GEMINI_API_KEY is unset
or invalid. GEMINI_API_KEY is documented elsewhere in this app as optional
(a non-fatal warning is printed if missing - see core/config.py), so an
unconditional, import-time-fatal client construction here was a real bug,
not intentional fail-closed behavior. It is now wrapped in try/except so a
missing/invalid key leaves `client = None` instead of crashing the whole
app's import. safe_generate() and `client` are otherwise unchanged and
still unused/dead.
"""
import json
import os
import re
from datetime import datetime
from pathlib import Path

import torch
from tenacity import retry, stop_after_attempt, wait_random_exponential
from transformers import AutoTokenizer, AutoModelForCausalLM
from google import genai

from coordinator_API.core.config import APP_DIR

# The SDK automatically checks for os.environ.get("GOOGLE_API_KEY")
# or os.environ.get("GEMINI_API_KEY").
# Initializing without arguments works if the env var is set.
#
# BUG FIX: this used to be unconditional (`client = genai.Client(...)`) and
# crashed import whenever GEMINI_API_KEY was unset/invalid. Guarded so a
# missing/invalid key just leaves client = None (matches how every other
# optional-Gemini-key code path in this app behaves).
try:
    client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
except Exception as e:
    print(f"⚠️ Gemini client (dead safe_generate() path) not initialized: {e}")
    client = None


@retry(
    wait=wait_random_exponential(min=1, max=60),
    stop=stop_after_attempt(5),
    reraise=True  # Recommended so you can see the final error if it fails 5 times
)
def safe_generate(prompt: str):
    """
    Generates content using Gemini 2.0 Flash Lite with exponential backoff.
    DEAD CODE - never called anywhere in the app. Relocated as-is.
    """
    response = client.models.generate_content(
        model='gemini-2.0-flash-lite',
        contents=prompt
    )
    return response.text

# Example usage:
# print(safe_generate("Explain quantum entanglement like I'm five."))


class DukeGenerativeBrain:
    def __init__(self, model_name="distilgpt2"):
        # 1. Hardware Detection
        self.device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"🧠 Initializing Duke's Generative Brain on {self.device}...")

        self.mode = "student"  # Default mode

        # Local-only brain: fine-tuned TinyLlama, no external AI APIs.
        # APP_DIR fix: was os.path.dirname(os.path.abspath(__file__)), which
        # assumed __file__ was coordinator_api.py's own location.
        base_dir = str(APP_DIR)
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
            # APP_DIR fix: was os.path.dirname(os.path.abspath(__file__)).
            base_dir = str(APP_DIR)
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
