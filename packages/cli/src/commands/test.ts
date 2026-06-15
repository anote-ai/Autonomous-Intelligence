import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { runAgentStream } from "../agent.js";

export function testCommand(): Command {
  return new Command("test")
    .alias("t")
    .description("Generate tests for your code")
    .argument("<file>", "file to generate tests for")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option(
      "--framework <name>",
      "test framework (jest, vitest, mocha, pytest, etc.)"
    )
    .option("--write", "write tests to a file automatically")
    .option("--coverage", "aim for high coverage (edge cases, error paths)")
    .action(async (file: string, opts) => {
      const cwd = path.resolve(opts.dir);
      const coverage = opts.coverage
        ? "with comprehensive coverage including edge cases, error paths, and boundary conditions"
        : "";
      const framework = opts.framework
        ? `Use ${opts.framework} as the testing framework.`
        : "Detect the project's testing framework from package.json or existing test files.";

      const prompt = `Generate tests for "${file}" ${coverage}.

${framework}

Steps:
1. Read "${file}" to understand what needs to be tested
2. Check for existing tests and test setup in the project
3. Generate comprehensive unit tests that cover:
   - Happy path scenarios
   - Edge cases and boundary conditions
   - Error handling
   - All exported functions/classes
${opts.write ? `4. Write the tests to the appropriate test file (follow project conventions for test file naming)` : `4. Show the complete test code`}

Make tests clear, well-documented, and following the project's existing test patterns.`;

      console.log(chalk.bold.green(`\n🧪 Generating tests for: ${chalk.white(file)}\n`));

      await runAgentStream({
        prompt,
        cwd,
        allowedTools: ["Read", "Write", "Edit", "Glob", "Grep", "Bash"],
        permissionMode: opts.write ? "acceptEdits" : "default",
      });
    });
}
