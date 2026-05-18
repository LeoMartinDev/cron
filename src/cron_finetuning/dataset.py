"""Dataset utilities: loading, saving, splitting, and pushing to HuggingFace Hub."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

from .utils import to_line


def write_jsonl(path: str | Path, examples: list[dict[str, Any]]) -> None:
    """Write examples to a JSONL file in chatml format."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    body = "\n".join(to_line(ex) for ex in examples) + "\n"
    path.write_text(body, encoding="utf-8")


def read_jsonl(path: str | Path) -> list[dict[str, Any]]:
    """Read examples from a JSONL file in chatml format."""
    path = Path(path)
    examples: list[dict[str, Any]] = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                examples.append(json.loads(line))
    return examples


def write_json(path: str | Path, value: Any) -> None:
    """Write a JSON object to a file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")


def write_manifest(
    output_dir: str | Path,
    all_examples: list[dict[str, Any]],
    train: list[dict[str, Any]],
    valid: list[dict[str, Any]],
    test: list[dict[str, Any]] | None = None,
    model_used: str | None = None,
) -> None:
    """Write a manifest.json describing the dataset."""
    manifest = {
        "format": "chatml",
        "cron_variant": "unix-5-fields-or-INVALID",
        "total_examples": len(all_examples),
        "train_examples": len(train),
        "valid_examples": len(valid),
        "test_examples": len(test) if test else 0,
        "model_for_synthetic_generation": model_used,
        "sources": {
            "template": sum(1 for x in all_examples if x["source"] == "template"),
            "llm": sum(1 for x in all_examples if x["source"] == "llm"),
        },
        "families": sorted({x["family"] for x in all_examples}),
        "special_outputs": ["INVALID"],
    }
    write_json(Path(output_dir) / "manifest.json", manifest)


# ---------------------------------------------------------------------------
# HuggingFace Hub integration
# ---------------------------------------------------------------------------


def _get_hf_token() -> str | None:
    """Get HuggingFace token from environment or cache."""
    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_HUB_TOKEN")
    if token:
        return token

    # Try to read from huggingface cache
    cache_dir = Path.home() / ".cache" / "huggingface"
    token_file = cache_dir / "token"
    if token_file.exists():
        return token_file.read_text().strip()

    return None


def push_dataset_to_hub(
    data_dir: str | Path,
    repo_id: str,
    *,
    private: bool = False,
    commit_message: str = "Update cron dataset",
) -> None:
    """Push the generated dataset to the HuggingFace Hub.

    Args:
        data_dir: Directory containing train.jsonl, valid.jsonl, test.jsonl, and manifest.json.
        repo_id: HuggingFace Hub repository ID (e.g. 'username/cron-dataset').
        private: Whether to create a private repository.
        commit_message: Commit message for the push.
    """
    from huggingface_hub import HfApi, create_repo

    token = _get_hf_token()
    if not token:
        raise RuntimeError(
            "HuggingFace token not found. Set HF_TOKEN environment variable "
            "or run `huggingface-cli login`."
        )

    data_dir = Path(data_dir)
    api = HfApi()

    # Create or get the repo
    try:
        create_repo(
            repo_id, token=token, private=private, repo_type="dataset", exist_ok=True
        )
        print(f"Using dataset repository: {repo_id}")
    except Exception as e:
        raise RuntimeError(f"Failed to create/access repo {repo_id}: {e}") from e

    # Upload all files from the data directory
    files_to_upload: list[str] = []
    for f in data_dir.iterdir():
        if f.is_file():
            files_to_upload.append(str(f))

    if not files_to_upload:
        raise RuntimeError(f"No files found in {data_dir}")

    for file_path in files_to_upload:
        rel_path = Path(file_path).name
        print(f"  Uploading {rel_path}...")
        api.upload_file(
            path_or_fileobj=file_path,
            path_in_repo=rel_path,
            repo_id=repo_id,
            repo_type="dataset",
            token=token,
            commit_message=commit_message,
        )

    print(f"Dataset pushed to https://huggingface.co/datasets/{repo_id}")


def push_model_to_hub(
    model_dir: str | Path,
    repo_id: str,
    *,
    private: bool = False,
    commit_message: str = "Update cron model",
) -> None:
    """Push a fine-tuned model to the HuggingFace Hub.

    Args:
        model_dir: Directory containing the model files (e.g. output/cron-model/final).
        repo_id: HuggingFace Hub repository ID (e.g. 'username/cron-model').
        private: Whether to create a private repository.
        commit_message: Commit message for the push.
    """
    from huggingface_hub import HfApi, create_repo

    token = _get_hf_token()
    if not token:
        raise RuntimeError(
            "HuggingFace token not found. Set HF_TOKEN environment variable "
            "or run `huggingface-cli login`."
        )

    model_dir = Path(model_dir)
    api = HfApi()

    # Create or get the repo
    try:
        create_repo(
            repo_id, token=token, private=private, repo_type="model", exist_ok=True
        )
        print(f"Using model repository: {repo_id}")
    except Exception as e:
        raise RuntimeError(f"Failed to create/access repo {repo_id}: {e}") from e

    # Upload the entire model directory
    api.upload_folder(
        folder_path=str(model_dir),
        repo_id=repo_id,
        repo_type="model",
        token=token,
        commit_message=commit_message,
    )

    print(f"Model pushed to https://huggingface.co/{repo_id}")


def load_dataset_from_hub(
    repo_id: str,
    *,
    split: str | None = None,
) -> Any:
    """Load the cron dataset from HuggingFace Hub using the datasets library.

    Args:
        repo_id: HuggingFace dataset repo ID.
        split: Which split to load ('train', 'validation', or None for all).

    Returns:
        A HuggingFace Dataset or DatasetDict.
    """
    from datasets import load_dataset

    return load_dataset(repo_id, split=split)
