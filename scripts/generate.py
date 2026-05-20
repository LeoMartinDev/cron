#!/usr/bin/env python3
"""Generate the cron dataset. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.constants import HUB_DATASET_REPO_ID
from cron_finetuning.generate import generate


def main() -> None:
    """CLI entry point for dataset generation."""
    parser = argparse.ArgumentParser(
        description="Generate the cron-expression fine-tuning dataset."
    )
    parser.add_argument(
        "--output-dir",
        "-o",
        default="data",
        help="Output directory for generated files (default: data/)",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the dataset to HuggingFace Hub after generation",
    )
    parser.add_argument(
        "--repo-id",
        default=HUB_DATASET_REPO_ID,
        help="HuggingFace Hub repository ID (default from constants.py, or e.g. 'username/cron-dataset')",
    )
    args = parser.parse_args()

    generate(
        output_dir=args.output_dir,
        push_to_hub=args.push,
        repo_id=args.repo_id,
    )


if __name__ == "__main__":
    main()
