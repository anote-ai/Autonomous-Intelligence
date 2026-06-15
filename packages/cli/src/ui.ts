import chalk from "chalk";

export const DEFAULT_MODEL = "claude-sonnet-4-6";

// ── Spinner ──────────────────────────────────────────────────────
const SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"];

export class Spinner {
  private frame = 0;
  private timer: ReturnType<typeof setInterval> | null = null;
  private text: string;

  constructor(text: string) {
    this.text = text;
  }

  start(): this {
    if (this.timer) return this;
    process.stderr.write("\x1b[?25l"); // hide cursor
    this.timer = setInterval(() => {
      const frame = SPINNER_FRAMES[this.frame % SPINNER_FRAMES.length];
      process.stderr.write(`\r${chalk.cyan(frame)} ${this.text}`);
      this.frame++;
    }, 80);
    return this;
  }

  update(text: string): void {
    this.text = text;
  }

  succeed(text?: string): void {
    this._stop();
    console.error(`\r${chalk.green("✓")} ${text ?? this.text}`);
  }

  fail(text?: string): void {
    this._stop();
    console.error(`\r${chalk.red("✗")} ${text ?? this.text}`);
  }

  stop(): void {
    this._stop();
    process.stderr.write("\r\x1b[K"); // clear spinner line
  }

  private _stop(): void {
    if (this.timer) {
      clearInterval(this.timer);
      this.timer = null;
    }
    process.stderr.write("\x1b[?25h"); // restore cursor
  }
}

export function createSpinner(text: string): Spinner {
  return new Spinner(text);
}

const SAMPLE_MODELS = [
  "claude-sonnet-4-6",
  "gpt-4.1",
  "gemini-2.5-pro",
  "llama-3.3-70b-instruct",
];

export function renderCliBanner(options: {
  cwd: string;
  model: string;
  toolsEnabled: boolean;
  sessionId?: string;
  agentMode?: string;
  agentEmoji?: string;
  agentDescription?: string;
}): string {
  const sessionLine = options.sessionId
    ? chalk.gray(`  Session     ${options.sessionId.slice(0, 8)}…`)
    : chalk.gray("  Session     new");

  const modeLabel = options.agentMode && options.agentMode !== "default"
    ? `${options.agentEmoji ?? "🤖"} ${options.agentMode}`
    : undefined;

  const modeLine = modeLabel
    ? chalk.gray(`  Mode        `) + chalk.bold.yellow(modeLabel) + chalk.gray(`  — ${options.agentDescription ?? ""}`)
    : undefined;

  return [
    "",
    chalk.bold.hex("#4ec9b0")("┌──────────────────────────────────────────────┐"),
    chalk.bold.hex("#4ec9b0")("│") +
      chalk.bold.white(" Anote") +
      chalk.gray("  AI-assisted coding tool") +
      " ".repeat(15) +
      chalk.bold.hex("#4ec9b0")("│"),
    chalk.bold.hex("#4ec9b0")("└──────────────────────────────────────────────┘"),
    chalk.gray(`  Workspace   ${options.cwd}`),
    chalk.gray(`  Model       ${options.model}`),
    chalk.gray(`  Tools       ${options.toolsEnabled ? "enabled" : "chat-only"}`),
    ...(modeLine ? [modeLine] : []),
    sessionLine,
    chalk.gray(
      `  Commands    ${chalk.white("/help")} for shortcuts, ${chalk.white("/exit")} to quit`
    ),
    "",
  ].join("\n");
}

export function renderModelSamples(currentModel: string): string {
  return [
    chalk.bold("\nSuggested models:"),
    ...SAMPLE_MODELS.map((model) =>
      `  ${model === currentModel ? chalk.green("●") : "○"} ${model}`
    ),
    chalk.gray("  You can also enter any provider-specific model id."),
  ].join("\n");
}

export function describeToolProgress(toolName: string, input: unknown): string {
  const payload = isRecord(input) ? input : {};
  switch (toolName) {
    case "Read":
      return describeWithTarget("Reading", payload.file_path ?? payload.path);
    case "Write":
      return describeWithTarget("Writing", payload.file_path ?? payload.path);
    case "Edit":
      return describeWithTarget("Editing", payload.file_path ?? payload.path);
    case "Glob":
      return describeWithTarget("Scanning for files", payload.pattern);
    case "Grep":
      return describeWithTarget("Searching code", payload.pattern ?? payload.query);
    case "Bash":
      return describeWithTarget("Running command", payload.command ?? payload.cmd);
    default:
      return `Using ${toolName}`;
  }
}

function describeWithTarget(action: string, target: unknown): string {
  if (typeof target !== "string" || target.trim().length === 0) {
    return action;
  }

  const clean = target.trim().replace(/\s+/g, " ");
  const shortened = clean.length > 60 ? `${clean.slice(0, 57)}...` : clean;
  return `${action} ${shortened}`;
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
