#!/usr/bin/env python3
"""Thin wrapper: generate the cron dataset. Run from project root."""

import sys
from pathlib import Path

# Ensure src/ is on the path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from cron_finetuning.generate import main

if __name__ == "__main__":
    main()
