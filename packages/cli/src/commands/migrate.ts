import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function migrateCommand(): Command {
  return new Command("migrate")
    .description("Find and rewrite deprecated patterns across the codebase")
    .requiredOption("--from <pattern>", "pattern or API to migrate away from")
    .requiredOption("--to <pattern>", "replacement pattern or API")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use")
    .option("--dry-run", "show what would change without writing any files")
    .option("--include <glob>", "only migrate files matching this glob")
    .action(async (opts: { from: string; to: string; dir: string; model?: string; dryRun?: boolean; include?: string }) => {
      const cwd = path.resolve(opts.dir);
      const isDryRun = Boolean(opts.dryRun);
      const scope = opts.include ? `Limit to files matching: ${opts.include}` : "Search the entire codebase.";

      console.log(chalk.bold.cyan(`\n◆ Anote  migrate`) +
        chalk.gray(`  ${opts.from} → ${opts.to}`) +
        (isDryRun ? chalk.yellow("  [dry-run]") : "") + "\n");

      const prompt = `Migrate the codebase from \`${opts.from}\` to \`${opts.to}\`.
${scope}
1. Search for all files using \`${opts.from}\`.
2. For each file: read, understand context, ${isDryRun ? "show planned diff — do NOT write" : "rewrite using `" + opts.to + "`"}.
3. Summarize: files changed, edge cases, files skipped.

Be careful with import paths, type signatures, and semantic differences.
${isDryRun ? "DRY RUN: Do not write or edit any files." : ""}`;

      await runAgentStream({
        prompt, cwd, model: opts.model,
        allowedTools: isDryRun ? ["Read", "Grep", "Glob"] : ["Read", "Write", "Edit", "Bash", "Grep", "Glob"],
        permissionMode: isDryRun ? "default" : "acceptEdits",
      });
    });
}
