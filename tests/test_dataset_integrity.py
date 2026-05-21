from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "src"))

from cron_finetuning.dataset import read_jsonl, write_jsonl
from cron_finetuning.families import build_base_dataset
from cron_finetuning.utils import is_cron_target, is_semantically_consistent


class DatasetIntegrityTests(unittest.TestCase):
    def test_every_60_minutes_maps_to_valid_hourly_cron(self) -> None:
        examples = build_base_dataset()
        targets = {
            example["target"]
            for example in examples
            if example["family"] == "every_n_minutes" and example["user"] == "every 60 minutes"
        }
        self.assertEqual(targets, {"0 * * * *"})

    def test_non_representable_multi_time_seed_is_removed(self) -> None:
        examples = build_base_dataset()
        users = {example["user"] for example in examples if example["family"] == "multi_time_at"}
        self.assertNotIn("twice a day at 9:00 and 17:30", users)

    def test_multi_time_daily_everyday_variant_maps_to_canonical_cron(self) -> None:
        examples = build_base_dataset()
        targets = {
            example["target"]
            for example in examples
            if example["family"] == "multi_time_at"
            and example["user"] == "everyday at 9pm and 5 am"
        }
        self.assertEqual(targets, {"0 5,21 * * *"})

    def test_multi_time_weekly_variant_maps_to_canonical_cron(self) -> None:
        examples = build_base_dataset()
        targets = {
            example["target"]
            for example in examples
            if example["family"] == "multi_time_at"
            and example["user"] == "every monday at 9 am and 5 pm"
        }
        self.assertEqual(targets, {"0 9,17 * * 1"})

    def test_multi_time_examples_cover_weekly_monthly_and_month_specific_shapes(self) -> None:
        examples = build_base_dataset()
        lookup = {
            example["user"]: example["target"]
            for example in examples
            if example["family"] == "multi_time_at"
        }
        self.assertEqual(lookup["every monday, wednesday, and friday at 9 am and 5 pm"], "0 9,17 * * 1,3,5")
        self.assertEqual(lookup["every monday through thursday at 9 am and 5 pm"], "0 9,17 * * 1-4")
        self.assertEqual(lookup["every weekday except monday at 9 am and 5 pm"], "0 9,17 * * 2,3,4,5")
        self.assertEqual(lookup["on the 15th day of every month at 8 am and 8 pm"], "0 8,20 15 * *")
        self.assertEqual(lookup["every january at 8 am and 8 pm"], "0 8,20 * 1 *")
        self.assertEqual(lookup["on january 5th at 9 am and 5 pm"], "0 9,17 5 1 *")

    def test_cron_validation_rejects_out_of_range_steps(self) -> None:
        self.assertFalse(is_cron_target("*/60 * * * *"))
        self.assertTrue(is_cron_target("0 * * * *"))

    def test_write_jsonl_preserves_metadata_for_evaluation(self) -> None:
        example = {
            "user": "every day at 6:30",
            "target": "30 6 * * *",
            "family": "daily_at",
            "source": "template",
        }
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.jsonl"
            write_jsonl(path, [example])
            [loaded] = read_jsonl(path)

        self.assertEqual(loaded["family"], "daily_at")
        self.assertEqual(loaded["source"], "template")
        self.assertEqual(loaded["user"], "every day at 6:30")
        self.assertEqual(loaded["target"], "30 6 * * *")

    def test_semantic_filter_rejects_mismatched_paraphrases(self) -> None:
        self.assertFalse(is_semantically_consistent("Every Monday at 8:00", "0 9 * * 1"))
        self.assertFalse(is_semantically_consistent("Every 5 minutes", "*/15 * * * *"))
        self.assertFalse(is_semantically_consistent("On the 5th day of every month at 8:00", "0 9 5 * *"))
        self.assertTrue(is_semantically_consistent("Everyday at 9pm and 5 am", "0 5,21 * * *"))
        self.assertTrue(is_semantically_consistent("Every Monday at 9 AM and 5 PM", "0 9,17 * * 1"))
        self.assertTrue(is_semantically_consistent("Every weekday at 9 AM and 5 PM", "0 9,17 * * 1-5"))
        self.assertTrue(is_semantically_consistent("Every weekday at 9:00", "0 9 * * 1-5"))


if __name__ == "__main__":
    unittest.main()
