window.CRON_DEMO_CONFIG = {
  title: "Cron Console",
  subtitle: "(English) to Cron.",
  breadcrumb: "/home/dev/cron-finetuning/demo",
  placeholder: "Every weekday at 9:00",
  defaultModelUrl: "../output/cron-model/final-gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf",
  fallbackModelUrls: [
    "./models/model-00001-of-00001.gguf",
  ],
  systemPrompt:
    "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation.",
};
