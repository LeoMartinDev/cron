import { Wllama } from "https://cdn.jsdelivr.net/npm/@wllama/wllama@3.1.1/esm/index.js";

const config = window.CRON_DEMO_CONFIG ?? {};
const CDN_WASM_PATHS = {
  default: "https://cdn.jsdelivr.net/npm/@wllama/wllama@3.1.1/esm/wasm/wllama.wasm",
};

const elements = {
  appTitle: document.querySelector("[data-app-title]"),
  appSubtitle: document.querySelector("[data-app-subtitle]"),
  promptInput: document.querySelector("[data-prompt-input]"),
  runButton: document.querySelector("[data-run]"),
  copyButton: document.querySelector("[data-copy]"),
  exampleList: document.querySelector("[data-examples]"),
  statusText: document.querySelector("[data-status-text]"),
  progressBar: document.querySelector("[data-progress-bar]"),
  progressText: document.querySelector("[data-progress-text]"),
  activeModel: document.querySelector("[data-active-model]"),
  normalizedOutput: document.querySelector("[data-normalized-output]"),
  rawOutput: document.querySelector("[data-raw-output]"),
  rawOutputWrap: document.querySelector("[data-raw-output-wrap]"),
  browserWarning: document.querySelector("[data-browser-warning]"),
};

const state = {
  wllama: null,
  modelLoaded: false,
  busy: false,
};

const CRON_FIELD = String.raw`\*|\*\/\d+|\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*`;
const CRON_REGEX = new RegExp(
  `\\b(${CRON_FIELD})\\s+(${CRON_FIELD})\\s+(${CRON_FIELD})\\s+(${CRON_FIELD})\\s+(${CRON_FIELD})\\b`,
  "i",
);

function setStatus(message, tone = "neutral") {
  elements.statusText.textContent = message;

  const toneClasses = {
    neutral: "text-stone-100",
    success: "text-emerald-200",
    warning: "text-amber-200",
    error: "text-rose-300",
  };

  elements.statusText.className = `text-sm font-medium ${toneClasses[tone] ?? toneClasses.neutral}`;
}

function setProgress(value, label = "") {
  const clamped = Math.max(0, Math.min(100, value));
  elements.progressBar.style.width = `${clamped}%`;
  elements.progressText.textContent = label || `${Math.round(clamped)}%`;
}

function setBusy(isBusy) {
  state.busy = isBusy;
  elements.runButton.disabled = isBusy || !state.modelLoaded;
  elements.copyButton.disabled = isBusy;
  elements.promptInput.disabled = isBusy && !state.modelLoaded;
}

function setLoadedModelLabel(label) {
  elements.activeModel.textContent = label;
}

function setOutputs(normalized, raw) {
  elements.normalizedOutput.textContent = normalized || "Waiting for a prediction...";
  elements.rawOutput.textContent = raw || "";
  elements.rawOutputWrap.hidden = !raw;
}

function normalizeModelOutput(raw) {
  const text = raw.trim();

  if (!text) {
    return "";
  }

  if (text.toUpperCase().startsWith("INVALID")) {
    return "INVALID";
  }

  const cronMatch = text.match(CRON_REGEX);
  if (cronMatch) {
    return cronMatch[0];
  }

  return text.split("\n")[0].trim();
}

function extractChatCompletionText(response) {
  if (typeof response === "string") {
    return response;
  }

  const content = response?.choices?.[0]?.message?.content;

  if (typeof content === "string") {
    return content;
  }

  if (Array.isArray(content)) {
    return content
      .map((part) => {
        if (typeof part === "string") {
          return part;
        }

        if (part && typeof part.text === "string") {
          return part.text;
        }

        return "";
      })
      .join("")
      .trim();
  }

  return "";
}

function resolveModelUrl(url) {
  try {
    return new URL(url, document.baseURI).href;
  } catch (error) {
    throw new Error(`Invalid model URL: ${url}`);
  }
}

function updateHeaderCopy() {
  elements.appTitle.textContent = config.title ?? "Cron Console";
  elements.appSubtitle.textContent =
    config.subtitle ??
    "Turn plain English scheduling requests into Unix cron with a local GGUF model.";
}

function renderExamples() {
  const examples = Array.isArray(config.examples) ? config.examples : [];
  elements.exampleList.innerHTML = "";

  for (const example of examples) {
    const button = document.createElement("button");
    button.type = "button";
    button.className =
      "rounded-full border border-stone-300 bg-white/80 px-3 py-2 text-left text-sm text-stone-700 transition hover:border-amber-500 hover:bg-amber-50 hover:text-stone-900";
    button.textContent = example;
    button.addEventListener("click", () => {
      elements.promptInput.value = example;
      elements.promptInput.focus();
    });
    elements.exampleList.append(button);
  }
}

function ensureBrowserSupport() {
  const supported = typeof WebAssembly === "object";
  if (!supported) {
    elements.browserWarning.hidden = false;
    setStatus("This browser is missing WebAssembly features required by wllama.", "error");
  }
}

async function createWllama() {
  if (!state.wllama) {
    state.wllama = new Wllama(CDN_WASM_PATHS);
  }
  return state.wllama;
}

async function releaseModel(resetStatus = true) {
  if (!state.wllama) {
    return;
  }

  try {
    await state.wllama.exit();
  } catch (error) {
    console.warn(error);
  } finally {
    state.wllama = null;
    state.modelLoaded = false;
    setLoadedModelLabel("No model loaded");

    if (resetStatus) {
      setStatus("Model unloaded.", "neutral");
      setProgress(0, "Idle");
    }
  }
}

async function loadModelFromUrl(url) {
  setBusy(true);
  setStatus("Loading GGUF model from the local server...", "warning");
  setProgress(2, "Starting");

  try {
    const resolvedUrl = resolveModelUrl(url);

    if (state.modelLoaded) {
      await releaseModel(false);
    }

    const wllama = await createWllama();
    await wllama.loadModelFromUrl(resolvedUrl, {
      n_threads: 1,
      progressCallback: ({ loaded, total }) => {
        if (!total) {
          setProgress(40, "Downloading model");
          return;
        }
        const percent = (loaded / total) * 100;
        setProgress(percent, `${Math.round(percent)}%`);
      },
    });

    state.modelLoaded = true;
    setLoadedModelLabel(resolvedUrl);
    setStatus("Model loaded. You can run cron generation now.", "success");
    setProgress(100, "Ready");
    setBusy(false);
  } catch (error) {
    state.modelLoaded = false;
    setLoadedModelLabel("No model loaded");
    setStatus(error instanceof Error ? error.message : "Failed to load the model.", "error");
    setProgress(0, "Idle");
    setBusy(false);
  }
}

async function runInference() {
  const prompt = elements.promptInput.value.trim();
  if (!prompt) {
    setStatus("Enter a scheduling request first.", "warning");
    elements.promptInput.focus();
    return;
  }

  if (!state.modelLoaded || !state.wllama) {
    setStatus("Load a GGUF model before running inference.", "warning");
    return;
  }

  setBusy(true);
  setStatus("Generating cron expression...", "warning");
  setProgress(100, "Running");
  setOutputs("Thinking...", "");

  try {
    const response = await state.wllama.createChatCompletion({
      messages: [
        {
          role: "system",
          content:
            config.systemPrompt ??
            "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      max_tokens: 24,
      temperature: 0,
      top_k: 1,
      top_p: 1,
    });

    const raw = extractChatCompletionText(response);
    if (!raw) {
      throw new Error("The model returned an empty response.");
    }

    const normalized = normalizeModelOutput(raw);
    setOutputs(
      normalized,
      typeof response === "string" ? raw : JSON.stringify(response, null, 2),
    );
    setStatus("Inference complete.", "success");
  } catch (error) {
    setOutputs("Generation failed.", "");
    setStatus(error instanceof Error ? error.message : "Inference failed.", "error");
  } finally {
    setBusy(false);
  }
}

async function copyOutput() {
  const value = elements.normalizedOutput.textContent?.trim();
  if (!value || value === "Waiting for a prediction..." || value === "Thinking...") {
    setStatus("There is no result to copy yet.", "warning");
    return;
  }

  try {
    await navigator.clipboard.writeText(value);
    setStatus("Result copied to the clipboard.", "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Copy failed.", "error");
  }
}

function wireEvents() {
  elements.runButton.addEventListener("click", runInference);
  elements.copyButton.addEventListener("click", copyOutput);

  elements.promptInput.addEventListener("keydown", (event) => {
    if ((event.metaKey || event.ctrlKey) && event.key === "Enter") {
      event.preventDefault();
      runInference();
    }
  });
}

function boot() {
  updateHeaderCopy();
  renderExamples();
  ensureBrowserSupport();
  setOutputs("", "");
  setLoadedModelLabel("No model loaded");
  setProgress(0, "Idle");
  setBusy(false);
  setStatus("Loading the repo GGUF model...");
  wireEvents();

  const url = config.defaultModelUrl;
  if (!url) {
    setStatus("No default GGUF URL is configured in demo/config.js.", "error");
    return;
  }

  loadModelFromUrl(url);
}

boot();
