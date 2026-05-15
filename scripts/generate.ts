const SYSTEM_PROMPT =
  "You must reply with either a 5-field Unix cron expression or the single token INVALID. No explanation.";

const OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions";
const DEFAULT_MODEL = Deno.env.get("OPENROUTER_MODEL") ?? "openai/gpt-4o-mini";

type Family =
  | "daily_at"
  | "every_n_minutes"
  | "weekdays_at"
  | "monthly_on_day_at"
  | "weekly_on_day_at"
  | "invalid";

type Source = "template" | "llm";

type Example = {
  user: string;
  target: string;
  family: Family;
  source: Source;
};

const WEEKDAYS = [
  { name: "Monday", short: "Mon", cron: 1 },
  { name: "Tuesday", short: "Tue", cron: 2 },
  { name: "Wednesday", short: "Wed", cron: 3 },
  { name: "Thursday", short: "Thu", cron: 4 },
  { name: "Friday", short: "Fri", cron: 5 },
] as const;

function pad2(n: number): string {
  return String(n).padStart(2, "0");
}

function ordinal(n: number): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return `${n}st`;
  if (mod10 === 2 && mod100 !== 12) return `${n}nd`;
  if (mod10 === 3 && mod100 !== 13) return `${n}rd`;
  return `${n}th`;
}

function toLine(example: Example): string {
  return JSON.stringify({
    messages: [
      { role: "system", content: SYSTEM_PROMPT },
      { role: "user", content: example.user },
      { role: "assistant", content: example.target },
    ],
    metadata: {
      family: example.family,
      source: example.source,
    },
  });
}

function cronRegex(): RegExp {
  return /^(\*|\*\/\d+|\d+|\d+-\d+)(\s+(\*|\*\/\d+|\d+|\d+-\d+)){4}$/;
}

function isCronTarget(value: string): boolean {
  return cronRegex().test(value.trim());
}

function isValidTarget(value: string): boolean {
  return value === "INVALID" || isCronTarget(value);
}

function normalizeUserText(value: string): string {
  return value.replace(/\s+/g, " ").trim();
}

function isReasonableUserText(value: string): boolean {
  const text = normalizeUserText(value);
  if (!text) return false;
  if (text.length < 3 || text.length > 200) return false;
  return true;
}

function validateExample(example: Example): boolean {
  if (!isReasonableUserText(example.user)) return false;
  if (!isValidTarget(example.target)) return false;
  return true;
}

function dedupe(examples: Example[]): Example[] {
  const seen = new Set<string>();
  const out: Example[] = [];

  for (const ex of examples) {
    const normalized: Example = {
      ...ex,
      user: normalizeUserText(ex.user),
      target: ex.target.trim(),
    };

    const key = `${normalized.user.toLowerCase()}|||${normalized.target}`;
    if (seen.has(key)) continue;
    if (!validateExample(normalized)) continue;

    seen.add(key);
    out.push(normalized);
  }

  return out;
}

function shuffle<T>(items: T[]): T[] {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function splitDataset<T>(
  items: T[],
  trainRatio = 0.9,
): { train: T[]; valid: T[] } {
  const shuffled = shuffle(items);
  const trainSize = Math.floor(shuffled.length * trainRatio);
  return {
    train: shuffled.slice(0, trainSize),
    valid: shuffled.slice(trainSize),
  };
}

function dailyAtExamples(): Example[] {
  const times = [
    { hour: 6, minute: 0 },
    { hour: 6, minute: 30 },
    { hour: 9, minute: 15 },
    { hour: 14, minute: 5 },
    { hour: 18, minute: 45 },
  ];

  const out: Example[] = [];

  for (const { hour, minute } of times) {
    const target = `${minute} ${hour} * * *`;

    out.push(
      {
        family: "daily_at",
        source: "template",
        user: `Every day at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "daily_at",
        source: "template",
        user: `Daily at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "daily_at",
        source: "template",
        user: `Run every day at ${hour}:${pad2(minute)}`,
        target,
      },
    );
  }

  return out;
}

function everyNMinutesExamples(): Example[] {
  const values = [5, 10, 15, 20, 30];

  return values.flatMap((n) => {
    const target = `*/${n} * * * *`;

    return [
      {
        family: "every_n_minutes",
        source: "template",
        user: `Every ${n} minutes`,
        target,
      },
      {
        family: "every_n_minutes",
        source: "template",
        user: `Run every ${n} minutes`,
        target,
      },
      {
        family: "every_n_minutes",
        source: "template",
        user: `Once every ${n} minutes`,
        target,
      },
    ];
  });
}

function weekdaysAtExamples(): Example[] {
  const slots = [
    { hour: 9, minute: 0 },
    { hour: 9, minute: 30 },
    { hour: 18, minute: 0 },
  ];

  return slots.flatMap(({ hour, minute }) => {
    const target = `${minute} ${hour} * * 1-5`;

    return [
      {
        family: "weekdays_at",
        source: "template",
        user: `Every weekday at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "weekdays_at",
        source: "template",
        user: `On weekdays at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "weekdays_at",
        source: "template",
        user: `Monday to Friday at ${hour}:${pad2(minute)}`,
        target,
      },
    ];
  });
}

function monthlyOnDayAtExamples(): Example[] {
  const days = [1, 5, 15, 28];
  const times = [
    { hour: 0, minute: 0 },
    { hour: 8, minute: 0 },
    { hour: 12, minute: 30 },
  ];

  const out: Example[] = [];

  for (const day of days) {
    for (const { hour, minute } of times) {
      const target = `${minute} ${hour} ${day} * *`;

      out.push(
        {
          family: "monthly_on_day_at",
          source: "template",
          user: `On the ${ordinal(day)} day of every month at ${hour}:${
            pad2(minute)
          }`,
          target,
        },
        {
          family: "monthly_on_day_at",
          source: "template",
          user: `Every month on day ${day} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "monthly_on_day_at",
          source: "template",
          user: `Run monthly on the ${ordinal(day)} at ${hour}:${pad2(minute)}`,
          target,
        },
      );
    }
  }

  return out;
}

function weeklyOnDayAtExamples(): Example[] {
  const times = [
    { hour: 8, minute: 0 },
    { hour: 10, minute: 30 },
    { hour: 17, minute: 15 },
  ];

  const out: Example[] = [];

  for (const day of WEEKDAYS) {
    for (const { hour, minute } of times) {
      const target = `${minute} ${hour} * * ${day.cron}`;

      out.push(
        {
          family: "weekly_on_day_at",
          source: "template",
          user: `Every ${day.name} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "weekly_on_day_at",
          source: "template",
          user: `On ${day.name} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "weekly_on_day_at",
          source: "template",
          user: `${day.short} at ${hour}:${pad2(minute)}`,
          target,
        },
      );
    }
  }

  return out;
}

function invalidExamples(): Example[] {
  const inputs = [
    "What is the capital of France?",
    "Write a poem about the ocean",
    "Translate this sentence to German",
    "How do I reverse a linked list?",
    "What is 27 multiplied by 14?",
    "Tell me a joke",
    "Summarize this article",
    "Generate a Docker Compose file",
    "Who won the World Cup?",
    "Explain quantum computing simply",
    "Book a flight to Tokyo",
    "Set the brightness to 80 percent",
    "Show me the weather for tomorrow",
    "Sort this array in ascending order",
    "What time is it in New York?",
  ];

  return inputs.map((user) => ({
    family: "invalid" as const,
    source: "template" as const,
    user,
    target: "INVALID",
  }));
}

function buildBaseDataset(): Example[] {
  return dedupe([
    ...dailyAtExamples(),
    ...everyNMinutesExamples(),
    ...weekdaysAtExamples(),
    ...monthlyOnDayAtExamples(),
    ...weeklyOnDayAtExamples(),
    ...invalidExamples(),
  ]);
}

function getOpenRouterHeaders(apiKey: string): HeadersInit {
  return {
    Authorization: `Bearer ${apiKey}`,
    "Content-Type": "application/json",
    "HTTP-Referer": "https://local.dataset.generator",
    "X-Title": "cron-dataset-generator",
  };
}

async function callOpenRouterJson<T>(
  apiKey: string,
  model: string,
  prompt: string,
  schemaName: string,
  schema: Record<string, unknown>,
): Promise<T> {
  const response = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: getOpenRouterHeaders(apiKey),
    body: JSON.stringify({
      model,
      messages: [
        {
          role: "system",
          content: "Return only valid JSON matching the provided schema.",
        },
        {
          role: "user",
          content: prompt,
        },
      ],
      temperature: 0.9,
      stream: false,
      response_format: {
        type: "json_schema",
        json_schema: {
          name: schemaName,
          strict: true,
          schema,
        },
      },
    }),
  });

  if (!response.ok) {
    const text = await response.text();
    throw new Error(`OpenRouter error ${response.status}: ${text}`);
  }

  const json = await response.json();
  const content = json?.choices?.[0]?.message?.content;

  if (typeof content !== "string") {
    throw new Error("OpenRouter returned no message content");
  }

  return JSON.parse(content) as T;
}

function makeValidParaphrasePrompt(seed: Example, count: number): string {
  return [
    "Generate training data for a small model.",
    "Task: create natural English user requests that map to exactly the same target output.",
    "Rules:",
    "- English only",
    "- preserve meaning exactly",
    "- do not mention cron syntax",
    "- do not explain anything",
    "- keep each prompt short and natural",
    `- generate ${count} items`,
    "",
    `Target output: ${seed.target}`,
    `Family: ${seed.family}`,
    `Canonical request: ${seed.user}`,
  ].join("\n");
}

function makeInvalidPrompt(count: number): string {
  return [
    "Generate negative training data for a cron generation model.",
    "Task: create realistic English user prompts that are not requests for cron generation.",
    "Rules:",
    "- clearly off-topic or unrelated to scheduling",
    "- no scheduling requests",
    "- short and realistic",
    `- generate ${count} items`,
  ].join("\n");
}

async function generateValidParaphrases(
  apiKey: string,
  model: string,
  seeds: Example[],
  countPerSeed: number,
): Promise<Example[]> {
  const schema = {
    type: "object",
    properties: {
      items: {
        type: "array",
        items: { type: "string" },
        minItems: countPerSeed,
        maxItems: countPerSeed,
      },
    },
    required: ["items"],
    additionalProperties: false,
  };

  const out: Example[] = [];

  for (const seed of seeds) {
    if (seed.target === "INVALID") continue;

    const prompt = makeValidParaphrasePrompt(seed, countPerSeed);
    const result = await callOpenRouterJson<{ items: string[] }>(
      apiKey,
      model,
      prompt,
      "valid_paraphrases",
      schema,
    );

    for (const user of result.items) {
      out.push({
        user,
        target: seed.target,
        family: seed.family,
        source: "llm",
      });
    }
  }

  return out;
}

async function generateInvalidWithLlm(
  apiKey: string,
  model: string,
  count: number,
): Promise<Example[]> {
  const schema = {
    type: "object",
    properties: {
      items: {
        type: "array",
        items: { type: "string" },
        minItems: count,
        maxItems: count,
      },
    },
    required: ["items"],
    additionalProperties: false,
  };

  const prompt = makeInvalidPrompt(count);
  const result = await callOpenRouterJson<{ items: string[] }>(
    apiKey,
    model,
    prompt,
    "invalid_prompts",
    schema,
  );

  return result.items.map((user) => ({
    user,
    target: "INVALID",
    family: "invalid" as const,
    source: "llm" as const,
  }));
}

async function maybeGenerateSyntheticData(base: Example[]): Promise<Example[]> {
  const apiKey = Deno.env.get("OPENROUTER_API_KEY");
  if (!apiKey) {
    console.log("OPENROUTER_API_KEY not set; skipping LLM augmentation.");
    return [];
  }

  const model = DEFAULT_MODEL;

  const validSeeds = base
    .filter((x) => x.target !== "INVALID")
    .slice(0, 20);

  const validSynthetic = await generateValidParaphrases(
    apiKey,
    model,
    validSeeds,
    6,
  );

  const invalidSynthetic = await generateInvalidWithLlm(apiKey, model, 20);

  return dedupe([...validSynthetic, ...invalidSynthetic]);
}

async function writeJson(path: string, value: unknown) {
  await Deno.writeTextFile(path, JSON.stringify(value, null, 2) + "\n");
}

async function writeJsonl(path: string, examples: Example[]) {
  const body = examples.map(toLine).join("\n") + "\n";
  await Deno.writeTextFile(path, body);
}

async function main() {
  const base = buildBaseDataset();
  const synthetic = await maybeGenerateSyntheticData(base);
  const all = dedupe([...base, ...synthetic]);
  const { train, valid } = splitDataset(all, 0.9);

  await Deno.mkdir("./data", { recursive: true });

  await writeJsonl("./data/train.jsonl", train);
  await writeJsonl("./data/valid.jsonl", valid);

  const manifest = {
    format: "chat-jsonl",
    cron_variant: "unix-5-fields-or-INVALID",
    total_examples: all.length,
    train_examples: train.length,
    valid_examples: valid.length,
    model_for_synthetic_generation: synthetic.length > 0 ? DEFAULT_MODEL : null,
    sources: {
      template: all.filter((x) => x.source === "template").length,
      llm: all.filter((x) => x.source === "llm").length,
    },
    families: [...new Set(all.map((x) => x.family))],
    special_outputs: ["INVALID"],
  };

  await writeJson("./data/manifest.json", manifest);

  console.log(`Generated ${all.length} examples`);
  console.log(`Train: ${train.length}`);
  console.log(`Valid: ${valid.length}`);
  console.log(`Synthetic: ${synthetic.length}`);
}

if (import.meta.main) {
  await main();
}
