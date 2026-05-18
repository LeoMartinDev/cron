# AGENTS.md

## Goal

This project generates a supervised training dataset for a very small language model that converts natural-language scheduling requests into 5-field Unix cron expressions.

The model must produce exactly one of two outputs:
- a valid **5-field Unix cron expression**
- the single token `INVALID` when the input is not a cron-generation request

## Dataset stats

| Metric | Value |
|---|---|
| Format | chatml (JSONL with `messages` array) |
| Train examples | ~1250 (80%) |
| Valid examples | ~150 (10%) |
| Test examples | ~150 (10%) |
| Unique cron targets | ~330 |
| INVALID ratio | ~7% |
| Template examples | ~1060 |
| LLM-augmented | ~220 |
| Cron families | 18 |
| Generation model | Google Gemini Flash Lite via OpenRouter |

## Supported cron patterns

All cron outputs are 5-field Unix format: `minute hour day-of-month month day-of-week`.

### 1. Daily at specific time (`daily_at`)

Input: natural 24h or 12h clock references to a time of day.

| Pattern | Example input | Output |
|---|---|---|
| "Every day at HH:MM" | `Every day at 6:30` | `30 6 * * *` |
| "Daily at HH:MM" | `Daily at 9:15` | `15 9 * * *` |
| "Run every day at HH:MM" | `Run every day at 14:05` | `5 14 * * *` |
| 12h clock | `Every day at 6 PM` | `0 18 * * *` |
| 12h with minutes | `Every day at 6:45 PM` | `45 18 * * *` |

Times covered: 32 distinct hour:minute pairs from 00:00 to 23:45.

### 2. Every N minutes (`every_n_minutes`)

Input: recurring interval in minutes. Uses `*/N` step syntax.

| Pattern | Example input | Output |
|---|---|---|
| "Every N minutes" | `Every 5 minutes` | `*/5 * * * *` |
| "Run every N minutes" | `Run every 15 minutes` | `*/15 * * * *` |
| "Once every N minutes" | `Once every 30 minutes` | `*/30 * * * *` |

N values: 2, 3, 5, 6, 10, 12, 15, 20, 30, 45, 60.

### 3. Weekdays at time (`weekdays_at`)

Input: Monday-through-Friday at a specific time. Uses `1-5` day-of-week range.

| Pattern | Example input | Output |
|---|---|---|
| "Every weekday at HH:MM" | `Every weekday at 9:00` | `0 9 * * 1-5` |
| "On weekdays at HH:MM" | `On weekdays at 18:00` | `0 18 * * 1-5` |
| "Monday to Friday at HH:MM" | `Monday to Friday at 9:30` | `30 9 * * 1-5` |

Times covered: 7 slots (8:00, 9:00, 9:30, 12:00, 15:00, 17:00, 18:00).

### 4. Monthly on specific day (`monthly_on_day_at`)

Input: a day of the month and a time. Uses specific day-of-month field.

| Pattern | Example input | Output |
|---|---|---|
| "On the Nth day of every month at HH:MM" | `On the 15th day of every month at 8:00` | `0 8 15 * *` |
| "Every month on day N at HH:MM" | `Every month on day 1 at 12:30` | `30 12 1 * *` |
| "Run monthly on the Nth at HH:MM" | `Run monthly on the 28th at 0:00` | `0 0 28 * *` |

Days: 1, 2, 5, 7, 10, 12, 15, 18, 20, 21, 25, 28. Times: 6 slots.

### 5. Weekly on specific weekday (`weekly_on_day_at`)

Input: a named day of the week at a time. Uses numeric day-of-week (0=Sun, 1=Mon, …, 7=Sun).

| Pattern | Example input | Output |
|---|---|---|
| "Every {day} at HH:MM" | `Every Monday at 10:30` | `30 10 * * 1` |
| "On {day} at HH:MM" | `On Friday at 17:15` | `15 17 * * 5` |
| "{short} at HH:MM" | `Wed at 8:00` | `0 8 * * 3` |
| 12h clock | `Every Monday at 5 PM` | `0 17 * * 1` |

Days: Mon–Fri. Times: 13 slots from 7:00 to 22:30.

### 6. Hour range (`hour_range_at`)

Input: a range of hours, repeating at a specific minute. Uses hour range syntax.

| Pattern | Example input | Output |
|---|---|---|
| "Every hour from H1:00 to H2:00 at minute M" | `Every hour from 9:00 to 17:00 at minute 0` | `0 9-17 * * *` |
| "Every hour between H1 and H2 at M past" | `Every hour between 8 and 20 at 0 past` | `0 8-20 * * *` |
| "From H1:00 to H2:00 every hour at minute M" | `From 6:00 to 22:00 every hour at minute 15` | `15 6-22 * * *` |

Ranges: 9–17, 9–17:30, 8–20, 6–22:15.

### 7. Multiple specific weekdays (`multi_weekday_at`)

Input: a list of named days. Uses comma-separated day-of-week.

| Pattern | Example input | Output |
|---|---|---|
| "Every {days} at HH:MM" | `Every Monday, Wednesday, and Friday at 8:00` | `0 8 * * 1,3,5` |
| "On {days} at HH:MM" | `On Tuesday and Thursday at 10:00` | `0 10 * * 2,4` |

Combos: Mon/Wed/Fri, Tue/Thu, Mon/Fri, Wed/Sat. Times: 3 slots.

### 8. Midnight, noon, and common phrases (`midnight_noon_at`)

| Example input | Output |
|---|---|
| `At midnight` | `0 0 * * *` |
| `Every night at midnight` | `0 0 * * *` |
| `At noon` | `0 12 * * *` |
| `Every day at noon` | `0 12 * * *` |
| `At midnight on weekdays` | `0 0 * * 1-5` |
| `Every hour` / `On the hour` | `0 * * * *` |
| `Every half hour` | `*/30 * * * *` |
| `Every quarter hour` | `*/15 * * * *` |

### 9. Every hour at minute X (`hourly_at_minute`)

Input: a minute offset past every hour. Uses wildcard hour with specific minute.

| Pattern | Example input | Output |
|---|---|---|
| "At M past every hour" | `At 5 past every hour` | `5 * * * *` |
| "At minute M of every hour" | `At minute 30 of every hour` | `30 * * * *` |
| "M minutes past every hour" | `15 minutes past every hour` | `15 * * * *` |
| "At quarter past every hour" | — | `15 * * * *` |
| "At half past every hour" | — | `30 * * * *` |
| "At quarter to every hour" | — | `45 * * * *` |

Minute values: 0, 5, 10, 15, 25, 30, 45, 55.

### 10. Twice daily (`twice_daily`)

Input: two specific times per day. Uses comma-separated hour field.

| Pattern | Example input | Output |
|---|---|---|
| "At H1:M1 and H2:M2 every day" | `At 8:00 and 20:00 every day` | `0 8,20 * * *` |
| "Twice a day at H1:M1 and H2:M2" | `Twice a day at 9:00 and 17:30` | `0 9,17 * * *` |
| "Every day at H1:M1 and H2:M2" | `Every day at 6:30 and 18:30` | `30 6,18 * * *` |

Pairs: 8:00/20:00, 9:00/17:30, 6:30/18:30, 7:00/19:00, 12:00/23:00.

### 11. Weekend (`weekend_at`)

Input: Saturday and Sunday. Uses `6,0` or `0,6` day-of-week.

| Pattern | Example input | Output |
|---|---|---|
| "Every weekend at HH:MM" | `Every weekend at 10:30` | `30 10 * * 6,0` |
| "On weekends at HH:MM" | `On weekends at 9:00` | `0 9 * * 6,0` |
| "Saturday and Sunday at HH:MM" | `Saturday and Sunday at 6 PM` | `0 18 * * 6,0` |

Times: 6 slots.

### 12. Weekdays except specific day (`except_weekday_at`)

Input: all weekdays minus one day. Uses comma-separated day-of-week list.

| Pattern | Example input | Output |
|---|---|---|
| "Every weekday except {day} at HH:MM" | `Every weekday except Monday at 18:00` | `0 18 * * 2,3,4,5` |
| "Weekdays except {day} at HH:MM" | `Weekdays except Friday at 9:00` | `0 9 * * 1,2,3,4` |
| "Every week day except {day} at H AM/PM" | `Every week day except Monday at 6 PM` | `0 18 * * 2,3,4,5` |
| "Every day except {day} at HH:MM" | `Every day except Sunday at 8:00` | `0 8 * * 1,2,3,4,5,6` |
| "Daily except {day} at H AM/PM" | `Daily except Sunday at 9 AM` | `0 9 * * 1,2,3,4,5,6` |

### 13. Every N hours (`every_n_hours`)

Input: repeating interval in hours. Uses `*/N` step in hour field.

| Pattern | Example input | Output |
|---|---|---|
| "Every N hours" | `Every 4 hours` | `0 */4 * * *` |
| "Run every N hours" | `Run every 6 hours` | `0 */6 * * *` |
| "Once every N hours" | `Once every 12 hours` | `0 */12 * * *` |

N values: 2, 3, 4, 6, 8, 12.

### 14. Every N days (`every_n_days`)

Input: repeating interval in days. Uses `*/N` step in day-of-month field.

| Pattern | Example input | Output |
|---|---|---|
| "Every N days" | `Every 3 days` | `0 0 */3 * *` |
| "Run every N days" | `Run every 7 days` | `0 0 */7 * *` |
| "Every week" (N=7) | `Every week` | `0 0 */7 * *` |
| "Every two weeks" (N=14) | `Every two weeks` | `0 0 */14 * *` |

N values: 2, 3, 7, 14.

### 15. Cron aliases and shorthands (`cron_aliases`)

Input: standard cron `@`-syntax aliases and standalone natural-language shorthands.

| Pattern | Example input | Output |
|---|---|---|
| `@daily` | `@daily` | `0 0 * * *` |
| `@hourly` | `@hourly` | `0 * * * *` |
| `@weekly` | `@weekly` | `0 0 * * 0` |
| `@monthly` | `@monthly` | `0 0 1 * *` |
| `@yearly` / `@annually` | `@yearly` | `0 0 1 1 *` |
| `@midnight` | `@midnight` | `0 0 * * *` |
| Standalone `hourly` | `hourly` | `0 * * * *` |
| Standalone `daily` / `monthly` / `yearly` | `daily` | `0 0 * * *` |
| `every minute` | `every minute` | `* * * * *` |

### 16. Month-specific patterns (`month_specific`)

Input: a month name, optionally with a specific day and time. Uses the month field (1–12).

| Pattern | Example input | Output |
|---|---|---|
| "Every {month} at HH:MM" | `Every January at 8:00` | `0 8 * 1 *` |
| "In {month} at HH:MM" | `In March at 9:00` | `0 9 * 3 *` |
| "On {month} Nth at HH:MM" | `On January 5th at 9:00` | `0 9 5 1 *` |

Months: all 12. Days: 1, 5, 10, 15, 20, 25. Times: 0:00, 8:00, 9:00.

### 17. Partial week ranges (`partial_week_range`)

Input: a range of consecutive weekdays (not full Monday–Friday). Uses day-of-week range.

| Pattern | Example input | Output |
|---|---|---|
| "Every {range} at HH:MM" | `Every Monday through Thursday at 8:00` | `0 8 * * 1-4` |
| "{range} at HH:MM" | `Tuesday to Friday at 17:00` | `0 17 * * 2-5` |

Ranges: Mon–Thu, Tue–Fri, Mon–Wed, Wed–Fri. Times: 8:00, 17:00.

### 18. Out-of-domain rejection (`invalid`)

Any input that is not a scheduling request must produce `INVALID`.

| Example input | Output |
|---|---|
| `What is the capital of France?` | `INVALID` |
| `Write a poem about the ocean` | `INVALID` |
| `How do I reverse a linked list?` | `INVALID` |
| `Book a flight to Tokyo` | `INVALID` |

40 template + ~40 LLM-generated off-topic prompts.

## Cron field coverage

| Field | Supported syntax |
|---|---|
| **Minute** | Specific values (0–59), step `*/N` |
| **Hour** | Specific values (0–23), ranges `N-M`, step `*/N`, comma lists `H1,H2` |
| **Day of month** | Specific values (1–28), step `*/N` |
| **Month** | Always `*` except month-specific patterns (1–12) |
| **Day of week** | Specific values (0–7), range `N-M`, comma lists `D1,D2,D3` |

## Output format

The dataset is exported as JSONL in chatml format:

```json
{
  "messages": [
    { "role": "system", "content": "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation." },
    { "role": "user", "content": "Every day at 6:30" },
    { "role": "assistant", "content": "30 6 * * *" }
  ]
}
```

## Training config (Unsloth Studio)

| Setting | Value |
|---|---|
| Format | `chatml` |
| Train on Completions | **ON** |
| Max Steps | `0` (use epochs) |
| Epochs | `5` |
| Learning Rate | `2e-4` |
| Batch Size | `4` |
| Grad Accum | `8` |
| Context Length | `512` |
| Method | QLoRA |
| LoRA Rank | `16` |
| LoRA Alpha | `32` |

## Environment & install

This project uses **uv** as its package manager. No pip, no poetry — just uv.

```bash
# Sync all dependencies (generate + train + evaluate):
uv sync

# Sync only what you need:
uv sync --group generate
uv sync --group train
uv sync --group evaluate
```

## Regenerate

```bash
# Generate dataset (templates only):
uv run cron-generate

# With LLM augmentation:
export OPENROUTER_API_KEY=sk-or-v1-...
uv run cron-generate

# Push to HuggingFace Hub:
export HF_TOKEN=hf_...
uv run cron-generate --push --repo-id your-username/cron-dataset
```

## Train

```bash
# Train the model:
uv run cron-train

# With custom base model:
uv run cron-train --base-model unsloth/Qwen2.5-0.5B

# Push trained model to HF Hub:
uv run cron-train --push --hub-repo-id your-username/cron-model
```

## Evaluate

```bash
# Evaluate on the held-out test set:
uv run cron-evaluate

# With custom paths:
uv run cron-evaluate --checkpoint output/cron-model/final --data-dir data

# Save results to JSON:
uv run cron-evaluate --save
```

The test set is **never used during training** — it's held out for unbiased final evaluation. `train.py` only loads `train.jsonl` and `valid.jsonl`.

## Dataset strategy

1. **Deterministic seed generation** — Canonical cron examples are created in code. This guarantees correct labels and consistent cron syntax.
2. **LLM-based augmentation** — OpenRouter (Google Gemini Flash Lite) generates additional English paraphrases and off-topic INVALID prompts. The LLM is never the source of truth for cron labels.

## Rules

- All user prompts must be in **English**
- All cron outputs must use **5-field Unix cron**
- Non-cron prompts must map to **`INVALID`**
- No explanations should appear in assistant outputs
- Synthetic examples must be validated and deduplicated before export
- 12h clock (AM/PM) and 24h clock inputs both accepted
- Compact 12h notation accepted: `6pm`, `9am`, `6:30pm` (no space)
- "Week day" (two words) and "weekday" (one word) both accepted
- Common typos like "excepted" → "except" handled by LLM-generated paraphrases
- Month names ("January", "March") and prepositions ("in January", "every January") accepted
- Time-of-day phrases: "every morning", "every afternoon", "every evening", "every night"
- Standard cron `@`-aliases: `@daily`, `@hourly`, `@weekly`, `@monthly`, `@yearly`, `@midnight`

## Data split strategy

The dataset is split **80/10/10** (train/valid/test) via `split_dataset()` in `utils.py`.
- **train.jsonl** — used for model fine-tuning
- **valid.jsonl** — used for early stopping and hyperparameter selection
- **test.jsonl** — held out; only used by `evaluate.py` for final metrics

The test set will eventually be split **by seed** (grouping by `target`) to prevent paraphrases of the same template from leaking across splits (see TODO #2).
