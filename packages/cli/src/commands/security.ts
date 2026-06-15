import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function securityCommand(): Command {
  return new Command("security")
    .description("Audit the codebase for vulnerabilities (OWASP Top 10)")
    .argument("[target]", "file or directory to audit (default: entire project)")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use")
    .option("--fix", "auto-apply fixes for issues the AI is confident about")
    .option("--dry-run", "report only — do not write any files")
    .option("--severity <level>", "minimum severity: critical, high, medium, low", "medium")
    .action(async (target: string | undefined, opts: {
      dir: string; model?: string; fix?: boolean; dryRun?: boolean; severity: string;
    }) => {
      const cwd = path.resolve(opts.dir);
      const doFix = Boolean(opts.fix) && !opts.dryRun;
      const scope = target ? `\`${target}\`` : "the entire codebase";

      console.log(chalk.bold.cyan(`\n◆ Anote  security`) +
        chalk.gray(`  auditing ${scope}`) +
        (doFix ? chalk.yellow("  [--fix]") : chalk.gray("  [report only]")) + "\n");

      const prompt = `Security audit of ${scope}. Minimum severity: ${opts.severity}.

Check OWASP Top 10: Injection, Broken Auth, Sensitive Data Exposure, Security Misconfiguration, XSS, Insecure Deserialization, Path Traversal, SSRF, Prototype Pollution, Dependency Issues.

For each finding:
[SEVERITY] file:line  Issue title
  Impact: ...
  Fix: ...

${doFix ? "Apply clear, safe fixes. Mark complex issues as \"Manual review required\"." : "Do NOT modify files."}
End with: "Found N issues (X critical, Y high, Z medium)"`;

      await runAgentStream({
        prompt, cwd, model: opts.model,
        allowedTools: doFix ? ["Read", "Write", "Edit", "Grep", "Glob", "Bash"] : ["Read", "Grep", "Glob", "Bash"],
        permissionMode: doFix ? "acceptEdits" : "default",
      });
    });
}
