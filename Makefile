.PHONY: lint format typecheck check fix all

# ── Quality ───────────────────────────────────────────────────────────

lint:
	uvx ruff check src/ scripts/

format:
	uvx ruff format src/ scripts/

format-check:
	uvx ruff format --check src/ scripts/

typecheck:
	uvx pyright src/ scripts/

fix:
	uvx ruff check --fix src/ scripts/
	uvx ruff format src/ scripts/

check: lint format-check typecheck
	@echo "✅ All checks passed"

# ── Dataset ───────────────────────────────────────────────────────────

generate:
	uv run cron-generate

generate-llm:
	OPENROUTER_API_KEY=$(OPENROUTER_API_KEY) uv run cron-generate

# ── Training ──────────────────────────────────────────────────────────

train:
	uv run cron-train

train-qwen:
	uv run cron-train --base-model unsloth/Qwen2.5-0.5B

# ── Evaluation ────────────────────────────────────────────────────────

evaluate:
	uv run cron-evaluate

evaluate-save:
	uv run cron-evaluate --save

# ── All ───────────────────────────────────────────────────────────────

all: check generate train evaluate
	@echo "✅ Full pipeline complete"
