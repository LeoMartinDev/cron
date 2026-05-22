# Demo

This directory contains a zero-build browser demo for the GGUF cron model.

## What it uses

- Tailwind via CDN script tag
- `wllama` ESM module loaded from jsDelivr
- `wllama.wasm` loaded from jsDelivr
- The repo GGUF at `../output/cron-model/final-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf`
- Optional fallback support for a demo-local GGUF at `./models/model-00001-of-00001.gguf`

## Run it

Recommended: start a plain static server from the project root. The demo will then load the GGUF directly from the repo output folder:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/demo/
```

If you prefer to serve only `demo/`, create the demo-local model link first:

```bash
mkdir -p demo/models
ln -sf ../../output/cron-model/final-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf demo/models/model-00001-of-00001.gguf
cd demo && python3 -m http.server 8000
```

## Notes

- The UI is intentionally minimal: one prompt input, one generate action, and one copyable output.
- The page auto-detects a reachable GGUF on startup and now prefers the repo-root export before `demo/models`. There is no model picker.
- The demo forces `wllama` to use `n_threads: 1`, so it works without COOP/COEP headers.
- The demo now depends on jsDelivr at runtime for both the `wllama` ES module and its `.wasm` runtime.
- The `wllama` version is pinned in [app.js](/home/leo/dev/cron-finetuning/demo/app.js:1) so the module and wasm stay in sync.
- Recent Safari versions are still a poor fit here because current `wllama` builds require Memory64.
- If the console shows `invalid magic characters: '<!DO'`, the browser received an HTML 404 page instead of a GGUF file.
- The visual direction is now aligned with `leomartin.dev`: dark single-column layout, `Inter` + `JetBrains Mono`, and a restrained terminal-like chrome.
