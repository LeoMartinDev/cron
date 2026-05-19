"""Main dataset generation orchestration.

Usage:
    python -m cron_finetuning.generate          # generate dataset
    python -m cron_finetuning.generate --push   # generate and push to HF Hub
"""

from __future__ import annotations

import os
from pathlib import Path

from .dataset import write_jsonl, write_manifest
from .families import build_base_dataset
from .llm import maybe_generate_synthetic_data
from .utils import dedupe, split_dataset


def generate(
    output_dir: str | Path = "data",
    push_to_hub: bool = False,
    repo_id: str | None = None,
) -> None:
    """Generate the cron dataset and optionally push to HuggingFace Hub.

    Args:
        output_dir: Directory to write train.jsonl, valid.jsonl, test.jsonl, and manifest.json.
        push_to_hub: If True, also push to HuggingFace Hub.
        repo_id: HF Hub repo ID (required if push_to_hub is True).
    """
    print("Building base dataset from templates...")
    base = build_base_dataset()
    print(f"  {len(base)} template examples generated")

    print("Generating LLM-augmented data...")
    synthetic = maybe_generate_synthetic_data(base)
    print(f"  {len(synthetic)} synthetic examples generated")

    all_examples = dedupe([*base, *synthetic])
    train, valid, test = split_dataset(all_examples, train_ratio=0.8, valid_ratio=0.1)

    print("\nDataset summary:")
    print(f"  Total:  {len(all_examples)}")
    print(f"  Train:  {len(train)}")
    print(f"  Valid:  {len(valid)}")
    print(f"  Test:   {len(test)}")

    # Write output files
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    write_jsonl(output_dir / "train.jsonl", train)
    write_jsonl(output_dir / "valid.jsonl", valid)
    write_jsonl(output_dir / "test.jsonl", test)

    model_used = os.environ.get("OPENROUTER_MODEL") if synthetic else None
    write_manifest(output_dir, all_examples, train, valid, test, model_used=model_used)

    print(f"\nDataset written to {output_dir.resolve()}/")

    # Optionally push to HuggingFace Hub
    if push_to_hub:
        if not repo_id:
            raise ValueError("repo_id is required when push_to_hub=True")

        from .dataset import push_dataset_to_hub

        push_dataset_to_hub(output_dir, repo_id)


if __name__ == "__main__":
    generate()
