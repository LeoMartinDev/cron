"""Utility functions for the cron dataset generator."""

from __future__ import annotations

import random
import re
from typing import Any

from .constants import SYSTEM_PROMPT


def pad2(n: int) -> str:
    """Zero-pad a number to 2 digits."""
    return f"{n:02d}"


def to12h(hour: int, minute: int | None = None) -> str:
    """Convert a 24h hour to 12-hour clock string (e.g. '6 PM' or '6:30 PM')."""
    h12 = 12 if hour == 0 else hour - 12 if hour > 12 else hour
    ampm = "PM" if hour >= 12 else "AM"
    if minute is not None and minute != 0:
        return f"{h12}:{pad2(minute)} {ampm}"
    return f"{h12} {ampm}"


def to12h_compact(hour: int, minute: int | None = None) -> str:
    """Convert to compact 12-hour notation (e.g. '6pm' or '6:30pm')."""
    h12 = 12 if hour == 0 else hour - 12 if hour > 12 else hour
    ampm = "pm" if hour >= 12 else "am"
    if minute is not None and minute != 0:
        return f"{h12}:{pad2(minute)}{ampm}"
    return f"{h12}{ampm}"


def ordinal(n: int) -> str:
    """Return the ordinal string for a number (1st, 2nd, 3rd, etc.)."""
    mod10 = n % 10
    mod100 = n % 100
    if mod10 == 1 and mod100 != 11:
        return f"{n}st"
    if mod10 == 2 and mod100 != 12:
        return f"{n}nd"
    if mod10 == 3 and mod100 != 13:
        return f"{n}rd"
    return f"{n}th"


def to_line(example: dict[str, Any]) -> str:
    """Convert an example dict to a JSONL line in chatml format."""
    import json

    return json.dumps(
        {
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": example["user"]},
                {"role": "assistant", "content": example["target"]},
            ]
        }
    )


def cron_field_regex() -> str:
    """Regex for a single cron field."""
    return r"(\*|\*/\d+|\d+(-\d+)?(,\d+(-\d+)?)*)"


def cron_regex() -> re.Pattern[str]:
    """Regex for a full 5-field cron expression."""
    field = cron_field_regex()
    return re.compile(rf"^{field}(\s+{field}){{4}}$")


def is_cron_target(value: str) -> bool:
    """Check if a value is a valid 5-field cron expression."""
    return bool(cron_regex().match(value.strip()))


def is_valid_target(value: str) -> bool:
    """Check if a target is either 'INVALID' or a valid cron expression."""
    return value == "INVALID" or is_cron_target(value)


def normalize_user_text(value: str) -> str:
    """Normalize user input text."""
    return re.sub(r"\s+", " ", value.lower()).strip()


def is_reasonable_user_text(value: str) -> bool:
    """Check if user text is reasonable (non-empty, appropriate length)."""
    text = normalize_user_text(value)
    if not text:
        return False
    return not (len(text) < 3 or len(text) > 200)


def validate_example(example: dict[str, Any]) -> bool:
    """Validate a single example."""
    if not is_reasonable_user_text(example["user"]):
        return False
    return is_valid_target(example["target"])


def dedupe(examples: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Deduplicate examples based on normalized (user, target) pairs."""
    seen: set[str] = set()
    out: list[dict[str, Any]] = []

    for ex in examples:
        normalized = {
            **ex,
            "user": normalize_user_text(ex["user"]),
            "target": ex["target"].strip(),
        }

        key = f"{normalized['user'].lower()}|||{normalized['target']}"
        if key in seen:
            continue
        if not validate_example(normalized):
            continue

        seen.add(key)
        out.append(normalized)

    return out


def shuffle(items: list[Any]) -> list[Any]:
    """Return a shuffled copy of a list."""
    copy = list(items)
    random.shuffle(copy)
    return copy


def split_dataset(
    examples: list[dict[str, Any]],
    train_ratio: float = 0.8,
    valid_ratio: float = 0.1,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Split examples into train, validation, and test sets.

    Default split: 80% train, 10% validation, 10% test.
    The test set is held out and never used during training — only for final evaluation.
    """
    shuffled = shuffle(examples)
    train_end = int(len(shuffled) * train_ratio)
    valid_end = train_end + int(len(shuffled) * valid_ratio)
    return shuffled[:train_end], shuffled[train_end:valid_end], shuffled[valid_end:]


def parse_cron_fields(target: str) -> list[str]:
    """Split a cron expression into its 5 fields."""
    return target.strip().split()


def is_semantically_consistent(user_text: str, target: str) -> bool:
    """Check that a paraphrased user prompt is semantically consistent with the cron target."""
    fields = parse_cron_fields(target)
    if len(fields) != 5:
        return False
    _min, _hour, _dom, _mon, dow = fields
    lower = user_text.lower()

    # "daily except X" / "every day except X" / "weekdays except X" are valid
    if re.search(r"\b(daily|every\s+day|weekdays?)\s+except\b", lower):
        return True

    # If cron has day-of-week restriction, must NOT say daily/every day without except
    if dow != "*" and re.search(r"\b(daily|every\s+day|each\s+day|run\s+every\s+day)\b", lower):
        return False

    # If cron is not the full weekday range (1-5), must NOT say weekday without except
    return not (
        (dow != "1-5" and dow != "*")
        and re.search(r"\b(weekdays?|monday\s+to\s+friday|m-f)\b(?!\s+except)", lower)
    )
