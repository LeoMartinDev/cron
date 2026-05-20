"""Constants and type definitions for the cron dataset generator."""

from __future__ import annotations

from typing import Literal

# System prompt used for all training examples
SYSTEM_PROMPT: str = (
    "You must reply with either a 5-field Unix cron expression "
    "or the single token INVALID. No explanation."
)

# Cron family types
Family = Literal[
    "daily_at",
    "every_n_minutes",
    "weekdays_at",
    "monthly_on_day_at",
    "weekly_on_day_at",
    "hour_range_at",
    "multi_weekday_at",
    "midnight_noon_at",
    "hourly_at_minute",
    "twice_daily",
    "weekend_at",
    "except_weekday_at",
    "every_n_hours",
    "every_n_days",
    "cron_aliases",
    "month_specific",
    "partial_week_range",
    "invalid",
]

# Source of an example
Source = Literal["template", "llm"]

# Weekday mapping: name -> (short, cron_number)
# NOTE: Monday-Friday only (the original dataset does not generate
# weekly_on_day examples for Saturday/Sunday — those are covered by weekend_at)
WEEKDAYS: list[dict[str, object]] = [
    {"name": "Monday", "short": "Mon", "cron": 1},
    {"name": "Tuesday", "short": "Tue", "cron": 2},
    {"name": "Wednesday", "short": "Wed", "cron": 3},
    {"name": "Thursday", "short": "Thu", "cron": 4},
    {"name": "Friday", "short": "Fri", "cron": 5},
]

# OpenRouter API endpoint
OPENROUTER_URL: str = "https://openrouter.ai/api/v1/chat/completions"

# Default model for LLM augmentation
DEFAULT_MODEL: str = "google/gemini-3.1-flash-litei"

# Default HuggingFace Hub repositories
HUB_MODEL_REPO_ID: str | None = "leom21/cron"  # e.g. "username/cron-model"
HUB_DATASET_REPO_ID: str | None = "leom21/cron"  # e.g. "username/cron-dataset"

# Default base model for fine-tuning and inference
BASE_MODEL: str = "unsloth/SmolLM2-360M-Instruct"

# Default paths
DEFAULT_DATA_DIR: str = "data"
DEFAULT_OUTPUT_DIR: str = "output/cron-model"
DEFAULT_CHECKPOINT: str = "output/cron-model/final"
