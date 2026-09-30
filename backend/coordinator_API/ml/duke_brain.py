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
from datetime import datetime
from pathlib import Path

import torch
from tenacity import retry, stop_after_attempt, wait_random_exponential
from transformers import AutoTokenizer, AutoModelForCausalLM, TextStreamer
from google import genai

from coordinator_API.core.config import APP_DIR, get_persistent_data_dir

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


# Upper bound on answer length, in tokens (~1,500 words). Not a style limit:
# the model ends answers on its own long before this - it only exists so a
# degenerate generation loop can't run forever. When it is ever reached,
# last_hit_token_limit is set so callers can say so instead of silently
# presenting a cut-off answer (the old 200/350 caps did exactly that).
MAX_NEW_TOKENS = 2048


class _CallbackStreamer(TextStreamer):
    """Forwards generated text to a callback as it's produced (whole words
    at a time - TextStreamer holds back partial words), so answers can be
    shown while they're still being written."""

    def __init__(self, tokenizer, on_text):
        super().__init__(tokenizer, skip_prompt=True, skip_special_tokens=True)
        self._on_text = on_text

    def on_finalized_text(self, text, stream_end=False):
        if text:
            self._on_text(text)


class DukeGenerativeBrain:
    # Qwen2.5-1.5B-Instruct (2024) replaces TinyLlama-1.1B-Chat (2023) as of
    # this upgrade - live testing throughout this project repeatedly showed
    # TinyLlama ignoring given context and getting basic reasoning wrong
    # (see core/math_solver.py, core/grounding.py, core/extractive_qa.py -
    # all exist specifically because this class's model couldn't be trusted
    # with those tasks). The old duke_chat_brain checkpoint (a fine-tune of
    # TinyLlama's specific architecture) is not compatible with a different
    # base model's weight shapes, so it's retired along with TinyLlama
    # rather than loaded against a mismatched architecture - Qwen runs with
    # its own general instruction-tuning until/unless a new fine-tune is
    # trained on this base model.
    def __init__(self, model_name="Qwen/Qwen2.5-1.5B-Instruct"):
        # 1. Hardware Detection
        self.device = "cuda" if torch.cuda.is_available() else ("mps" if torch.backends.mps.is_available() else "cpu")
        print(f"🧠 Initializing Duke's Generative Brain on {self.device}...")

        self.mode = "student"  # Default mode
        self.model = None
        self.tokenizer = None
        self._initialize_local_model(model_name)

    def _initialize_local_model(self, model_name):
        """Load DUKE's base model, falling back to a tiny emergency model if that fails."""
        # A previous real LoRA fine-tune (see ml/finetune.py, triggered by
        # POST /admin/retrain-agents) saves its merged result here, in the
        # Space's persistent Storage Bucket - load that instead of the
        # stock base model if one exists, so training survives restarts.
        finetuned_dir = get_persistent_data_dir("duke_finetuned_model")
        has_finetuned = os.path.isdir(finetuned_dir) and len(os.listdir(finetuned_dir)) > 0
        load_path = finetuned_dir if has_finetuned else model_name

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
            self.mode = "fine-tuned" if has_finetuned else "instruct"

        except Exception as e:
            print(f"❌ Critical Local Load Error: {e}")
            try:
                print("⚠️ Falling back to distilgpt2 (emergency fallback only)")
                self.tokenizer = AutoTokenizer.from_pretrained("distilgpt2")
                self.model = AutoModelForCausalLM.from_pretrained("distilgpt2").to(self.device)
                self.mode = "student"
            except Exception:
                self.model = None
                self.mode = "unavailable"

    def generate_response(self, prompt, max_length=256, system_prompt=None, on_text=None):
        """on_text: optional callback receiving text as it's generated."""
        self.last_hit_token_limit = False
        if not self.model or not self.tokenizer:
            return "Duke Brain is currently offline or initializing."

        # Date/time (and weather) questions are intercepted before this is
        # ever called - see core/grounding.py, used by routers/tasks.py -
        # so this model is never asked to guess at them.

        try:
            # Ground the model in the real date so date-adjacent answers
            # (e.g. "how many days until...") aren't computed from whatever
            # date happened to show up in training data.
            today_str = datetime.now().strftime('%Y-%m-%d')
            # apply_chat_template() builds whichever special-token format
            # the loaded model actually expects (ChatML for Qwen, ones for
            # other model families) - a hardcoded template string here was
            # TinyLlama-specific and would silently miscommunicate with any
            # other model, degrading answer quality without ever raising an
            # error.
            # The persona's instructions go in the system role (where
            # instruction-tuned models like Qwen expect them to carry the
            # most weight), not mixed into the user turn with the question.
            system_content = f"Today's date is {today_str}."
            if system_prompt:
                system_content = f"{system_prompt}\n\n{system_content}"
            messages = [
                {"role": "system", "content": system_content},
                {"role": "user", "content": prompt},
            ]
            try:
                chat_prompt = self.tokenizer.apply_chat_template(
                    messages, tokenize=False, add_generation_prompt=True
                )
            except Exception:
                # Emergency-fallback models (distilgpt2) have no chat
                # template at all - plain concatenation is the best this
                # non-instruct model could use anyway.
                chat_prompt = f"{system_content}\n{prompt}\n"
            inputs = self.tokenizer(chat_prompt, return_tensors="pt", add_special_tokens=False).to(self.device)

            with torch.no_grad():
                outputs = self.model.generate(
                    inputs["input_ids"],
                    attention_mask=inputs["attention_mask"],
                    # See MAX_NEW_TOKENS - a safety ceiling, not a length
                    # limit (350 still cut real answers off mid-list).
                    max_new_tokens=MAX_NEW_TOKENS,
                    streamer=_CallbackStreamer(self.tokenizer, on_text) if on_text else None,
                    # Greedy decoding: factual Q&A wants the model's most
                    # likely answer, not a random sample (the old
                    # temperature=0.7 sampling added creative drift).
                    do_sample=False,
                    # Mild penalty only. The old 1.3 + no_repeat_ngram_size=4
                    # forbade repeating any 4-word phrase, so the model was
                    # forced into odd synonyms for terms it legitimately
                    # needed twice ("public key", "training data") - the
                    # source of its stilted, run-on wording.
                    repetition_penalty=1.1,
                    pad_token_id=self.tokenizer.eos_token_id
                )

            # Only decode the newly generated tokens, not the echoed prompt
            new_tokens = outputs[0][inputs["input_ids"].shape[1]:]
            self.last_hit_token_limit = len(new_tokens) >= MAX_NEW_TOKENS
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
