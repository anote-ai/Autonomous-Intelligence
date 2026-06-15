// Tool implementations for the non-Anthropic agentic loop.
// Each tool mirrors the behaviour of the claude-agent-sdk built-in tools.

import * as fs from "fs";
import * as path from "path";
import * as child_process from "child_process";
import { glob } from "glob";

export interface ToolResult {
  content: string;
  isError?: boolean;
}

// OpenAI-compatible tool definitions (also used for Gemini via adapter)
export const TOOL_DEFINITIONS = [
  {
    type: "function" as const,
    function: {
      name: "Read",
      description: "Read a file from the filesystem. Returns the file content.",
      parameters: {
        type: "object",
        properties: {
          file_path: { type: "string", description: "Absolute or cwd-relative file path to read" },
          offset: { type: "number", description: "Line number to start reading from (1-based, optional)" },
          limit: { type: "number", description: "Number of lines to read (optional)" },
        },
        required: ["file_path"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "Write",
      description: "Write content to a file, creating it if it does not exist.",
      parameters: {
        type: "object",
        properties: {
          file_path: { type: "string", description: "File path to write" },
          content: { type: "string", description: "Content to write" },
        },
        required: ["file_path", "content"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "Edit",
      description: "Replace an exact string in a file with new text.",
      parameters: {
        type: "object",
        properties: {
          file_path: { type: "string", description: "File path to edit" },
          old_string: { type: "string", description: "Exact string to find and replace" },
          new_string: { type: "string", description: "Replacement string" },
        },
        required: ["file_path", "old_string", "new_string"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "Bash",
      description: "Run a shell command. Returns stdout + stderr combined.",
      parameters: {
        type: "object",
        properties: {
          command: { type: "string", description: "Shell command to execute" },
          timeout: { type: "number", description: "Timeout in milliseconds (default 30000)" },
        },
        required: ["command"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "Glob",
      description: "Find files matching a glob pattern.",
      parameters: {
        type: "object",
        properties: {
          pattern: { type: "string", description: "Glob pattern e.g. src/**/*.ts" },
          cwd: { type: "string", description: "Directory to search from (optional)" },
        },
        required: ["pattern"],
      },
    },
  },
  {
    type: "function" as const,
    function: {
      name: "Grep",
      description: "Search for a regex pattern in files.",
      parameters: {
        type: "object",
        properties: {
          pattern: { type: "string", description: "Regex or literal pattern to search for" },
          path: { type: "string", description: "File or directory to search (optional)" },
          include: { type: "string", description: "Glob pattern to restrict which files are searched" },
        },
        required: ["pattern"],
      },
    },
  },
];

/** Execute a named tool with the given args, relative to cwd. */
export async function executeTool(
  name: string,
  args: Record<string, unknown>,
  cwd: string,
  allowedTools: string[]
): Promise<ToolResult> {
  if (!allowedTools.includes(name)) {
    return { content: `Tool "${name}" is not in the allowed tools list.`, isError: true };
  }

  try {
    switch (name) {
      case "Read": {
        const filePath = resolveFilePath(String(args["file_path"]), cwd);
        const raw = fs.readFileSync(filePath, "utf8");
        const lines = raw.split("\n");
        const offset = typeof args["offset"] === "number" ? args["offset"] - 1 : 0;
        const limit = typeof args["limit"] === "number" ? args["limit"] : lines.length;
        const slice = lines.slice(offset, offset + limit);
        return { content: slice.map((l, i) => `${offset + i + 1}\t${l}`).join("\n") };
      }

      case "Write": {
        const filePath = resolveFilePath(String(args["file_path"]), cwd);
        fs.mkdirSync(path.dirname(filePath), { recursive: true });
        fs.writeFileSync(filePath, String(args["content"]), "utf8");
        return { content: `Written ${filePath}` };
      }

      case "Edit": {
        const filePath = resolveFilePath(String(args["file_path"]), cwd);
        const src = fs.readFileSync(filePath, "utf8");
        const oldStr = String(args["old_string"]);
        if (!src.includes(oldStr)) {
          return { content: `old_string not found in ${filePath}`, isError: true };
        }
        fs.writeFileSync(filePath, src.replace(oldStr, () => String(args["new_string"])), "utf8");
        return { content: `Edited ${filePath}` };
      }

      case "Bash": {
        const cmd = String(args["command"]);
        const timeout = typeof args["timeout"] === "number" ? args["timeout"] : 30_000;
        const result = child_process.spawnSync("bash", ["-c", cmd], {
          cwd,
          timeout,
          encoding: "utf8",
          maxBuffer: 2 * 1024 * 1024,
        });
        const out = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
        return { content: out || "(no output)", isError: result.status !== 0 };
      }

      case "Glob": {
        const searchCwd = args["cwd"] ? resolveFilePath(String(args["cwd"]), cwd) : cwd;
        const files = await glob(String(args["pattern"]), { cwd: searchCwd, nodir: true });
        return { content: files.length ? files.join("\n") : "(no matches)" };
      }

      case "Grep": {
        const grepPath = args["path"] ? resolveFilePath(String(args["path"]), cwd) : cwd;
        const include = args["include"] ? `--include="${String(args["include"])}"` : "";
        const cmd = `grep -rn --color=never ${include} -E ${JSON.stringify(String(args["pattern"]))} ${JSON.stringify(grepPath)} 2>/dev/null | head -200`;
        const result = child_process.spawnSync("bash", ["-c", cmd], {
          encoding: "utf8",
          maxBuffer: 1024 * 1024,
        });
        return { content: result.stdout.trim() || "(no matches)" };
      }

      default:
        return { content: `Unknown tool: ${name}`, isError: true };
    }
  } catch (err) {
    return { content: String(err), isError: true };
  }
}

function resolveFilePath(filePath: string, cwd: string): string {
  return path.isAbsolute(filePath) ? filePath : path.resolve(cwd, filePath);
}
