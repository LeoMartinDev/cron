#!/usr/bin/env python3
"""Push an existing trained model or dataset to HuggingFace Hub. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.constants import HUB_DATASET_REPO_ID, HUB_MODEL_REPO_ID
from cron_finetuning.dataset import push_dataset_to_hub, push_model_to_hub


def _check_repo_id(repo_id: str | None, name: str) -> str:
    """Validate that a repo ID is configured, and return it."""
    if not repo_id:
        raise SystemExit(
            f"No {name} repo ID configured. "
            f"Set the appropriate constant in src/cron_finetuning/constants.py"
        )
    return repo_id


def main() -> None:
    """CLI entry point for pushing to HuggingFace Hub."""
    parser = argparse.ArgumentParser(
        description="Push a trained cron model or dataset to HuggingFace Hub."
    )
    sub = parser.add_subparsers(dest="what", required=True, help="What to push")

    # ── Model ──────────────────────────────────────────────────────────
    model_parser = sub.add_parser("model", help="Push a fine-tuned model")
    model_parser.add_argument(
        "--model-dir",
        default="output/cron-model/final",
        help="Directory containing the model files (default: output/cron-model/final)",
    )
    model_parser.add_argument(
        "--private",
        action="store_true",
        help="Create a private repository",
    )
    model_parser.add_argument(
        "--message",
        "-m",
        default="Update cron model",
        help="Commit message (default: 'Update cron model')",
    )

    # ── Merged model ───────────────────────────────────────────────────
    merged_parser = sub.add_parser("merged", help="Push a full merged 16-bit model")
    merged_parser.add_argument(
        "--model-dir",
        default="output/cron-model/final-merged",
        help="Directory containing the merged model (default: output/cron-model/final-merged)",
    )
    merged_parser.add_argument(
        "--private",
        action="store_true",
        help="Create a private repository",
    )
    merged_parser.add_argument(
        "--message",
        "-m",
        default="Update merged 16-bit model",
        help="Commit message",
    )

    # ── GGUF ───────────────────────────────────────────────────────────
    gguf_parser = sub.add_parser("gguf", help="Push a GGUF quantized model")
    gguf_parser.add_argument(
        "--model-dir",
        default="output/cron-model/final-gguf",
        help="Directory containing the GGUF files (default: output/cron-model/final-gguf)",
    )
    gguf_parser.add_argument(
        "--private",
        action="store_true",
        help="Create a private repository",
    )
    gguf_parser.add_argument(
        "--message",
        "-m",
        default="Update GGUF model",
        help="Commit message",
    )

    # ── Dataset ────────────────────────────────────────────────────────
    dataset_parser = sub.add_parser("dataset", help="Push the generated dataset")
    dataset_parser.add_argument(
        "--data-dir",
        default="data",
        help="Directory containing train.jsonl, valid.jsonl, test.jsonl, and manifest.json (default: data/)",
    )
    dataset_parser.add_argument(
        "--private",
        action="store_true",
        help="Create a private repository",
    )
    dataset_parser.add_argument(
        "--message",
        "-m",
        default="Update cron dataset",
        help="Commit message (default: 'Update cron dataset')",
    )

    args = parser.parse_args()

    if args.what == "model":
        push_model_to_hub(
            model_dir=args.model_dir,
            repo_id=_check_repo_id(HUB_MODEL_REPO_ID, "model"),
            private=args.private,
            commit_message=args.message,
        )
    elif args.what == "merged":
        push_model_to_hub(
            model_dir=args.model_dir,
            repo_id=_check_repo_id(HUB_MODEL_REPO_ID, "model"),
            private=args.private,
            commit_message=args.message,
        )
    elif args.what == "gguf":
        push_model_to_hub(
            model_dir=args.model_dir,
            repo_id=_check_repo_id(HUB_MODEL_REPO_ID, "model"),
            private=args.private,
            commit_message=args.message,
        )
    elif args.what == "dataset":
        push_dataset_to_hub(
            data_dir=args.data_dir,
            repo_id=_check_repo_id(HUB_DATASET_REPO_ID, "dataset"),
            private=args.private,
            commit_message=args.message,
        )


if __name__ == "__main__":
    main()
