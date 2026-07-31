"""
ml/pipeline.py - RealDukeMLPipeline (the real, trainable Duke model wrapper)
and the duke_pipeline singleton used across the app.
"""
import json
import logging
import os
import pickle
import uuid
from pathlib import Path

import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F
from sqlalchemy.orm import Session

from coordinator_API.core.config import DUKE_MODEL_LAST, DUKE_EMBEDDER, DUKE_RESPONSES, FEEDBACK_LOG_FILE
from coordinator_API.models.orm import TrainingData, ModelVersionBase
from coordinator_API.ml.models_nn import EnhancedModelConfig, EnhancedDukeModel, TextEmbedder, ResponseGenerator

logger = logging.getLogger("LabeleeDuke")


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
