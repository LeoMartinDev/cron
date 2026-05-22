Place a browser-loadable GGUF here when you want to serve only the `demo/` directory.

Expected filename:

- `model-00001-of-00001.gguf`

Local shortcut from the repo root:

```bash
mkdir -p demo/models
ln -sf ../../output/cron-model/final-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf demo/models/model-00001-of-00001.gguf
```
