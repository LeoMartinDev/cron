window.CRON_DEMO_CONFIG = {
  title: "Cron Console",
  subtitle: "Turn plain English scheduling requests into Unix cron with a local GGUF model.",
  defaultModelUrl:
    "../output/cron-model/final-gguf_gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf",
  systemPrompt:
    "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation.",
  examples: [
    "Every day at 6:30",
    "Monday to Friday at 9:30",
    "Every 15 minutes",
    "At 8:00 and 20:00 every day",
    "On January 5th at 9:00",
    "What is the capital of France?",
  ],
};
