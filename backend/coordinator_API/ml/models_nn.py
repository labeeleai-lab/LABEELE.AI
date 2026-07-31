"""
ml/models_nn.py - the Duke neural network building blocks: SimpleDukeModel,
ResidualBlock, EnhancedDukeModel, TextEmbedder, ResponseGenerator, and
EnhancedModelConfig.

APP_DIR fix (Finding B in the modularization plan): EnhancedModelConfig used
to compute base_dir via `os.path.dirname(os.path.abspath(__file__))`,
assuming `__file__` was coordinator_api.py's own location. Now that this
class lives in coordinator_API/ml/, that assumption breaks - checkpoint_dir
and weights_dir would silently resolve one level too deep. Rewritten to use
coordinator_API.core.config.APP_DIR instead, which is anchored correctly in
both the local (backend/) and Hugging Face flat-copy (repo root) layouts.
"""
import os
import logging

import numpy as np
import torch
import torch.nn as nn
from datetime import datetime

from coordinator_API.core.config import APP_DIR

logger = logging.getLogger("LabeleeDuke")


class SimpleDukeModel(nn.Module):
    def __init__(self, input_dim=512, hidden_dim=256, output_dim=512):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, output_dim)
        )
    def forward(self, x): return self.network(x)


class ResidualBlock(nn.Module):
    def __init__(self, hidden_dim=512):
        super().__init__()
        self.block = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
        )
    def forward(self, x): return x + self.block(x)

class EnhancedDukeModel(nn.Module):
    """
    Labelee Duke Model V2.0
    Now utilizes EnhancedModelConfig for modular initialization.
    Integrates the CrossModalBridge and TrustScoringHead.
    """
    def __init__(self, config):
        super().__init__()
        self.config = config

        # Perception layers (Input dimensions from config)
        self.input_proj = nn.Linear(config.embed_dim, config.embed_dim)

        # V2.0 Feature: Bi-Directional Cross-Modal Bridge
        # Note: In a full multimodal setup, you'd pass visual and text dims separately.
        # For the coordinator's flattened input, we use the bridge to refine representations.
        self.bridge = nn.MultiheadAttention(config.embed_dim, num_heads=8, batch_first=True)

        self.residual_blocks = nn.Sequential(
            *[ResidualBlock(config.embed_dim) for _ in range(4)]
        )

        # Final Output Projection
        self.output_proj = nn.Sequential(
            nn.Linear(config.embed_dim, config.embed_dim),
            nn.LayerNorm(config.embed_dim),
            nn.ReLU(),
            nn.Linear(config.embed_dim, config.embed_dim)
        )

        # V2.0 Upgrade: LABEELE AI Trust System Head
        if config.use_trust_head:
            self.trust_head = nn.Sequential(
                nn.Linear(config.embed_dim, config.embed_dim // 4),
                nn.ReLU(),
                nn.Linear(config.embed_dim // 4, 1),
                nn.Sigmoid()
            )
            logger.info("🛡️ TrustScoringHead Online for V2.0 Pipeline")

    def forward(self, x):
        # 1. Initial Projection
        x = self.input_proj(x)

        # 2. Refinement via Attention (Self-Attention here as x is fused)
        # Using the bridge logic: x attends to itself to find internal correlations
        attn_out, _ = self.bridge(x, x, x)
        x = x + attn_out

        # 3. Non-linear depth
        x = self.residual_blocks(x)

        # 4. Generate Main Embedding
        embedding = self.output_proj(x)

        # 5. Generate Trust Score (V2.0 Exclusive)
        trust_score = torch.tensor([0.95]) # Default fallback
        if self.config.use_trust_head:
            trust_score = self.trust_head(embedding)

        return embedding, trust_score

class TextEmbedder:
    def __init__(self, embedding_dim=512):
        self.embedding_dim = embedding_dim
        self.vocab = {}
        self.vocab_size = 0

    def build_vocab(self, texts):
        all_words = set()
        for text in texts:
            words = text.lower().split()
            all_words.update(words)
        self.vocab = {word: idx for idx, word in enumerate(sorted(all_words))}
        self.vocab_size = len(self.vocab)
        logger.info(f"📚 Built vocabulary with {self.vocab_size} words")

    def embed(self, text: str):
        words = text.lower().split()
        bow = np.zeros(self.embedding_dim)
        for word in words:
            if word in self.vocab:
                idx = self.vocab[word]
                if idx < self.embedding_dim:
                    bow[idx] = 1
        if bow.sum() > 0: bow = bow / bow.sum()
        if len(bow) < self.embedding_dim: bow = np.pad(bow, (0, self.embedding_dim - len(bow)))
        return bow

class ResponseGenerator:
    def __init__(self):
        self.response_database = []
        self.min_similarity_threshold = 0.3
        self.response_truncation = 1500

    def add_response(self, embedding, response: str, metadata: dict = None):
        if not response or len(response) < 20: return False
        self.response_database.append({
            "embedding": embedding,
            "response": response,
            "metadata": metadata or {},
            "length": len(response),
            "added_at": datetime.now().isoformat(),
        })
        return True

    def generate(self, output_embedding, complexity: int = None, fallback_mode: bool = False):
        if not self.response_database: return self._get_fallback(complexity)

        similarities = []
        for item in self.response_database:
            dot_product = np.dot(output_embedding, item["embedding"])
            norm_product = (np.linalg.norm(output_embedding) * np.linalg.norm(item["embedding"]))
            similarity = dot_product / (norm_product + 1e-8)

            if complexity and "complexity" in item["metadata"]:
                complexity_match = 1 - abs(complexity - item["metadata"]["complexity"]) / 10
                similarity *= (0.7 + 0.3 * complexity_match)

            similarities.append({"score": similarity, "response": item["response"]})

        similarities.sort(key=lambda x: x["score"], reverse=True)
        best_match = similarities[0]

        if best_match["score"] > self.min_similarity_threshold:
            return best_match["response"]
        return self._get_fallback(complexity)

    def _get_fallback(self, complexity: int = None):
        return "Duke ML is continuously learning. Check back soon!"

    def get_stats(self):
        if not self.response_database: return {}
        lengths = [item["length"] for item in self.response_database]
        return {
            "total_responses": len(self.response_database),
            "avg_response_length": int(np.mean(lengths)),
            "max_response_length": max(lengths),
            "min_response_length": min(lengths),
        }

class EnhancedModelConfig:
    """
    Centralized Configuration for Labelee Duke Model V2.0
    Created by Immanuel Olajuyigbe
    """
    def __init__(self):
        # --- Core Architecture ---
        self.model_name = "Labelee Duke Model"
        self.vision_backbone = "vit_base_patch16_224"
        self.text_backbone = "sentence-transformers/all-MiniLM-L6-v2"
        self.embed_dim = 768
        self.latent_dim = 512

        # --- MISSING ATTRIBUTES ADDED HERE ---
        self.use_trust_head = True      # Required for the V2 Trust Scoring logic
        self.dropout_rate = 0.1         # Standard regularization
        self.num_heads = 8              # For cross-modal attention layers
        self.use_bottleneck = True      # For latent space compression

        # --- Training Hyperparameters ---
        self.learning_rate = 1e-4
        self.batch_size = 32
        self.epochs = 20
        self.weight_decay = 0.01
        self.warmup_steps = 500

        # --- LoRA / PEFT Settings ---
        self.use_lora = True
        self.lora_rank = 8
        self.lora_alpha = 16
        self.lora_dropout = 0.05

        # --- Loss Balancing (Multi-Task) ---
        self.recon_weight = 1.0
        self.trust_weight = 0.1
        self.contrastive_weight = 0.5

        # --- Path Configuration ---
        # APP_DIR fix: was os.path.dirname(os.path.abspath(__file__)), which
        # assumed __file__ was coordinator_api.py's own location.
        self.base_dir = str(APP_DIR)
        self.checkpoint_dir = os.path.join(self.base_dir, "duke_checkpoints")
        self.weights_dir = os.path.join(self.base_dir, "labeele_duke", "fine_tuned_weights_v2")

        # Ensure directories exist
        os.makedirs(self.checkpoint_dir, exist_ok=True)
        os.makedirs(self.weights_dir, exist_ok=True)

    def to_dict(self):
        """Export config for logging or serialization"""
        return {k: v for k, v in self.__dict__.items() if not k.startswith('_')}
