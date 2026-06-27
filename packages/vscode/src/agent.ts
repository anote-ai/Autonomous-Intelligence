import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
// eslint-disable-next-line @typescript-eslint/no-require-imports
const { query } = require("@anthropic-ai/claude-agent-sdk") as typeof import("@anthropic-ai/claude-agent-sdk");
import type { Options, SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import {
  directRuntimeSupportMessage,
  getConfiguredApiKey,
  getMcpServers,
  getModel,
  getProvider,
  getServerUrl,
} from "./config";

export interface StreamChunk {
  type: "text" | "tool" | "tool_result" | "done" | "error";
  content?: string;
  toolName?: string;
  /** Raw tool identifier ("Write", "Edit", "Read", etc.) */
  toolRawName?: string;
  /** Raw tool input arguments */
  toolInput?: Record<string, unknown>;
  error?: string;
}

const BASE_SYSTEM_PROMPT = `You are Anote, an expert AI coding assistant built by Anote AI.
You have access to read files, edit code, run shell commands, and search the codebase.
Help the user with their coding tasks, answer questions, fix bugs, explain code, and generate new functionality.

When making function calls using tools that accept array or object parameters ensure those are structured using JSON. For example:
<example>
example_complex_tool(parameter=[{"color": "orange", "options": {"option_key_1": true, "option_key_2": "value"}}, {"color": "purple", "options": {"option_key_1": true, "option_key_2": "value"}}])
</example>

Answer the user's request using the relevant tool(s), if they are available. Check that all the required parameters for each tool call are provided or can reasonably be inferred from context. IF there are no relevant tools or there are missing values for required parameters, ask the user to supply these values; otherwise proceed with the tool calls. If the user provides a specific value for a parameter (for example provided in quotes), make sure to use that value EXACTLY. DO NOT make up values for or ask about optional parameters.

If you intend to call multiple tools and there are no dependencies between the calls, make all of the independent calls in the same response, otherwise you MUST wait for previous calls to finish first to determine the dependent values (do NOT use placeholders or guess missing parameters).

## Core Reasoning Principles

Think through problems step by step before acting. Use this workflow:

1. **Understand** — Clarify what the user is asking. Identify the goal, constraints, and any ambiguities.
2. **Explore** — Read relevant files, search the codebase, understand existing patterns before proposing changes.
3. **Plan** — Break the task into concrete steps. Identify what needs to change and why.
4. **Execute** — Make targeted, minimal changes. Prefer editing existing files over creating new ones.
5. **Verify** — Run tests or linters when available. Validate that the change is correct and complete.

## Code Quality Standards

- Always read relevant files before making changes — never modify code you haven't inspected
- Make minimal, targeted edits unless asked to refactor broadly
- Follow the existing code style, naming conventions, and project structure
- Explain your reasoning: what you changed, why, and what to watch out for
- Consider edge cases and error handling when adding new functionality

## Tool Usage Patterns

- **Read / Glob / Grep** — Use these first to understand the codebase before writing anything
- **Edit** — Prefer targeted edits over full file rewrites
- **Write** — Only for creating genuinely new files
- **Bash** — Run tests, linters, build commands, or verify output when useful
- Use multiple tools in parallel when they are independent (e.g. reading several files at once)

## Communication Style

- Be concise and practical — lead with the answer, follow with context
- Format code with language-tagged fences (\`\`\`ts, \`\`\`py, etc.)
- Format responses with markdown. Specify language for all code blocks.
- Always be concise and practical. When modifying files, explain your changes.`;

/** Walk up from cwd looking for CLAUDE.md or CLAW.md and return its content. */
function loadProjectMemory(cwd: string): string {
  const names = ["CLAUDE.md", "CLAW.md", "claude.md", "claw.md"];
  let dir = cwd;
  for (let i = 0; i < 6; i++) {
    for (const name of names) {
      const p = path.join(dir, name);
      if (fs.existsSync(p)) {
        try {
          return fs.readFileSync(p, "utf8").trim();
        } catch {
          // skip unreadable
        }
      }
    }
    const parent = path.dirname(dir);
    if (parent === dir) break;
    dir = parent;
  }
  return "";
}

export class AnoteAgent {
  constructor(private readonly context: vscode.ExtensionContext) {}

  private getMaxTurns(): number {
    return vscode.workspace.getConfiguration("anote").get<number>("maxTurns") ?? 30;
  }

  private isAutoEdit(): boolean {
    return vscode.workspace.getConfiguration("anote").get<boolean>("autoEdit") ?? false;
  }

  getCwdForWorkspace(): string {
    const folders = vscode.workspace.workspaceFolders;
    return folders && folders.length > 0 ? folders[0].uri.fsPath : process.cwd();
  }

  async *stream(
    messages: Array<{ role: "user" | "assistant"; content: string }>,
    opts: {
      /** Called BEFORE the SDK executes Write/Edit. Return false to abort without writing. */
      onPreToolUse?: (toolName: string, input: Record<string, unknown>) => Promise<boolean>;
      systemPromptOverride?: string;
    } = {}
  ): AsyncGenerator<StreamChunk> {
    const serverUrl = getServerUrl();
    if (serverUrl) {
      yield* this.streamViaServer(serverUrl, messages);
      return;
    }

    const provider = getProvider();
    const providerWarning = directRuntimeSupportMessage(provider);
    if (providerWarning) {
      yield {
        type: "error",
        error: providerWarning,
      };
      return;
    }

    const apiKey = getConfiguredApiKey();
    if (!apiKey) {
      yield {
        type: "error",
        error: "No API key. Set ANTHROPIC_API_KEY or anote.apiKey in VS Code settings, or configure anote.serverUrl.",
      };
      return;
    }

    // Inject API key so the SDK can find it
    process.env.ANTHROPIC_API_KEY = apiKey;

    const cwd = this.getCwdForWorkspace();

    // Load project memory (CLAUDE.md / CLAW.md)
    const memory = loadProjectMemory(cwd);
    const systemPrompt = opts.systemPromptOverride
      ?? (memory ? `${BASE_SYSTEM_PROMPT}\n\n---\n\n${memory}` : BASE_SYSTEM_PROMPT);

    const last = messages[messages.length - 1];
    let prompt = last?.content ?? "";
    if (messages.length > 1) {
      const history = messages
        .slice(0, -1)
        .map((m) => `${m.role === "user" ? "User" : "Assistant"}: ${m.content}`)
        .join("\n\n");
      prompt = `Previous conversation:\n${history}\n\nUser: ${prompt}`;
    }

    // Wire configured MCP servers and auto-allow their tools (mcp__<server>).
    const mcpServers = getMcpServers();
    const mcpAllow = mcpServers ? Object.keys(mcpServers).map((s) => `mcp__${s}`) : [];

    const options: Options = {
      cwd,
      allowedTools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep", ...mcpAllow],
      permissionMode: this.isAutoEdit() ? "acceptEdits" : "default",
      systemPrompt,
      maxTurns: this.getMaxTurns(),
      model: getModel(),
      ...(mcpServers ? { mcpServers: mcpServers as Options["mcpServers"] } : {}),
    };

    try {
      for await (const sdkMsg of query({ prompt, options })) {
        const msg = sdkMsg as SDKMessage;

        if (msg.type === "assistant") {
          for (const block of msg.message.content) {
            if (block.type === "text") {
              yield { type: "text", content: block.text };
            } else if (block.type === "tool_use") {
              yield {
                type: "tool",
                toolName: block.name,
                toolRawName: block.name,
                toolInput: (block.input as Record<string, unknown>) ?? {},
              };
              // Pre-tool approval: fires AFTER yield but BEFORE the SDK executes the tool
              if (opts.onPreToolUse && (block.name === "Write" || block.name === "Edit")) {
                const approved = await opts.onPreToolUse(
                  block.name,
                  (block.input as Record<string, unknown>) ?? {}
                );
                if (!approved) {
                  yield { type: "error", error: `User rejected the ${block.name} to ${(block.input as Record<string, unknown>).file_path ?? "file"}.` };
                  return;
                }
              }
            }
          }
        } else if (msg.type === "user") {
          for (const block of msg.message.content as Array<{ type: string; tool_use_id?: string }>) {
            if (block.type === "tool_result") {
              yield { type: "tool_result", toolName: block.tool_use_id };
            }
          }
        } else if (msg.type === "result") {
          yield { type: "done" };
        }
      }
    } catch (err) {
      yield { type: "error", error: err instanceof Error ? err.message : String(err) };
    }
  }

  private async *streamViaServer(
    serverUrl: string,
    messages: Array<{ role: "user" | "assistant"; content: string }>
  ): AsyncGenerator<StreamChunk> {
    const last = messages[messages.length - 1];
    const message = last?.content?.trim();
    if (!message) {
      return;
    }

    const response = await fetch(new URL("/api/chat/stream", serverUrl), {
      method: "POST",
      headers: {
        "content-type": "application/json",
      },
      body: JSON.stringify({
        cwd: this.getCwdForWorkspace(),
        message,
        model: getModel(),
        mode: this.isAutoEdit() ? "auto" : "default",
      }),
    });

    if (!response.ok || !response.body) {
      const body = await response.text();
      yield {
        type: "error",
        error: body || `Server request failed with status ${response.status}`,
      };
      return;
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = "";

    while (true) {
      const { done, value } = await reader.read();
      if (done) {
        break;
      }

      buffer += decoder.decode(value, { stream: true });

      while (true) {
        const boundary = buffer.indexOf("\n\n");
        if (boundary === -1) {
          break;
        }

        const rawEvent = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const event = parseServerEvent(rawEvent);
        if (!event) {
          continue;
        }

        switch (event.type) {
          case "text":
            yield {
              type: "text",
              content:
                typeof event.data.text === "string" ? event.data.text : "",
            };
            break;
          case "tool":
            yield {
              type: "tool",
              toolName: describeServerTool(event.data.tool, event.data.input),
              toolRawName: typeof event.data.tool === "string" ? event.data.tool : undefined,
              toolInput: (typeof event.data.input === "object" && event.data.input !== null)
                ? event.data.input as Record<string, unknown>
                : {},
            };
            break;
          case "tool_result":
            yield { type: "tool_result", toolName: "tool-result" };
            break;
          case "done":
            yield { type: "done" };
            break;
          case "error":
            yield {
              type: "error",
              error:
                typeof event.data.message === "string"
                  ? event.data.message
                  : "Unknown server error",
            };
            return;
        }
      }
    }
  }
}

function parseServerEvent(raw: string):
  | { type: string; data: Record<string, unknown> }
  | undefined {
  const lines = raw.split("\n");
  const eventLine = lines.find((line) => line.startsWith("event: "));
  const dataLine = lines.find((line) => line.startsWith("data: "));
  if (!eventLine || !dataLine) {
    return undefined;
  }

  try {
    return {
      type: eventLine.slice(7).trim(),
      data: JSON.parse(dataLine.slice(6)),
    };
  } catch {
    return undefined;
  }
}

function describeServerTool(toolName: unknown, input: unknown): string {
  if (typeof toolName !== "string") {
    return "Using tool";
  }

  const payload = typeof input === "object" && input !== null
    ? (input as Record<string, unknown>)
    : {};
  const target = stringifyTarget(
    payload.file_path ?? payload.path ?? payload.command ?? payload.cmd ?? payload.pattern
  );

  switch (toolName) {
    case "Read":
      return suffix("Reading", target);
    case "Write":
      return suffix("Writing", target);
    case "Edit":
      return suffix("Editing", target);
    case "Glob":
      return suffix("Scanning", target);
    case "Grep":
      return suffix("Searching", target);
    case "Bash":
      return suffix("Running", target);
    default:
      return `Using ${toolName}`;
  }
}

function suffix(prefix: string, target: unknown): string {
  if (typeof target !== "string" || target.trim().length === 0) {
    return prefix;
  }

  const value = target.trim().replace(/\s+/g, " ");
  return `${prefix} ${value.length > 60 ? `${value.slice(0, 57)}...` : value}`;
}

function stringifyTarget(value: unknown): string | undefined {
  return typeof value === "string" ? value : undefined;
}
