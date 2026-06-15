import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import * as fs from "fs";
import * as os from "os";
import { execSync } from "child_process";
import { runAgentStream } from "../agent.js";
import { createSpinner } from "../ui.js";

export function explainCommand(): Command {
  return new Command("explain")
    .alias("e")
    .description(
      "Generate a CODEBASE.md tour of any repository (no args), or explain a specific file/function/concept"
    )
    .argument(
      "[target]",
      "file path, function name, or concept to explain (omit to generate CODEBASE.md)"
    )
    .argument("[question...]", "optional question about the target")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use (e.g. gpt-4.1, gemini-2.5-pro, ollama/llama3.2)")
    .option(
      "--depth <level>",
      "explanation depth for code explain: basic|detailed|expert",
      "detailed"
    )
    .option("--stdout", "print CODEBASE.md to stdout instead of writing a file")
    .option("--refresh", "update an existing CODEBASE.md instead of generating from scratch")
    .option(
      "--include-recent-commits <n>",
      "include the last N git commits as context when generating CODEBASE.md",
      "0"
    )
    .action(async (target: string | undefined, questionParts: string[], opts) => {
      const cwd = path.resolve(opts.dir as string);

      if (target) {
        const question = (questionParts as string[]).join(" ");
        const targetPath = path.resolve(cwd, target);

        let prompt: string;
        if (fs.existsSync(targetPath)) {
          const stat = fs.statSync(targetPath);
          if (stat.isDirectory()) {
            prompt = `Explain what the code in the directory "${target}" does.\nRead the key files, understand the architecture, and give a ${opts.depth as string} explanation.\n${question ? `\nSpecific question: ${question}` : ""}`;
          } else {
            prompt = `Explain the code in "${target}" at a ${opts.depth as string} level.\n${question ? `\nSpecific question: ${question}` : "Explain: what it does, how it works, key patterns used, and any important details."}`;
          }
        } else {
          prompt = `Explain "${target}" in the context of this codebase at a ${opts.depth as string} level.\nSearch for it in the code, then provide a ${opts.depth as string} explanation.\n${question ? `\nSpecific question: ${question}` : ""}`;
        }

        console.log(chalk.bold.magenta(`\n📖 Explaining: ${chalk.white(target)}\n`));
        await runAgentStream({
          prompt,
          cwd,
          allowedTools: ["Read", "Glob", "Grep"],
          model: opts.model as string | undefined,
          permissionMode: "default",
        });
        return;
      }

      const isRefresh = Boolean(opts.refresh);
      const isStdout = Boolean(opts.stdout);
      const recentCommits = Math.max(0, parseInt(opts.includeRecentCommits as string, 10) || 0);

      const destPath = path.join(cwd, "CODEBASE.md");
      const outputPath = isStdout
        ? path.join(os.tmpdir(), `anote-codebase-${Date.now()}.md`)
        : destPath;

      let fileTree = "";
      try {
        fileTree = execSync("git ls-files", { cwd, encoding: "utf8" }).trim();
      } catch {
        try {
          fileTree = execSync(
            'find . -type f -not -path "*/node_modules/*" -not -path "*/.git/*" ' +
            '-not -path "*/dist/*" -not -path "*/build/*" -not -path "*/.next/*"',
            { cwd, encoding: "utf8" }
          ).trim();
        } catch { /* no ls available */ }
      }

      let commitsContext = "";
      if (recentCommits > 0) {
        try {
          const log = execSync(`git log --oneline -${recentCommits}`, { cwd, encoding: "utf8" }).trim();
          commitsContext = `\n\nRecent commits (last ${recentCommits}):\n${log}`;
        } catch { /* no git history */ }
      }

      let existingContent = "";
      if (isRefresh && fs.existsSync(destPath)) {
        existingContent = fs.readFileSync(destPath, "utf8");
      }

      const parts: string[] = [];

      if (isRefresh && existingContent) {
        parts.push(
          "You are updating an existing CODEBASE.md file.",
          "Read the current version below, explore the repository for recent changes, " +
          "and produce an updated, accurate version.",
          "",
          "Current CODEBASE.md:",
          "```markdown",
          existingContent,
          "```",
          ""
        );
      } else {
        parts.push(
          "Generate a comprehensive CODEBASE.md file for this repository.",
          "The file will help developers — and AI assistants — understand the codebase quickly.",
          ""
        );
      }

      parts.push(
        "Repository file tree (from git ls-files):",
        "```",
        fileTree,
        "```",
        commitsContext,
        "",
        "Explore the repository thoroughly using Read, Glob, and Grep tools.",
        `Then write CODEBASE.md to "${outputPath}".`,
        "",
        "The CODEBASE.md must cover these sections:",
        "1. **Overview** — what this project does and who it is for",
        "2. **Entry points** — main executables, CLI commands, API routes, or UI entry files",
        "3. **Architecture** — high-level structure, major packages/modules, and how they relate",
        "4. **Key files** — the most important files/directories with a one-line description each",
        "5. **Data flow** — how data moves through the system (e.g. request → handler → storage)",
        "6. **Conventions** — naming, file organisation, testing, build, and project-specific patterns",
        "",
        "Keep it concise but complete. Use headings, bullet points, and short code snippets.",
        `Write the final document directly to "${outputPath}".`
      );

      const prompt = parts.join("\n");

      console.log(chalk.bold.cyan(`\n◆ Anote  ${isRefresh ? "Refreshing" : "Generating"} CODEBASE.md\n`));

      const spinner = createSpinner("Exploring repository...").start();
      let spinnerStopped = false;
      const stopSpinner = () => { if (!spinnerStopped) { spinner.stop(); spinnerStopped = true; } };

      await runAgentStream({
        prompt,
        cwd,
        allowedTools: ["Read", "Glob", "Grep", "Write"],
        model: opts.model as string | undefined,
        permissionMode: "acceptEdits",
        suppressTextOutput: true,
        onTool: (toolName, input) => {
          stopSpinner();
          const inp = input as Record<string, unknown>;
          if (toolName === "Write" || toolName === "Edit") {
            const fp = typeof inp.file_path === "string" ? inp.file_path : outputPath;
            console.log(chalk.cyan("◆ ") + chalk.white(`Writing ${fp}`));
          } else if (toolName === "Read") {
            const fp = typeof inp.file_path === "string" ? path.relative(cwd, inp.file_path) : "";
            if (fp) console.log(chalk.gray(`  • Reading ${fp}`));
          } else if (toolName === "Glob" || toolName === "Grep") {
            const pat = typeof inp.pattern === "string" ? inp.pattern : "";
            if (pat) console.log(chalk.gray(`  • ${toolName} ${pat}`));
          }
        },
        showToolUse: false,
      });

      stopSpinner();

      if (isStdout) {
        if (fs.existsSync(outputPath)) {
          process.stdout.write(fs.readFileSync(outputPath, "utf8"));
          try { fs.unlinkSync(outputPath); } catch { /* best-effort cleanup */ }
        }
        return;
      }

      if (!fs.existsSync(outputPath)) {
        console.log(chalk.red("\n✗ CODEBASE.md was not written — the AI may have encountered an error.\n"));
        return;
      }

      autoReferenceCodebase(cwd);
      console.log(chalk.green(`\n◆ Written: ${path.relative(cwd, outputPath)}\n`));
    });
}

function autoReferenceCodebase(cwd: string): void {
  const names = ["CLAUDE.md", "CLAW.md"];
  for (const name of names) {
    const claudePath = path.join(cwd, name);
    if (!fs.existsSync(claudePath)) continue;
    const content = fs.readFileSync(claudePath, "utf8");
    if (content.includes("CODEBASE.md")) return;
    const ref =
      "\n\n## Codebase Tour\n\n" +
      "See [CODEBASE.md](./CODEBASE.md) for an overview of the repository " +
      "architecture, entry points, and conventions.\n";
    try {
      fs.writeFileSync(claudePath, content + ref, "utf8");
      console.log(chalk.dim(`  (referenced in ${name})`));
    } catch { /* skip if unwritable */ }
    return;
  }
}
