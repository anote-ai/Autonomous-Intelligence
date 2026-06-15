import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { execSync } from "child_process";
import { runAgentStream } from "../agent.js";

export function changelogCommand(): Command {
  return new Command("changelog")
    .description("Read git history and write a human-readable CHANGELOG section")
    .option("--since <tag>", "git tag or commit to start from (e.g. v1.0.0, HEAD~20)")
    .option("--until <ref>", "end reference (default: HEAD)")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use")
    .option("--dry-run", "print the changelog to stdout instead of writing CHANGELOG.md")
    .option("--append", "prepend the new section at the top of the existing CHANGELOG.md")
    .action(async (opts: { since?: string; until?: string; dir: string; model?: string; dryRun?: boolean; append?: boolean }) => {
      const cwd = path.resolve(opts.dir);
      const isDryRun = Boolean(opts.dryRun);
      const since = opts.since ?? "";
      const until = opts.until ?? "HEAD";

      let gitLog = "";
      try {
        const range = since ? `${since}..${until}` : `${until}~50..${until}`;
        gitLog = execSync(
          `git log ${range} --pretty=format:"%h %s (%an)" --no-merges 2>/dev/null | head -200`,
          { cwd, encoding: "utf8", shell: "/bin/bash" }
        ).trim();
      } catch { /* git not available or no commits */ }

      if (!gitLog) {
        console.log(chalk.yellow("\n◆ No commits found in the given range.\n"));
        console.log(chalk.gray("  Try: anote changelog --since v1.0.0"));
        return;
      }

      const rangeLabel = since ? `since ${since}` : "last 50 commits";
      console.log(chalk.bold.cyan(`\n◆ Anote  changelog`) +
        chalk.gray(`  ${rangeLabel}`) +
        (isDryRun ? chalk.yellow("  [stdout]") : "") + "\n");

      const today = new Date().toISOString().slice(0, 10);
      const prompt = `Write a CHANGELOG section from the following git commit history.

Git log (${rangeLabel}):
\`\`\`
${gitLog}
\`\`\`

Format as a Markdown CHANGELOG section (## [Unreleased] — ${today}). Group by: Features, Bug Fixes, Breaking Changes, Improvements. Rewrite commit messages in plain English. Skip trivial commits.

${isDryRun ? "Print only the Markdown. Do not write files." : "Write to CHANGELOG.md (prepend if exists, create with header if not)."}`;

      await runAgentStream({
        prompt, cwd, model: opts.model,
        allowedTools: isDryRun ? ["Read", "Bash"] : ["Read", "Write", "Edit", "Bash"],
        permissionMode: isDryRun ? "default" : "acceptEdits",
      });
    });
}
