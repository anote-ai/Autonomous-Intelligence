import { Command } from "commander";
import chalk from "chalk";
import * as path from "path";
import { search } from "../embeddings/retriever.js";
import { readMeta } from "../embeddings/store.js";

export function searchCommand(): Command {
  return new Command("search")
    .alias("s")
    .description("Semantic search of the indexed codebase")
    .argument("<query>", "what to search for")
    .option("-d, --dir <path>", "project directory", process.cwd())
    .option("-n, --top <n>", "number of results", "10")
    .option("--json", "output results as JSON")
    .action((query: string, opts) => {
      const cwd = path.resolve(opts.dir);
      const topK = Math.max(1, Math.min(50, parseInt(opts.top, 10) || 10));
      const meta = readMeta(cwd);
      if (!meta) {
        console.error(chalk.red("✗ No index found.") + chalk.gray(`\n  Run: anote index${opts.dir !== process.cwd() ? ` ${opts.dir}` : ``}`));
        process.exit(1);
      }
      const results = search(query, cwd, topK);
      if (opts.json) { console.log(JSON.stringify(results, null, 2)); return; }
      if (results.length === 0) {
        console.log(chalk.yellow(`\nNo results found for "${query}"`));
        return;
      }
      console.log(chalk.bold.cyan(`\n◆ Anote Search`) + chalk.dim(`  "${query}"  ·  ${results.length} result${results.length !== 1 ? "s" : ""}\n`));
      for (const r of results) {
        console.log(`  ${chalk.cyan(r.file)}${chalk.dim(`:${r.startLine}`)}  ${chalk.dim(`(${r.score.toFixed(2)})`)}`);
        console.log(chalk.dim(`    ${r.preview.slice(0, 100)}`));
        console.log();
      }
    });
}
