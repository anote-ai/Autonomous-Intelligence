import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import chokidar from "chokidar";
import { runAgentStream } from "../agent.js";

const DEFAULT_IGNORED = [
  "**/node_modules/**",
  "**/.git/**",
  "**/dist/**",
  "**/build/**",
  "**/.next/**",
  "**/__pycache__/**",
  "**/*.pyc",
  "**/.DS_Store",
];

export function watchCommand(): Command {
  return new Command("watch")
    .alias("w")
    .description("Watch files for changes and run AI analysis automatically")
    .argument("[glob]", "glob pattern to watch", "**/*.{ts,tsx,js,jsx,py,go,rs,java}")
    .option("-d, --dir <path>", "working directory", process.cwd())
    .option(
      "-p, --prompt <text>",
      "prompt to run on each changed file",
      "Review this changed file for bugs, style issues, or improvements. Be concise."
    )
    .option("--debounce <ms>", "debounce delay in ms", "800")
    .option("--no-clear", "don't clear the screen between analyses")
    .action(async (glob: string, opts) => {
      const cwd = path.resolve(opts.dir);
      const debounceMs = parseInt(opts.debounce, 10) || 800;

      console.log(chalk.cyan("\n  Anote Watch\n"));
      console.log(chalk.dim(`  Directory : ${cwd}`));
      console.log(chalk.dim(`  Pattern   : ${glob}`));
      console.log(chalk.dim(`  Debounce  : ${debounceMs}ms`));
      console.log(chalk.dim("  Press Ctrl+C to stop.\n"));

      const watcher = chokidar.watch(glob, {
        cwd,
        ignored: DEFAULT_IGNORED,
        persistent: true,
        ignoreInitial: true,
        awaitWriteFinish: { stabilityThreshold: debounceMs, pollInterval: 100 },
      });

      const pending = new Set<string>();
      let analysisRunning = false;

      async function analyse(file: string): Promise<void> {
        if (analysisRunning) { pending.add(file); return; }
        analysisRunning = true;

        if (opts.clear) process.stdout.write("\x1Bc");

        const rel = path.relative(cwd, path.join(cwd, file));
        console.log(chalk.bold.cyan(`\n  ↺  ${rel}`) + chalk.dim(` — ${new Date().toLocaleTimeString()}`));
        console.log(chalk.dim("─".repeat(60)) + "\n");

        const prompt = `File changed: ${rel}\n\n${opts.prompt}`;

        try {
          await runAgentStream({
            prompt,
            cwd,
            allowedTools: ["Read", "Glob", "Grep"],
            permissionMode: "default",
            onFirstToken: () => {},
          });
        } catch (err) {
          console.error(chalk.red("  Analysis failed:"), String(err));
        }

        console.log("\n" + chalk.dim("─".repeat(60)));
        analysisRunning = false;

        if (pending.size > 0) {
          const next = [...pending][0];
          pending.delete(next);
          await analyse(next);
        }
      }

      watcher
        .on("change", (file: string) => { void analyse(file); })
        .on("add",    (file: string) => { void analyse(file); })
        .on("error",  (err: unknown)  => { console.error(chalk.red("Watcher error:"), err); });

      await new Promise<void>((resolve) => {
        process.on("SIGINT",  () => { watcher.close(); resolve(); });
        process.on("SIGTERM", () => { watcher.close(); resolve(); });
      });

      console.log(chalk.dim("\n  Watch stopped.\n"));
    });
}
