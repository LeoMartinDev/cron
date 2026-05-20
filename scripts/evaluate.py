#!/usr/bin/env python3
"""Evaluate the cron model on the held-out test set. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.evaluate import evaluate, print_results, save_results


def main() -> None:
    """CLI entry point for evaluation."""
    parser = argparse.ArgumentParser(
        description="Evaluate fine-tuned cron model on the held-out test set."
    )
    parser.add_argument(
        "--save",
        action="store_true",
        help="Save evaluation results to data/evaluation_results.json",
    )
    args = parser.parse_args()

    results = evaluate()

    print_results(results)

    if args.save:
        save_results(results)


if __name__ == "__main__":
    main()
