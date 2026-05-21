"""Utility functions for the cron dataset generator."""

from __future__ import annotations

import json
import random
import re
from typing import Any

from .constants import SYSTEM_PROMPT

MONTH_NAME_TO_NUMBER = {
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "may": 5,
    "june": 6,
    "july": 7,
    "august": 8,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
}

WEEKDAY_NAME_TO_NUMBER = {
    "monday": 1,
    "mon": 1,
    "tuesday": 2,
    "tue": 2,
    "tues": 2,
    "wednesday": 3,
    "wed": 3,
    "thursday": 4,
    "thu": 4,
    "thurs": 4,
    "friday": 5,
    "fri": 5,
    "saturday": 6,
    "sat": 6,
    "sunday": 0,
    "sun": 0,
}


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
    return json.dumps(
        {
            **example,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": example["user"]},
                {"role": "assistant", "content": example["target"]},
            ],
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
    value = value.strip()
    if not cron_regex().match(value):
        return False

    fields = value.split()
    if len(fields) != 5:
        return False

    bounds = [
        (0, 59),
        (0, 23),
        (1, 31),
        (1, 12),
        (0, 7),
    ]
    return all(_is_valid_field(field, min_value, max_value) for field, (min_value, max_value) in zip(fields, bounds))


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
    if len(fields) != 5 or not is_cron_target(target):
        return False

    minute, hour, day_of_month, month, day_of_week = fields
    lower = user_text.lower()

    expected_time = _target_single_time(fields)
    mentioned_time = _extract_time_mentions(lower)
    mentioned_days = _extract_weekday_mentions(lower)
    mentioned_months = _extract_month_mentions(lower)
    mentioned_month_days = _extract_day_of_month_mentions(lower)
    mentioned_minute_interval = _extract_minute_interval(lower)
    mentions_weekdays = _mentions_weekdays(lower)

    if _is_daily_target(fields):
        return (
            expected_time is not None
            and mentioned_time == {expected_time}
            and not mentions_weekdays
            and not mentioned_days
            and not mentioned_months
            and not mentioned_month_days
            and mentioned_minute_interval is None
        )

    if _is_every_n_minutes_target(fields):
        expected_interval = int(minute[2:])
        return (
            mentioned_minute_interval == expected_interval
            and not mentioned_time
            and not mentions_weekdays
            and not mentioned_days
            and not mentioned_months
            and not mentioned_month_days
        )

    if _is_weekdays_target(fields):
        return (
            expected_time is not None
            and mentioned_time == {expected_time}
            and _mentions_full_weekdays(lower, mentioned_days)
            and not mentioned_months
            and not mentioned_month_days
            and mentioned_minute_interval is None
        )

    if _is_monthly_on_day_target(fields):
        return (
            expected_time is not None
            and mentioned_time == {expected_time}
            and mentioned_month_days == {int(day_of_month)}
            and not mentions_weekdays
            and not mentioned_days
            and not mentioned_months
            and mentioned_minute_interval is None
        )

    if _is_weekly_on_day_target(fields):
        expected_days = _expand_day_of_week_field(day_of_week)
        return (
            expected_time is not None
            and mentioned_time == {expected_time}
            and expected_days is not None
            and mentioned_days == expected_days
            and not mentions_weekdays
            and not mentioned_months
            and not mentioned_month_days
            and mentioned_minute_interval is None
        )

    if _is_multi_time_daily_target(fields):
        expected_times = _target_time_set(fields)
        return (
            expected_times is not None
            and mentioned_time == expected_times
            and _mentions_daily(lower)
            and not mentions_weekdays
            and not mentioned_days
            and not mentioned_months
            and not mentioned_month_days
            and mentioned_minute_interval is None
        )

    if _is_multi_time_weekdays_target(fields):
        expected_times = _target_time_set(fields)
        return (
            expected_times is not None
            and mentioned_time == expected_times
            and _mentions_full_weekdays(lower, mentioned_days)
            and not mentioned_months
            and not mentioned_month_days
            and mentioned_minute_interval is None
        )

    if _is_multi_time_weekly_target(fields):
        expected_times = _target_time_set(fields)
        expected_days = _expand_day_of_week_field(day_of_week)
        if expected_times is None or expected_days is None:
            return False

        if expected_days == {0, 6}:
            return (
                mentioned_time == expected_times
                and (_mentions_weekends(lower) or mentioned_days == expected_days)
                and not mentions_weekdays
                and not mentioned_months
                and not mentioned_month_days
                and mentioned_minute_interval is None
            )

        return (
            mentioned_time == expected_times
            and mentioned_days == expected_days
            and not mentions_weekdays
            and not mentioned_months
            and not mentioned_month_days
            and mentioned_minute_interval is None
        )

    if _is_top_of_hour_target(fields):
        return (
            (
                mentioned_minute_interval == 60
                or bool(re.search(r"\b(every hour|run every hour|once every hour|hourly|on the hour)\b", lower))
            )
            and not mentioned_time
            and not mentions_weekdays
            and not mentioned_days
            and not mentioned_months
            and not mentioned_month_days
        )

    # For unsupported target shapes, keep the filter conservative and reject.
    return False


def _is_valid_field(field: str, min_value: int, max_value: int) -> bool:
    if field == "*":
        return True

    if field.startswith("*/"):
        step_value = field[2:]
        return step_value.isdigit() and 1 <= int(step_value) <= max_value

    for part in field.split(","):
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            if not start_str.isdigit() or not end_str.isdigit():
                return False
            start, end = int(start_str), int(end_str)
            if not (min_value <= start <= max_value and min_value <= end <= max_value and start <= end):
                return False
            continue

        if not part.isdigit():
            return False

        value = int(part)
        if not (min_value <= value <= max_value):
            return False

    return True


def _is_daily_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    return minute.isdigit() and hour.isdigit() and day_of_month == "*" and month == "*" and day_of_week == "*"


def _is_every_n_minutes_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    return minute.startswith("*/") and hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*"


def _is_top_of_hour_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    return minute == "0" and hour == "*" and day_of_month == "*" and month == "*" and day_of_week == "*"


def _is_weekdays_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    return minute.isdigit() and hour.isdigit() and day_of_month == "*" and month == "*" and day_of_week == "1-5"


def _is_monthly_on_day_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    return minute.isdigit() and hour.isdigit() and day_of_month.isdigit() and month == "*" and day_of_week == "*"


def _is_weekly_on_day_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    return (
        minute.isdigit()
        and hour.isdigit()
        and day_of_month == "*"
        and month == "*"
        and _expand_day_of_week_field(day_of_week) is not None
        and day_of_week != "1-5"
    )


def _is_multi_time_daily_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    if day_of_month != "*" or month != "*" or day_of_week != "*":
        return False

    time_set = _target_time_set(fields)
    return time_set is not None and len(time_set) > 1


def _is_multi_time_weekdays_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    if day_of_month != "*" or month != "*" or day_of_week != "1-5":
        return False

    time_set = _target_time_set(fields)
    return time_set is not None and len(time_set) > 1


def _is_multi_time_weekly_target(fields: list[str]) -> bool:
    minute, hour, day_of_month, month, day_of_week = fields
    if day_of_month != "*" or month != "*":
        return False
    if day_of_week == "*" or day_of_week == "1-5":
        return False

    time_set = _target_time_set(fields)
    expected_days = _expand_day_of_week_field(day_of_week)
    return time_set is not None and len(time_set) > 1 and expected_days is not None


def _target_single_time(fields: list[str]) -> tuple[int, int] | None:
    minute, hour, *_ = fields
    if not minute.isdigit() or not hour.isdigit():
        return None
    return int(hour), int(minute)


def _target_time_set(fields: list[str]) -> set[tuple[int, int]] | None:
    minute, hour, *_ = fields
    if not minute.isdigit():
        return None

    hour_parts = hour.split(",")
    if not hour_parts or any(not part.isdigit() for part in hour_parts):
        return None

    return {(int(part), int(minute)) for part in hour_parts}


def _extract_time_mentions(text: str) -> set[tuple[int, int]]:
    matches: set[tuple[int, int]] = set()

    if "midnight" in text:
        matches.add((0, 0))
    if "noon" in text:
        matches.add((12, 0))

    for match in re.finditer(r"\b(?P<hour>1[0-2]|0?[1-9])(?::(?P<minute>[0-5]\d))?\s*(?P<ampm>am|pm)\b", text):
        hour = int(match.group("hour")) % 12
        minute = int(match.group("minute") or "0")
        if match.group("ampm") == "pm":
            hour += 12
        matches.add((hour, minute))

    for match in re.finditer(r"\b(?P<hour>[01]?\d|2[0-3]):(?P<minute>[0-5]\d)\b", text):
        matches.add((int(match.group("hour")), int(match.group("minute"))))

    for match in re.finditer(r"\bat\s+(?P<hour>\d{1,2})\b", text):
        hour = int(match.group("hour"))
        if hour > 23:
            continue

        if hour > 12:
            matches.add((hour, 0))
            continue

        if "morning" in text:
            matches.add((0 if hour == 12 else hour, 0))
        elif "afternoon" in text or "evening" in text or "night" in text:
            matches.add((12 if hour == 12 else hour + 12, 0))

    return matches


def _extract_minute_interval(text: str) -> int | None:
    match = re.search(
        r"\b(?:every|run every|once every)\s+(?P<value>\d+)\s*(?:minutes?|mins?|min|m)\b",
        text,
    )
    if match:
        return int(match.group("value"))

    if "every half hour" in text:
        return 30
    if "every quarter hour" in text:
        return 15
    return None


def _extract_day_of_month_mentions(text: str) -> set[int]:
    matches = {int(value) for value in re.findall(r"\b(\d{1,2})(?:st|nd|rd|th)\b", text)}
    matches.update(int(value) for value in re.findall(r"\bday\s+(\d{1,2})\b", text))
    return matches


def _extract_month_mentions(text: str) -> set[int]:
    matches: set[int] = set()
    for name, number in MONTH_NAME_TO_NUMBER.items():
        if re.search(rf"\b{name}\b", text):
            matches.add(number)
    return matches


def _extract_weekday_mentions(text: str) -> set[int]:
    matches: set[int] = set()
    for name, number in WEEKDAY_NAME_TO_NUMBER.items():
        if re.search(rf"\b{name}\b", text):
            matches.add(number)
    return matches


def _mentions_weekdays(text: str) -> bool:
    return bool(
        re.search(
            r"\b(weekday|weekdays|monday\s+(?:to|through)\s+friday|mon\s*-\s*fri|m-f)\b",
            text,
        )
    )


def _mentions_daily(text: str) -> bool:
    return bool(
        re.search(
            r"\b(every day|everyday|daily|twice a day|twice daily|\d+\s+times a day|\d+\s+times daily)\b",
            text,
        )
    )


def _mentions_weekends(text: str) -> bool:
    return bool(re.search(r"\b(weekend|weekends)\b", text))


def _mentions_full_weekdays(text: str, explicit_days: set[int]) -> bool:
    if _mentions_weekdays(text):
        return True

    return explicit_days == {1, 2, 3, 4, 5}


def _expand_day_of_week_field(field: str) -> set[int] | None:
    if field == "*":
        return None

    values: set[int] = set()
    for part in field.split(","):
        if "-" in part:
            start_str, end_str = part.split("-", 1)
            if not start_str.isdigit() or not end_str.isdigit():
                return None
            start, end = int(start_str), int(end_str)
            if start > end:
                return None
            values.update(_normalize_day_of_week(value) for value in range(start, end + 1))
        else:
            if not part.isdigit():
                return None
            values.add(_normalize_day_of_week(int(part)))
    return values


def _normalize_day_of_week(value: int) -> int:
    return 0 if value == 7 else value
