# Cron-Finetuning Model Demo

Runs the fine-tuned SmolLM2-360M-Instruct model entirely **in the browser** using [wllama](https://github.com/ngxson/wllama) (llama.cpp compiled to WebAssembly).

## Quick start (no server required)

1. Open `demo/index.html` directly in your browser (Chrome, Edge, or Firefox)
2. Click **1. Load Model** → select your GGUF file:
   ```
   ~/.unsloth/studio/exports/SmolLM2-360M-Instruct-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf
   ```
3. Wait for the model to load into WASM (~5-15 seconds)
4. Type a scheduling request or click an example chip
5. See the cron expression (or `INVALID`) appear

## Optional: Serve via HTTP (avoids file picker)

If you'd prefer to load the model from a URL instead of the file picker:

```bash
deno run -A demo/serve.ts
```

Then open `http://localhost:8080` and modify the HTML to use `loadModelFromUrl('/model.gguf')`.

You can override the model path:
```bash
MODEL_PATH=/path/to/your/model.gguf deno run -A demo/serve.ts
```

## How it works

- **wllama** loads the GGUF model into a WebAssembly runtime (llama.cpp)
- The model receives the system prompt (from `AGENTS.md`) + the user's natural language request
- It outputs either a **5-field Unix cron expression** or `INVALID`
- Everything runs locally — no data leaves your browser

## Model details

| Property | Value |
|---|---|
| Base model | SmolLM2-360M-Instruct |
| Quantization | Q4_K_M |
| Context length | 512 |
| Output format | chatml (system + user + assistant) |
| Training | QLoRA (Unsloth Studio), 5 epochs |

## Supported inputs

All 17 cron families from the training set, including:
- Daily at specific times (24h and 12h)
- Every N minutes/hours/days
- Weekdays/weekends at time
- Monthly on specific day
- Multiple weekdays
- Midnight, noon, common phrases
- Cron aliases (`@daily`, `@hourly`, etc.)
- Month-specific patterns
- Partial week ranges
- Out-of-domain → `INVALID`
