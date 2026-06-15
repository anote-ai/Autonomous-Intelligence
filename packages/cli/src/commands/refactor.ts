import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function refactorCommand(): Command {
  return new Command("refactor")
    .description("Intelligently refactor code for clarity and maintainability")
    .argument("<file>", "file to refactor")
    .argument("[instruction...]", "specific refactoring instruction")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("--dry-run", "show proposed changes without applying them")
    .option("--auto", "auto-accept all changes")
    .action(async (file: string, instrParts: string[], opts) => {
      const cwd = path.resolve(opts.dir);
      const instruction = instrParts.join(" ");

      const prompt = `Refactor "${file}"${instruction ? ` with the following goal: ${instruction}` : ""}.

Steps:
1. Read the file and understand the current implementation
2. Check for tests that should still pass after refactoring
3. Plan the refactoring approach:
   ${instruction || "- Improve readability and maintainability\n   - Remove duplication\n   - Improve naming\n   - Simplify complex logic\n   - Apply SOLID principles where appropriate"}
${opts.dryRun ? `4. Show the proposed changes with clear explanations — do NOT write to files` : `4. Apply the refactoring changes to the file
5. Verify the changes are correct and run tests if available`}

Preserve all existing functionality. Explain each significant change made.`;

      console.log(
        chalk.bold.blue(
          `\n♻️  Refactoring: ${chalk.white(file)}${opts.dryRun ? chalk.gray(" (dry run)") : ""}\n`
        )
      );

      await runAgentStream({
        prompt,
        cwd,
        allowedTools: ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],
        permissionMode: opts.auto
          ? "acceptEdits"
          : opts.dryRun
            ? "default"
            : "default",
      });
    });
}
