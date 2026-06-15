/**
 * `anote generate <description>` — generate new code files from a natural language description.
 */

import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function generateCommand(): Command {
  return new Command("generate")
    .alias("gen")
    .description("Generate new code or files from a description")
    .argument("<description>", "what to generate")
    .option("-o, --output <file>", "output file path")
    .option("-l, --lang <language>", "programming language")
    .option("--framework <name>", "framework or library to use")
    .option("--dry-run", "show what would be generated without writing files")
    .action(async (description: string, opts) => {
      const cwd = process.cwd();

      let prompt = `Generate code for: ${description}`;
      if (opts.lang) prompt += `\nLanguage: ${opts.lang}`;
      if (opts.framework) prompt += `\nFramework: ${opts.framework}`;
      if (opts.output) {
        prompt += `\nOutput file: ${path.resolve(opts.output)}`;
        if (!opts.dryRun) {
          prompt += `\nWrite the generated code to that file.`;
        } else {
          prompt += `\nDo NOT write files — only show the generated code.`;
        }
      } else {
        prompt += `\nShow the generated code in full. Do not write any files unless explicitly asked.`;
      }

      prompt += `\n\nRequirements:\n- Write production-quality code with proper error handling\n- Follow best practices for the language/framework\n- Add brief comments for non-obvious logic\n- Include a usage example if appropriate`;

      await runAgentStream({
        prompt,
        cwd,
        allowedTools: opts.dryRun
          ? ["Read", "Glob"]
          : ["Read", "Write", "Edit", "Glob", "Grep"],
        showToolUse: true,
      });

      if (opts.output && !opts.dryRun) {
        console.log(chalk.green(`\n✓ Output written to ${opts.output}`));
      }
    });
}
