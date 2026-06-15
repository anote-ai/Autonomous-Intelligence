/**
 * `anote sessions` — list and manage saved chat sessions.
 */

import { Command } from "commander";
import chalk from "chalk";
import { listSessions, loadSession, deleteSession } from "../session.js";

export function sessionsCommand(): Command {
  const cmd = new Command("sessions")
    .description("List and manage saved chat sessions");

  cmd
    .command("list")
    .alias("ls")
    .description("List saved sessions")
    .option("-n, --limit <n>", "max sessions to show", "20")
    .action((opts) => {
      const sessions = listSessions(parseInt(opts.limit, 10));
      if (sessions.length === 0) {
        console.log(chalk.gray("No saved sessions."));
        return;
      }
      console.log(chalk.bold(`\nSaved sessions (${sessions.length}):`));
      for (const s of sessions) {
        const age = Math.round((Date.now() - s.updatedAt) / 60000);
        const ageStr = age < 60 ? `${age}m ago` : `${Math.round(age / 60)}h ago`;
        console.log(
          chalk.cyan(`  ${s.sessionId.slice(0, 8)}`) +
          chalk.gray(`  ${s.messages.length} msgs`) +
          chalk.gray(`  in=${s.inputTokens.toLocaleString()} out=${s.outputTokens.toLocaleString()}`) +
          chalk.gray(`  ${ageStr}`) +
          chalk.white(`  ${s.cwd}`)
        );
      }
    });

  cmd
    .command("show <sessionId>")
    .description("Show messages in a session")
    .option("-n, --limit <n>", "max messages to show", "20")
    .action((sessionId, opts) => {
      const session = loadSession(sessionId) ?? listSessions(100).find(
        (s) => s.sessionId.startsWith(sessionId)
      );
      if (!session) {
        console.error(chalk.red(`Session not found: ${sessionId}`));
        process.exit(1);
      }
      const limit = parseInt(opts.limit, 10);
      const msgs = session.messages.slice(-limit);
      console.log(chalk.bold(`\nSession ${session.sessionId.slice(0, 8)}  (${session.messages.length} total messages)`));
      console.log(chalk.gray(`  Directory: ${session.cwd}`));
      console.log(chalk.gray(`  Tokens: in=${session.inputTokens.toLocaleString()} out=${session.outputTokens.toLocaleString()}\n`));
      for (const m of msgs) {
        const prefix = m.role === "user"
          ? chalk.bold.green("You: ")
          : chalk.bold.cyan("Anote: ");
        console.log(prefix + m.content.slice(0, 200) + (m.content.length > 200 ? "…" : ""));
        console.log();
      }
    });

  cmd
    .command("delete <sessionId>")
    .alias("rm")
    .description("Delete a saved session")
    .action((sessionId) => {
      const deleted = deleteSession(sessionId);
      if (deleted) {
        console.log(chalk.green(`✓ Deleted session ${sessionId}`));
      } else {
        console.error(chalk.red(`Session not found: ${sessionId}`));
        process.exit(1);
      }
    });

  return cmd;
}
