import { Command } from "commander";
import chalk from "chalk";
import * as fs from "fs";
import * as path from "path";
import chokidar from "chokidar";
import { listSourceFiles, writeIndex, hashFile, getIndexDir } from "../embeddings/store.js";
import { chunkFile } from "../embeddings/chunker.js";
import { buildTfIdf } from "../embeddings/tfidf.js";
import { invalidateCache } from "../embeddings/retriever.js";
import type { Chunk, IndexMeta } from "../embeddings/types.js";

const WATCH_IGNORED = ["**/node_modules/**","**/.git/**","**/dist/**","**/build/**","**/.anote/**","**/__pycache__/**","**/*.pyc"];

export function indexCommand(): Command {
  return new Command("index")
    .description("Index the codebase for semantic search")
    .argument("[dir]", "directory to index", process.cwd())
    .option("--watch", "re-index on file changes")
    .action(async (dir: string, opts) => {
      const cwd = path.resolve(dir);
      if (!fs.existsSync(cwd)) { console.error(chalk.red(`Directory not found: ${cwd}`)); process.exit(1); }
      await runIndex(cwd);
      if (opts.watch) {
        console.log(chalk.dim("\n  Watching for changes… (Ctrl+C to stop)\n"));
        const watcher = chokidar.watch(cwd, { ignored: WATCH_IGNORED, ignoreInitial: true, persistent: true });
        let debounceTimer: ReturnType<typeof setTimeout> | null = null;
        const changed = new Set<string>();
        const scheduleReindex = (filePath: string): void => {
          changed.add(path.relative(cwd, filePath));
          if (debounceTimer) clearTimeout(debounceTimer);
          debounceTimer = setTimeout(async () => { changed.clear(); await runIndex(cwd); }, 800);
        };
        watcher.on("add", scheduleReindex).on("change", scheduleReindex).on("unlink", scheduleReindex);
      }
    });
}

export async function runIndex(cwd: string): Promise<void> {
  const start = Date.now();
  const allFiles = listSourceFiles(cwd);
  if (allFiles.length === 0) { console.log(chalk.yellow("No source files found to index.")); return; }
  console.log(chalk.cyan("\n◆ Anote Index  ") + chalk.white(`Indexing ${allFiles.length} files…\n`));
  const allChunks: Chunk[] = [];
  const fileHashes: IndexMeta["files"] = {};
  let filesDone = 0;
  for (const absPath of allFiles) {
    const relPath = path.relative(cwd, absPath);
    try {
      const content = fs.readFileSync(absPath, "utf-8");
      const chunks = chunkFile(relPath, content);
      allChunks.push(...chunks);
      fileHashes[relPath] = { hash: hashFile(absPath), chunks: chunks.length, indexedAt: Date.now() };
    } catch { /* skip unreadable files */ }
    filesDone++;
    if (filesDone % 25 === 0 || filesDone === allFiles.length) {
      const pct = Math.round((filesDone / allFiles.length) * 100);
      process.stdout.write(`\r  ${chalk.dim(`${filesDone}/${allFiles.length} files (${pct}%) — ${allChunks.length} chunks`)}`);
    }
  }
  if (allChunks.length === 0) { console.log(chalk.yellow("\nNo chunks produced — nothing to index.")); return; }
  process.stdout.write(`\r  ${chalk.dim("Building TF-IDF vectors…")}`);
  const { indexed, vocab } = buildTfIdf(allChunks);
  const meta: IndexMeta = { version: 1, indexedAt: Date.now(), provider: "tfidf", numChunks: indexed.length, vocab, files: fileHashes };
  writeIndex(cwd, indexed, meta);
  invalidateCache();
  const elapsed = ((Date.now() - start) / 1000).toFixed(1);
  process.stdout.write("\r" + " ".repeat(70) + "\r");
  console.log(chalk.green(`  ✓ Indexed ${allFiles.length} files → ${indexed.length} chunks`) + chalk.dim(` (${elapsed}s)`));
  console.log(chalk.dim(`  Vocab: ${Object.keys(vocab).length} terms  ·  Index: ${getIndexDir(cwd)}\n`));
}
