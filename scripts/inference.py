#!/usr/bin/env python3
"""Run inference with the fine-tuned cron model. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.inference import DEFAULT_CHECKPOINT, run


def main() -> None:
    """CLI entry point for inference."""
    parser = argparse.ArgumentParser(description="Run inference with a fine-tuned cron model.")
    parser.add_argument(
        "input",
        nargs="*",
        help="Natural-language scheduling request (omit for interactive mode)",
    )
    parser.add_argument(
        "--checkpoint",
        default=DEFAULT_CHECKPOINT,
        help=f"Path to the LoRA checkpoint (default: {DEFAULT_CHECKPOINT})",
    )
    args = parser.parse_args()

    user_input = " ".join(args.input) if args.input else None
    run(checkpoint_path=args.checkpoint, user_input=user_input)


if __name__ == "__main__":
    main()
