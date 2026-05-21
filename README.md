# Cron Fine-Tuning

A Python project for generating a supervised fine-tuning dataset and training a small language model that converts natural-language scheduling requests into 5-field Unix cron expressions.

The model must produce exactly one of two outputs:
- A valid **5-field Unix cron expression**
- The single token `INVALID` when the input is not a cron-generation request

## Project structure

```
cron-finetuning/
├── pyproject.toml              # Python package configuration
├── README.md
├── .env.example                # Environment variable template
├── src/
│   └── cron_finetuning/        # Main package
│       ├── __init__.py
│       ├── constants.py        # Types, prompts, weekday mappings
│       ├── utils.py            # Helpers: time formatting, validation, dedup
│       ├── families.py         # 18 template-based example generators
│       ├── llm.py              # LLM augmentation via OpenRouter
│       ├── dataset.py          # I/O + HuggingFace Hub push utilities
│       ├── generate.py         # Main dataset generation orchestration
│       ├── train.py            # Unsloth fine-tuning script
│       └── inference.py        # Interactive inference script
├── scripts/                    # Thin CLI wrappers
│   ├── generate.py
│   ├── train.py
│   ├── inference.py
│   └── evaluate.py
├── data/                       # Generated dataset (git-ignored)
│   ├── train.jsonl
│   ├── valid.jsonl
│   ├── test.jsonl
│   └── manifest.json
└── demo/                       # Browser demo (wllama)
```

## Quick start

### 1. Install

```bash
# Install with pip
pip install -e ".[all]"

# Or install only what you need:
pip install -e ".[generate]"      # dataset generation only
pip install -e ".[train]"         # training only
pip install -e ".[inference]"     # inference only
```

### 2. Generate the dataset

```bash
# Using the CLI entry point (after pip install)
cron-generate

# Or using the wrapper script
python scripts/generate.py

# Or as a module
python -m cron_finetuning.generate

# With LLM augmentation (requires OpenRouter API key)
export OPENROUTER_API_KEY=sk-or-v1-...
cron-generate
```

### 3. Push dataset to HuggingFace Hub

```bash
# Set your HF token
export HF_TOKEN=hf_...

# Push manually
python -c "
from cron_finetuning.dataset import push_dataset_to_hub
push_dataset_to_hub('data', 'your-username/cron-dataset')
"

# Or during generation
cron-generate --push --repo-id your-username/cron-dataset
```

### 4. Train the model

```bash
cron-train

# With custom model
cron-train --base-model unsloth/Qwen2.5-0.5B

# Push trained model to HuggingFace Hub
cron-train --push --repo-id your-username/cron-model
```

### 5. Run inference

```bash
cron-inference "Every day at 6:30"
# Output: 30 6 * * *

cron-inference "What is the capital of France?"
# Output: INVALID

# Interactive mode
cron-inference
```

### 6. Evaluate on test set

```bash
# Evaluate the fine-tuned model on the held-out test set
cron-evaluate

# With custom paths
cron-evaluate --checkpoint output/cron-model/final --data-dir data

# Save results to JSON
cron-evaluate --save
```

## Dataset

| Metric | Value |
|---|---|
| Format | chatml (JSONL with `messages` array) |
| Train examples | ~1250 (80%) |
| Valid examples | ~150 (10%) |
| Test examples | ~150 (10%) |
| Cron families | 18 |
| INVALID ratio | ~7% |

### Supported cron patterns

1. **daily_at** — Every day at a specific time
2. **every_n_minutes** — Recurring interval in minutes
3. **weekdays_at** — Monday–Friday at a time
4. **monthly_on_day_at** — Specific day of month at a time
5. **weekly_on_day_at** — Named weekday at a time
6. **hour_range_at** — Range of hours at a specific minute
7. **multi_weekday_at** — List of specific days at a time
8. **midnight_noon_at** — Midnight, noon, and common phrases
9. **hourly_at_minute** — Minute past every hour
10. **multi_time_at** — Multiple specific times within the same schedule
11. **weekend_at** — Saturday and Sunday at a time
12. **except_weekday_at** — Weekdays minus a specific day
13. **every_n_hours** — Recurring interval in hours
14. **every_n_days** — Recurring interval in days
15. **cron_aliases** — `@daily`, `@hourly`, etc.
16. **month_specific** — Month-specific patterns
17. **partial_week_range** — Sub-range of consecutive weekdays
18. **invalid** — Off-topic prompts → `INVALID`

### Example format

```json
{
  "messages": [
    { "role": "system", "content": "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation." },
    { "role": "user", "content": "Every day at 6:30" },
    { "role": "assistant", "content": "30 6 * * *" }
  ]
}
```

## Dataset strategy

1. **Deterministic template generation** — Canonical cron examples are created in code (`families.py`). This guarantees correct labels and consistent cron syntax.
2. **LLM-based augmentation** — Optional. Uses OpenRouter to generate additional English paraphrases and off-topic INVALID prompts. Valid paraphrases are generated across 7 writing styles: `precise`, `concise`, `hurried`, `sloppy`, `shorthand`, `conversational`, and `polite`. The LLM is never the source of truth for cron labels.

## Training config

| Setting | Value |
|---|---|
| Base model | `unsloth/SmolLM2-360M-Instruct` |
| Method | QLoRA |
| LoRA Rank | 32 |
| LoRA Alpha | 64 |
| Epochs | 15 |
| Learning Rate | 2e-4 |
| Batch Size | 2 × 4 grad accum |
| Context Length | 256 |

## License

MIT
