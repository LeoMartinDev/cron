#!/usr/bin/env python3
"""Fine-tune the cron model with Unsloth. Run from project root."""

import argparse
import sys
from pathlib import Path

# Ensure src/ is on the path so we can import cron_finetuning
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.train import train


def main() -> None:
    """CLI entry point for training."""
    parser = argparse.ArgumentParser(description="Fine-tune cron model with Unsloth")
    parser.add_argument(
        "--resume-from-checkpoint",
        default=None,
        help="Path to a checkpoint to resume from",
    )
    parser.add_argument(
        "--push",
        action="store_true",
        help="Push the final model to HuggingFace Hub",
    )
    parser.add_argument(
        "--no-merged",
        action="store_true",
        help="Skip saving the full 16-bit merged model",
    )
    parser.add_argument(
        "--no-gguf",
        action="store_true",
        help="Skip saving the GGUF quantized model",
    )
    parser.add_argument(
        "--gguf-quant",
        default="q4_k_m",
        help="GGUF quantization method (default: q4_k_m). Also accepts: 'quantized', 'fast_quantized', 'not_quantized', 'f16', 'q8_0', 'q5_k_m', etc.",
    )
    args = parser.parse_args()

    train(
        resume_from_checkpoint=args.resume_from_checkpoint,
        push_to_hub=args.push,
        export_merged=not args.no_merged,
        export_gguf=not args.no_gguf,
        gguf_quant=args.gguf_quant,
    )


if __name__ == "__main__":
    main()
