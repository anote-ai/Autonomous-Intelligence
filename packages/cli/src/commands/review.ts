import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import * as child_process from "child_process";
import { runAgentStream } from "../agent.js";
import { createSpinner } from "../ui.js";

interface ReviewComment {
  file: string;
  line: number;
  severity: "security" | "bug" | "logic" | "suggestion" | "nit";
  title: string;
  body: string;
}

interface ReviewResult {
  summary: string;
  comments: ReviewComment[];
}

const SEVERITY_EMOJI: Record<string, string> = {
  security: "🔴",
  bug: "🔴",
  logic: "🟡",
  suggestion: "🔵",
  nit: "⚪",
};

async function readStdin(): Promise<string> {
  if (process.stdin.isTTY) return "";
  return new Promise((resolve) => {
    const chunks: Buffer[] = [];
    process.stdin.on("data", (c: Buffer) => chunks.push(c));
    process.stdin.on("end", () => resolve(Buffer.concat(chunks).toString("utf8").trim()));
    process.stdin.on("error", () => resolve(""));
  });
}

function getGitHubToken(): string | null {
  if (process.env["GITHUB_TOKEN"]) return process.env["GITHUB_TOKEN"];
  try {
    return child_process.execSync("gh auth token 2>/dev/null", { encoding: "utf8" }).trim() || null;
  } catch {
    return null;
  }
}

function getRepoFromRemote(cwd: string): { owner: string; repo: string } | null {
  try {
    const remote = child_process
      .execSync("git remote get-url origin", { cwd, encoding: "utf8" })
      .trim();
    const m = remote.match(/github\.com[:/]([^/]+)\/([^/.]+)/);
    if (!m) return null;
    return { owner: m[1], repo: m[2] };
  } catch {
    return null;
  }
}

function getCurrentPrNumber(cwd: string): number | null {
  try {
    const json = child_process.execSync("gh pr view --json number", { cwd, encoding: "utf8" });
    return (JSON.parse(json) as { number: number }).number ?? null;
  } catch {
    return null;
  }
}

function getPrDiff(prNumber: number, cwd: string): string {
  return child_process.execSync(`gh pr diff ${prNumber}`, { cwd, encoding: "utf8", maxBuffer: 4 * 1024 * 1024 });
}

function parseReviewJson(text: string): ReviewResult | null {
  const tagged = text.match(/<review_json>([\s\S]*?)<\/review_json>/);
  const raw = tagged ? tagged[1].trim() : text.trim();
  const fenced = raw.match(/```json\s*([\s\S]*?)```/);
  const jsonStr = fenced ? fenced[1].trim() : raw;
  try {
    const parsed = JSON.parse(jsonStr) as ReviewResult;
    if (typeof parsed.summary === "string" && Array.isArray(parsed.comments)) return parsed;
  } catch { /* fall through */ }
  return null;
}

async function postGitHubReview(token: string, owner: string, repo: string, prNumber: number, review: ReviewResult): Promise<void> {
  const counts: Record<string, number> = {};
  for (const c of review.comments) counts[c.severity] = (counts[c.severity] ?? 0) + 1;

  const countLine = Object.entries(counts).map(([k, n]) => `${SEVERITY_EMOJI[k] ?? "•"} ${n} ${k}`).join("   ");
  const body = ["## AI Code Review", "", review.summary, "", countLine ? `**Findings:** ${countLine}` : "_No issues found._", "", "_Posted by [Anote](https://github.com/anote-ai/AI-Assisted-Coding-Tool)_"].join("\n");
  const githubComments = review.comments.filter((c) => c.line > 0).map((c) => ({ path: c.file, line: c.line, side: "RIGHT", body: `**${SEVERITY_EMOJI[c.severity] ?? "•"} ${c.severity.toUpperCase()}: ${c.title}**\n\n${c.body}` }));

  const res = await fetch(`https://api.github.com/repos/${owner}/${repo}/pulls/${prNumber}/reviews`, {
    method: "POST",
    headers: { Authorization: `token ${token}`, "Content-Type": "application/json", Accept: "application/vnd.github.v3+json" },
    body: JSON.stringify({ body, event: "COMMENT", comments: githubComments }),
  });

  if (!res.ok) throw new Error(`GitHub API ${res.status}: ${await res.text()}`);
}

function printReview(review: ReviewResult): void {
  console.log("\n" + chalk.bold("── Review Summary ───────────────────────────────────────────────────────────────"));
  console.log(chalk.white(review.summary));
  if (review.comments.length === 0) { console.log(chalk.green("\n✓ No issues found.")); return; }
  console.log();
  for (const c of review.comments) {
    const emoji = SEVERITY_EMOJI[c.severity] ?? "•";
    const loc = c.line > 0 ? chalk.gray(` (${c.file}:${c.line})`) : chalk.gray(` (${c.file})`);
    console.log(`${emoji} ${chalk.bold(c.title)}${loc}`);
    console.log(chalk.dim("   " + c.body.replace(/\n/g, "\n   ")));
    console.log();
  }
}

export function reviewCommand(): Command {
  return new Command("review")
    .alias("r")
    .description("AI code review — review files, diffs, or GitHub PRs")
    .argument("[file]", "file or directory to review (default: full codebase scan)")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("--pr [number]", "review a GitHub PR and post inline comments")
    .option("--dry-run", "print review to terminal without posting to GitHub")
    .option("--focus <areas>", "comma-separated areas to focus on (e.g. security,performance,logic)")
    .option("--security", "shorthand for --focus security")
    .option("--performance", "shorthand for --focus performance")
    .option("--style", "shorthand for --focus code style")
    .option("--diff", "review only git-staged changes")
    .option("-m, --model <model>", "model to use (e.g. gpt-4.1, gemini-2.5-pro)")
    .action(async (file: string | undefined, opts) => {
      const cwd = path.resolve(opts.dir as string);
      const isDryRun = Boolean(opts.dryRun);
      const isPr = opts.pr !== undefined;

      const focusParts: string[] = [];
      if (opts.focus) focusParts.push(...(opts.focus as string).split(",").map((s: string) => s.trim()));
      if (opts.security) focusParts.push("security");
      if (opts.performance) focusParts.push("performance");
      if (opts.style) focusParts.push("code style");
      const focus = focusParts.join(", ");

      if (isPr) {
        let prNumber: number | null = null;
        if (typeof opts.pr === "string" && /^\d+$/.test(opts.pr)) {
          prNumber = parseInt(opts.pr, 10);
        } else {
          prNumber = getCurrentPrNumber(cwd);
          if (!prNumber) { console.error(chalk.red("✗ Could not find an open PR for the current branch.")); process.exit(1); }
        }

        const token = getGitHubToken();
        if (!token && !isDryRun) { console.error(chalk.red("✗ GITHUB_TOKEN is not set.")); process.exit(1); }

        let diff: string;
        try { diff = getPrDiff(prNumber, cwd); } catch (err) { console.error(chalk.red(`✗ Could not fetch PR #${prNumber}: ${String(err)}`)); process.exit(1); }
        if (!diff.trim()) { console.log(chalk.yellow(`PR #${prNumber} has no diff to review.`)); return; }

        console.log(chalk.bold.cyan(`\n◆ Anote  Reviewing PR #${prNumber}`) + (focus ? chalk.gray(`  focus: ${focus}`) : "") + (isDryRun ? chalk.yellow("  (dry-run)") : "") + "\n");

        const MAX_DIFF = 60_000;
        const diffText = diff.length > MAX_DIFF ? diff.slice(0, MAX_DIFF) + "\n\n[diff truncated]" : diff;
        const spinner = createSpinner("Analyzing diff...").start();
        const rawOutput = await runAgentStream({ prompt: buildPrReviewPrompt(diffText, focus), cwd, allowedTools: [], suppressTextOutput: true, model: opts.model as string | undefined, onFirstToken: () => spinner.stop() });
        spinner.stop();

        const review = parseReviewJson(rawOutput);
        if (!review) { console.log(chalk.yellow("\n⚠ Could not parse structured review. Raw AI output:\n")); console.log(rawOutput); return; }
        printReview(review);
        if (isDryRun) { console.log(chalk.yellow("\n  Dry-run: review not posted to GitHub.")); return; }

        const repoInfo = getRepoFromRemote(cwd);
        if (!repoInfo) { console.error(chalk.red("✗ Could not determine GitHub owner/repo.")); process.exit(1); }
        process.stdout.write(chalk.cyan("\n◆ Posting review to GitHub... "));
        try {
          await postGitHubReview(token!, repoInfo.owner, repoInfo.repo, prNumber, review);
          console.log(chalk.green("done."));
        } catch (err) { console.error(chalk.red(`\n✗ Failed to post review: ${String(err)}`)); process.exit(1); }
        return;
      }

      const stdinDiff = await readStdin();
      if (stdinDiff) {
        const spinner = createSpinner("Analyzing diff...").start();
        const rawOutput = await runAgentStream({ prompt: buildPrReviewPrompt(stdinDiff, focus), cwd, allowedTools: [], suppressTextOutput: true, model: opts.model as string | undefined, onFirstToken: () => spinner.stop() });
        spinner.stop();
        const review = parseReviewJson(rawOutput);
        if (review) printReview(review); else console.log(rawOutput);
        return;
      }

      let focusSuffix = "";
      if (opts.security) focusSuffix += " with a focus on security vulnerabilities";
      if (opts.performance) focusSuffix += " with a focus on performance issues";
      if (opts.style) focusSuffix += " with a focus on code style and best practices";
      if (focus && !focusSuffix) focusSuffix = ` with a focus on ${focus}`;

      let prompt: string;
      if (opts.diff) {
        let diff = "";
        try { diff = child_process.execSync("git diff --cached", { cwd, encoding: "utf-8" }); if (!diff) diff = child_process.execSync("git diff HEAD", { cwd, encoding: "utf-8" }); } catch { console.error(chalk.red("Not a git repository or no changes found.")); process.exit(1); }
        if (!diff) { console.log(chalk.yellow("No changes to review.")); return; }
        prompt = `Review the following git diff${focusSuffix}:\n\`\`\`diff\n${diff}\n\`\`\`\n\nProvide actionable feedback.`;
      } else if (file) {
        prompt = `Perform a thorough code review of "${file}"${focusSuffix}.\nRead the file and any related files for context.\nIdentify: bugs, security issues, performance problems, code quality issues, and suggest improvements.`;
      } else {
        prompt = `Perform a code review of this entire codebase${focusSuffix}.\nExplore the project structure, read key files, and provide a comprehensive review.`;
      }

      console.log(chalk.bold.yellow(`\n🔍 Reviewing${file ? `: ${file}` : opts.diff ? " git diff" : " project"}\n`));
      await runAgentStream({ prompt, cwd, allowedTools: ["Read", "Glob", "Grep", "Bash"], model: opts.model as string | undefined, permissionMode: "default" });
    });
}

function buildPrReviewPrompt(diff: string, focus: string): string {
  return `You are an expert code reviewer. Analyze the following pull request diff and produce a structured review.
${focus ? `\nFocus especially on: ${focus}\n` : ""}
The diff:
\`\`\`diff
${diff}
\`\`\`

Output your review as JSON wrapped in <review_json> tags. Use exactly this format:

<review_json>
{
  "summary": "2-4 sentence overview of the PR and the key findings",
  "comments": [
    {
      "file": "path/to/file.ts",
      "line": 47,
      "severity": "security",
      "title": "Short title under 80 chars",
      "body": "Detailed explanation and suggested fix"
    }
  ]
}
</review_json>

Rules:
- severity must be one of: security, bug, logic, suggestion, nit
- line must be the line number in the NEW version of the file
- Only comment on lines that are added (+) or in context of additions
- If you cannot determine the exact line, use 0
- Be specific and actionable
- Output ONLY the <review_json> block — no other text`;
}
