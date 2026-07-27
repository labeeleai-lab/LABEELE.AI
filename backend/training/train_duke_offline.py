import os
import json
import torch
from torch.utils.data import Dataset, DataLoader
from torch.optim import AdamW
from transformers import AutoTokenizer, AutoModelForCausalLM
from peft import LoraConfig, get_peft_model
from tqdm import tqdm

# ================= CONFIGURATION =================
BASE_MODEL_NAME = "TinyLlama/TinyLlama-1.1B-Chat-v1.0"
MEMORY_FILE_PATH = "../duke_training_memory.json"
# Dedicated dir - fine_tuned_weights_v2 holds the unrelated vision-embedding
# model (LabeeleDukeModel), not a causal LM, so it can't be reused here.
OUTPUT_DIR = "../labeele_duke/duke_chat_brain"

# LoRA fine-tuning: the GPU here has 8GB VRAM, not enough for full-parameter
# fp32 fine-tuning of a 1.1B model (weights + gradients + AdamW state would
# need ~17GB). LoRA trains a small adapter on top of a frozen bf16 base
# model instead, which comfortably fits, then we merge it back into a
# normal standalone checkpoint so inference code doesn't need to know
# LoRA was involved.
EPOCHS = 3
BATCH_SIZE = 1
LEARNING_RATE = 2e-4  # LoRA adapters need a higher LR than full fine-tuning

class DukeOfflineDataset(Dataset):
    def __init__(self, file_path, tokenizer):
        self.samples = []
        if not os.path.exists(file_path):
            file_path = os.path.basename(file_path)

        if not os.path.exists(file_path):
            print(f"❌ ERROR: Could not find memory file at {file_path}")
            return

        with open(file_path, 'r', encoding="utf-8") as f:
            data = json.load(f)

        print(f"📂 Loading memories from: {file_path}")
        for entry in data:
            if 'instruction' in entry and 'output' in entry:
                # TinyLlama Chat Format
                full_text = f"<|user|>\n{entry['instruction']}</s>\n<|assistant|>\n{entry['output']}</s>"

                enc = tokenizer(
                    full_text,
                    truncation=True,
                    padding="max_length",
                    max_length=512,
                    return_tensors="pt"
                )
                input_ids = enc.input_ids[0]
                attention_mask = enc.attention_mask[0]

                # Don't train the loss on padding tokens
                labels = input_ids.clone()
                labels[attention_mask == 0] = -100

                self.samples.append((input_ids, attention_mask, labels))

    def __len__(self): return len(self.samples)
    def __getitem__(self, idx): return self.samples[idx]

def train():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"🚀 Initializing Duke Chat Brain fine-tune (TinyLlama + LoRA) on {device}")

    tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
    tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        BASE_MODEL_NAME,
        torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32
    ).to(device)

    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora_config)
    model.print_trainable_parameters()

    dataset = DukeOfflineDataset(MEMORY_FILE_PATH, tokenizer)
    if len(dataset) == 0:
        print("❌ No valid memories found. Training skipped.")
        return

    loader = DataLoader(dataset, batch_size=BATCH_SIZE, shuffle=True)
    optimizer = AdamW(model.parameters(), lr=LEARNING_RATE)

    print("🔥 Starting LoRA Fine-Tuning...")
    model.train()

    for epoch in range(EPOCHS):
        loop = tqdm(loader, desc=f"Epoch {epoch+1}/{EPOCHS}")
        for input_ids, attention_mask, labels in loop:
            input_ids = input_ids.to(device)
            attention_mask = attention_mask.to(device)
            labels = labels.to(device)

            outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
            loss = outputs.loss

            if torch.isnan(loss):
                print("⚠️ Warning: NaN detected, skipping batch.")
                continue

            optimizer.zero_grad()
            loss.backward()
            optimizer.step()

            loop.set_postfix(loss=loss.item())

    print("🔗 Merging LoRA adapter into base model...")
    model = model.merge_and_unload()

    print(f"💾 Saving Duke Chat Brain to {OUTPUT_DIR}...")
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    model.save_pretrained(OUTPUT_DIR)
    tokenizer.save_pretrained(OUTPUT_DIR)
    print("✅ Fine-tune complete.")

if __name__ == "__main__":
    train()
