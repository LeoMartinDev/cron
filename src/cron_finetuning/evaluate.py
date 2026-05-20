#!/usr/bin/env python3
"""
Evaluate a fine-tuned cron model on the held-out test set.

Usage:
    python -m cron_finetuning.evaluate
    python -m cron_finetuning.evaluate --checkpoint output/cron-model/final
    python -m cron_finetuning.evaluate --data-dir data --checkpoint output/cron-model/final
"""

from __future__ import annotations

import json
import sys
import warnings
from collections import defaultdict
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

# Default paths
BASE_MODEL = "unsloth/SmolLM2-360M-Instruct"
DEFAULT_CHECKPOINT = "output/cron-model/final"
DEFAULT_DATA_DIR = "data"

# System prompt (same as training)
SYSTEM_PROMPT = (
    "You must reply with either a 5-field Unix cron expression "
    "or the single token INVALID. No explanation."
)


def load_model(checkpoint_path: str, base_model: str = BASE_MODEL):
    """Load base model and apply fine-tuned LoRA adapters."""
    print(f"Loading base model: {base_model}")
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=base_model,
        max_seq_length=256,
        dtype=None,
        load_in_4bit=True,
    )

    print(f"Loading LoRA adapters from: {checkpoint_path}")
    model.load_adapter(checkpoint_path)
    FastLanguageModel.for_inference(model)

    return model, tokenizer


def load_test_data(data_dir: str | Path) -> list[dict]:
    """Load the test.jsonl file."""
    test_path = Path(data_dir) / "test.jsonl"
    if not test_path.exists():
        raise FileNotFoundError(f"Test file not found: {test_path}")

    examples = []
    with open(test_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def predict(model, tokenizer, user_input: str) -> str:
    """Generate a cron expression (or INVALID) from a natural-language request."""
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
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


def is_valid_cron(value: str) -> bool:
    """Check if a string is a valid 5-field cron expression."""
    import re

    field = r"(\*|\*/\d+|\d+(-\d+)?(,\d+(-\d+)?)*)"
    pattern = re.compile(rf"^{field}(\s+{field}){{4}}$")
    return bool(pattern.match(value.strip()))


def evaluate(
    data_dir: str | Path = DEFAULT_DATA_DIR,
    checkpoint_path: str | Path = DEFAULT_CHECKPOINT,
    base_model: str = BASE_MODEL,
) -> dict:
    """Run evaluation on the test set.

    Returns a dict with all computed metrics.
    """
    project_root = Path(__file__).resolve().parent.parent.parent

    data_dir = Path(data_dir)
    if not data_dir.is_absolute():
        data_dir = project_root / data_dir

    checkpoint = Path(checkpoint_path)
    if not checkpoint.is_absolute():
        checkpoint = project_root / checkpoint

    if not checkpoint.exists():
        print(f"Checkpoint not found at {checkpoint}")
        sys.exit(1)

    # Load test data
    print(f"\nLoading test set from {data_dir / 'test.jsonl'}...")
    test_examples = load_test_data(data_dir)
    print(f"  Test examples: {len(test_examples)}")

    # Load model
    model, tokenizer = load_model(str(checkpoint), base_model=base_model)

    # Run inference on all test examples
    print(f"\nRunning evaluation on {len(test_examples)} examples...")
    correct = 0
    total = len(test_examples)

    # Per-family stats
    family_stats: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "correct": 0})

    # Confusion matrix for valid/invalid
    invalid_as_invalid = 0  # True negatives (INVALID predicted as INVALID)
    invalid_as_cron = 0  # False positives (INVALID predicted as cron)
    cron_as_cron = 0  # True positives (cron predicted correctly)
    cron_as_invalid = 0  # False negatives (cron predicted as INVALID)
    cron_as_wrong_cron = 0  # cron predicted but wrong cron

    for i, ex in enumerate(test_examples):
        # Extract user text from messages (role=user) or top-level 'user' key
        user_text = ""
        for msg in ex.get("messages", []):
            if msg.get("role") == "user":
                user_text = msg["content"]
                break
        if not user_text:
            user_text = ex.get("user", "")

        # Extract target from messages (role=assistant) or top-level 'target' key
        target = ""
        for msg in ex.get("messages", []):
            if msg.get("role") == "assistant":
                target = msg["content"]
                break
        if not target:
            target = ex.get("target", "")

        family = ex.get("family", "unknown")

        prediction = predict(model, tokenizer, user_text)

        family_stats[family]["total"] += 1

        if prediction == target:
            correct += 1
            family_stats[family]["correct"] += 1
            if target == "INVALID":
                invalid_as_invalid += 1
            else:
                cron_as_cron += 1
        else:
            if target == "INVALID":
                invalid_as_cron += 1
            elif prediction == "INVALID":
                cron_as_invalid += 1
            else:
                cron_as_wrong_cron += 1

        # Print progress
        if (i + 1) % 50 == 0 or i == 0 or i == total - 1:
            pct = 100 * (i + 1) / total
            acc = 100 * correct / (i + 1)
            print(f"  [{i + 1}/{total}] {pct:.0f}% — accuracy so far: {acc:.1f}%")

    # Compute metrics
    accuracy = 100 * correct / total if total > 0 else 0.0

    def _get_target(ex):
        for msg in ex.get("messages", []):
            if msg.get("role") == "assistant":
                return msg["content"]
        return ex.get("target", "")

    cron_total = sum(1 for ex in test_examples if _get_target(ex) != "INVALID")
    invalid_total = total - cron_total

    cron_correct = cron_as_cron
    cron_accuracy = 100 * cron_correct / cron_total if cron_total > 0 else 0.0

    invalid_recall = 100 * invalid_as_invalid / invalid_total if invalid_total > 0 else 0.0

    # Per-family accuracy (sorted by performance)
    family_accuracy = {
        fam: {
            "total": stats["total"],
            "correct": stats["correct"],
            "accuracy": round(100 * stats["correct"] / stats["total"], 1)
            if stats["total"] > 0
            else 0.0,
        }
        for fam, stats in sorted(
            family_stats.items(), key=lambda x: x[1]["correct"] / max(x[1]["total"], 1)
        )
    }

    results = {
        "checkpoint": str(checkpoint),
        "test_examples": total,
        "accuracy": round(accuracy, 2),
        "cron_examples": cron_total,
        "cron_accuracy": round(cron_accuracy, 2),
        "invalid_examples": invalid_total,
        "invalid_recall": round(invalid_recall, 2),
        "confusion": {
            "invalid_as_invalid": invalid_as_invalid,
            "invalid_as_cron": invalid_as_cron,
            "cron_as_cron": cron_as_cron,
            "cron_as_invalid": cron_as_invalid,
            "cron_as_wrong_cron": cron_as_wrong_cron,
        },
        "family_accuracy": family_accuracy,
    }

    return results


def print_results(results: dict) -> None:
    """Pretty-print evaluation results."""
    print("\n" + "=" * 60)
    print("EVALUATION RESULTS ON HELD-OUT TEST SET")
    print("=" * 60)
    print(f"  Checkpoint:        {results['checkpoint']}")
    print(f"  Test examples:     {results['test_examples']}")
    print(f"  Overall accuracy:  {results['accuracy']}%")
    print(
        f"  Cron accuracy:     {results['cron_accuracy']}%  ({results['cron_examples']} examples)"
    )
    print(
        f"  INVALID recall:    {results['invalid_recall']}%  ({results['invalid_examples']} examples)"
    )
    print()
    print("Confusion matrix:")
    c = results["confusion"]
    print(f"  INVALID → INVALID:       {c['invalid_as_invalid']}")
    print(f"  INVALID → cron (FP):     {c['invalid_as_cron']}")
    print(f"  cron → correct cron:     {c['cron_as_cron']}")
    print(f"  cron → INVALID (FN):     {c['cron_as_invalid']}")
    print(f"  cron → wrong cron:       {c['cron_as_wrong_cron']}")
    print()
    print("Per-family accuracy (sorted):")
    for fam, stats in results["family_accuracy"].items():
        bar = "█" * int(stats["accuracy"] / 5) + "░" * (20 - int(stats["accuracy"] / 5))
        print(f"  {fam:<25s} {bar} {stats['accuracy']:5.1f}% ({stats['correct']}/{stats['total']})")
    print("=" * 60)


def save_results(results: dict, data_dir: str | Path) -> None:
    """Save evaluation results to a JSON file."""
    output_path = Path(data_dir) / "evaluation_results.json"
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2)
    print(f"\nResults saved to {output_path}")


if __name__ == "__main__":
    evaluate()
