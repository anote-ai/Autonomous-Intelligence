import { query, type Options, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import { loadConfig } from "./config.js";
import { HookRunner } from "./hooks.js";
import { describeToolProgress } from "./ui.js";
import { ANOTE_SYSTEM_PROMPT, buildSystemPrompt } from "./prompts.js";
import { resolveProvider, getAdapter } from "./providers/index.js";

export interface AgentRunOptions {
  prompt: string;
  cwd?: string;
  allowedTools?: string[];
  permissionMode?: "default" | "acceptEdits" | "bypassPermissions";
  systemPrompt?: string;
  maxTurns?: number;
  model?: string;
  /** If true, emit a tool-use indicator line for each tool call */
  showToolUse?: boolean;
  /** Called once when the first text token is emitted (useful for dismissing spinners). */
  onFirstToken?: () => void;
  /** Called for each tool call with the tool name and input (useful for updating spinners). */
  onTool?: (toolName: string, input: unknown) => void;
  /** If true, suppress streaming text to stdout (useful when output is captured). */
  suppressTextOutput?: boolean;
}

/** Re-export so existing callers continue to work. */
export const CODING_SYSTEM_PROMPT = ANOTE_SYSTEM_PROMPT;

/** Walk up from cwd to find CLAUDE.md or CLAW.md and return its content. */
function loadProjectMemory(cwd: string): string {
  const names = ["CLAUDE.md", "CLAW.md", "claude.md", "claw.md"];
  let dir = cwd;
  for (let i = 0; i < 8; i++) {
    for (const name of names) {
      const p = path.join(dir, name);
      if (fs.existsSync(p)) {
        try {
          const content = fs.readFileSync(p, "utf8").trim();
          if (content) return content;
        } catch { /* skip */ }
      }
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return "";
}

export async function runAgentStream(opts: AgentRunOptions): Promise<string> {
  const cwd = opts.cwd ?? process.cwd();
  const config = loadConfig(cwd);
  const hooks = new HookRunner(config.hooks ?? {});

  // Build system prompt — append project memory if found
  let systemPrompt = opts.systemPrompt;
  if (!systemPrompt) {
    const memory = loadProjectMemory(cwd);
    systemPrompt = buildSystemPrompt(memory);
    if (memory) {
      console.log(chalk.gray("  (project memory loaded)\n"));
    }
  }

  const allowedTools = opts.allowedTools ?? ["Read", "Write", "Edit", "Bash", "Glob", "Grep"];
  const maxTurns = opts.maxTurns ?? config.maxTurns ?? 30;
  const model = opts.model ?? config.model ?? "";

  console.log(chalk.bold.cyan("\n── Anote ──────────────────────────────"));

  const provider = model ? resolveProvider(model) : "anthropic";

  if (provider !== "anthropic") {
    const result = await runViaAdapter(provider, model, opts.prompt, {
      cwd,
      allowedTools,
      systemPrompt,
      maxTurns,
      model,
    }, opts, hooks);
    console.log(chalk.bold.cyan("\n────────────────────────────────────\n"));
    return result;
  }

  // ── Anthropic path — claude-agent-sdk ────────────────────────────────────
  const options: Options = {
    cwd,
    allowedTools,
    permissionMode: opts.permissionMode ?? config.permissionMode ?? "default",
    systemPrompt,
    maxTurns,
  };

  let result = "";
  let firstToken = true;

  for await (const message of query({ prompt: opts.prompt, options })) {
    const msg = message as SDKMessage;

    if (msg.type === "result" && msg.subtype === "success") {
      result = msg.result;
    } else if (msg.type === "assistant") {
      for (const block of msg.message.content) {
        if (block.type === "text") {
          if (firstToken) {
            firstToken = false;
            opts.onFirstToken?.();
          }
          if (!opts.suppressTextOutput) process.stdout.write(block.text);
        } else if (block.type === "tool_use" && opts.showToolUse !== false) {
          const hookResult = hooks.runPreToolUse(
            block.name,
            JSON.stringify(block.input ?? {})
          );
          if (hookResult.denied) {
            process.stdout.write(
              chalk.red(`\n  ✗ Hook denied ${block.name}: ${hookResult.messages[0] ?? ""}\n`)
            );
          } else if (opts.onTool) {
            opts.onTool(block.name, block.input);
          } else {
            process.stdout.write(
              chalk.gray(`\n  • ${describeToolProgress(block.name, block.input)}\n`)
            );
          }
        }
      }
    }
  }

  console.log(chalk.bold.cyan("\n────────────────────────────────────\n"));
  return result;
}

// ── Non-Anthropic provider path ──────────────────────────────────────────────────

async function runViaAdapter(
  provider: string,
  model: string,
  prompt: string,
  streamOpts: { cwd: string; allowedTools: string[]; systemPrompt: string; maxTurns: number; model: string },
  runOpts: AgentRunOptions,
  hooks: HookRunner
): Promise<string> {
  const { adapter, error } = getAdapter(model);

  if (error) {
    process.stderr.write(chalk.red(`\n✗ ${error}\n`) +
      chalk.gray(`  Set ${providerKeyEnvVar(provider)} or switch to a different model.\n\n`));
    return "";
  }

  const messages = [{ role: "user" as const, content: prompt }];
  let result = "";
  let firstToken = true;

  for await (const event of adapter.stream(messages, streamOpts)) {
    switch (event.type) {
      case "text":
        if (firstToken) {
          firstToken = false;
          runOpts.onFirstToken?.();
        }
        if (!runOpts.suppressTextOutput) process.stdout.write(event.text);
        result += event.text;
        break;

      case "tool": {
        const toolName = event.tool;
        const input = event.input as Record<string, unknown>;
        const hookResult = hooks.runPreToolUse(toolName, JSON.stringify(input));
        if (hookResult.denied) {
          process.stdout.write(
            chalk.red(`\n  ✗ Hook denied ${toolName}: ${hookResult.messages[0] ?? ""}\n`)
          );
        } else if (runOpts.onTool) {
          runOpts.onTool(toolName, input);
        } else if (runOpts.showToolUse !== false) {
          process.stdout.write(
            chalk.gray(`\n  • ${describeToolProgress(toolName, input)}\n`)
          );
        }
        break;
      }

      case "done":
        if (event.result) result = event.result;
        break;

      case "error":
        process.stderr.write(chalk.red(`\n✗ ${event.message}\n`));
        break;
    }
  }

  return result;
}

function providerKeyEnvVar(provider: string): string {
  switch (provider) {
    case "openai": return "OPENAI_API_KEY";
    case "gemini": return "GEMINI_API_KEY";
    default: return "ANTHROPIC_API_KEY";
  }
}
