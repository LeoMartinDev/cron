#!/usr/bin/env python3
"""Evaluate the cron model on the held-out test set. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.evaluate import (
    BASE_MODEL,
    DEFAULT_CHECKPOINT,
    DEFAULT_DATA_DIR,
    evaluate,
    print_results,
    save_results,
)


def main() -> None:
    """CLI entry point for evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate fine-tuned cron model on the held-out test set."
    )
    parser.add_argument(
        "--data-dir",
        default=DEFAULT_DATA_DIR,
        help=f"Directory containing test.jsonl (default: {DEFAULT_DATA_DIR})",
    )
    parser.add_argument(
        "--checkpoint",
        default=DEFAULT_CHECKPOINT,
        help=f"Path to LoRA checkpoint (default: {DEFAULT_CHECKPOINT})",
    )
    parser.add_argument(
        "--base-model",
        default=BASE_MODEL,
        help=f"Base model ID (default: {BASE_MODEL})",
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save evaluation results to data/evaluation_results.json",
    )
    args = parser.parse_args()

    results = evaluate(
        data_dir=args.data_dir,
        checkpoint_path=args.checkpoint,
        base_model=args.base_model,
    )

    print_results(results)

    if args.save:
        save_results(results, args.data_dir)


if __name__ == "__main__":
    main()
