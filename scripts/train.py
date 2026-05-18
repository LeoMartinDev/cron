#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "unsloth>=2024.12",
#     "transformers>=4.46",
#     "datasets>=3.0",
#     "accelerate>=1.0",
#     "bitsandbytes>=0.44",
#     "trl>=0.12",
# ]
# ///
"""
Fine-tune a small language model for cron-expression generation using Unsloth.

Usage:
    uv run scripts/train.py [--base-model MODEL] [--resume-from-checkpoint PATH]

Default base model: unsloth/SmolLM2-360M-Instruct (360M params)
Also works with: unsloth/Qwen2.5-0.5B, unsloth/Llama-3.2-1B, unsloth/Qwen2.5-1.5B
"""

# Unsloth MUST be imported before torch, transformers, trl, peft, etc.
# It monkey-patches them for QLoRA + fast kernels.
import argparse
import json
import os
from pathlib import Path

import torch
from datasets import Dataset
from transformers import TrainingArguments
from trl import SFTTrainer
from unsloth import FastLanguageModel, is_bfloat16_supported
from unsloth.chat_templates import get_chat_template

# ============================================================================
# Configuration
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
    examples = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def format_chatml(examples: list[dict]) -> Dataset:
    return Dataset.from_list(examples)


# ============================================================================
# Training
# ============================================================================


def main():
    parser = argparse.ArgumentParser(description="Fine-tune cron model with Unsloth")
    parser.add_argument("--base-model", default=CONFIG["base_model"])
    parser.add_argument("--resume-from-checkpoint", default=None)
    parser.add_argument("--output-dir", default=CONFIG["output_dir"])
    args = parser.parse_args()

    project_root = Path(__file__).resolve().parent.parent
    train_path = project_root / CONFIG["data_dir"] / "train.jsonl"
    valid_path = project_root / CONFIG["data_dir"] / "valid.jsonl"
    output_dir = project_root / args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"Project root : {project_root}")
    print(f"Train data   : {train_path}")
    print(f"Valid data   : {valid_path}")
    print(f"Output dir   : {output_dir}")
    print(f"Base model   : {args.base_model}")

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
        model_name=args.base_model,
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
    trainer.train(resume_from_checkpoint=args.resume_from_checkpoint)

    # 8. Save
    print("\nSaving final model...")
    model.save_pretrained(str(output_dir / "final"))
    tokenizer.save_pretrained(str(output_dir / "final"))
    print(f"\nDone! Model saved to {output_dir}")


if __name__ == "__main__":
    main()
