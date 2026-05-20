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

    def test_non_representable_twice_daily_seed_is_removed(self) -> None:
        examples = build_base_dataset()
        users = {example["user"] for example in examples if example["family"] == "twice_daily"}
        self.assertNotIn("twice a day at 9:00 and 17:30", users)

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
        self.assertTrue(is_semantically_consistent("Every weekday at 9:00", "0 9 * * 1-5"))


if __name__ == "__main__":
    unittest.main()
