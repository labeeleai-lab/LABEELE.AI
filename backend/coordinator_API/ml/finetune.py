"""
ml/finetune.py - real LoRA fine-tuning of DUKE's actual answer-generating
model (ml/duke_brain.py's Qwen2.5-1.5B-Instruct), triggered by
POST /admin/retrain-agents.

Replaces the previous "Retrain agents" behavior (ml/pipeline.py's
RealDukeMLPipeline.train_model()), which trained a completely different
kind of model - a custom embedding-to-embedding regressor with no text
generation head at all - and was proven (live A/B testing, 2026-09) to
have zero effect on DUKE's real answers. This module actually adjusts the
real model's weights using LoRA (via `peft`), the same technique already
used by training/train_duke_offline.py (a separate, manual, GPU-only
script) - far less memory than full fine-tuning, and much lower risk of
catastrophically overwriting the base model's general instruction-
following ability.

Runs on the same curated data as before (error/placeholder responses,
too-short answers, exact duplicates, and anything rated 1-2 stars in
Annotate are excluded), with an 85/15 train/validation split and early
stopping - it just trains a text generator on that data now instead of an
embedding regressor.
"""
import asyncio
import json
import math
import os
import random
import uuid
from datetime import datetime, timezone

import torch
from peft import LoraConfig, get_peft_model
from sqlalchemy import desc
from sqlalchemy.orm import Session

from coordinator_API.core.config import logger, FEEDBACK_LOG_FILE, get_persistent_data_dir
from coordinator_API.core.db import SessionLocal
import coordinator_API.core.state as state
from coordinator_API.models.orm import TrainingData, ModelVersionBase

FINETUNED_MODEL_DIR = get_persistent_data_dir("duke_finetuned_model")

MAX_EPOCHS = 3
PATIENCE = 2
MAX_SEQ_LEN = 512
MAX_TRAIN_EXAMPLES = 300  # bounds worst-case wall-clock time on this CPU-only deployment
LEARNING_RATE = 2e-4  # LoRA adapters need a higher LR than full fine-tuning (same as train_duke_offline.py)

ERROR_MARKERS = ("error:", "not initialized", "completely unavailable", "no response received")

progress = {
    "status": "idle",  # idle | curating | training | saving | complete | skipped | error
    "message": "No training run in progress.",
    "epoch": 0,
    "max_epochs": 0,
    "train_loss": None,
    "val_loss": None,
    "best_val_loss": None,
    "usable_samples": 0,
    "total_samples": 0,
    "history": [],
    "model_version": None,
    "validation_accuracy": None,
    "result": None,  # final run_finetune() return value, set once a background run ends
}


def _load_low_rated_task_ids(min_rating: int = 3) -> set:
    """Same feedback-log read as the old pipeline.py - excludes examples a
    human already flagged as bad in Annotate."""
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
        logger.warning(f"⚠️ Could not read feedback log for fine-tune filter: {e}")
    return low_rated


def _curate_samples(db: Session) -> tuple[list[tuple[str, str]], dict]:
    """Same data-quality filtering as the old pipeline.py's train_model():
    drop error/placeholder responses, too-short responses, and exact-
    duplicate descriptions, plus anything rated 1-2 stars in Annotate."""
    training_data = db.query(TrainingData).all()
    low_rated_ids = _load_low_rated_task_ids()

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

    stats = {
        "total_samples_considered": len(training_data),
        "skipped_error": skipped_error,
        "skipped_short": skipped_short,
        "skipped_duplicate": skipped_duplicate,
        "skipped_low_rated": skipped_low_rated,
    }
    return quality_samples, stats


def _build_labeled_example(tokenizer, instruction: str, output: str):
    """Tokenizes a (instruction, output) pair as a real chat turn and masks
    the loss on the prompt portion (set to -100, which CrossEntropyLoss
    ignores) so the model is only trained to predict the assistant's
    response, not to reproduce the user's question - standard supervised
    fine-tuning practice, and a step up from train_duke_offline.py, which
    only masks padding and lets the loss run over the whole sequence."""
    user_only = [{"role": "user", "content": instruction}]
    prompt_text = tokenizer.apply_chat_template(user_only, tokenize=False, add_generation_prompt=True)
    full_text = tokenizer.apply_chat_template(
        user_only + [{"role": "assistant", "content": output}], tokenize=False, add_generation_prompt=False
    )

    prompt_ids = tokenizer(prompt_text, add_special_tokens=False)["input_ids"]
    full_ids = tokenizer(full_text, add_special_tokens=False)["input_ids"][:MAX_SEQ_LEN]

    labels = list(full_ids)
    mask_len = min(len(prompt_ids), len(full_ids))
    for i in range(mask_len):
        labels[i] = -100

    return full_ids, labels


def _run_epoch(peft_model, tokenizer, examples, optimizer=None) -> float:
    """optimizer=None runs in eval/no-grad mode (validation); otherwise trains.
    Plain blocking code - only ever called from _train_merge_save(), which
    runs in a worker thread."""
    training = optimizer is not None
    peft_model.train() if training else peft_model.eval()

    total_loss, counted = 0.0, 0
    for instruction, output in examples:
        input_ids, labels = _build_labeled_example(tokenizer, instruction, output)
        if all(l == -100 for l in labels):
            continue  # the prompt alone already ate the whole sequence budget

        input_tensor = torch.tensor([input_ids])
        label_tensor = torch.tensor([labels])

        if training:
            optimizer.zero_grad()
            out = peft_model(input_ids=input_tensor, labels=label_tensor)
            if torch.isnan(out.loss):
                continue
            out.loss.backward()
            optimizer.step()
        else:
            with torch.no_grad():
                out = peft_model(input_ids=input_tensor, labels=label_tensor)

        total_loss += out.loss.item()
        counted += 1

    return total_loss / counted if counted else 0.0


def _train_merge_save(brain, train_set, val_set) -> tuple:
    """All of the actual compute: LoRA training, merge, live swap, and save.

    Runs in a worker thread (asyncio.to_thread) - NOT on the event loop.
    Previously this ran inline in the request coroutine, with
    `await asyncio.sleep(0)` between steps; that wasn't enough - every
    forward/backward pass, and especially merge_and_unload() + writing the
    multi-GB checkpoint to the Storage Bucket, blocked the whole server, so
    every other request (/health, /agents, the dashboard's polls) hung until
    the Vercel proxies gave up and returned 502s.

    Holds state.model_lock throughout so no generation runs against the
    model while it's wrapped in LoRA layers / in train mode. Mutating
    `progress` from this thread is fine - the event loop only reads it."""
    with state.model_lock:
        lora_config = LoraConfig(
            r=8,
            lora_alpha=16,
            lora_dropout=0.05,
            bias="none",
            task_type="CAUSAL_LM",
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
        )
        peft_model = get_peft_model(brain.model, lora_config)
        optimizer = torch.optim.AdamW(peft_model.parameters(), lr=LEARNING_RATE)

        best_val_loss = float("inf")
        best_state = None
        patience_counter = 0
        epochs_run = 0

        for epoch in range(MAX_EPOCHS):
            epochs_run = epoch + 1
            random.shuffle(train_set)

            train_loss = _run_epoch(peft_model, brain.tokenizer, train_set, optimizer)
            val_loss = _run_epoch(peft_model, brain.tokenizer, val_set)

            progress["epoch"] = epochs_run
            progress["train_loss"] = train_loss
            progress["val_loss"] = val_loss
            progress["message"] = f"Training epoch {epochs_run} of up to {MAX_EPOCHS}..."

            if val_loss < best_val_loss - 1e-4:
                best_val_loss = val_loss
                best_state = {k: v.clone() for k, v in peft_model.state_dict().items()}
                patience_counter = 0
            else:
                patience_counter += 1

            progress["best_val_loss"] = best_val_loss
            progress["history"].append({"epoch": epochs_run, "train_loss": train_loss, "val_loss": val_loss})

            if patience_counter >= PATIENCE:
                logger.info(f"⏹️ Early stopping at epoch {epochs_run} (no val improvement for {PATIENCE} epochs)")
                progress["message"] = f"Early stopping at epoch {epochs_run} - no improvement for {PATIENCE} epochs."
                break

        if best_state is not None:
            peft_model.load_state_dict(best_state)

        progress["status"] = "saving"
        progress["message"] = "Merging adapter into the base model and saving checkpoint..."

        # Merge the LoRA deltas into the base weights and swap the result
        # into live serving immediately - the next /tasks/submit call uses
        # the newly trained model, no restart required. merge_and_unload()
        # returns a plain model (no PEFT wrapper), so duke_brain.py's
        # generate_response() needs no changes to keep working.
        merged_model = peft_model.merge_and_unload()
        merged_model.eval()
        brain.model = merged_model

        merged_model.save_pretrained(FINETUNED_MODEL_DIR)
        brain.tokenizer.save_pretrained(FINETUNED_MODEL_DIR)

    return epochs_run, best_val_loss


def is_running() -> bool:
    return progress["status"] in ("curating", "training", "saving")


def start_finetune() -> None:
    """Kick off a run in the background and return immediately. The request
    that triggers training can't wait for it: a run takes 10-20+ minutes and
    the admin proxy gives up after 60s. The Training page follows the run
    via GET /admin/training/progress instead, and reads the final outcome
    from progress["result"]."""
    progress.update({
        "status": "curating",
        "message": "Reading training samples and filtering out low-quality data...",
        "result": None,
    })
    asyncio.create_task(_run_finetune_background())


async def _run_finetune_background() -> None:
    db = SessionLocal()
    try:
        result = await run_finetune(db)
        progress["result"] = result
    except Exception as e:
        # run_finetune already recorded status "error" for training failures;
        # this also covers anything that failed before training started.
        logger.error(f"❌ Background fine-tune run failed: {e}")
        progress.update({"status": "error", "message": str(e)})
    finally:
        db.close()


async def run_finetune(db: Session) -> dict:
    brain = state.duke_brain
    if not brain or not brain.model or not brain.tokenizer:
        raise RuntimeError("Duke Brain is not initialized")

    progress.update({
        "status": "curating",
        "message": "Reading training samples and filtering out low-quality data...",
        "epoch": 0,
        "max_epochs": 0,
        "train_loss": None,
        "val_loss": None,
        "best_val_loss": None,
        "history": [],
        "model_version": None,
        "validation_accuracy": None,
    })

    quality_samples, stats = _curate_samples(db)
    # Done with this session - training below runs 10-20+ minutes, and
    # holding a pooled connection idle that long is what let Neon drop it.
    db.close()
    progress["usable_samples"] = len(quality_samples)
    progress["total_samples"] = stats["total_samples_considered"]

    if len(quality_samples) < 10:
        logger.warning(f"⚠️ Not enough quality samples for fine-tuning: {len(quality_samples)} (need 10+)")
        progress.update({
            "status": "skipped",
            "message": f"Skipped - only {len(quality_samples)} usable sample(s) after quality filtering (need 10+).",
        })
        return {
            "status": "skipped",
            "reason": "insufficient_quality_samples",
            "usable_samples": len(quality_samples),
            "total_samples": stats["total_samples_considered"],
        }

    random.shuffle(quality_samples)
    quality_samples = quality_samples[:MAX_TRAIN_EXAMPLES]
    split_idx = max(1, int(len(quality_samples) * 0.85))
    train_set = quality_samples[:split_idx]
    val_set = quality_samples[split_idx:] or quality_samples[-1:]

    progress.update({
        "status": "training",
        "message": f"Training epoch 1 of up to {MAX_EPOCHS}...",
        "max_epochs": MAX_EPOCHS,
    })

    try:
        epochs_run, best_val_loss = await asyncio.to_thread(_train_merge_save, brain, train_set, val_set)

        # An honest "accuracy-like" score derived from real validation loss:
        # e^-loss is the model's average per-token probability on held-out
        # data (loss is mean cross-entropy / negative log-likelihood), not
        # a fabricated number and not classification accuracy - documented
        # as such wherever it's displayed.
        validation_accuracy = math.exp(-best_val_loss) if best_val_loss != float("inf") else None

        logger.info(
            f"✅ DUKE fine-tuned & deployed (LoRA r=8, epochs: {epochs_run}, "
            f"val_loss: {best_val_loss:.4f})"
        )

    except Exception as e:
        # Anything up to here is the actual training compute - a failure
        # means the model was NOT successfully retrained, so this really is
        # an error.
        logger.error(f"❌ DUKE fine-tuning failed: {e}")
        progress.update({"status": "error", "message": str(e)})
        raise

    # The model is already merged, live-swapped into brain.model, and saved
    # to persistent disk at this point - real success, independent of
    # whether recording it in the dashboard's history table below works.
    #
    # Deliberately opens a BRAND NEW session here: pool_pre_ping (core/db.py)
    # only tests a connection when it's checked OUT of the pool, so a
    # session held idle through the whole 10-20+ minute training run never
    # got its stale connection caught. A fresh session gets a
    # freshly-verified connection regardless of how long training took.
    version_number = None
    fresh_db = SessionLocal()
    try:
        latest = fresh_db.query(ModelVersionBase).order_by(desc(ModelVersionBase.version_number)).first()
        version_number = (latest.version_number if latest else 0) + 1

        fresh_db.add(ModelVersionBase(
            id=str(uuid.uuid4()),
            version_number=version_number,
            training_samples=len(quality_samples),
            validation_accuracy=validation_accuracy,
            is_production=True,
            model_info={
                "kind": "lora_finetune",
                "base_model": "Qwen/Qwen2.5-1.5B-Instruct",
                "epochs_run": epochs_run,
                "train_samples": len(train_set),
                "val_samples": len(val_set),
                "best_val_loss": best_val_loss,
                **stats,
            },
        ))
        fresh_db.commit()
    except Exception as e:
        logger.error(f"⚠️ Fine-tune succeeded but recording it to model_versions failed: {e}")
        fresh_db.rollback()
        version_number = None
    finally:
        fresh_db.close()

    progress.update({
        "status": "complete",
        "message": (
            f"Fine-tuning complete - model v{version_number} deployed."
            if version_number is not None
            else "Fine-tuning complete and deployed (history bookkeeping failed to save - see server logs)."
        ),
        "model_version": version_number,
        "validation_accuracy": validation_accuracy,
    })

    return {
        "status": "success",
        "model_version": version_number,
        "epochs_run": epochs_run,
        "train_samples": len(train_set),
        "val_samples": len(val_set),
        "validation_accuracy": validation_accuracy,
        "best_val_loss": best_val_loss,
        **stats,
    }
