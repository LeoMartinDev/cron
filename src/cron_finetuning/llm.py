"""LLM-based augmentation for the cron dataset.

Uses OpenRouter API (or any OpenAI-compatible endpoint) to generate:
- Paraphrases of valid cron examples
- Additional off-topic INVALID prompts
"""

from __future__ import annotations

import os
from collections import defaultdict
from typing import Any

from .constants import DEFAULT_MODEL, OPENROUTER_URL
from .utils import dedupe, is_semantically_consistent

WRITING_STYLES: tuple[dict[str, str], ...] = (
    {
        "name": "precise",
        "description": "fully specified, explicit, and unambiguous",
    },
    {
        "name": "concise",
        "description": "short and efficient, but still clear",
    },
    {
        "name": "hurried",
        "description": "typed quickly with minimal filler words",
    },
    {
        "name": "sloppy",
        "description": "slightly messy or casual, still readable English",
    },
    {
        "name": "shorthand",
        "description": "telegraphic shorthand with compact time notation when natural",
    },
    {
        "name": "conversational",
        "description": "natural spoken wording, like a casual request",
    },
    {
        "name": "polite",
        "description": "courteous wording such as please or can you",
    },
)


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


def _style_names(styles: tuple[dict[str, str], ...]) -> tuple[str, ...]:
    return tuple(style["name"] for style in styles)


def _parse_styled_lines(
    text: str,
    styles: tuple[dict[str, str], ...] = WRITING_STYLES,
) -> list[tuple[str, str]]:
    """Parse style-labeled model output into (style, user_prompt) tuples."""
    import re

    lines = _parse_line_list(text)
    style_names = _style_names(styles)
    style_pattern = "|".join(re.escape(name) for name in style_names)
    pattern = re.compile(rf"^(?P<style>{style_pattern})\s*[:\-]\s*(?P<user>.+)$", re.IGNORECASE)

    parsed: list[tuple[str, str]] = []
    seen_styles: set[str] = set()
    remaining_styles = list(style_names)

    for line in lines:
        match = pattern.match(line)
        if match:
            style = match.group("style").lower()
            user = match.group("user").strip()
            if user and style not in seen_styles:
                parsed.append((style, user))
                seen_styles.add(style)
                if style in remaining_styles:
                    remaining_styles.remove(style)
            continue

        if remaining_styles:
            style = remaining_styles.pop(0)
            user = line.strip()
            if user:
                parsed.append((style, user))
                seen_styles.add(style)

    return parsed


def _make_valid_paraphrase_prompt(
    seed: dict[str, Any],
    styles: tuple[dict[str, str], ...] = WRITING_STYLES,
) -> str:
    style_lines = [f"- {style['name']}: {style['description']}" for style in styles]
    output_format = [f"{style['name']}: <request>" for style in styles]

    return "\n".join(
        [
            f"Generate {len(styles)} natural English user requests that map to this cron expression.",
            f"Cron: {seed['target']}",
            f"Family: {seed['family']}",
            f'Example: "{seed["user"]}"',
            "",
            "Create exactly one request for each writing style below:",
            *style_lines,
            "",
            "Output format:",
            *output_format,
            "",
            "Rules:",
            "- English only",
            "- preserve meaning exactly — if the cron has day-of-week constraints (like Mon,Wed,Fri), your paraphrases MUST mention those specific days",
            "- do NOT use 'daily' or 'every day' unless the cron runs every day (day-of-month = *, day-of-week = *)",
            "- do NOT use 'weekdays' or 'Monday to Friday' unless the cron restricts to 1-5",
            "- each line must start with the exact style label followed by ':'",
            "- do not mention cron syntax",
            "- do not explain anything",
            "- keep each prompt short, natural, and meaning-preserving",
            "- one request per line, no numbering",
        ]
    )


def _make_invalid_prompt(count: int) -> str:
    style_names = ", ".join(style["name"] for style in WRITING_STYLES)
    return "\n".join(
        [
            f"Generate {count} realistic English user prompts that are NOT requests for cron/scheduling.",
            "",
            "Rules:",
            "- clearly off-topic or unrelated to scheduling",
            "- no scheduling requests",
            "- short and realistic",
            f"- vary the writing style across the set; mix tones like: {style_names}",
            "- one prompt per line, no numbering",
        ]
    )


def generate_valid_paraphrases(
    api_key: str,
    model: str,
    seeds: list[dict[str, Any]],
    styles: tuple[dict[str, str], ...] = WRITING_STYLES,
) -> list[dict[str, Any]]:
    """Generate LLM-paraphrased versions of valid cron examples."""
    out: list[dict[str, Any]] = []

    for seed in seeds:
        if seed["target"] == "INVALID":
            continue

        prompt = _make_valid_paraphrase_prompt(seed, styles=styles)
        try:
            text = _call_openrouter_text(
                api_key,
                model,
                "Return only the requested style-labeled lines, no numbering, no explanation.",
                prompt,
            )
        except Exception as e:
            print(f"  Warning: LLM call failed for seed '{seed['user'][:50]}...': {e}")
            continue

        styled_lines = _parse_styled_lines(text, styles=styles)
        for style_name, user in styled_lines:
            if not is_semantically_consistent(user, seed["target"]):
                continue
            out.append(
                {
                    "user": user,
                    "target": seed["target"],
                    "family": seed["family"],
                    "source": "llm",
                    "style": style_name,
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

    # Pick a balanced subset of valid seeds for paraphrasing.
    seed_families = (
        "daily_at",
        "every_n_minutes",
        "weekdays_at",
        "monthly_on_day_at",
        "weekly_on_day_at",
        "multi_time_at",
    )
    per_family_limit = 8
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for example in base:
        family = example["family"]
        if example["target"] == "INVALID" or family not in seed_families:
            continue
        if len(grouped[family]) < per_family_limit:
            grouped[family].append(example)

    valid_seeds = [seed for family in seed_families for seed in grouped[family]]

    print(f"Generating paraphrases from {len(valid_seeds)} seeds across {len(WRITING_STYLES)} styles...")
    valid_synthetic = generate_valid_paraphrases(api_key, model, valid_seeds, styles=WRITING_STYLES)
    print(f"  Got {len(valid_synthetic)} valid paraphrases")

    print("Generating off-topic INVALID prompts...")
    invalid_synthetic = generate_invalid_with_llm(api_key, model, count=50)
    print(f"  Got {len(invalid_synthetic)} INVALID prompts")

    return dedupe([*valid_synthetic, *invalid_synthetic])
