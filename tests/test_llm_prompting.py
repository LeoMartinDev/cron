from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cron_finetuning.llm import (  # noqa: E402
    WRITING_STYLES,
    _make_invalid_prompt,
    _make_valid_paraphrase_prompt,
    _parse_styled_lines,
    generate_valid_paraphrases,
)


class LLMPromptingTests(unittest.TestCase):
    def setUp(self) -> None:
        self.seed = {
            "user": "every day at 9:00",
            "target": "0 9 * * *",
            "family": "daily_at",
            "source": "template",
        }

    def test_valid_paraphrase_prompt_requests_each_style(self) -> None:
        prompt = _make_valid_paraphrase_prompt(self.seed, styles=WRITING_STYLES)

        self.assertIn("Generate 7 natural English user requests", prompt)
        self.assertIn("Create exactly one request for each writing style below:", prompt)
        self.assertIn("each line must start with the exact style label followed by ':'", prompt)
        for style in WRITING_STYLES:
            self.assertIn(f"- {style['name']}:", prompt)
            self.assertIn(f"{style['name']}: <request>", prompt)

    def test_parse_styled_lines_reads_labeled_output(self) -> None:
        text = "\n".join(
            [
                "1. precise: Every day at 9:00",
                "concise: daily 9am",
                "hurried: need this every day at 9am",
                "sloppy: everyday 9am",
                "shorthand: 9am daily",
                "conversational: run this every day at 9 in the morning",
                "polite: please run every day at 9 am",
            ]
        )

        parsed = _parse_styled_lines(text, styles=WRITING_STYLES)

        self.assertEqual(len(parsed), 7)
        self.assertEqual(parsed[0], ("precise", "Every day at 9:00"))
        self.assertEqual(parsed[-1], ("polite", "please run every day at 9 am"))

    def test_invalid_prompt_requests_style_mix(self) -> None:
        prompt = _make_invalid_prompt(50)

        self.assertIn("Generate 50 realistic English user prompts", prompt)
        self.assertIn("vary the writing style across the set", prompt)
        for style in WRITING_STYLES:
            self.assertIn(style["name"], prompt)

    def test_generate_valid_paraphrases_keeps_style_metadata(self) -> None:
        model_output = "\n".join(
            [
                "precise: Every day at 9:00",
                "concise: daily 9am",
                "hurried: need this every day at 9am",
                "sloppy: everyday 9am",
                "shorthand: 9am daily",
                "conversational: run this every day at 9 in the morning",
                "polite: please run every day at 9 am",
            ]
        )

        with patch("cron_finetuning.llm._call_openrouter_text", return_value=model_output):
            examples = generate_valid_paraphrases("fake-key", "fake-model", [self.seed], styles=WRITING_STYLES)

        self.assertEqual(len(examples), 7)
        self.assertEqual({example["style"] for example in examples}, {style["name"] for style in WRITING_STYLES})
        self.assertTrue(all(example["source"] == "llm" for example in examples))
        self.assertTrue(all(example["target"] == "0 9 * * *" for example in examples))


if __name__ == "__main__":
    unittest.main()
