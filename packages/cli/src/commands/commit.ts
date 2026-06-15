import { Command } from "commander";
import chalk from "chalk";
import { execSync, spawnSync } from "child_process";
import { query, type Options, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import { CODING_SYSTEM_PROMPT } from "../agent.js";

function getStagedDiff(cwd: string): string {
  try {
    return execSync("git diff --cached", { cwd, encoding: "utf8" });
  } catch {
    return "";
  }
}

function getStagedFiles(cwd: string): string {
  try {
    return execSync("git diff --cached --name-only", { cwd, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function getRecentLog(cwd: string, n = 5): string {
  try {
    return execSync(`git log --oneline -${n}`, { cwd, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

async function generateCommitMessage(diff: string, stagedFiles: string, recentLog: string): Promise<string> {
  const prompt = `Generate a concise, conventional git commit message for the following staged changes.

Staged files:
${stagedFiles || "(none listed)"}

Recent commit history (for style reference):
${recentLog || "(no history)"}

Staged diff:
\`\`\`diff
${diff.slice(0, 8000)}
\`\`\`

Rules:
- Use conventional commit format: type(scope): short description
- Types: feat, fix, refactor, docs, test, chore, style, perf, build, ci
- First line: max 72 characters, imperative mood, no trailing period
- Optionally add a blank line and a short body (2-4 bullet points) for complex changes
- Be specific about what changed, not just that it changed
- Output ONLY the commit message, nothing else`;

  const options: Options = {
    cwd: process.cwd(),
    allowedTools: [],
    permissionMode: "default",
    systemPrompt: CODING_SYSTEM_PROMPT,
    maxTurns: 1,
  };

  let result = "";
  for await (const message of query({ prompt, options })) {
    const msg = message as SDKMessage;
    if (msg.type === "result" && msg.subtype === "success") {
      result = msg.result.trim();
    }
  }
  return result;
}

export function commitCommand(): Command {
  const cmd = new Command("commit");
  cmd
    .description("Generate an AI commit message and optionally commit staged changes")
    .option("-y, --yes", "Commit immediately without prompting")
    .option("-e, --edit", "Open the message in $EDITOR before committing")
    .option("--dry-run", "Print the generated message but do not commit")
    .option("--amend", "Amend the previous commit with the generated message")
    .action(async (options: { yes?: boolean; edit?: boolean; dryRun?: boolean; amend?: boolean }) => {
      const cwd = process.cwd();

      const stagedFiles = getStagedFiles(cwd);
      if (!stagedFiles && !options.amend) {
        console.error(chalk.red("No staged changes found. Run `git add` first."));
        process.exit(1);
      }

      const diff = getStagedDiff(cwd);
      if (!diff && !options.amend) {
        console.error(chalk.red("No staged diff found. Ensure changes are staged with `git add`."));
        process.exit(1);
      }

      const recentLog = getRecentLog(cwd);

      console.log(chalk.cyan("\n── Generating commit message ──────────────────────────\n"));

      let commitMsg: string;
      try {
        commitMsg = await generateCommitMessage(diff, stagedFiles, recentLog);
      } catch (err) {
        console.error(chalk.red("Failed to generate commit message:"), String(err));
        process.exit(1);
      }

      if (!commitMsg) {
        console.error(chalk.red("No commit message was generated."));
        process.exit(1);
      }

      console.log(chalk.bold("Generated commit message:\n"));
      console.log(chalk.white(commitMsg));
      console.log();

      if (options.dryRun) {
        console.log(chalk.gray("(dry-run: not committing)"));
        return;
      }

      let confirmed = options.yes ?? false;
      if (!confirmed && !options.edit) {
        const { createInterface } = await import("readline");
        const rl = createInterface({ input: process.stdin, output: process.stdout });
        confirmed = await new Promise<boolean>((resolve) => {
          rl.question(chalk.bold("Commit with this message? [Y/n/e(edit)] "), (ans) => {
            rl.close();
            const a = ans.trim().toLowerCase();
            if (a === "e") {
              resolve(false);
              options.edit = true;
            } else {
              resolve(a === "" || a === "y");
            }
          });
        });
      }

      if (options.edit) {
        const os = await import("os");
        const path = await import("path");
        const fs = await import("fs");
        const tmpFile = path.join(os.tmpdir(), `anote-commit-${Date.now()}.txt`);
        fs.writeFileSync(tmpFile, commitMsg, "utf8");
        const editor = process.env.EDITOR ?? process.env.VISUAL ?? "vi";
        spawnSync(editor, [tmpFile], { stdio: "inherit" });
        commitMsg = fs.readFileSync(tmpFile, "utf8").trim();
        fs.unlinkSync(tmpFile);
        confirmed = true;
      }

      if (!confirmed) {
        console.log(chalk.gray("Commit cancelled."));
        return;
      }

      try {
        const args = ["commit", "-m", commitMsg];
        if (options.amend) args.push("--amend");
        const result = spawnSync("git", args, { cwd, encoding: "utf8", stdio: "pipe" });
        if (result.status !== 0) {
          console.error(chalk.red("git commit failed:"), result.stderr?.trim() ?? "");
          process.exit(1);
        }
        console.log(chalk.green("\n✔ Committed successfully\n"));
        console.log(result.stdout.trim());
      } catch (err) {
        console.error(chalk.red("Error running git commit:"), String(err));
        process.exit(1);
      }
    });
  return cmd;
}
