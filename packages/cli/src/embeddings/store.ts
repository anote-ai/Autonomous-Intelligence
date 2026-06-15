import * as fs from "fs";
import * as path from "path";
import * as crypto from "crypto";
import type { IndexedChunk, IndexMeta } from "./types.js";

const INDEX_DIR_NAME = ".anote/index";
const CHUNKS_FILE = "chunks.json";
const META_FILE = "meta.json";

export function getIndexDir(cwd: string): string { return path.join(cwd, INDEX_DIR_NAME); }

export function ensureIndexDir(cwd: string): void {
  const dir = getIndexDir(cwd);
  if (!fs.existsSync(dir)) fs.mkdirSync(dir, { recursive: true });
  const gitignorePath = path.join(cwd, ".gitignore");
  if (fs.existsSync(gitignorePath)) {
    const content = fs.readFileSync(gitignorePath, "utf8");
    if (!content.includes(".anote/")) fs.appendFileSync(gitignorePath, "\n# Anote index\n.anote/\n");
  }
}

export function readIndex(cwd: string): { chunks: IndexedChunk[]; meta: IndexMeta } | null {
  const dir = getIndexDir(cwd);
  const chunksPath = path.join(dir, CHUNKS_FILE);
  const metaPath = path.join(dir, META_FILE);
  if (!fs.existsSync(chunksPath) || !fs.existsSync(metaPath)) return null;
  try {
    const meta = JSON.parse(fs.readFileSync(metaPath, "utf8")) as IndexMeta;
    const chunks = JSON.parse(fs.readFileSync(chunksPath, "utf8")) as IndexedChunk[];
    return { meta, chunks };
  } catch { return null; }
}

export function writeIndex(cwd: string, chunks: IndexedChunk[], meta: IndexMeta): void {
  ensureIndexDir(cwd);
  const dir = getIndexDir(cwd);
  fs.writeFileSync(path.join(dir, META_FILE), JSON.stringify(meta), "utf8");
  fs.writeFileSync(path.join(dir, CHUNKS_FILE), JSON.stringify(chunks), "utf8");
}

export function readMeta(cwd: string): IndexMeta | null {
  const metaPath = path.join(getIndexDir(cwd), META_FILE);
  if (!fs.existsSync(metaPath)) return null;
  try { return JSON.parse(fs.readFileSync(metaPath, "utf8")) as IndexMeta; } catch { return null; }
}

export function hashFile(filePath: string): string {
  const buf = fs.readFileSync(filePath);
  return crypto.createHash("sha1").update(buf).digest("hex");
}

export function listSourceFiles(cwd: string): string[] {
  const INCLUDE_EXTS = new Set(["ts","tsx","js","jsx","mjs","cjs","py","go","rs","java","kt","swift","cpp","cc","c","h","hpp","cs","rb","php","scala","lua","md","txt","sh","bash","zsh","json","yaml","yml","toml"]);
  const EXCLUDE_DIRS = new Set(["node_modules",".git","dist","build","out",".next","__pycache__",".cache","coverage",".anote","vendor","target",".venv","venv"]);
  const files: string[] = [];
  function walk(dir: string): void {
    let entries: fs.Dirent[];
    try { entries = fs.readdirSync(dir, { withFileTypes: true }); } catch { return; }
    for (const entry of entries) {
      if (entry.name.startsWith(".") && entry.name !== ".anote") continue;
      if (entry.isDirectory()) { if (!EXCLUDE_DIRS.has(entry.name)) walk(path.join(dir, entry.name)); }
      else if (entry.isFile()) {
        const ext = entry.name.split(".").pop()?.toLowerCase() ?? "";
        if (INCLUDE_EXTS.has(ext) && entry.name.length < 200) files.push(path.join(dir, entry.name));
      }
    }
  }
  walk(cwd);
  return files;
}
