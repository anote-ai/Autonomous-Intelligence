import { Command } from "commander";
import chalk from "chalk";
import * as readline from "readline";
import { runAgentStream } from "../agent.js";

export function chatCommand(): Command {
  return new Command("chat")
    .alias("c")
    .description("Start an interactive chat session with the AI assistant")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option("-m, --model <model>", "model to use", "claude-sonnet-4-6")
    .option("--plan", "planning mode: reason through the task read-only, no edits or commands")
    .action(async (opts) => {
      const cwd = opts.dir as string;
      const model = opts.model as string;

      console.log(
        chalk.bold.cyan("\n◆ Anote Chat") +
        chalk.dim("  Type your message and press Enter. Type 'exit' to quit.\n")
      );

      const rl = readline.createInterface({
        input: process.stdin,
        output: process.stdout,
        terminal: true,
      });

      const history: Array<{ role: string; content: string }> = [];

      const prompt = () => {
        rl.question(chalk.cyan("You: "), async (input) => {
          const message = input.trim();
          if (!message) { prompt(); return; }
          if (message.toLowerCase() === "exit" || message.toLowerCase() === "quit") {
            console.log(chalk.dim("\nGoodbye!\n"));
            rl.close();
            return;
          }

          history.push({ role: "user", content: message });
          process.stdout.write(chalk.bold("\nAnote: "));

          try {
            await runAgentStream({
              prompt: message,
              cwd,
              model,
              allowedTools: ["Read", "Glob", "Grep", "WebSearch", "WebFetch"],
              permissionMode: opts.plan ? "plan" : "default",
            });
          } catch (err) {
            console.error(chalk.red(`\nError: ${err instanceof Error ? err.message : String(err)}`));
          }

          console.log();
          prompt();
        });
      };

      prompt();
    });
}
