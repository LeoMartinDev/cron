#!/usr/bin/env python3
"""
Run inference with the fine-tuned cron model.

Usage:
    python -m cron_finetuning.inference "Every day at 6:30"
    python -m cron_finetuning.inference "What is the capital of France?"
    python -m cron_finetuning.inference  # interactive mode
"""

from __future__ import annotations

import sys
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

# Unsloth MUST be imported before torch — it monkey-patches transformers/torch.
# isort: off
from unsloth import FastLanguageModel  # noqa: E402

# isort: on
import torch  # noqa: E402

from .constants import BASE_MODEL, DEFAULT_CHECKPOINT  # noqa: E402


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
            # Set max_length=None to override the model's default max_length
            # (required when using max_new_tokens to avoid a generation warning)
            max_length=None,
            temperature=0.0,  # greedy decoding for deterministic output
            pad_token_id=tokenizer.pad_token_id,
            eos_token_id=tokenizer.eos_token_id,
        )

    # Decode only the newly generated tokens (skip the input prompt)
    response = tokenizer.decode(
        outputs[0][inputs["input_ids"].shape[1] :],
        skip_special_tokens=True,
    ).strip()

    return response


def run(user_input: str | None = None) -> None:
    """Run inference.

    Args:
        user_input: If provided, run one-shot inference. Otherwise, interactive mode.
    """
    project_root = Path(__file__).resolve().parent.parent.parent
    checkpoint = Path(DEFAULT_CHECKPOINT)
    if not checkpoint.is_absolute():
        checkpoint = project_root / checkpoint

    if not checkpoint.exists():
        print(f"Checkpoint not found at {checkpoint}")
        print("Run train.py first, or update DEFAULT_CHECKPOINT in constants.py.")
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
    run()
