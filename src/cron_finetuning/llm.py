"""LLM-based augmentation for the cron dataset.

Uses OpenRouter API (or any OpenAI-compatible endpoint) to generate:
- Paraphrases of valid cron examples
- Additional off-topic INVALID prompts
"""

from __future__ import annotations

import os
from typing import Any

from .constants import DEFAULT_MODEL, OPENROUTER_URL
from .utils import dedupe, is_semantically_consistent


def _get_headers(api_key: str) -> dict[str, str]:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://local.dataset.generator",
        "X-Title": "cron-dataset-generator",
    }


def _call_openrouter_text(
    api_key: str,
    model: str,
    system_prompt: str,
    user_prompt: str,
    base_url: str = OPENROUTER_URL,
) -> str:
    """Call the OpenRouter (or any OpenAI-compatible) API and return the text response."""
    import json as _json
    import urllib.request

    body = _json.dumps(
        {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0.9,
            "stream": False,
        }
    ).encode("utf-8")

    req = urllib.request.Request(base_url, data=body, headers=_get_headers(api_key))
    req.add_header("Content-Type", "application/json")

    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = _json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        raise RuntimeError(f"OpenRouter API call failed: {e}") from e

    content = data.get("choices", [{}])[0].get("message", {}).get("content")
    if not isinstance(content, str):
        raise RuntimeError("OpenRouter returned no message content")

    return content


def _parse_line_list(text: str) -> list[str]:
    """Parse a numbered/bulleted list into individual lines."""
    import re

    lines = []
    for line in text.split("\n"):
        cleaned = re.sub(r"^\d+[\).\s]\s*", "", line).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def _make_valid_paraphrase_prompt(seed: dict[str, Any], count: int) -> str:
    return "\n".join(
        [
            f"Generate {count} natural English user requests that map to this cron expression.",
            f"Cron: {seed['target']}",
            f"Family: {seed['family']}",
            f'Example: "{seed["user"]}"',
            "",
            "Rules:",
            "- English only",
            "- preserve meaning exactly — if the cron has day-of-week constraints (like Mon,Wed,Fri), your paraphrases MUST mention those specific days",
            "- do NOT use 'daily' or 'every day' unless the cron runs every day (day-of-month = *, day-of-week = *)",
            "- do NOT use 'weekdays' or 'Monday to Friday' unless the cron restricts to 1-5",
            "- do not mention cron syntax",
            "- do not explain anything",
            "- keep each prompt short and natural",
            "- one request per line, no numbering",
        ]
    )


def _make_invalid_prompt(count: int) -> str:
    return "\n".join(
        [
            f"Generate {count} realistic English user prompts that are NOT requests for cron/scheduling.",
            "",
            "Rules:",
            "- clearly off-topic or unrelated to scheduling",
            "- no scheduling requests",
            "- short and realistic",
            "- one prompt per line, no numbering",
        ]
    )


def generate_valid_paraphrases(
    api_key: str,
    model: str,
    seeds: list[dict[str, Any]],
    count_per_seed: int = 4,
) -> list[dict[str, Any]]:
    """Generate LLM-paraphrased versions of valid cron examples."""
    out: list[dict[str, Any]] = []

    for seed in seeds:
        if seed["target"] == "INVALID":
            continue

        prompt = _make_valid_paraphrase_prompt(seed, count_per_seed)
        try:
            text = _call_openrouter_text(
                api_key,
                model,
                "Return only the requested lines, no numbering, no explanation.",
                prompt,
            )
        except Exception as e:
            print(f"  Warning: LLM call failed for seed '{seed['user'][:50]}...': {e}")
            continue

        lines = _parse_line_list(text)
        for user in lines:
            if not is_semantically_consistent(user, seed["target"]):
                continue
            out.append(
                {
                    "user": user,
                    "target": seed["target"],
                    "family": seed["family"],
                    "source": "llm",
                }
            )

    return out


def generate_invalid_with_llm(
    api_key: str,
    model: str,
    count: int = 50,
) -> list[dict[str, Any]]:
    """Generate additional off-topic prompts using an LLM."""
    prompt = _make_invalid_prompt(count)
    try:
        text = _call_openrouter_text(
            api_key,
            model,
            "Return only the requested lines, no numbering, no explanation.",
            prompt,
        )
    except Exception as e:
        print(f"  Warning: LLM call for invalid prompts failed: {e}")
        return []

    lines = _parse_line_list(text)
    return [
        {
            "user": user,
            "target": "INVALID",
            "family": "invalid",
            "source": "llm",
        }
        for user in lines
    ]


def maybe_generate_synthetic_data(base: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Generate LLM-augmented data if an API key is available."""
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if not api_key:
        print("OPENROUTER_API_KEY not set; skipping LLM augmentation.")
        return []

    model = os.environ.get("OPENROUTER_MODEL", DEFAULT_MODEL)
    print(f"Using model: {model}")

    # Pick a subset of valid seeds for paraphrasing
    valid_seeds = [
        x
        for x in base
        if x["target"] != "INVALID"
        and x["family"]
        in (
            "daily_at",
            "every_n_minutes",
            "weekdays_at",
            "monthly_on_day_at",
            "weekly_on_day_at",
        )
    ][:40]

    print(f"Generating paraphrases from {len(valid_seeds)} seeds...")
    valid_synthetic = generate_valid_paraphrases(
        api_key, model, valid_seeds, count_per_seed=4
    )
    print(f"  Got {len(valid_synthetic)} valid paraphrases")

    print("Generating off-topic INVALID prompts...")
    invalid_synthetic = generate_invalid_with_llm(api_key, model, count=50)
    print(f"  Got {len(invalid_synthetic)} INVALID prompts")

    return dedupe([*valid_synthetic, *invalid_synthetic])
