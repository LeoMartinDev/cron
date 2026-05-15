# AGENTS.md

## Goal

This project generates a supervised training dataset for a very small language model that converts natural-language scheduling requests into cron expressions.

The model must produce exactly one of two outputs:
- a valid **5-field Unix cron expression**
- the single token `INVALID` when the input is not a cron-generation request

## What the dataset teaches

The dataset is designed to teach the model two behaviors:

1. **Cron generation**
   - Example: `"Every weekday at 09:30"` → `30 9 * * 1-5`
   - Example: `"Every 15 minutes"` → `*/15 * * * *`

2. **Out-of-domain rejection**
   - Example: `"Write a poem about the ocean"` → `INVALID`
   - Example: `"What is the capital of France?"` → `INVALID`

## Dataset strategy

The dataset is generated in two stages:

1. **Deterministic seed generation**
   - Canonical cron examples are created in code.
   - This guarantees correct labels and consistent cron syntax.

2. **LLM-based augmentation**
   - OpenRouter is used to generate additional English paraphrases for valid examples.
   - OpenRouter is also used to generate off-topic prompts that should map to `INVALID`.
   - The LLM must never be the source of truth for cron labels.

## Source of truth

The cron target is always produced by code, not guessed by the LLM.

The LLM is only used to generate:
- alternate phrasings of valid scheduling requests
- invalid / off-topic user prompts

## Output format

The dataset is exported as JSONL in chat format:

```json
{
  "messages": [
    { "role": "system", "content": "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation." },
    { "role": "user", "content": "Every day at 6:30" },
    { "role": "assistant", "content": "30 6 * * *" }
  ]
}
```

## Rules

- All user prompts must be in **English**
- All cron outputs must use **5-field Unix cron**
- Non-cron prompts must map to **`INVALID`**
- No explanations should appear in assistant outputs
- Synthetic examples must be validated and deduplicated before export

## Why this exists

The objective is to create a compact, high-quality dataset that is safe for fine-tuning a sub-1B model on a narrowly scoped structured-output task.

This project favors:
- correctness over volume
- deterministic labels over freeform generation
- LLM augmentation only where it improves linguistic diversity
