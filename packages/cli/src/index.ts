#!/usr/bin/env node
import { Command } from "commander";
import chalk from "chalk";
import { askCommand } from "./commands/ask.js";
import { chatCommand } from "./commands/chat.js";
import { fixCommand } from "./commands/fix.js";
import { explainCommand } from "./commands/explain.js";
import { reviewCommand } from "./commands/review.js";
import { testCommand } from "./commands/test.js";
import { refactorCommand } from "./commands/refactor.js";
import { sessionsCommand } from "./commands/sessions.js";
import { generateCommand } from "./commands/generate.js";
import { initCommand } from "./commands/init.js";
import { doctorCommand } from "./commands/doctor.js";
import { commitCommand } from "./commands/commit.js";
import { prCommand } from "./commands/pr.js";
import { diffCommand } from "./commands/diff.js";
import { configCommand } from "./commands/config.js";
import { watchCommand } from "./commands/watch.js";
import { indexCommand } from "./commands/index.js";
import { searchCommand } from "./commands/search.js";
import { migrateCommand } from "./commands/migrate.js";
import { docsCommand } from "./commands/docs.js";
import { changelogCommand } from "./commands/changelog.js";
import { securityCommand } from "./commands/security.js";
import { perfCommand } from "./commands/perf.js";

const LOGO = chalk.cyan(`
   ___                    _          _    ___
  / _ \\  _ __   ___  ___ | |_  ___  | |  / _ \\
 | (_) || '_ \\ / _ \\/ _ \\| __|/ _ \\ | | | (_) |
  \\__\\_\\| | | | (_) | (_)|| |_|  __/ |_|  \\__\\_\\
        |_| |_|\\___/ \\___/ \\__|\\___||___|
`);

const program = new Command();

program
  .name("anote")
  .description(
    chalk.bold("Anote AI Coding Tool") +
      " — AI coding assistant for your terminal"
  )
  .version("1.0.0");

program.addHelpText("beforeAll", LOGO);

program.hook("preAction", (thisCommand) => {
  if (thisCommand.name() === "init" || thisCommand.name() === "doctor") return;
  if (!process.env.ANTHROPIC_API_KEY) {
    console.error(
      chalk.red("\n✗ ANTHROPIC_API_KEY is not set.\n") +
      chalk.white(
        "  1. Get a key at " + chalk.cyan("https://console.anthropic.com") + "\n" +
        "  2. Set it:  " + chalk.yellow("export ANTHROPIC_API_KEY=sk-ant-...") + "\n" +
        "  3. Or add it to your shell profile (~/.bashrc, ~/.zshrc)\n\n" +
        "  First time? Run " + chalk.cyan("anote init") + " for a guided setup.\n"
      )
    );
    process.exit(1);
  }
});

program.addCommand(chatCommand());
program.addCommand(askCommand());
program.addCommand(fixCommand());
program.addCommand(explainCommand());
program.addCommand(reviewCommand());
program.addCommand(testCommand());
program.addCommand(refactorCommand());
program.addCommand(sessionsCommand());
program.addCommand(generateCommand());
program.addCommand(initCommand());
program.addCommand(doctorCommand());
program.addCommand(commitCommand());
program.addCommand(prCommand());
program.addCommand(diffCommand());
program.addCommand(configCommand());
program.addCommand(watchCommand());
program.addCommand(indexCommand());
program.addCommand(searchCommand());
program.addCommand(migrateCommand());
program.addCommand(docsCommand());
program.addCommand(changelogCommand());
program.addCommand(securityCommand());
program.addCommand(perfCommand());

program.parseAsync(process.argv).catch((err: Error) => {
  console.error(chalk.red("Error:"), err.message);
  process.exit(1);
});
