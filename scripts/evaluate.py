#!/usr/bin/env python3
"""Thin wrapper: evaluate the cron model on the held-out test set. Run from project root."""

import sys
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.evaluate import main

if __name__ == "__main__":
    main()
