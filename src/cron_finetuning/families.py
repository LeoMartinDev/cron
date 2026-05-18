"""Template-based example generators for each cron family.

Each function returns a list of example dicts with keys:
    user, target, family, source
"""

from __future__ import annotations

from typing import Any

from .constants import WEEKDAYS
from .utils import ordinal, pad2, to12h, to12h_compact


def _ex(  # helper: build a single example dict
    family: str,
    source: str = "template",
    *,
    user: str,
    target: str,
) -> dict[str, Any]:
    return {"family": family, "source": source, "user": user, "target": target}


# ---------------------------------------------------------------------------
# 1. daily_at
# ---------------------------------------------------------------------------


def daily_at_examples() -> list[dict[str, Any]]:
    """Every day at a specific time."""
    times = [
        {"hour": 0, "minute": 0},
        {"hour": 0, "minute": 30},
        {"hour": 1, "minute": 0},
        {"hour": 2, "minute": 0},
        {"hour": 3, "minute": 15},
        {"hour": 4, "minute": 0},
        {"hour": 5, "minute": 30},
        {"hour": 6, "minute": 0},
        {"hour": 6, "minute": 30},
        {"hour": 7, "minute": 0},
        {"hour": 7, "minute": 45},
        {"hour": 8, "minute": 0},
        {"hour": 8, "minute": 30},
        {"hour": 9, "minute": 0},
        {"hour": 9, "minute": 15},
        {"hour": 10, "minute": 0},
        {"hour": 10, "minute": 45},
        {"hour": 11, "minute": 30},
        {"hour": 12, "minute": 0},
        {"hour": 13, "minute": 0},
        {"hour": 14, "minute": 5},
        {"hour": 15, "minute": 0},
        {"hour": 15, "minute": 30},
        {"hour": 16, "minute": 0},
        {"hour": 17, "minute": 0},
        {"hour": 18, "minute": 0},
        {"hour": 18, "minute": 45},
        {"hour": 20, "minute": 0},
        {"hour": 21, "minute": 30},
        {"hour": 22, "minute": 0},
        {"hour": 23, "minute": 0},
        {"hour": 23, "minute": 45},
    ]

    out: list[dict[str, Any]] = []

    for slot in times:
        h, m = slot["hour"], slot["minute"]
        target = f"{m} {h} * * *"

        out.append(_ex("daily_at", user=f"Every day at {h}:{pad2(m)}", target=target))
        out.append(_ex("daily_at", user=f"Daily at {h}:{pad2(m)}", target=target))
        out.append(
            _ex("daily_at", user=f"Run every day at {h}:{pad2(m)}", target=target)
        )
        out.append(_ex("daily_at", user=f"Every day at {to12h(h, m)}", target=target))
        out.append(
            _ex("daily_at", user=f"Every day at {to12h_compact(h, m)}", target=target)
        )

        # Natural time-of-day phrases for round hours
        if m == 0:
            if 6 <= h <= 11:
                out.append(_ex("daily_at", user=f"Every morning at {h}", target=target))
            if 12 <= h <= 17:
                out.append(
                    _ex(
                        "daily_at", user=f"Every afternoon at {to12h(h)}", target=target
                    )
                )
            if 18 <= h <= 21:
                out.append(
                    _ex("daily_at", user=f"Every evening at {to12h(h)}", target=target)
                )
            if h >= 22 or h <= 4:
                out.append(
                    _ex("daily_at", user=f"Every night at {to12h(h)}", target=target)
                )

        # Terse / lazy phrasings
        if m == 0:
            out.append(_ex("daily_at", user=f"Daily at {h}", target=target))
        out.append(_ex("daily_at", user=f"Daily {to12h_compact(h, m)}", target=target))
        out.append(_ex("daily_at", user=f"{to12h_compact(h, m)} daily", target=target))

    return out


# ---------------------------------------------------------------------------
# 2. every_n_minutes
# ---------------------------------------------------------------------------


def every_n_minutes_examples() -> list[dict[str, Any]]:
    """Recurring interval in minutes."""
    values = [2, 3, 5, 6, 10, 12, 15, 20, 30, 45, 60]

    out: list[dict[str, Any]] = []
    for n in values:
        target = f"*/{n} * * * *"
        out.append(_ex("every_n_minutes", user=f"Every {n} minutes", target=target))
        out.append(_ex("every_n_minutes", user=f"Run every {n} minutes", target=target))
        out.append(
            _ex("every_n_minutes", user=f"Once every {n} minutes", target=target)
        )
        out.append(_ex("every_n_minutes", user=f"Every {n}m", target=target))
        out.append(_ex("every_n_minutes", user=f"Every {n} min", target=target))
    return out


# ---------------------------------------------------------------------------
# 3. weekdays_at
# ---------------------------------------------------------------------------


def weekdays_at_examples() -> list[dict[str, Any]]:
    """Monday through Friday at a specific time."""
    slots = [
        {"hour": 8, "minute": 0},
        {"hour": 9, "minute": 0},
        {"hour": 9, "minute": 30},
        {"hour": 12, "minute": 0},
        {"hour": 15, "minute": 0},
        {"hour": 17, "minute": 0},
        {"hour": 18, "minute": 0},
    ]

    out: list[dict[str, Any]] = []
    for slot in slots:
        h, m = slot["hour"], slot["minute"]
        target = f"{m} {h} * * 1-5"

        out.append(
            _ex("weekdays_at", user=f"Every weekday at {h}:{pad2(m)}", target=target)
        )
        out.append(
            _ex("weekdays_at", user=f"On weekdays at {h}:{pad2(m)}", target=target)
        )
        out.append(
            _ex("weekdays_at", user=f"Monday to Friday at {h}:{pad2(m)}", target=target)
        )
        out.append(
            _ex("weekdays_at", user=f"Every weekday at {to12h(h, m)}", target=target)
        )
        out.append(
            _ex(
                "weekdays_at",
                user=f"Every weekday at {to12h_compact(h, m)}",
                target=target,
            )
        )
        out.append(
            _ex("weekdays_at", user=f"Weekdays {to12h_compact(h, m)}", target=target)
        )
        out.append(
            _ex("weekdays_at", user=f"{to12h_compact(h, m)} weekdays", target=target)
        )

    return out


# ---------------------------------------------------------------------------
# 4. monthly_on_day_at
# ---------------------------------------------------------------------------


def monthly_on_day_at_examples() -> list[dict[str, Any]]:
    """A specific day of the month at a time."""
    days = [1, 2, 5, 7, 10, 12, 15, 18, 20, 21, 25, 28]
    times = [
        {"hour": 0, "minute": 0},
        {"hour": 6, "minute": 0},
        {"hour": 8, "minute": 0},
        {"hour": 9, "minute": 30},
        {"hour": 12, "minute": 30},
        {"hour": 17, "minute": 0},
    ]

    out: list[dict[str, Any]] = []
    for day in days:
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} {day} * *"

            out.append(
                _ex(
                    "monthly_on_day_at",
                    user=f"On the {ordinal(day)} day of every month at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "monthly_on_day_at",
                    user=f"Every month on day {day} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "monthly_on_day_at",
                    user=f"Run monthly on the {ordinal(day)} at {h}:{pad2(m)}",
                    target=target,
                )
            )

    return out


# ---------------------------------------------------------------------------
# 5. weekly_on_day_at
# ---------------------------------------------------------------------------


def weekly_on_day_at_examples() -> list[dict[str, Any]]:
    """A named day of the week at a specific time."""
    times = [
        {"hour": 7, "minute": 0},
        {"hour": 8, "minute": 0},
        {"hour": 8, "minute": 30},
        {"hour": 9, "minute": 0},
        {"hour": 9, "minute": 45},
        {"hour": 10, "minute": 30},
        {"hour": 12, "minute": 0},
        {"hour": 14, "minute": 0},
        {"hour": 15, "minute": 30},
        {"hour": 17, "minute": 15},
        {"hour": 19, "minute": 0},
        {"hour": 20, "minute": 0},
        {"hour": 22, "minute": 30},
    ]

    out: list[dict[str, Any]] = []
    for day in WEEKDAYS:
        name = str(day["name"])
        short = str(day["short"])
        cron_val = int(day["cron"])  # type: ignore[arg-type]
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} * * {cron_val}"

            out.append(
                _ex(
                    "weekly_on_day_at",
                    user=f"Every {name} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "weekly_on_day_at",
                    user=f"On {name} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex("weekly_on_day_at", user=f"{short} at {h}:{pad2(m)}", target=target)
            )
            out.append(
                _ex(
                    "weekly_on_day_at",
                    user=f"Every {name} at {to12h(h, m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "weekly_on_day_at",
                    user=f"{short} {to12h_compact(h, m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "weekly_on_day_at",
                    user=f"{to12h_compact(h, m)} {short.lower()}",
                    target=target,
                )
            )

    return out


# ---------------------------------------------------------------------------
# 6. hour_range_at
# ---------------------------------------------------------------------------


def hour_range_at_examples() -> list[dict[str, Any]]:
    """A range of hours at a specific minute."""
    ranges: list[dict[str, Any]] = [
        {"from": 9, "to": 17, "minute": 0},
        {"from": 9, "to": 17, "minute": 30},
        {"from": 8, "to": 20, "minute": 0},
        {"from": 6, "to": 22, "minute": 15},
    ]

    out: list[dict[str, Any]] = []
    for r in ranges:
        frm, to, m = r["from"], r["to"], r["minute"]
        target = f"{m} {frm}-{to} * * *"

        out.append(
            _ex(
                "hour_range_at",
                user=f"Every hour from {frm}:00 to {to}:00 at minute {m}",
                target=target,
            )
        )
        out.append(
            _ex(
                "hour_range_at",
                user=f"Every hour between {frm} and {to} at {m} past",
                target=target,
            )
        )
        out.append(
            _ex(
                "hour_range_at",
                user=f"From {frm}:00 to {to}:00 every hour at minute {m}",
                target=target,
            )
        )

    return out


# ---------------------------------------------------------------------------
# 7. multi_weekday_at
# ---------------------------------------------------------------------------


def multi_weekday_at_examples() -> list[dict[str, Any]]:
    """A list of specific named days at a time."""
    combos = [
        {"days": [1, 3, 5], "label": "Monday, Wednesday, and Friday"},
        {"days": [2, 4], "label": "Tuesday and Thursday"},
        {"days": [1, 5], "label": "Monday and Friday"},
        {"days": [3, 6], "label": "Wednesday and Saturday"},
    ]

    times = [
        {"hour": 8, "minute": 0},
        {"hour": 10, "minute": 0},
        {"hour": 15, "minute": 45},
    ]

    out: list[dict[str, Any]] = []
    for combo in combos:
        days, label = combo["days"], combo["label"]
        cron_days = ",".join(str(d) for d in days)
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} * * {cron_days}"

            out.append(
                _ex(
                    "multi_weekday_at",
                    user=f"Every {label} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "multi_weekday_at",
                    user=f"On {label} at {h}:{pad2(m)}",
                    target=target,
                )
            )

            # Compact version without "and"
            compact_label = label.replace(", and ", " ").replace(" and ", " ")
            out.append(
                _ex(
                    "multi_weekday_at",
                    user=f"{compact_label} {to12h_compact(h, m)}",
                    target=target,
                )
            )

    return out


# ---------------------------------------------------------------------------
# 8. midnight_noon_at
# ---------------------------------------------------------------------------


def midnight_noon_at_examples() -> list[dict[str, Any]]:
    """Midnight, noon, and other common time phrases."""
    return [
        _ex("midnight_noon_at", user="At midnight", target="0 0 * * *"),
        _ex("midnight_noon_at", user="Every night at midnight", target="0 0 * * *"),
        _ex("midnight_noon_at", user="Run at midnight", target="0 0 * * *"),
        _ex("midnight_noon_at", user="At noon", target="0 12 * * *"),
        _ex("midnight_noon_at", user="Every day at noon", target="0 12 * * *"),
        _ex("midnight_noon_at", user="Run at noon every day", target="0 12 * * *"),
        _ex("midnight_noon_at", user="At midnight on weekdays", target="0 0 * * 1-5"),
        _ex("midnight_noon_at", user="Every weekday at midnight", target="0 0 * * 1-5"),
        _ex("midnight_noon_at", user="Every hour", target="0 * * * *"),
        _ex("midnight_noon_at", user="Run every hour", target="0 * * * *"),
        _ex("midnight_noon_at", user="At the top of every hour", target="0 * * * *"),
        _ex("midnight_noon_at", user="On the hour", target="0 * * * *"),
        _ex("midnight_noon_at", user="Every half hour", target="*/30 * * * *"),
        _ex("midnight_noon_at", user="Every quarter hour", target="*/15 * * * *"),
    ]


# ---------------------------------------------------------------------------
# 9. hourly_at_minute
# ---------------------------------------------------------------------------


def hourly_at_minute_examples() -> list[dict[str, Any]]:
    """A specific minute past every hour."""
    minutes = [0, 5, 10, 15, 25, 30, 45, 55]
    out: list[dict[str, Any]] = []

    for minute in minutes:
        target = f"{minute} * * * *"

        out.append(
            _ex("hourly_at_minute", user=f"At {minute} past every hour", target=target)
        )
        out.append(
            _ex(
                "hourly_at_minute",
                user=f"At minute {minute} of every hour",
                target=target,
            )
        )
        out.append(
            _ex(
                "hourly_at_minute",
                user=f"{minute} minutes past every hour",
                target=target,
            )
        )

        if minute == 0:
            out.append(
                _ex(
                    "hourly_at_minute", user="At the start of every hour", target=target
                )
            )
        elif minute == 15:
            out.append(
                _ex(
                    "hourly_at_minute", user="At quarter past every hour", target=target
                )
            )
        elif minute == 30:
            out.append(
                _ex("hourly_at_minute", user="At half past every hour", target=target)
            )
        elif minute == 45:
            out.append(
                _ex("hourly_at_minute", user="At quarter to every hour", target=target)
            )

    return out


# ---------------------------------------------------------------------------
# 10. twice_daily
# ---------------------------------------------------------------------------


def twice_daily_examples() -> list[dict[str, Any]]:
    """Two specific times every day."""
    pairs: list[dict[str, Any]] = [
        {"h1": 8, "m1": 0, "h2": 20, "m2": 0},
        {"h1": 9, "m1": 0, "h2": 17, "m2": 30},
        {"h1": 6, "m1": 30, "h2": 18, "m2": 30},
        {"h1": 7, "m1": 0, "h2": 19, "m2": 0},
        {"h1": 12, "m1": 0, "h2": 23, "m2": 0},
    ]

    out: list[dict[str, Any]] = []
    for p in pairs:
        h1, m1, h2, m2 = p["h1"], p["m1"], p["h2"], p["m2"]
        target = f"{m1} {h1},{h2} * * *"

        out.append(
            _ex(
                "twice_daily",
                user=f"At {h1}:{pad2(m1)} and {h2}:{pad2(m2)} every day",
                target=target,
            )
        )
        out.append(
            _ex(
                "twice_daily",
                user=f"Twice a day at {h1}:{pad2(m1)} and {h2}:{pad2(m2)}",
                target=target,
            )
        )
        out.append(
            _ex(
                "twice_daily",
                user=f"Every day at {h1}:{pad2(m1)} and {h2}:{pad2(m2)}",
                target=target,
            )
        )

    return out


# ---------------------------------------------------------------------------
# 11. weekend_at
# ---------------------------------------------------------------------------


def weekend_at_examples() -> list[dict[str, Any]]:
    """Saturday and Sunday at a specific time."""
    times = [
        {"hour": 7, "minute": 0},
        {"hour": 9, "minute": 0},
        {"hour": 10, "minute": 30},
        {"hour": 14, "minute": 0},
        {"hour": 18, "minute": 0},
        {"hour": 20, "minute": 30},
    ]

    out: list[dict[str, Any]] = []
    for slot in times:
        h, m = slot["hour"], slot["minute"]
        target = f"{m} {h} * * 6,0"

        out.append(
            _ex("weekend_at", user=f"Every weekend at {h}:{pad2(m)}", target=target)
        )
        out.append(
            _ex("weekend_at", user=f"On weekends at {h}:{pad2(m)}", target=target)
        )
        out.append(
            _ex(
                "weekend_at",
                user=f"Saturday and Sunday at {h}:{pad2(m)}",
                target=target,
            )
        )
        out.append(
            _ex(
                "weekend_at",
                user=f"Every Saturday and Sunday at {to12h(h, m)}",
                target=target,
            )
        )
        out.append(
            _ex("weekend_at", user=f"Weekends {to12h_compact(h, m)}", target=target)
        )
        out.append(
            _ex("weekend_at", user=f"Sat Sun {to12h_compact(h, m)}", target=target)
        )

    return out


# ---------------------------------------------------------------------------
# 12. except_weekday_at
# ---------------------------------------------------------------------------


def except_weekday_at_examples() -> list[dict[str, Any]]:
    """Weekdays minus a specific day at a time."""
    except_day = [
        {"day": "Monday", "short": "Monday", "dow": 1, "exclude": [2, 3, 4, 5]},
        {"day": "Friday", "short": "Friday", "dow": 5, "exclude": [1, 2, 3, 4]},
        {"day": "Wednesday", "short": "Wednesday", "dow": 3, "exclude": [1, 2, 4, 5]},
    ]

    times = [
        {"hour": 8, "minute": 0},
        {"hour": 9, "minute": 0},
        {"hour": 17, "minute": 0},
        {"hour": 18, "minute": 0},
    ]

    out: list[dict[str, Any]] = []

    for ed in except_day:
        day, short, exclude = ed["day"], ed["short"], ed["exclude"]
        cron_days = ",".join(str(d) for d in exclude)
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} * * {cron_days}"

            out.append(
                _ex(
                    "except_weekday_at",
                    user=f"Every weekday except {day} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "except_weekday_at",
                    user=f"Weekdays except {short} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "except_weekday_at",
                    user=f"Every week day except {day} at {to12h(h, m)}",
                    target=target,
                )
            )

    # Also add "every day except Sunday/Saturday" patterns
    daily_except = [
        {"day": "Sunday", "cron": 0, "other": [1, 2, 3, 4, 5, 6]},
        {"day": "Saturday", "cron": 6, "other": [1, 2, 3, 4, 5, 0]},
    ]

    for de in daily_except:
        day, other = de["day"], de["other"]
        cron_days = ",".join(str(d) for d in other)
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} * * {cron_days}"

            out.append(
                _ex(
                    "except_weekday_at",
                    user=f"Every day except {day} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "except_weekday_at",
                    user=f"Daily except {day} at {to12h(h, m)}",
                    target=target,
                )
            )

    return out


# ---------------------------------------------------------------------------
# 13. every_n_hours
# ---------------------------------------------------------------------------


def every_n_hours_examples() -> list[dict[str, Any]]:
    """Recurring interval in hours."""
    values = [2, 3, 4, 6, 8, 12]
    out: list[dict[str, Any]] = []

    for n in values:
        target = f"0 */{n} * * *"
        out.append(_ex("every_n_hours", user=f"Every {n} hours", target=target))
        out.append(_ex("every_n_hours", user=f"Run every {n} hours", target=target))
        out.append(_ex("every_n_hours", user=f"Once every {n} hours", target=target))
        out.append(_ex("every_n_hours", user=f"Every {n}h", target=target))
        out.append(_ex("every_n_hours", user=f"Every {n} hrs", target=target))
        if n == 2:
            out.append(_ex("every_n_hours", user="Every other hour", target=target))

    return out


# ---------------------------------------------------------------------------
# 14. every_n_days
# ---------------------------------------------------------------------------


def every_n_days_examples() -> list[dict[str, Any]]:
    """Recurring interval in days."""
    values = [2, 3, 7, 14]
    out: list[dict[str, Any]] = []

    for n in values:
        target = f"0 0 */{n} * *"
        out.append(_ex("every_n_days", user=f"Every {n} days", target=target))
        out.append(_ex("every_n_days", user=f"Run every {n} days", target=target))

        if n == 7:
            out.append(_ex("every_n_days", user="Every week", target=target))
        elif n == 14:
            out.append(_ex("every_n_days", user="Every two weeks", target=target))
        else:
            out.append(_ex("every_n_days", user=f"Once every {n} days", target=target))

        if n == 2:
            out.append(_ex("every_n_days", user="Every other day", target=target))

    return out


# ---------------------------------------------------------------------------
# 15. cron_aliases
# ---------------------------------------------------------------------------


def cron_aliases_examples() -> list[dict[str, Any]]:
    """Standard cron @-aliases and natural language shorthands."""
    out: list[dict[str, Any]] = []

    # every minute
    out.append(_ex("cron_aliases", user="every minute", target="* * * * *"))
    out.append(_ex("cron_aliases", user="Run every minute", target="* * * * *"))

    # @-syntax aliases
    out.append(_ex("cron_aliases", user="@daily", target="0 0 * * *"))
    out.append(_ex("cron_aliases", user="@hourly", target="0 * * * *"))
    out.append(_ex("cron_aliases", user="@weekly", target="0 0 * * 0"))
    out.append(_ex("cron_aliases", user="@monthly", target="0 0 1 * *"))
    out.append(_ex("cron_aliases", user="@yearly", target="0 0 1 1 *"))
    out.append(_ex("cron_aliases", user="@annually", target="0 0 1 1 *"))
    out.append(_ex("cron_aliases", user="@midnight", target="0 0 * * *"))

    # natural language standalone shorthands
    out.append(_ex("cron_aliases", user="hourly", target="0 * * * *"))
    out.append(_ex("cron_aliases", user="daily", target="0 0 * * *"))
    out.append(_ex("cron_aliases", user="weekly", target="0 0 * * 0"))
    out.append(_ex("cron_aliases", user="monthly", target="0 0 1 * *"))
    out.append(_ex("cron_aliases", user="yearly", target="0 0 1 1 *"))
    out.append(_ex("cron_aliases", user="annually", target="0 0 1 1 *"))
    out.append(
        _ex("cron_aliases", user="every minute of every day", target="* * * * *")
    )

    return out


# ---------------------------------------------------------------------------
# 16. month_specific
# ---------------------------------------------------------------------------


def month_specific_examples() -> list[dict[str, Any]]:
    """Month-specific patterns with optional day and time."""
    months = [
        {"name": "January", "num": 1},
        {"name": "February", "num": 2},
        {"name": "March", "num": 3},
        {"name": "April", "num": 4},
        {"name": "May", "num": 5},
        {"name": "June", "num": 6},
        {"name": "July", "num": 7},
        {"name": "August", "num": 8},
        {"name": "September", "num": 9},
        {"name": "October", "num": 10},
        {"name": "November", "num": 11},
        {"name": "December", "num": 12},
    ]

    days = [1, 5, 10, 15, 20, 25]
    times = [
        {"hour": 0, "minute": 0},
        {"hour": 8, "minute": 0},
        {"hour": 9, "minute": 0},
    ]

    out: list[dict[str, Any]] = []

    # "Every January at 8:00" → 0 8 * 1 *
    for mo in months:
        name, num = mo["name"], mo["num"]
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} * {num} *"

            out.append(
                _ex(
                    "month_specific",
                    user=f"Every {name} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex("month_specific", user=f"In {name} at {h}:{pad2(m)}", target=target)
            )

    # "On January 15th at 9:00" → 0 9 15 1 *
    for mo in months[:6]:
        name, num = mo["name"], mo["num"]
        for day in days:
            out.append(
                _ex(
                    "month_specific",
                    user=f"On {name} {ordinal(day)} at 9:00",
                    target=f"0 9 {day} {num} *",
                )
            )

    return out


# ---------------------------------------------------------------------------
# 17. partial_week_range
# ---------------------------------------------------------------------------


def partial_week_range_examples() -> list[dict[str, Any]]:
    """A sub-range of consecutive weekdays."""
    ranges = [
        {"from": 1, "to": 4, "label": "Monday through Thursday"},
        {"from": 2, "to": 5, "label": "Tuesday to Friday"},
        {"from": 1, "to": 3, "label": "Monday through Wednesday"},
        {"from": 3, "to": 5, "label": "Wednesday to Friday"},
    ]

    times = [
        {"hour": 8, "minute": 0},
        {"hour": 17, "minute": 0},
    ]

    out: list[dict[str, Any]] = []
    for r in ranges:
        frm, to, label = r["from"], r["to"], r["label"]
        for slot in times:
            h, m = slot["hour"], slot["minute"]
            target = f"{m} {h} * * {frm}-{to}"

            out.append(
                _ex(
                    "partial_week_range",
                    user=f"Every {label} at {h}:{pad2(m)}",
                    target=target,
                )
            )
            out.append(
                _ex(
                    "partial_week_range",
                    user=f"{label} at {h}:{pad2(m)}",
                    target=target,
                )
            )

    return out


# ---------------------------------------------------------------------------
# 18. invalid
# ---------------------------------------------------------------------------


def invalid_examples() -> list[dict[str, Any]]:
    """Off-topic prompts that should map to INVALID."""
    inputs = [
        "What is the capital of France?",
        "Write a poem about the ocean",
        "Translate this sentence to German",
        "How do I reverse a linked list?",
        "What is 27 multiplied by 14?",
        "Tell me a joke",
        "Summarize this article",
        "Generate a Docker Compose file",
        "Who won the World Cup?",
        "Explain quantum computing simply",
        "Book a flight to Tokyo",
        "Set the brightness to 80 percent",
        "Show me the weather for tomorrow",
        "Sort this array in ascending order",
        "What time is it in New York?",
        "Write a Python function to sort a list",
        "How do I make pancakes?",
        "What is the meaning of life?",
        "Convert 100 USD to EUR",
        "How tall is Mount Everest?",
        "Create a React component for a login form",
        "What are the symptoms of a cold?",
        "Write a haiku about spring",
        "How do I install Docker on Ubuntu?",
        "What is the speed of light?",
        "Name three types of cloud computing",
        "How far is the moon from Earth?",
        "Define artificial intelligence",
        "Write a regular expression to match email addresses",
        "What is the derivative of x squared?",
        "Fix the bug in this code",
        "Write a cover letter for a job application",
        "What is the boiling point of water?",
        "How do I cook rice?",
        "Explain how blockchain works",
        "What year did World War II end?",
        "Design a database schema for a blog",
        "Write unit tests for this function",
        "How much does an elephant weigh?",
        "What is photosynthesis?",
    ]

    return [_ex("invalid", user=text, target="INVALID") for text in inputs]


# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------


def build_base_dataset() -> list[dict[str, Any]]:
    """Build the complete base dataset from all template families."""
    from .utils import dedupe

    return dedupe(
        [
            *daily_at_examples(),
            *every_n_minutes_examples(),
            *weekdays_at_examples(),
            *monthly_on_day_at_examples(),
            *weekly_on_day_at_examples(),
            *hour_range_at_examples(),
            *multi_weekday_at_examples(),
            *midnight_noon_at_examples(),
            *hourly_at_minute_examples(),
            *twice_daily_examples(),
            *weekend_at_examples(),
            *except_weekday_at_examples(),
            *every_n_hours_examples(),
            *every_n_days_examples(),
            *cron_aliases_examples(),
            *month_specific_examples(),
            *partial_week_range_examples(),
            *invalid_examples(),
        ]
    )
