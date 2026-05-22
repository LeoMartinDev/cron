import { Wllama } from "https://cdn.jsdelivr.net/npm/@wllama/wllama@3.1.1/esm/index.js";

const config = window.CRON_DEMO_CONFIG ?? {};
const CDN_WASM_PATHS = {
  default: "https://cdn.jsdelivr.net/npm/@wllama/wllama@3.1.1/esm/wasm/wllama.wasm",
};
const PLACEHOLDER_OUTPUT = "Ready for a prediction.";
const PENDING_OUTPUT = "Generating...";
const DEFAULT_MODEL_CANDIDATES = [
  "./models/model-00001-of-00001.gguf",
  "../output/cron-model/final-gguf_gguf/SmolLM2-360M-Instruct.Q4_K_M.gguf",
];

const elements = {
  appTitle: document.querySelector("[data-app-title]"),
  appSubtitle: document.querySelector("[data-app-subtitle]"),
  breadcrumbPath: document.querySelector("[data-breadcrumb-path]"),
  promptForm: document.querySelector("[data-prompt-form]"),
  promptInput: document.querySelector("[data-prompt-input]"),
  runButton: document.querySelector("[data-run]"),
  copyButton: document.querySelector("[data-copy]"),
  statusText: document.querySelector("[data-status-text]"),
  statusDot: document.querySelector("[data-status-dot]"),
  normalizedOutput: document.querySelector("[data-normalized-output]"),
};

const state = {
  wllama: null,
  modelLoaded: false,
  phase: "booting",
  outputState: "placeholder",
  lastOutput: "",
  copyResetTimer: null,
};

const CRON_FIELD = String.raw`\*|\*\/\d+|\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*`;
const CRON_REGEX = new RegExp(
  `\\b(${CRON_FIELD})\\s+(${CRON_FIELD})\\s+(${CRON_FIELD})\\s+(${CRON_FIELD})\\s+(${CRON_FIELD})\\b`,
  "i",
);

function setStatus(message, tone = "neutral") {
  if (elements.statusText) {
    elements.statusText.textContent = message;
  }

  if (elements.statusDot) {
    elements.statusDot.dataset.tone = tone;
  }
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

function getCandidateModelUrls() {
  const queryModelUrl = new URLSearchParams(window.location.search).get("model");
  const configuredFallbacks = Array.isArray(config.fallbackModelUrls) ? config.fallbackModelUrls : [];
  const candidates = [
    queryModelUrl,
    config.defaultModelUrl,
    ...configuredFallbacks,
    ...DEFAULT_MODEL_CANDIDATES,
  ].filter((value) => typeof value === "string" && value.trim());

  return [...new Set(candidates.map((value) => value.trim()))];
}

async function inspectModelUrl(url) {
  const resolvedUrl = resolveModelUrl(url);

  let response;
  try {
    response = await fetch(resolvedUrl, {
      method: "HEAD",
      cache: "no-store",
    });
  } catch (error) {
    return {
      ok: false,
      reason:
        error instanceof Error ? error.message : "The browser could not reach the local server.",
      resolvedUrl,
    };
  }

  if (!response.ok) {
    return {
      ok: false,
      reason: `HTTP ${response.status}`,
      resolvedUrl,
    };
  }

  const contentType = (response.headers.get("content-type") ?? "").toLowerCase();
  if (contentType.includes("text/html")) {
    return {
      ok: false,
      reason: "Received HTML instead of a GGUF file",
      resolvedUrl,
    };
  }

  return {
    ok: true,
    resolvedUrl,
  };
}

async function resolveAvailableModelUrl() {
  const candidates = getCandidateModelUrls();
  const failures = [];

  for (const candidate of candidates) {
    const result = await inspectModelUrl(candidate);
    if (result.ok) {
      return result.resolvedUrl;
    }

    failures.push(`${candidate} (${result.reason})`);
  }

  const detail = failures.join("; ");
  throw new Error(
    "No reachable GGUF model was found. Serve the repo root at /demo/ or place a model at demo/models/model-00001-of-00001.gguf."
      + (detail ? ` Tried: ${detail}.` : ""),
  );
}

function updateHeaderCopy() {
  elements.appTitle.textContent = config.title ?? "Cron Console";
  elements.appSubtitle.textContent =
    config.subtitle ??
    "(English) to Cron.";
  elements.promptInput.placeholder = config.placeholder ?? "Every weekday at 9:00";
  elements.breadcrumbPath.textContent =
    config.breadcrumb ?? "/home/dev/cron-finetuning/demo";
}

function syncControls() {
  const loadingModel = state.phase === "booting" || state.phase === "loading";
  const generating = state.phase === "running";

  if (loadingModel) {
    elements.runButton.textContent = "Loading model...";
  } else if (generating) {
    elements.runButton.textContent = "Generating...";
  } else if (state.modelLoaded) {
    elements.runButton.textContent = "Generate";
  } else {
    elements.runButton.textContent = "Model unavailable";
  }

  elements.runButton.disabled = state.phase !== "ready";
  elements.copyButton.disabled = generating || state.outputState !== "result";
  elements.promptInput.disabled = loadingModel || generating;
}

function clearCopyResetTimer() {
  if (state.copyResetTimer) {
    window.clearTimeout(state.copyResetTimer);
    state.copyResetTimer = null;
  }
}

function resetCopyButtonLabel() {
  clearCopyResetTimer();
  elements.copyButton.textContent = "Copy";
}

function flashCopyButtonLabel(label) {
  resetCopyButtonLabel();
  elements.copyButton.textContent = label;
  state.copyResetTimer = window.setTimeout(() => {
    elements.copyButton.textContent = "Copy";
    state.copyResetTimer = null;
  }, 1400);
}

function setOutput(value, outputState = "result") {
  state.lastOutput = value;
  state.outputState = outputState;
  elements.normalizedOutput.textContent = value;
  elements.normalizedOutput.classList.toggle("is-placeholder", outputState === "placeholder");
  elements.normalizedOutput.classList.toggle("is-error", outputState === "error");
  elements.normalizedOutput.classList.toggle(
    "is-invalid",
    outputState === "result" && value === "INVALID",
  );
  resetCopyButtonLabel();
  syncControls();
}

function ensureBrowserSupport() {
  const supported = typeof WebAssembly === "object";
  if (!supported) {
    state.phase = "error";
    setStatus("This browser is missing WebAssembly features required by wllama.", "error");
    syncControls();
  }

  return supported;
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
    if (resetStatus) {
      state.phase = "error";
      setStatus("Model unloaded.", "neutral");
      syncControls();
    }
  }
}

async function loadModelFromUrl(url) {
  state.phase = "loading";
  syncControls();
  setStatus("Looking for a reachable GGUF model...", "warning");

  try {
    const resolvedUrl = url ? resolveModelUrl(url) : await resolveAvailableModelUrl();
    const probe = await inspectModelUrl(resolvedUrl);
    if (!probe.ok) {
      throw new Error(
        `The configured model URL is not serving a GGUF file: ${probe.reason}. URL: ${resolvedUrl}`,
      );
    }

    if (state.modelLoaded) {
      await releaseModel(false);
    }

    const wllama = await createWllama();
    await wllama.loadModelFromUrl(resolvedUrl, {
      n_threads: 1,
      progressCallback: ({ loaded, total }) => {
        if (total) {
          const percent = Math.round((loaded / total) * 100);
          setStatus(`Loading GGUF model from the local server... ${percent}%`, "warning");
        }
      },
    });

    state.modelLoaded = true;
    state.phase = "ready";
    setStatus("Local model ready.", "success");
  } catch (error) {
    state.modelLoaded = false;
    state.phase = "error";
    setStatus(error instanceof Error ? error.message : "Failed to load the model.", "error");
  }

  syncControls();
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

  state.phase = "running";
  syncControls();
  setStatus("Generating cron expression...", "warning");
  setOutput(PENDING_OUTPUT, "pending");

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
    setOutput(normalized, "result");
    setStatus(
      normalized === "INVALID" ? "Request classified as INVALID." : "Cron expression generated.",
      "success",
    );
  } catch (error) {
    setOutput("Generation failed.", "error");
    setStatus(error instanceof Error ? error.message : "Inference failed.", "error");
  } finally {
    state.phase = state.modelLoaded ? "ready" : "error";
    syncControls();
  }
}

async function copyOutput() {
  if (state.outputState !== "result") {
    setStatus("There is no result to copy yet.", "warning");
    return;
  }

  try {
    await navigator.clipboard.writeText(state.lastOutput);
    flashCopyButtonLabel("Copied");
    setStatus("Result copied to the clipboard.", "success");
  } catch (error) {
    setStatus(error instanceof Error ? error.message : "Copy failed.", "error");
  }
}

function wireEvents() {
  elements.runButton.addEventListener("click", runInference);
  elements.copyButton.addEventListener("click", copyOutput);
  elements.promptInput.addEventListener("input", resetCopyButtonLabel);
  elements.promptInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      runInference();
    }
  });
}

function boot() {
  updateHeaderCopy();
  setOutput(PLACEHOLDER_OUTPUT, "placeholder");
  setStatus("Loading the local GGUF model...");
  wireEvents();
  syncControls();

  if (!ensureBrowserSupport()) {
    return;
  }

  const urls = getCandidateModelUrls();
  if (urls.length === 0) {
    state.phase = "error";
    setStatus("No GGUF URL is configured in demo/config.js.", "error");
    syncControls();
    return;
  }

  loadModelFromUrl();
}

boot();
