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
  | "hour_range_at"
  | "multi_weekday_at"
  | "midnight_noon_at"
  | "hourly_at_minute"
  | "twice_daily"
  | "weekend_at"
  | "except_weekday_at"
  | "every_n_hours"
  | "every_n_days"
  | "cron_aliases"
  | "month_specific"
  | "partial_week_range"
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

function to12h(hour: number, minute?: number): string {
  const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  const ampm = hour >= 12 ? "PM" : "AM";
  if (minute !== undefined && minute !== 0) {
    return `${h12}:${pad2(minute)} ${ampm}`;
  }
  return `${h12} ${ampm}`;
}

function to12hCompact(hour: number, minute?: number): string {
  const h12 = hour === 0 ? 12 : hour > 12 ? hour - 12 : hour;
  const ampm = hour >= 12 ? "pm" : "am";
  if (minute !== undefined && minute !== 0) {
    return `${h12}:${pad2(minute)}${ampm}`;
  }
  return `${h12}${ampm}`;
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
  });
}

function cronFieldRegex(): string {
  return "(\\*|\\*/\\d+|\\d+(-\\d+)?(,\\d+(-\\d+)?)*)";
}

function cronRegex(): RegExp {
  return new RegExp(
    `^${cronFieldRegex()}(\\s+${cronFieldRegex()}){4}$`,
  );
}

function isCronTarget(value: string): boolean {
  return cronRegex().test(value.trim());
}

function isValidTarget(value: string): boolean {
  return value === "INVALID" || isCronTarget(value);
}

function normalizeUserText(value: string): string {
  return value.toLowerCase().replace(/\s+/g, " ").trim();
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
    { hour: 0, minute: 0 },
    { hour: 0, minute: 30 },
    { hour: 1, minute: 0 },
    { hour: 2, minute: 0 },
    { hour: 3, minute: 15 },
    { hour: 4, minute: 0 },
    { hour: 5, minute: 30 },
    { hour: 6, minute: 0 },
    { hour: 6, minute: 30 },
    { hour: 7, minute: 0 },
    { hour: 7, minute: 45 },
    { hour: 8, minute: 0 },
    { hour: 8, minute: 30 },
    { hour: 9, minute: 0 },
    { hour: 9, minute: 15 },
    { hour: 10, minute: 0 },
    { hour: 10, minute: 45 },
    { hour: 11, minute: 30 },
    { hour: 12, minute: 0 },
    { hour: 13, minute: 0 },
    { hour: 14, minute: 5 },
    { hour: 15, minute: 0 },
    { hour: 15, minute: 30 },
    { hour: 16, minute: 0 },
    { hour: 17, minute: 0 },
    { hour: 18, minute: 0 },
    { hour: 18, minute: 45 },
    { hour: 20, minute: 0 },
    { hour: 21, minute: 30 },
    { hour: 22, minute: 0 },
    { hour: 23, minute: 0 },
    { hour: 23, minute: 45 },
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
      {
        family: "daily_at",
        source: "template",
        user: `Every day at ${to12h(hour, minute)}`,
        target,
      },
      {
        family: "daily_at",
        source: "template",
        user: `Every day at ${to12hCompact(hour, minute)}`,
        target,
      },
    );

    // Natural time-of-day phrases for round hours
    if (minute === 0) {
      if (hour >= 6 && hour <= 11) {
        out.push({
          family: "daily_at",
          source: "template",
          user: `Every morning at ${hour}`,
          target,
        });
      }
      if (hour >= 12 && hour <= 17) {
        out.push({
          family: "daily_at",
          source: "template",
          user: `Every afternoon at ${to12h(hour)}`,
          target,
        });
      }
      if (hour >= 18 && hour <= 21) {
        out.push({
          family: "daily_at",
          source: "template",
          user: `Every evening at ${to12h(hour)}`,
          target,
        });
      }
      if (hour >= 22 || hour <= 4) {
        out.push({
          family: "daily_at",
          source: "template",
          user: `Every night at ${to12h(hour)}`,
          target,
        });
        }
      }

    // Terse / lazy phrasings
    if (minute === 0) {
      out.push({
        family: "daily_at",
        source: "template",
        user: `Daily at ${hour}`,
        target,
      });
    }
    out.push(
      {
        family: "daily_at",
        source: "template",
        user: `Daily ${to12hCompact(hour, minute)}`,
        target,
      },
      {
        family: "daily_at",
        source: "template",
        user: `${to12hCompact(hour, minute)} daily`,
        target,
      },
    );
  }

  return out;
}

function everyNMinutesExamples(): Example[] {
  const values = [2, 3, 5, 6, 10, 12, 15, 20, 30, 45, 60];

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
      {
        family: "every_n_minutes",
        source: "template",
        user: `Every ${n}m`,
        target,
      },
      {
        family: "every_n_minutes",
        source: "template",
        user: `Every ${n} min`,
        target,
      },
    ];
  });
}

function weekdaysAtExamples(): Example[] {
  const slots = [
    { hour: 8, minute: 0 },
    { hour: 9, minute: 0 },
    { hour: 9, minute: 30 },
    { hour: 12, minute: 0 },
    { hour: 15, minute: 0 },
    { hour: 17, minute: 0 },
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
      {
        family: "weekdays_at",
        source: "template",
        user: `Every weekday at ${to12h(hour, minute)}`,
        target,
      },
      {
        family: "weekdays_at",
        source: "template",
        user: `Every weekday at ${to12hCompact(hour, minute)}`,
        target,
      },
      {
        family: "weekdays_at",
        source: "template",
        user: `Weekdays ${to12hCompact(hour, minute)}`,
        target,
      },
      {
        family: "weekdays_at",
        source: "template",
        user: `${to12hCompact(hour, minute)} weekdays`,
        target,
      },
    ];
  });
}

function monthlyOnDayAtExamples(): Example[] {
  const days = [1, 2, 5, 7, 10, 12, 15, 18, 20, 21, 25, 28];
  const times = [
    { hour: 0, minute: 0 },
    { hour: 6, minute: 0 },
    { hour: 8, minute: 0 },
    { hour: 9, minute: 30 },
    { hour: 12, minute: 30 },
    { hour: 17, minute: 0 },
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
    { hour: 7, minute: 0 },
    { hour: 8, minute: 0 },
    { hour: 8, minute: 30 },
    { hour: 9, minute: 0 },
    { hour: 9, minute: 45 },
    { hour: 10, minute: 30 },
    { hour: 12, minute: 0 },
    { hour: 14, minute: 0 },
    { hour: 15, minute: 30 },
    { hour: 17, minute: 15 },
    { hour: 19, minute: 0 },
    { hour: 20, minute: 0 },
    { hour: 22, minute: 30 },
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
        {
          family: "weekly_on_day_at",
          source: "template",
          user: `Every ${day.name} at ${to12h(hour, minute)}`,
          target,
        },
        {
          family: "weekly_on_day_at",
          source: "template",
          user: `${day.short} ${to12hCompact(hour, minute)}`,
          target,
        },
        {
          family: "weekly_on_day_at",
          source: "template",
          user: `${to12hCompact(hour, minute)} ${day.short.toLowerCase()}`,
          target,
        },
      );
    }
  }

  return out;
}

function hourRangeAtExamples(): Example[] {
  const ranges: Array<{ from: number; to: number; minute: number }> = [
    { from: 9, to: 17, minute: 0 },
    { from: 9, to: 17, minute: 30 },
    { from: 8, to: 20, minute: 0 },
    { from: 6, to: 22, minute: 15 },
  ];

  const out: Example[] = [];

  for (const { from, to, minute } of ranges) {
    const target = `${minute} ${from}-${to} * * *`;

    out.push(
      {
        family: "hour_range_at",
        source: "template",
        user: `Every hour from ${from}:00 to ${to}:00 at minute ${minute}`,
        target,
      },
      {
        family: "hour_range_at",
        source: "template",
        user: `Every hour between ${from} and ${to} at ${minute} past`,
        target,
      },
      {
        family: "hour_range_at",
        source: "template",
        user: `From ${from}:00 to ${to}:00 every hour at minute ${minute}`,
        target,
      },
    );
  }

  return out;
}

function multiWeekdayAtExamples(): Example[] {
  const combos: Array<{ days: number[]; label: string }> = [
    { days: [1, 3, 5], label: "Monday, Wednesday, and Friday" },
    { days: [2, 4], label: "Tuesday and Thursday" },
    { days: [1, 5], label: "Monday and Friday" },
    { days: [3, 6], label: "Wednesday and Saturday" },
  ];

  const times = [
    { hour: 8, minute: 0 },
    { hour: 10, minute: 0 },
    { hour: 15, minute: 45 },
  ];

  const out: Example[] = [];

  for (const { days, label } of combos) {
    for (const { hour, minute } of times) {
      const cronDays = days.join(",");
      const target = `${minute} ${hour} * * ${cronDays}`;

      out.push(
        {
          family: "multi_weekday_at",
          source: "template",
          user: `Every ${label} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "multi_weekday_at",
          source: "template",
          user: `On ${label} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "multi_weekday_at",
          source: "template",
          user: `${label.replace(/, and /g, " ").replace(/ and /g, " ")} ${to12hCompact(hour, minute)}`,
          target,
        },
      );
    }
  }

  return out;
}

function midnightNoonAtExamples(): Example[] {
  const out: Example[] = [];

  out.push(
    {
      family: "midnight_noon_at",
      source: "template",
      user: "At midnight",
      target: "0 0 * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Every night at midnight",
      target: "0 0 * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Run at midnight",
      target: "0 0 * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "At noon",
      target: "0 12 * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Every day at noon",
      target: "0 12 * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Run at noon every day",
      target: "0 12 * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "At midnight on weekdays",
      target: "0 0 * * 1-5",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Every weekday at midnight",
      target: "0 0 * * 1-5",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Every hour",
      target: "0 * * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Run every hour",
      target: "0 * * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "At the top of every hour",
      target: "0 * * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "On the hour",
      target: "0 * * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Every half hour",
      target: "*/30 * * * *",
    },
    {
      family: "midnight_noon_at",
      source: "template",
      user: "Every quarter hour",
      target: "*/15 * * * *",
    },
  );

  return out;
}

function hourlyAtMinuteExamples(): Example[] {
  const minutes = [0, 5, 10, 15, 25, 30, 45, 55];

  const out: Example[] = [];

  for (const minute of minutes) {
    const target = `${minute} * * * *`;

    out.push(
      {
        family: "hourly_at_minute",
        source: "template",
        user: `At ${minute} past every hour`,
        target,
      },
      {
        family: "hourly_at_minute",
        source: "template",
        user: `At minute ${minute} of every hour`,
        target,
      },
      {
        family: "hourly_at_minute",
        source: "template",
        user: `${minute} minutes past every hour`,
        target,
      },
    );

    if (minute === 0) {
      out.push({
        family: "hourly_at_minute",
        source: "template",
        user: "At the start of every hour",
        target,
      });
    }
    if (minute === 15) {
      out.push({
        family: "hourly_at_minute",
        source: "template",
        user: "At quarter past every hour",
        target,
      });
    }
    if (minute === 30) {
      out.push({
        family: "hourly_at_minute",
        source: "template",
        user: "At half past every hour",
        target,
      });
    }
    if (minute === 45) {
      out.push({
        family: "hourly_at_minute",
        source: "template",
        user: "At quarter to every hour",
        target,
      });
    }
  }

  return out;
}

function twiceDailyExamples(): Example[] {
  const pairs: Array<{ h1: number; m1: number; h2: number; m2: number }> = [
    { h1: 8, m1: 0, h2: 20, m2: 0 },
    { h1: 9, m1: 0, h2: 17, m2: 30 },
    { h1: 6, m1: 30, h2: 18, m2: 30 },
    { h1: 7, m1: 0, h2: 19, m2: 0 },
    { h1: 12, m1: 0, h2: 23, m2: 0 },
  ];

  const out: Example[] = [];

  for (const { h1, m1, h2, m2 } of pairs) {
    const target = `${m1} ${h1},${h2} * * *`;

    out.push(
      {
        family: "twice_daily",
        source: "template",
        user: `At ${h1}:${pad2(m1)} and ${h2}:${pad2(m2)} every day`,
        target,
      },
      {
        family: "twice_daily",
        source: "template",
        user: `Twice a day at ${h1}:${pad2(m1)} and ${h2}:${pad2(m2)}`,
        target,
      },
      {
        family: "twice_daily",
        source: "template",
        user: `Every day at ${h1}:${pad2(m1)} and ${h2}:${pad2(m2)}`,
        target,
      },
    );
  }

  return out;
}

function weekendAtExamples(): Example[] {
  const times = [
    { hour: 7, minute: 0 },
    { hour: 9, minute: 0 },
    { hour: 10, minute: 30 },
    { hour: 14, minute: 0 },
    { hour: 18, minute: 0 },
    { hour: 20, minute: 30 },
  ];

  const out: Example[] = [];

  for (const { hour, minute } of times) {
    const target = `${minute} ${hour} * * 6,0`;

    out.push(
      {
        family: "weekend_at",
        source: "template",
        user: `Every weekend at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "weekend_at",
        source: "template",
        user: `On weekends at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "weekend_at",
        source: "template",
        user: `Saturday and Sunday at ${hour}:${pad2(minute)}`,
        target,
      },
      {
        family: "weekend_at",
        source: "template",
        user: `Every Saturday and Sunday at ${to12h(hour, minute)}`,
        target,
      },
      {
        family: "weekend_at",
        source: "template",
        user: `Weekends ${to12hCompact(hour, minute)}`,
        target,
      },
      {
        family: "weekend_at",
        source: "template",
        user: `Sat Sun ${to12hCompact(hour, minute)}`,
        target,
      },
    );
  }

  return out;
}

function exceptWeekdayAtExamples(): Example[] {
  const exceptDay = [
    { day: "Monday", short: "Monday", dow: 1, exclude: [2, 3, 4, 5] },
    { day: "Friday", short: "Friday", dow: 5, exclude: [1, 2, 3, 4] },
    { day: "Wednesday", short: "Wednesday", dow: 3, exclude: [1, 2, 4, 5] },
  ];

  const times = [
    { hour: 8, minute: 0 },
    { hour: 9, minute: 0 },
    { hour: 17, minute: 0 },
    { hour: 18, minute: 0 },
  ];

  const out: Example[] = [];

  for (const { day, short, exclude } of exceptDay) {
    for (const { hour, minute } of times) {
      const cronDays = exclude.join(",");
      const target = `${minute} ${hour} * * ${cronDays}`;

      out.push(
        {
          family: "except_weekday_at",
          source: "template",
          user: `Every weekday except ${day} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "except_weekday_at",
          source: "template",
          user: `Weekdays except ${short} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "except_weekday_at",
          source: "template",
          user: `Every week day except ${day} at ${to12h(hour, minute)}`,
          target,
        },
      );
    }
  }

  // Also add "every day except Sunday" patterns
  const dailyExcept = [
    { day: "Sunday", cron: 0, other: [1, 2, 3, 4, 5, 6] },
    { day: "Saturday", cron: 6, other: [1, 2, 3, 4, 5, 0] },
  ];

  for (const { day, other } of dailyExcept) {
    for (const { hour, minute } of times) {
      const cronDays = other.join(",");
      const target = `${minute} ${hour} * * ${cronDays}`;

      out.push(
        {
          family: "except_weekday_at",
          source: "template",
          user: `Every day except ${day} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "except_weekday_at",
          source: "template",
          user: `Daily except ${day} at ${to12h(hour, minute)}`,
          target,
        },
      );
    }
  }

  return out;
}

function everyNHoursExamples(): Example[] {
  const values = [2, 3, 4, 6, 8, 12];

  return values.flatMap((n) => {
    const target = `0 */${n} * * *`;

    return [
      {
        family: "every_n_hours",
        source: "template",
        user: `Every ${n} hours`,
        target,
      },
      {
        family: "every_n_hours",
        source: "template",
        user: `Run every ${n} hours`,
        target,
      },
      {
        family: "every_n_hours",
        source: "template",
        user: `Once every ${n} hours`,
        target,
      },
      {
        family: "every_n_hours",
        source: "template",
        user: `Every ${n}h`,
        target,
      },
      {
        family: "every_n_hours",
        source: "template",
        user: `Every ${n} hrs`,
        target,
      },
      ...(n === 2
        ? [{
            family: "every_n_hours" as Family,
            source: "template" as const,
            user: "Every other hour",
            target,
          }]
        : []),
    ];
  });
}

function everyNDaysExamples(): Example[] {
  const values = [2, 3, 7, 14];

  return values.flatMap((n) => {
    const target = `0 0 */${n} * *`;

    return [
      {
        family: "every_n_days",
        source: "template",
        user: `Every ${n} days`,
        target,
      },
      {
        family: "every_n_days",
        source: "template",
        user: `Run every ${n} days`,
        target,
      },
      {
        family: "every_n_days",
        source: "template",
        user: n === 7
          ? "Every week"
          : n === 14
          ? "Every two weeks"
          : `Once every ${n} days`,
        target,
      },
      ...(n === 2
        ? [{
            family: "every_n_days" as Family,
            source: "template" as const,
            user: "Every other day",
            target,
          }]
        : []),
    ];
  });
}

function cronAliasesExamples(): Example[] {
  const out: Example[] = [];

  // Standard cron aliases (@-syntax)
  out.push(
    {
      family: "cron_aliases",
      source: "template",
      user: "every minute",
      target: "* * * * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "Run every minute",
      target: "* * * * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@daily",
      target: "0 0 * * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@hourly",
      target: "0 * * * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@weekly",
      target: "0 0 * * 0",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@monthly",
      target: "0 0 1 * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@yearly",
      target: "0 0 1 1 *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@annually",
      target: "0 0 1 1 *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "@midnight",
      target: "0 0 * * *",
    },
  );

  // Natural language standalone shorthands
  out.push(
    {
      family: "cron_aliases",
      source: "template",
      user: "hourly",
      target: "0 * * * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "daily",
      target: "0 0 * * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "weekly",
      target: "0 0 * * 0",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "monthly",
      target: "0 0 1 * *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "yearly",
      target: "0 0 1 1 *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "annually",
      target: "0 0 1 1 *",
    },
    {
      family: "cron_aliases",
      source: "template",
      user: "every minute of every day",
      target: "* * * * *",
    },
  );

  return out;
}

function monthSpecificExamples(): Example[] {
  const months: Array<{ name: string; num: number }> = [
    { name: "January", num: 1 },
    { name: "February", num: 2 },
    { name: "March", num: 3 },
    { name: "April", num: 4 },
    { name: "May", num: 5 },
    { name: "June", num: 6 },
    { name: "July", num: 7 },
    { name: "August", num: 8 },
    { name: "September", num: 9 },
    { name: "October", num: 10 },
    { name: "November", num: 11 },
    { name: "December", num: 12 },
  ];

  const days = [1, 5, 10, 15, 20, 25];
  const times = [
    { hour: 0, minute: 0 },
    { hour: 8, minute: 0 },
    { hour: 9, minute: 0 },
  ];

  const out: Example[] = [];

  // "Every January at 8:00" → 0 8 * 1 *
  for (const { name, num } of months) {
    for (const { hour, minute } of times) {
      const target = `${minute} ${hour} * ${num} *`;

      out.push(
        {
          family: "month_specific",
          source: "template",
          user: `Every ${name} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "month_specific",
          source: "template",
          user: `In ${name} at ${hour}:${pad2(minute)}`,
          target,
        },
      );
    }
  }

  // "On January 15th at 9:00" → 0 9 15 1 *
  for (const { name, num } of months.slice(0, 6)) {
    for (const day of days) {
      out.push(
        {
          family: "month_specific",
          source: "template",
          user: `On ${name} ${ordinal(day)} at 9:00`,
          target: `0 9 ${day} ${num} *`,
        },
      );
    }
  }

  return out;
}

function partialWeekRangeExamples(): Example[] {
  const ranges: Array<{ from: number; to: number; label: string }> = [
    { from: 1, to: 4, label: "Monday through Thursday" },
    { from: 2, to: 5, label: "Tuesday to Friday" },
    { from: 1, to: 3, label: "Monday through Wednesday" },
    { from: 3, to: 5, label: "Wednesday to Friday" },
  ];

  const times = [
    { hour: 8, minute: 0 },
    { hour: 17, minute: 0 },
  ];

  const out: Example[] = [];

  for (const { from, to, label } of ranges) {
    for (const { hour, minute } of times) {
      const target = `${minute} ${hour} * * ${from}-${to}`;

      out.push(
        {
          family: "partial_week_range",
          source: "template",
          user: `Every ${label} at ${hour}:${pad2(minute)}`,
          target,
        },
        {
          family: "partial_week_range",
          source: "template",
          user: `${label} at ${hour}:${pad2(minute)}`,
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
    "Write a Python function to sort a list",
    "How do I make pancakes?",
    "What is the meaning of life?",
    "Convert 100 USD to EUR",
    "How tall is Mount Everest?",
    "Create a React component for a login form",
    "What are the symptoms of a cold?",
    "Write a haiku about spring",
    "How do I install Docker on Ubuntu?",
    "What is the speed of light?",
    "Name three types of cloud computing",
    "How far is the moon from Earth?",
    "Define artificial intelligence",
    "Write a regular expression to match email addresses",
    "What is the derivative of x squared?",
    "Fix the bug in this code",
    "Write a cover letter for a job application",
    "What is the boiling point of water?",
    "How do I cook rice?",
    "Explain how blockchain works",
    "What year did World War II end?",
    "Design a database schema for a blog",
    "Write unit tests for this function",
    "How much does an elephant weigh?",
    "What is photosynthesis?",
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
    ...hourRangeAtExamples(),
    ...multiWeekdayAtExamples(),
    ...midnightNoonAtExamples(),
    ...hourlyAtMinuteExamples(),
    ...twiceDailyExamples(),
    ...weekendAtExamples(),
    ...exceptWeekdayAtExamples(),
    ...everyNHoursExamples(),
    ...everyNDaysExamples(),
    ...cronAliasesExamples(),
    ...monthSpecificExamples(),
    ...partialWeekRangeExamples(),
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

async function callOpenRouterText(
  apiKey: string,
  model: string,
  systemPrompt: string,
  userPrompt: string,
): Promise<string> {
  const response = await fetch(OPENROUTER_URL, {
    method: "POST",
    headers: getOpenRouterHeaders(apiKey),
    body: JSON.stringify({
      model,
      messages: [
        { role: "system", content: systemPrompt },
        { role: "user", content: userPrompt },
      ],
      temperature: 0.9,
      stream: false,
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

  return content;
}

function parseLineList(text: string): string[] {
  return text
    .split("\n")
    .map((line) => line.replace(/^\d+[\).\s]\s*/, "").trim())
    .filter((line) => line.length > 0);
}

function makeValidParaphrasePrompt(seed: Example, count: number): string {
  return [
    `Generate ${count} natural English user requests that map to this cron expression.`,
    `Cron: ${seed.target}`,
    `Family: ${seed.family}`,
    `Example: "${seed.user}"`,
    "",
    "Rules:",
    "- English only",
    "- preserve meaning exactly — if the cron has day-of-week constraints (like Mon,Wed,Fri), your paraphrases MUST mention those specific days",
    "- do NOT use 'daily' or 'every day' unless the cron runs every day (day-of-month = *, day-of-week = *)",
    "- do NOT use 'weekdays' or 'Monday to Friday' unless the cron restricts to 1-5",
    "- do not mention cron syntax",
    "- do not explain anything",
    "- keep each prompt short and natural",
    "- one request per line, no numbering",
  ].join("\n");
}

function makeInvalidPrompt(count: number): string {
  return [
    `Generate ${count} realistic English user prompts that are NOT requests for cron/scheduling.`,
    "",
    "Rules:",
    "- clearly off-topic or unrelated to scheduling",
    "- no scheduling requests",
    "- short and realistic",
    "- one prompt per line, no numbering",
  ].join("\n");
}

function parseCronFields(target: string): string[] {
  return target.trim().split(/\s+/);
}

function isSemanticallyConsistent(userText: string, target: string): boolean {
  const fields = parseCronFields(target);
  if (fields.length !== 5) return false;
  const [_min, _hour, _dom, _mon, dow] = fields;
  const lower = userText.toLowerCase();

  // "daily except X" / "every day except X" / "weekdays except X" are valid
  if (/\b(daily|every\s+day|weekdays?)\s+except\b/i.test(lower)) return true;

  // If cron has day-of-week restriction, must NOT say daily/every day without except
  if (dow !== "*") {
    if (/\b(daily|every\s+day|each\s+day|run\s+every\s+day)\b/i.test(lower)) return false;
  }
  // If cron is not the full weekday range (1-5), must NOT say weekday without except
  if (dow !== "1-5" && dow !== "*") {
    if (/\b(weekdays?|monday\s+to\s+friday|m-f)\b(?!\s+except)/i.test(lower)) return false;
  }

  return true;
}

async function generateValidParaphrases(
  apiKey: string,
  model: string,
  seeds: Example[],
  countPerSeed: number,
): Promise<Example[]> {
  const out: Example[] = [];

  for (const seed of seeds) {
    if (seed.target === "INVALID") continue;

    const prompt = makeValidParaphrasePrompt(seed, countPerSeed);
    const text = await callOpenRouterText(
      apiKey,
      model,
      "Return only the requested lines, no numbering, no explanation.",
      prompt,
    );
    const lines = parseLineList(text);

    for (const user of lines) {
      if (!isSemanticallyConsistent(user, seed.target)) continue;
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
  const prompt = makeInvalidPrompt(count);
  const text = await callOpenRouterText(
    apiKey,
    model,
    "Return only the requested lines, no numbering, no explanation.",
    prompt,
  );
  const lines = parseLineList(text);

  return lines.map((user) => ({
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
    .filter((x) =>
      x.target !== "INVALID" &&
      ["daily_at", "every_n_minutes", "weekdays_at", "monthly_on_day_at", "weekly_on_day_at"].includes(x.family)
    )
    .slice(0, 40);

  const validSynthetic = await generateValidParaphrases(
    apiKey,
    model,
    validSeeds,
    4,
  );

  const invalidSynthetic = await generateInvalidWithLlm(apiKey, model, 50);

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
    format: "chatml",
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
