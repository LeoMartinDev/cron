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

import argparse
import json
from pathlib import Path

# Unsloth MUST be imported before torch, transformers, trl, peft
# as it monkey-patches them for QLoRA + fast kernels.
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template

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
    "epochs": 15,
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
    hub_repo_id: str | None = None,
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
        hub_repo_id: HF Hub model repo ID (required if push_to_hub is True).
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
        random_state=42,
    )

    # 4. Attach chat template
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

    def apply_chat_template(examples):
        texts = []
        for messages in examples["messages"]:
            text = tokenizer.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=False
            )
            texts.append(text)
        return {"text": texts}

    train_ds = train_ds.map(apply_chat_template, batched=True)
    valid_ds = valid_ds.map(apply_chat_template, batched=True)

    # 5. Training arguments
    training_args = TrainingArguments(
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
        bf16=is_bfloat16_supported(),
        fp16=not is_bfloat16_supported(),
        report_to=CONFIG["report_to"],
        seed=42,
        run_name="cron-finetune",
    )

    # 6. Trainer
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        args=training_args,
        train_dataset=train_ds,
        eval_dataset=valid_ds,
        dataset_text_field="text",
        max_seq_length=CONFIG["context_length"],
        packing=False,
    )

    # 7. Train
    print("\nStarting training...")
    trainer.train(resume_from_checkpoint=resume_from_checkpoint)

    # 8. Save final model
    final_dir = output_dir / "final"
    print(f"\nSaving final model to {final_dir}...")
    model.save_pretrained(str(final_dir))
    tokenizer.save_pretrained(str(final_dir))
    print(f"Done! Model saved to {final_dir}")

    # 9. Optionally push to HuggingFace Hub
    if push_to_hub:
        if not hub_repo_id:
            raise ValueError("hub_repo_id is required when push_to_hub=True")

        from .dataset import push_model_to_hub

        push_model_to_hub(final_dir, hub_repo_id)


# ============================================================================
# CLI
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Fine-tune cron model with Unsloth")
    parser.add_argument(
        "--base-model",
        default=CONFIG["base_model"],
        help="HuggingFace base model ID",
    )
    parser.add_argument(
        "--resume-from-checkpoint",
        default=None,
        help="Path to a checkpoint to resume from",
    )
    parser.add_argument(
        "--output-dir",
        default=CONFIG["output_dir"],
        help="Directory to save model outputs",
    )
    parser.add_argument(
        "--data-dir",
        default=CONFIG["data_dir"],
        help="Directory containing train.jsonl, valid.jsonl, and test.jsonl (test is ignored during training)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the final model to HuggingFace Hub",
    )
    parser.add_argument(
        "--hub-repo-id",
        default=None,
        help="HuggingFace Hub model repo ID (e.g. 'username/cron-model')",
    )
    args = parser.parse_args()

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        base_model=args.base_model,
        resume_from_checkpoint=args.resume_from_checkpoint,
        push_to_hub=args.push,
        hub_repo_id=args.hub_repo_id,
    )


if __name__ == "__main__":
    main()
