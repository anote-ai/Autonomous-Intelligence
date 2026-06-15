import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";
import * as fs from "fs";
import { query, type Options, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import { CODING_SYSTEM_PROMPT } from "../agent.js";

function run(cmd: string, cwd: string): string {
  try {
    return execSync(cmd, { cwd, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

async function reviewDiff(diff: string, context: string): Promise<void> {
  if (!diff.trim()) {
    console.log(chalk.yellow("No diff to review."));
    return;
  }

  const prompt = `Review the following code diff and provide actionable feedback.

${context ? `Context: ${context}\n\n` : ""}Diff:
\`\`\`diff
${diff.slice(0, 12000)}
\`\`\`

For each issue found:
- State the file and line(s) affected
- Describe the problem clearly
- Suggest a concrete fix

Cover: bugs, security issues, performance problems, missing error handling, style inconsistencies, and logic errors.
If the diff looks good, say so briefly. Be concise and direct.`;

  const options: Options = {
    cwd: process.cwd(),
    allowedTools: [],
    permissionMode: "default",
    systemPrompt: CODING_SYSTEM_PROMPT,
    maxTurns: 1,
  };

  console.log(chalk.bold.cyan("\n── Anote Diff Review ──────────────────────\n"));

  for await (const message of query({ prompt, options })) {
    const msg = message as SDKMessage;
    if (msg.type === "assistant") {
      for (const block of msg.message.content) {
        if (block.type === "text") process.stdout.write(block.text);
      }
    }
  }

  console.log(chalk.bold.cyan("\n────────────────────────────────────────\n"));
}

export function diffCommand(): Command {
  const cmd = new Command("diff");
  cmd
    .description("AI review of a git diff or file")
    .option("--staged", "Review staged changes (git diff --cached)")
    .option("--head", "Review changes vs HEAD (git diff HEAD)")
    .option("-b, --base <branch>", "Review diff against a base branch")
    .option("-f, --file <path>", "Review a specific diff file instead of running git diff")
    .option("--last <n>", "Review the last N commits", "1")
    .option("-c, --context <text>", "Additional context to pass to the reviewer")
    .action(async (options: {
      staged?: boolean;
      head?: boolean;
      base?: string;
      file?: string;
      last?: string;
      context?: string;
    }) => {
      const cwd = process.cwd();
      let diff = "";

      const isStdinPiped = !process.stdin.isTTY;
      if (isStdinPiped) {
        const chunks: Buffer[] = [];
        for await (const chunk of process.stdin) chunks.push(chunk as Buffer);
        diff = Buffer.concat(chunks).toString("utf8");
      } else if (options.file) {
        if (!fs.existsSync(options.file)) {
          console.error(chalk.red(`File not found: ${options.file}`));
          process.exit(1);
        }
        diff = fs.readFileSync(options.file, "utf8");
      } else if (options.staged) {
        diff = run("git diff --cached", cwd);
        if (!diff) {
          console.error(chalk.red("No staged changes. Use `git add` to stage files first."));
          process.exit(1);
        }
      } else if (options.base) {
        const branch = run("git rev-parse --abbrev-ref HEAD", cwd);
        diff = run(`git diff ${options.base}...${branch}`, cwd);
        if (!diff) console.log(chalk.yellow(`No diff found between ${options.base} and ${branch}.`));
      } else if (options.last) {
        const n = parseInt(options.last, 10);
        diff = run(`git diff HEAD~${n}..HEAD`, cwd);
      } else {
        diff = run("git diff HEAD", cwd);
        if (!diff) {
          console.log(chalk.yellow("No changes found. Try --staged or --last."));
          return;
        }
      }

      await reviewDiff(diff, options.context ?? "");
    });

  return cmd;
}
