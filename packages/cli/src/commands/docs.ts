import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function docsCommand(): Command {
  return new Command("docs")
    .description("Generate JSDoc / docstrings for undocumented exported functions")
    .argument("[target]", "file or directory to document (default: entire project)")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use")
    .option("--overwrite", "regenerate documentation even if a docstring already exists")
    .option("--dry-run", "show planned docs without writing any files")
    .option("--style <style>", "documentation style: jsdoc, tsdoc, google, numpy, sphinx")
    .action(async (target: string | undefined, opts: {
      dir: string; model?: string; overwrite?: boolean; dryRun?: boolean; style?: string;
    }) => {
      const cwd = path.resolve(opts.dir);
      const isDryRun = Boolean(opts.dryRun);
      const scope = target ? `\`${target}\`` : "the entire project";

      console.log(chalk.bold.cyan(`\n◆ Anote  docs`) +
        chalk.gray(`  ${scope}`) +
        (isDryRun ? chalk.yellow("  [dry-run]") : "") + "\n");

      const styleNote = opts.style
        ? `Use ${opts.style} documentation style.`
        : "Auto-detect style from existing docstrings (JSDoc for TS/JS, Google-style for Python).";
      const overwriteNote = opts.overwrite
        ? "Regenerate ALL documentation, even for functions that already have docstrings."
        : "Only document exported functions/classes with NO docstring yet.";

      const prompt = `Generate documentation for ${scope}.
${styleNote}
${overwriteNote}
1. Find source files (skip tests, node_modules, dist).
2. For each undocumented item: write a concise docstring with @param/@returns.
3. ${isDryRun ? "Show planned docstrings — do NOT write files." : "Insert and save."}
4. Print summary: files processed, docstrings added, items skipped.`;

      await runAgentStream({
        prompt, cwd, model: opts.model,
        allowedTools: isDryRun ? ["Read", "Grep", "Glob"] : ["Read", "Write", "Edit", "Grep", "Glob"],
        permissionMode: isDryRun ? "default" : "acceptEdits",
      });
    });
}
