# Demo

This directory contains a zero-build browser demo for the GGUF cron model.

## What it uses

- Tailwind via CDN script tag
- `wllama` ESM module loaded from jsDelivr
- `wllama.wasm` loaded from jsDelivr
- The fixed local GGUF at `../output/cron-model/final-gguf_gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf`

## Run it

Start a plain static server from the project root:

```bash
python3 -m http.server 8000
```

Then open:

```text
http://localhost:8000/demo/
```

## Notes

- The UI is intentionally minimal: prompt input, actions, and output only.
- The page auto-loads the repo GGUF on startup. There is no model picker.
- The demo forces `wllama` to use `n_threads: 1`, so it works without COOP/COEP headers.
- The demo now depends on jsDelivr at runtime for both the `wllama` ES module and its `.wasm` runtime.
- The `wllama` version is pinned in [app.js](/home/leo/dev/cron-finetuning/demo/app.js:1) so the module and wasm stay in sync.
- Recent Safari versions are still a poor fit here because current `wllama` builds require Memory64.
- If the GGUF path changes in the repo, update `demo/config.js`.
