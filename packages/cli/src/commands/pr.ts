import { Command } from "commander";
import chalk from "chalk";
import { execSync } from "child_process";
import { query, type Options, type SDKMessage } from "@anthropic-ai/claude-agent-sdk";
import { CODING_SYSTEM_PROMPT } from "../agent.js";

function run(cmd: string, cwd: string): string {
  try {
    return execSync(cmd, { cwd, encoding: "utf8" }).trim();
  } catch {
    return "";
  }
}

function getDefaultBranch(cwd: string): string {
  const remote = run("git remote show origin 2>/dev/null | grep 'HEAD branch' | awk '{print $NF}'", cwd);
  return remote || "main";
}

async function generatePRDescription(
  branch: string,
  baseBranch: string,
  commits: string,
  diff: string,
  repoName: string
): Promise<{ title: string; body: string }> {
  const prompt = `Generate a clear GitHub Pull Request title and description for the following branch changes.

Repository: ${repoName}
Branch: ${branch}
Base: ${baseBranch}

Commits:
${commits || "(no commits)"}

Diff summary (first 6000 chars):
\`\`\`diff
${diff.slice(0, 6000)}
\`\`\`

Output a JSON object with exactly these fields:
{
  "title": "<concise PR title, max 72 chars, imperative mood>",
  "body": "<full markdown PR description with ## Summary, ## Changes, ## Testing sections>"
}

Output ONLY the JSON object, nothing else.`;

  const options: Options = {
    cwd: process.cwd(),
    allowedTools: [],
    permissionMode: "default",
    systemPrompt: CODING_SYSTEM_PROMPT,
    maxTurns: 1,
  };

  let raw = "";
  for await (const message of query({ prompt, options })) {
    const msg = message as SDKMessage;
    if (msg.type === "result" && msg.subtype === "success") {
      raw = msg.result.trim();
    }
  }

  const jsonMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/) ?? raw.match(/(\{[\s\S]*\})/);
  const jsonStr = jsonMatch ? jsonMatch[1].trim() : raw;

  try {
    const parsed = JSON.parse(jsonStr) as { title?: string; body?: string };
    return {
      title: parsed.title ?? "Update",
      body: parsed.body ?? "",
    };
  } catch {
    const lines = raw.split("\n");
    return { title: lines[0].slice(0, 72), body: lines.slice(1).join("\n").trim() };
  }
}

export function prCommand(): Command {
  const cmd = new Command("pr");
  cmd
    .description("Generate an AI pull request description for the current branch")
    .option("-b, --base <branch>", "Base branch to diff against (default: main or master)")
    .option("--title-only", "Print only the generated title")
    .option("--body-only", "Print only the generated body")
    .option("--copy", "Copy the full PR description to clipboard")
    .option("--gh", "Create the PR using the `gh` CLI (requires gh to be installed)")
    .action(async (options: {
      base?: string;
      titleOnly?: boolean;
      bodyOnly?: boolean;
      copy?: boolean;
      gh?: boolean;
    }) => {
      const cwd = process.cwd();

      const branch = run("git rev-parse --abbrev-ref HEAD", cwd);
      if (!branch || branch === "HEAD") {
        console.error(chalk.red("Could not determine current branch. Are you in a git repo?"));
        process.exit(1);
      }

      const baseBranch = options.base ?? getDefaultBranch(cwd);
      const commits = run(`git log --oneline ${baseBranch}..${branch}`, cwd);
      if (!commits) {
        console.error(chalk.yellow(`No commits found between ${baseBranch} and ${branch}.`));
      }

      const diff = run(`git diff ${baseBranch}...${branch}`, cwd);

      let repoName = run("git remote get-url origin 2>/dev/null", cwd)
        .replace(/\.git$/, "")
        .split("/")
        .slice(-2)
        .join("/");
      if (!repoName) repoName = cwd.split("/").pop() ?? "repo";

      console.log(chalk.cyan("\n── Generating PR description ──────────────────────────\n"));
      console.log(chalk.gray(`Branch: ${branch} → ${baseBranch}`));
      console.log(chalk.gray(`Commits: ${commits.split("\n").length}`));

      let title: string;
      let body: string;
      try {
        ({ title, body } = await generatePRDescription(branch, baseBranch, commits, diff, repoName));
      } catch (err) {
        console.error(chalk.red("Failed to generate PR description:"), String(err));
        process.exit(1);
      }

      console.log();

      if (!options.bodyOnly) {
        console.log(chalk.bold("Title:"));
        console.log(chalk.white(title));
        console.log();
      }

      if (!options.titleOnly) {
        console.log(chalk.bold("Description:"));
        console.log(chalk.white(body));
        console.log();
      }

      if (options.copy) {
        try {
          const full = `${title}\n\n${body}`;
          const clipboard = process.platform === "darwin" ? "pbcopy" : "xclip -selection clipboard";
          const cp = await import("child_process");
          const proc = cp.spawnSync(clipboard.split(" ")[0], clipboard.split(" ").slice(1), {
            input: full,
            encoding: "utf8",
          });
          if (proc.status === 0) {
            console.log(chalk.green("✔ Copied to clipboard"));
          }
        } catch {
          // ignore clipboard errors
        }
      }

      if (options.gh) {
        const { spawnSync } = await import("child_process");
        const result = spawnSync(
          "gh",
          ["pr", "create", "--title", title, "--body", body, "--base", baseBranch],
          { cwd, stdio: "inherit", encoding: "utf8" }
        );
        if (result.status !== 0) {
          console.error(chalk.red("gh pr create failed. Ensure the `gh` CLI is installed and authenticated."));
          process.exit(1);
        }
      }
    });
  return cmd;
}
