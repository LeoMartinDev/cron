#!/usr/bin/env python3
"""
Fine-tune a small language model for cron-expression generation using Unsloth.

Usage:
    python -m cron_finetuning.train
    python -m cron_finetuning.train --base-model unsloth/Qwen2.5-0.5B
    python -m cron_finetuning.train --resume-from-checkpoint output/cron-model/checkpoint-600

Default base model: unsloth/SmolLM2-360M-Instruct (360M params)
Also works with: unsloth/Qwen2.5-0.5B, unsloth/Llama-3.2-1B, unsloth/Qwen2.5-1.5B
"""

from __future__ import annotations

import json
import warnings
from pathlib import Path

# Suppress FutureWarning from transformers' deprecated attention mask API.
# The old API (transformers.modeling_attn_mask_utils.AttentionMaskConverter)
# is deprecated in favor of transformers.masking_utils.
# Unsloth still uses the old API as of v2026.5.4 — this suppresses the noise.
warnings.filterwarnings(
    "ignore",
    message=".*attention mask API.*",
    category=FutureWarning,
)

# Unsloth MUST be imported before torch, transformers, trl, peft
# as it monkey-patches them for QLoRA + fast kernels.
from datasets import Dataset
from trl import SFTConfig
from unsloth import FastLanguageModel, UnslothTrainer, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template, train_on_responses_only

# ============================================================================
# Default configuration
# ============================================================================

CONFIG = {
    "base_model": "unsloth/SmolLM2-360M-Instruct",
    "dtype": None,
    "load_in_4bit": True,
    "lora_rank": 32,
    "lora_alpha": 64,
    "lora_dropout": 0.0,
    "lora_target_modules": [
        "q_proj",
        "k_proj",
        "v_proj",
        "o_proj",
        "gate_proj",
        "up_proj",
        "down_proj",
    ],
    "epochs": 3,  # Unsloth recommends 1-3 epochs for instruction fine-tuning
    "per_device_train_batch_size": 2,
    "gradient_accumulation_steps": 4,
    "learning_rate": 2e-4,
    "optimizer": "adamw_8bit",
    "max_steps": 0,
    "warmup_steps": 5,
    "context_length": 256,
    "lr_scheduler_type": "linear",
    "weight_decay": 0.01,
    "logging_steps": 5,
    "save_steps": 200,
    "eval_steps": 200,
    "report_to": "none",
    "data_dir": "data",
    "output_dir": "output/cron-model",
}


# ============================================================================
# Dataset helpers
# ============================================================================


def load_jsonl(path: str) -> list[dict]:
    """Load a JSONL file into a list of dicts."""
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def format_chatml(examples: list[dict]) -> Dataset:
    """Convert a list of chatml examples to a HuggingFace Dataset."""
    return Dataset.from_list(examples)


# ============================================================================
# Main training function
# ============================================================================


def train(
    data_dir: str | Path = "data",
    output_dir: str | Path = "output/cron-model",
    base_model: str | None = None,
    resume_from_checkpoint: str | None = None,
    push_to_hub: bool = False,
    repo_id: str | None = None,
) -> None:
    """Run the full training pipeline.

    Args:
        data_dir: Directory containing train.jsonl, valid.jsonl, and test.jsonl.
                  Only train.jsonl and valid.jsonl are used for training;
                  test.jsonl is held out for final evaluation via evaluate.py.
        output_dir: Directory to save model checkpoints and final model.
        base_model: HuggingFace base model ID.
        resume_from_checkpoint: Path to a checkpoint to resume from.
        push_to_hub: Whether to push the final model to HuggingFace Hub.
        repo_id: HF Hub model repo ID (required if push_to_hub is True).
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    train_path = Path(data_dir) / "train.jsonl"
    valid_path = Path(data_dir) / "valid.jsonl"
    output_dir = Path(output_dir)

    if not train_path.is_absolute():
        train_path = project_root / train_path
        valid_path = project_root / valid_path
        output_dir = project_root / output_dir

    if base_model is None:
        base_model = CONFIG["base_model"]

    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project root : {project_root}")
    print(f"Train data   : {train_path}")
    print(f"Valid data   : {valid_path}")
    print(f"Output dir   : {output_dir}")
    print(f"Base model   : {base_model}")

    # 1. Load datasets
    print("\nLoading datasets...")
    train_raw = load_jsonl(str(train_path))
    valid_raw = load_jsonl(str(valid_path))
    print(f"  Train examples : {len(train_raw)}")
    print(f"  Valid examples : {len(valid_raw)}")
    train_ds = format_chatml(train_raw)
    valid_ds = format_chatml(valid_raw)

    # 2. Load model & tokeniser
    print("\nLoading model & tokeniser...")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=CONFIG["context_length"],
        dtype=CONFIG["dtype"],
        load_in_4bit=CONFIG["load_in_4bit"],
    )

    # 3. Apply LoRA
    print("\nApplying LoRA adapters...")
    model = FastLanguageModel.get_peft_model(
        model,
        r=CONFIG["lora_rank"],
        lora_alpha=CONFIG["lora_alpha"],
        lora_dropout=CONFIG["lora_dropout"],
        target_modules=CONFIG["lora_target_modules"],
        use_gradient_checkpointing="unsloth",
        random_state=3407,  # Unsloth recommended seed
    )

    # 4. Attach chat template & pre-tokenize
    tokenizer = get_chat_template(
        tokenizer,
        chat_template="chatml",
        mapping={
            "role": "role",
            "content": "content",
            "user": "user",
            "assistant": "assistant",
        },
    )

    # Pre-tokenize datasets here to avoid SFTTrainer's internal
    # multiprocessing-based tokenization (broken on Python 3.13 + dill).
    max_seq_length = CONFIG["context_length"]

    def _tokenize(examples):
        """Apply chat template and tokenize in one pass."""
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)
        tokenized = tokenizer(
            texts,
            truncation=True,
            padding=False,
            max_length=max_seq_length,
        )
        return tokenized

    print("\nTokenizing datasets...")
    train_ds = train_ds.map(_tokenize, batched=True, batch_size=64)
    valid_ds = valid_ds.map(_tokenize, batched=True, batch_size=64)
    print(f"  Train tokens max length: {max(len(ids) for ids in train_ds['input_ids'])}")
    print(f"  Valid tokens max length: {max(len(ids) for ids in valid_ds['input_ids'])}")

    # 5. Training arguments — use SFTConfig from trl (Unsloth recommended)
    bf16 = is_bfloat16_supported()
    training_args = SFTConfig(
        output_dir=str(output_dir),
        num_train_epochs=CONFIG["epochs"],
        per_device_train_batch_size=CONFIG["per_device_train_batch_size"],
        per_device_eval_batch_size=2,
        gradient_accumulation_steps=CONFIG["gradient_accumulation_steps"],
        learning_rate=CONFIG["learning_rate"],
        optim=CONFIG["optimizer"],
        max_steps=CONFIG["max_steps"] if CONFIG["max_steps"] > 0 else -1,
        warmup_steps=CONFIG["warmup_steps"],
        lr_scheduler_type=CONFIG["lr_scheduler_type"],
        weight_decay=CONFIG["weight_decay"],
        logging_steps=CONFIG["logging_steps"],
        save_steps=CONFIG["save_steps"],
        eval_steps=CONFIG["eval_steps"],
        eval_strategy="steps",
        save_strategy="steps",
        load_best_model_at_end=True,
        metric_for_best_model="eval_loss",
        greater_is_better=False,
        bf16=bf16,
        fp16=not bf16,
        bf16_full_eval=bf16,  # Reduce eval memory usage (Unsloth recommended)
        fp16_full_eval=not bf16,
        report_to=CONFIG["report_to"],
        seed=3407,
        run_name="cron-finetune",
    )

    # 6. Trainer — use Unsloth's own trainer which handles the lazy-logits
    #    output from Unsloth's patched forward pass correctly.
    trainer = UnslothTrainer(
        model=model,
        processing_class=tokenizer,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
    )

    # 7. Train on assistant responses only — masks out the user/system
    #    portions so the model focuses on learning to generate correct
    #    cron expressions. This is known to increase accuracy by 1%+.
    trainer = train_on_responses_only(
        trainer,
        instruction_part="<|im_start|>user\n",
        response_part="<|im_start|>assistant\n",
    )

    # 8. Train
    print("\nStarting training...")
    trainer.train(resume_from_checkpoint=resume_from_checkpoint)

    # 9. Save final model
    final_dir = output_dir / "final"
    print(f"\nSaving final model to {final_dir}...")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"Done! Model saved to {final_dir}")

    # 10. Optionally push to HuggingFace Hub
    if push_to_hub:
        if not repo_id:
            raise ValueError("repo_id is required when push_to_hub=True")

        from .dataset import push_model_to_hub

        push_model_to_hub(final_dir, repo_id)


# ============================================================================
# CLI
# ============================================================================


if __name__ == "__main__":
    train()
