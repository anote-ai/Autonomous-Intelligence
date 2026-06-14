/**
 * Hook runner — executes PreToolUse / PostToolUse shell hooks.
 * Mirrors the Rust implementation in rust/crates/runtime/src/hooks.rs.
 *
 * Exit-code semantics:
 *   0  → allow (stdout captured as message)
 *   2  → deny  (stdout captured as reason)
 *   other → warn but allow
 */

import { execSync } from "child_process";
import chalk from "chalk";
import type { HookConfig } from "./config.js";

export interface HookRunResult {
  denied: boolean;
  messages: string[];
}

export class HookRunner {
  constructor(private readonly config: HookConfig = {}) {}

  runPreToolUse(toolName: string, toolInput: string): HookRunResult {
    return this.runCommands(
      "PreToolUse",
      this.config.preToolUse ?? [],
      toolName,
      toolInput,
      undefined,
      false
    );
  }

  runPostToolUse(
    toolName: string,
    toolInput: string,
    toolOutput: string,
    isError: boolean
  ): HookRunResult {
    return this.runCommands(
      "PostToolUse",
      this.config.postToolUse ?? [],
      toolName,
      toolInput,
      toolOutput,
      isError
    );
  }

  private runCommands(
    event: string,
    commands: string[],
    toolName: string,
    toolInput: string,
    toolOutput: string | undefined,
    isError: boolean
  ): HookRunResult {
    if (commands.length === 0) return { denied: false, messages: [] };

    const payload = JSON.stringify({
      hook_event_name: event,
      tool_name: toolName,
      tool_input: tryParseJson(toolInput),
      tool_input_json: toolInput,
      tool_output: toolOutput ?? null,
      tool_result_is_error: isError,
    });

    const messages: string[] = [];

    for (const cmd of commands) {
      const env: NodeJS.ProcessEnv = {
        ...process.env,
        HOOK_EVENT: event,
        HOOK_TOOL_NAME: toolName,
        HOOK_TOOL_INPUT: toolInput,
        HOOK_TOOL_IS_ERROR: isError ? "1" : "0",
        ...(toolOutput !== undefined ? { HOOK_TOOL_OUTPUT: toolOutput } : {}),
      };

      try {
        const stdout = execSync(cmd, {
          input: payload,
          env,
          encoding: "utf8",
          stdio: ["pipe", "pipe", "pipe"],
        }).trim();

        if (stdout) messages.push(stdout);
      } catch (err: unknown) {
        const e = err as { status?: number; stdout?: string; stderr?: string; message?: string };
        const stdout = (e.stdout ?? "").trim();
        const stderr = (e.stderr ?? "").trim();
        const status = e.status;

        if (status === 2) {
          // Deny
          const reason =
            stdout || `${event} hook denied tool \`${toolName}\``;
          messages.push(reason);
          return { denied: true, messages };
        }

        // Warn but allow
        const detail = stdout || stderr || e.message || "";
        const warning = `Hook \`${cmd}\` exited with status ${status ?? "?"} for \`${toolName}\`; allowing${detail ? ": " + detail : ""}`;
        console.warn(chalk.yellow(`  ⚠ ${warning}`));
        messages.push(warning);
      }
    }

    return { denied: false, messages };
  }
}

function tryParseJson(raw: string): unknown {
  try {
    return JSON.parse(raw);
  } catch {
    return { raw };
  }
}
