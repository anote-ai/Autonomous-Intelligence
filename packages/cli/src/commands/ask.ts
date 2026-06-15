import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import { runAgentStream } from "../agent.js";
import { createSpinner } from "../ui.js";

/** Read all of stdin (non-blocking — returns "" if stdin is a TTY). */
async function readStdin(): Promise<string> {
  if (process.stdin.isTTY) return "";
  return new Promise((resolve) => {
    const chunks: Buffer[] = [];
    process.stdin.on("data", (chunk: Buffer) => chunks.push(chunk));
    process.stdin.on("end", () => resolve(Buffer.concat(chunks).toString("utf8").trim()));
    process.stdin.on("error", () => resolve(""));
  });
}

const DEFAULT_COMPARE_MODELS = [
  "claude-opus-4-6",
  "claude-sonnet-4-6",
  "claude-haiku-4-5-20251001",
];

export function askCommand(): Command {
  return new Command("ask")
    .alias("a")
    .description("Ask a question about your code or get AI help")
    .argument("[question...]", "your question or request (omit to read from stdin)")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-f, --file <path>", "focus on a specific file")
    .option("--no-edit", "read-only mode, no file modifications")
    .option("--compare", "run the same prompt across multiple models side by side")
    .option(
      "--models <list>",
      "comma-separated models to use with --compare",
      DEFAULT_COMPARE_MODELS.join(","),
    )
    .action(async (questionParts: string[], opts) => {
      const cwd = path.resolve(opts.dir);

      // Read piped stdin (e.g. `git diff | anote ask "write a commit message"`)
      const stdinContent = await readStdin();

      const question = questionParts.join(" ").trim();
      if (!question && !stdinContent) {
        console.error(chalk.red("Provide a question as an argument or pipe content via stdin."));
        process.exit(1);
      }

      // Build the prompt: if stdin is present, include it as context
      let prompt: string;
      if (stdinContent && question) {
        prompt = `${question}\n\n\`\`\`\n${stdinContent}\n\`\`\``;
      } else if (stdinContent) {
        prompt = stdinContent;
      } else {
        prompt = question;
      }

      if (opts.file) {
        const filePath = path.resolve(cwd, opts.file);
        if (!fs.existsSync(filePath)) {
          console.error(chalk.red(`File not found: ${filePath}`));
          process.exit(1);
        }
        const MAX_FILE_BYTES = 150_000;
        const stat = fs.statSync(filePath);
        let content = fs.readFileSync(filePath, "utf-8");
        if (stat.size > MAX_FILE_BYTES) {
          console.warn(
            chalk.yellow(
              `Warning: ${opts.file} is large (${(stat.size / 1024).toFixed(0)}KB). ` +
              `Including only the first ${(MAX_FILE_BYTES / 1024).toFixed(0)}KB.\n`
            )
          );
          content = content.slice(0, MAX_FILE_BYTES) + "\n\n[... file truncated ...]";
        }
        prompt = `File: ${opts.file}\n\`\`\`\n${content}\n\`\`\`\n\n${prompt}`;
      }

      // ── Compare mode ─────────────────────────────────────────────────────
      if (opts.compare) {
        const models: string[] = (opts.models as string)
          .split(",")
          .map((m: string) => m.trim())
          .filter(Boolean);

        if (models.length < 2) {
          console.error(chalk.red("--compare requires at least 2 models. Use --models a,b[,c]."));
          process.exit(1);
        }

        console.log(
          chalk.bold.cyan("\n── Compare mode ───────────────────────────────────────────────────\n") +
          chalk.gray(`  Models: ${models.join("  •  ")}\n`) +
          chalk.gray(`  Prompt: ${prompt.slice(0, 80)}${prompt.length > 80 ? "…" : ""}\n`)
        );

        const spinner = createSpinner("Querying models sequentially…").start();
        spinner.stop();

        for (const model of models) {
          const bar = "─".repeat(Math.max(0, 54 - model.length));
          console.log(chalk.bold.cyan(`\n── ${model} ${bar}`));
          try {
            await runAgentStream({
              prompt,
              cwd,
              model,
              allowedTools: opts.edit
                ? ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
                : ["Read", "Glob", "Grep"],
              permissionMode: "default",
              showToolUse: false,
            });
          } catch (err) {
            console.error(chalk.red(`Error: ${err instanceof Error ? err.message : String(err)}`));
          }
        }
        console.log(chalk.bold.cyan("\n" + "─".repeat(58) + "\n"));
        return;
      }

      // ── Normal mode ─────────────────────────────────────────────────────────
      const label = question || (stdinContent.slice(0, 60) + (stdinContent.length > 60 ? "…" : ""));
      const spinner = createSpinner(`Thinking about: ${label}`).start();

      // Stop spinner as soon as the first token arrives
      let spinnerStopped = false;
      const stopSpinner = () => {
        if (!spinnerStopped) { spinner.stop(); spinnerStopped = true; }
      };

      process.stdout.on("write" as never, stopSpinner);

      try {
        await runAgentStream({
          prompt,
          cwd,
          allowedTools: opts.edit
            ? ["Read", "Write", "Edit", "Bash", "Glob", "Grep"]
            : ["Read", "Glob", "Grep"],
          permissionMode: "default",
          onFirstToken: stopSpinner,
        });
      } finally {
        stopSpinner();
      }
    });
}
