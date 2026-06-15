import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function perfCommand(): Command {
  return new Command("perf")
    .description("Identify performance bottlenecks and suggest targeted improvements")
    .argument("[target]", "entry file or directory to analyse (default: entire project)")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use")
    .option("--fix", "auto-apply refactors the AI is confident about")
    .option("--dry-run", "report only — do not write files")
    .option("--focus <areas>", "comma-separated: db,io,memory,bundle,rendering,concurrency")
    .action(async (target: string | undefined, opts: {
      dir: string; model?: string; fix?: boolean; dryRun?: boolean; focus?: string;
    }) => {
      const cwd = path.resolve(opts.dir);
      const doFix = Boolean(opts.fix) && !opts.dryRun;
      const scope = target ? `\`${target}\`` : "the project";
      const focusAreas = opts.focus
        ? opts.focus.split(",").map((s) => s.trim()).filter(Boolean)
        : ["database", "I/O", "memory", "CPU", "bundle size", "concurrency"];

      console.log(chalk.bold.cyan(`\n◆ Anote  perf`) +
        chalk.gray(`  analysing ${scope}`) +
        (doFix ? chalk.yellow("  [--fix]") : chalk.gray("  [report only]")) + "\n");

      const prompt = `Analyse ${scope} for performance bottlenecks. Focus: ${focusAreas.join(", ")}.

Look for: N+1 queries, missing indexes, sequential awaits, blocking I/O, memory leaks, O(n²) loops, large bundle imports, event-loop blocking.

For each issue: Severity (high/medium/low), File:Line, Pattern, Before/After snippet.
${doFix ? "Apply confident refactors. Add // perf: <reason> comment." : "Do NOT modify files. Report only."}
Summarise: "Found N bottlenecks (X high, Y medium, Z low)."``;

      await runAgentStream({
        prompt, cwd, model: opts.model,
        allowedTools: doFix ? ["Read", "Write", "Edit", "Grep", "Glob", "Bash"] : ["Read", "Grep", "Glob", "Bash"],
        permissionMode: doFix ? "acceptEdits" : "default",
      });
    });
}
