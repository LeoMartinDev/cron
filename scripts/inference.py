#!/usr/bin/env python3
# /// script
# requires-python = ">=3.10"
# dependencies = [
#     "unsloth>=2024.12",
#     "transformers>=4.46",
#     "accelerate>=1.0",
#     "bitsandbytes>=0.44",
# ]
# ///
"""
Run inference with the fine-tuned cron model.

Usage:
    uv run scripts/inference.py "Every day at 6:30"
    uv run scripts/inference.py "What is the capital of France?"
    uv run scripts/inference.py  # interactive mode
"""

import sys
from pathlib import Path

import torch
from unsloth import FastLanguageModel

# Path to the saved LoRA checkpoint
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


def main():
    project_root = Path(__file__).resolve().parent.parent
    checkpoint = project_root / DEFAULT_CHECKPOINT

    if not checkpoint.exists():
        print(f"Checkpoint not found at {checkpoint}")
        print("Run train.py first, or specify a checkpoint path.")
        sys.exit(1)

    model, tokenizer = load_model(str(checkpoint))

    # Non-interactive: one-shot from command line
    if len(sys.argv) > 1:
        user_input = " ".join(sys.argv[1:])
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
    main()
