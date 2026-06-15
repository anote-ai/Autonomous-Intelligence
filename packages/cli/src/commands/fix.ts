import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import { spawnSync } from "child_process";
import { runAgentStream } from "../agent.js";
import { createSpinner, describeToolProgress } from "../ui.js";

export function fixCommand(): Command {
  return new Command("fix")
    .alias("f")
    .description("Find and fix bugs — optionally loop until a command passes")
    .argument("[file]", "file to fix (omit to fix the whole project)")
    .argument("[description...]", "description of the bug or error message")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use (e.g. gpt-4.1, gemini-2.5-pro, ollama/llama3.2)")
    .option("--error <message>", "paste an error message to fix a specific error")
    .option("--auto", "auto-accept all file edits without confirmation")
    .option("--loop", "run --cmd, feed failures to the AI, and repeat until it passes")
    .option("--cmd <command>", "command to run each iteration (required with --loop)")
    .option("--max-iterations <n>", "iteration cap for --loop mode (default: 10)", "10")
    .option("--dry-run", "show what the AI would do without writing any files")
    .action(async (file: string | undefined, descParts: string[], opts) => {
      const cwd = path.resolve(opts.dir as string);
      const desc = (descParts as string[]).join(" ");
      const isLoop = Boolean(opts.loop);
      const isDryRun = Boolean(opts.dryRun);
      const maxIterations = isLoop ? Math.max(1, parseInt(opts.maxIterations as string, 10) || 10) : 1;

      // --loop requires --cmd or auto-detection
      let loopCmd: string | null = null;
      if (isLoop) {
        loopCmd = (opts.cmd as string | undefined) ?? detectTestCommand(cwd);
        if (!loopCmd) {
          console.error(
            chalk.red("✗ --loop requires --cmd <command> or a detectable test runner.\n") +
            chalk.gray("  Examples: --cmd \"npm test\"  --cmd \"npx tsc --noEmit\"  --cmd \"cargo test\"")
          );
          process.exit(1);
        }
      }

      // Build initial prompt
      let prompt: string;
      if (opts.error) {
        prompt = `Fix the following error:\n\`\`\`\n${opts.error as string}\n\`\`\`${file ? `\n\nFocus on file: ${file}` : ""}${desc ? `\nAdditional context: ${desc}` : ""}`;
      } else if (file) {
        prompt = `Fix any bugs, errors, or issues in ${file}.${desc ? `\n\nSpecific issue: ${desc}` : "\n\nAnalyze the file thoroughly, identify all problems, and fix them."}`;
      } else if (isLoop && loopCmd) {
        prompt = `The command \`${loopCmd}\` is failing. Read the relevant source files, understand the failures, and fix them.`;
      } else {
        prompt = `Analyze the codebase for bugs and issues.${desc ? `\n\nFocus on: ${desc}` : ""}\n\nRead relevant files, identify problems, and fix them.`;
      }

      const allowedTools = isDryRun
        ? ["Read", "Glob", "Grep"]
        : ["Read", "Write", "Edit", "Bash", "Glob", "Grep"];

      const startTime = Date.now();
      const filesChanged = new Set<string>();
      let aborted = false;
      let iterationsRun = 0;
      let exitReason: "passed" | "max_iterations" | "aborted" | "done" = "done";

      process.on("SIGINT", () => {
        aborted = true;
        process.stderr.write(chalk.yellow("\n\n  Stopping after this iteration...\n"));
      });

      if (isDryRun) {
        console.log(chalk.yellow("\n◆ Anote  Dry-run mode — no files will be written\n"));
      }

      console.log(chalk.bold.cyan(`◆ Anote  fix${isLoop ? ` --loop (max ${maxIterations} iterations)` : ""}`) +
        (loopCmd ? chalk.gray(`  cmd: ${loopCmd}`) : "") + "\n");

      for (let iteration = 1; iteration <= maxIterations && !aborted; iteration++) {
        iterationsRun = iteration;

        if (isLoop) {
          console.log(chalk.bold(`\n◆ Anote  Iteration ${iteration}/${maxIterations}`));
        }

        if (isLoop && loopCmd) {
          const cmdResult = runCommand(loopCmd, cwd);
          printCommandResult(cmdResult);

          if (cmdResult.exitCode === 0) {
            exitReason = "passed";
            break;
          }

          if (iteration === maxIterations) {
            exitReason = "max_iterations";
            break;
          }

          const trimmed = cmdResult.output.slice(-6000);
          prompt = buildFailurePrompt(loopCmd, trimmed, iteration, file);
        }

        const spinner = createSpinner("Analyzing failures...").start();
        let spinnerStopped = false;
        const stopSpinner = () => { if (!spinnerStopped) { spinner.stop(); spinnerStopped = true; } };

        await runAgentStream({
          prompt,
          cwd,
          allowedTools,
          model: opts.model as string | undefined,
          permissionMode: opts.auto || isLoop ? "acceptEdits" : "default",
          onFirstToken: stopSpinner,
          onTool: (toolName, input) => {
            stopSpinner();
            const desc = describeToolProgress(toolName, input);
            console.log(chalk.cyan("◆ ") + chalk.white(desc));
            if ((toolName === "Write" || toolName === "Edit") && typeof (input as Record<string, unknown>)["file_path"] === "string") {
              filesChanged.add((input as Record<string, unknown>)["file_path"] as string);
            }
          },
          showToolUse: false,
        });

        stopSpinner();

        if (!isLoop) break;
      }

      if (aborted) exitReason = "aborted";

      const elapsed = ((Date.now() - startTime) / 1000).toFixed(1);
      const filesStr = filesChanged.size > 0
        ? `${filesChanged.size} file${filesChanged.size > 1 ? "s" : ""} changed`
        : "no files changed";

      if (isLoop) {
        if (exitReason === "passed") {
          console.log(chalk.green(
            `\n◆ Done in ${iterationsRun} iteration${iterationsRun !== 1 ? "s" : ""}, ${elapsed}s. ${filesStr}.`
          ));
        } else if (exitReason === "max_iterations") {
          console.log(chalk.red(`\n◆ Stopped  Reached limit of ${maxIterations} iterations without passing.`));
          console.log(chalk.dim(`  ${filesStr}, ${elapsed}s elapsed`));
        } else if (exitReason === "aborted") {
          console.log(chalk.yellow(`\n◆ Interrupted after ${iterationsRun} iteration${iterationsRun !== 1 ? "s" : ""}.`));
          console.log(chalk.dim(`  ${filesStr}, ${elapsed}s elapsed`));
        }
        if (isDryRun) console.log(chalk.yellow("  Dry-run: no files were written."));
      } else if (filesChanged.size > 0) {
        const relFiles = [...filesChanged].map(f => path.relative(cwd, path.resolve(cwd, f))).join(", ");
        console.log(chalk.dim(`\n  ${filesStr}: ${relFiles}\n`));
        if (isDryRun) console.log(chalk.yellow("  Dry-run: no files were written."));
      }
      console.log();
    });
}

function runCommand(cmd: string, cwd: string): { exitCode: number; output: string; duration: number } {
  const t0 = Date.now();
  process.stdout.write(chalk.cyan("◆ Running: ") + chalk.white(cmd) + "\n");

  const result = spawnSync("bash", ["-c", cmd], {
    cwd,
    encoding: "utf8",
    maxBuffer: 10 * 1024 * 1024,
  });

  const duration = (Date.now() - t0) / 1000;
  const output = [result.stdout, result.stderr].filter(Boolean).join("\n").trim();
  const exitCode = result.status ?? 1;

  return { exitCode, output, duration };
}

function printCommandResult(result: { exitCode: number; output: string; duration: number }): void {
  const { exitCode, output, duration } = result;
  const durationStr = `${duration.toFixed(1)}s`;

  if (exitCode === 0) {
    console.log(chalk.green(`  ✓ All tests passed`) + chalk.dim(` (${durationStr})`));
  } else {
    const failMatch =
      output.match(/(\d+)\s+(?:tests?\s+)?fail(?:ed|ures?)/i) ??
      output.match(/(?:found\s+)?(\d+)\s+errors?/i);
    const summary = failMatch
      ? `${failMatch[1]} test${parseInt(failMatch[1]) !== 1 ? "s" : ""} failed`
      : "failed";
    console.log(chalk.red(`  ✗ ${summary}`) + chalk.dim(` (${durationStr})`));

    const lines = output.split("\n");
    const preview = lines.slice(-20).join("\n");
    console.log(chalk.dim(preview.split("\n").map(l => `    ${l}`).join("\n")));
  }
  console.log();
}

function buildFailurePrompt(cmd: string, output: string, iteration: number, file?: string): string {
  return [
    `Iteration ${iteration}: The command \`${cmd}\` is still failing.`,
    ``,
    `Command output:`,
    `\`\`\``,
    output,
    `\`\`\``,
    ``,
    `Read the relevant source files, understand the root cause, and fix the remaining failures.`,
    file ? `Focus primarily on: ${file}` : "",
    `Avoid re-applying fixes you already tried in earlier iterations.`,
  ].filter(Boolean).join("\n");
}

function detectTestCommand(cwd: string): string | null {
  try {
    const pkg = JSON.parse(fs.readFileSync(path.join(cwd, "package.json"), "utf8"));
    if (pkg.scripts?.test) return "npm test";
    if (pkg.scripts?.vitest) return "npx vitest run";
  } catch { /* no package.json */ }

  const runners: Array<[string, string]> = [
    ["pytest.ini", "pytest"],
    ["pyproject.toml", "pytest"],
    ["setup.py", "python -m pytest"],
    ["Cargo.toml", "cargo test"],
    ["go.mod", "go test ./..."],
  ];

  for (const [indicator, cmd] of runners) {
    if (fs.existsSync(path.join(cwd, indicator))) return cmd;
  }

  return null;
}
