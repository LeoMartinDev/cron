#!/usr/bin/env python3
"""Fine-tune the cron model with Unsloth. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.train import CONFIG, train


def main() -> None:
    """CLI entry point for training."""
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
        default=None,
        help="Push the final model to HuggingFace Hub",
    )
    parser.add_argument(
        "--hub-repo-id",
        default=None,
        dest="repo_id",
        help="HuggingFace Hub model repo ID (e.g. 'username/cron-model')",
    )
    args = parser.parse_args()

    # Auto-enable push when hub-repo-id is provided
    push = args.push if args.push is not None else (args.repo_id is not None)

    train(
        data_dir=args.data_dir,
        output_dir=args.output_dir,
        base_model=args.base_model,
        resume_from_checkpoint=args.resume_from_checkpoint,
        push_to_hub=push,
        repo_id=args.repo_id,
    )


if __name__ == "__main__":
    main()
