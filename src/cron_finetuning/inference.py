#!/usr/bin/env python3
"""
Run inference with the fine-tuned cron model.

Usage:
    python -m cron_finetuning.inference "Every day at 6:30"
    python -m cron_finetuning.inference "What is the capital of France?"
    python -m cron_finetuning.inference  # interactive mode
    python -m cron_finetuning.inference --checkpoint path/to/model
"""

from __future__ import annotations

import sys
from pathlib import Path

import torch
from unsloth import FastLanguageModel

# Default paths
DEFAULT_CHECKPOINT = "output/cron-model/final"
BASE_MODEL = "unsloth/SmolLM2-360M-Instruct"


def load_model(checkpoint_path: str):
    """Load the base model and apply the fine-tuned LoRA adapters."""
    print(f"Loading base model: {BASE_MODEL}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=BASE_MODEL,
        max_seq_length=256,
        dtype=None,
        load_in_4bit=True,
    )

    # Load LoRA weights
    print(f"Loading LoRA adapters from: {checkpoint_path}")
    model.load_adapter(checkpoint_path)

    # Switch to inference mode (fuses LoRA, speeds up generation)
    FastLanguageModel.for_inference(model)

    return model, tokenizer


def predict(model, tokenizer, user_input: str) -> str:
    """Generate a cron expression (or INVALID) from a natural-language request."""
    messages = [
        {
            "role": "system",
            "content": "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation.",
        },
        {"role": "user", "content": user_input},
    ]

    text = tokenizer.apply_chat_template(
        messages,
        tokenize=False,
        add_generation_prompt=True,
    )

    inputs = tokenizer([text], return_tensors="pt").to(model.device)

    with torch.no_grad():
        outputs = model.generate(
            **inputs,
            max_new_tokens=32,
            temperature=0.0,  # greedy decoding for deterministic output
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode only the newly generated tokens
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1] :],
        skip_special_tokens=True,
    ).strip()

    return response


def run(checkpoint_path: str, user_input: str | None = None) -> None:
    """Run inference.

    Args:
        checkpoint_path: Path to the fine-tuned LoRA checkpoint.
        user_input: If provided, run one-shot inference. Otherwise, interactive mode.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    checkpoint = Path(checkpoint_path)
    if not checkpoint.is_absolute():
        checkpoint = project_root / checkpoint

    if not checkpoint.exists():
        print(f"Checkpoint not found at {checkpoint}")
        print("Run train.py first, or specify a checkpoint path with --checkpoint.")
        sys.exit(1)

    model, tokenizer = load_model(str(checkpoint))

    # Non-interactive: one-shot from command line
    if user_input:
        result = predict(model, tokenizer, user_input)
        print(f"Input : {user_input}")
        print(f"Output: {result}")
        return

    # Interactive mode
    print("\nCron model interactive mode. Type 'quit' to exit.\n")
    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGoodbye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("quit", "exit", "q"):
            break

        result = predict(model, tokenizer, user_input)
        print(f"Bot: {result}\n")


if __name__ == "__main__":
    run(checkpoint_path=DEFAULT_CHECKPOINT)
