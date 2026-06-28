/**
 * Config loader — reads .anote.json (or falls back to CLAW.md discovery).
 * Supports PreToolUse / PostToolUse shell hooks, model override, and permission mode.
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export interface HookConfig {
  preToolUse?: string[];
  postToolUse?: string[];
}

export interface AnoteConfig {
  model?: string;
  permissionMode?: "default" | "acceptEdits" | "bypassPermissions" | "plan";
  hooks?: HookConfig;
  maxTurns?: number;
  compactAfterMessages?: number;
  /** Explicit provider override. Usually auto-detected from the model string. */
  provider?: string;
  /** Base URL for OpenAI-compatible endpoints (e.g. http://localhost:11434/v1 for Ollama). */
  baseUrl?: string;
}

const CONFIG_FILENAMES = [".anote.json", ".claw.json", "anote.config.json"];

/**
 * Walk up from cwd searching for a config file.
 */
export function loadConfig(cwd: string = process.cwd()): AnoteConfig {
  let dir = path.resolve(cwd);
  const root = path.parse(dir).root;

  while (dir !== root) {
    for (const filename of CONFIG_FILENAMES) {
      const candidate = path.join(dir, filename);
      if (fs.existsSync(candidate)) {
        try {
          const raw = fs.readFileSync(candidate, "utf8");
          const parsed = JSON.parse(raw) as AnoteConfig;
          return parsed;
        } catch (err) {
          process.stderr.write(
            `\x1b[33mWarning: Could not parse config file ${candidate} — ${err instanceof Error ? err.message : String(err)}\x1b[0m\n`
          );
        }
      }
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }

  // Also check ~/.anote/config.json
  const globalConfig = path.join(os.homedir(), ".anote", "config.json");
  if (fs.existsSync(globalConfig)) {
    try {
      const raw = fs.readFileSync(globalConfig, "utf8");
      return JSON.parse(raw) as AnoteConfig;
    } catch (err) {
      process.stderr.write(
        `\x1b[33mWarning: Could not parse global config ${globalConfig} — ${err instanceof Error ? err.message : String(err)}\x1b[0m\n`
      );
    }
  }

  return {};
}
