import type { SearchResult } from "./types.js";
import { readIndex } from "./store.js";
import { embedQuery, cosineSimilarity } from "./tfidf.js";

let cachedCwd: string | null = null;
let cachedChunks: ReturnType<typeof readIndex> | null = null;

function loadCached(cwd: string) {
  if (cachedCwd !== cwd) { cachedChunks = readIndex(cwd); cachedCwd = cwd; }
  return cachedChunks;
}

export function invalidateCache(): void { cachedCwd = null; cachedChunks = null; }

export function search(query: string, cwd: string, topK = 5, minScore = 0.05): SearchResult[] {
  const idx = loadCached(cwd);
  if (!idx || idx.chunks.length === 0) return [];
  const qVec = embedQuery(query, idx.meta.vocab);
  if (Object.keys(qVec).length === 0) return [];
  return idx.chunks
    .map((c) => ({ chunk: c, score: cosineSimilarity(qVec, c.vec) }))
    .filter((r) => r.score > minScore)
    .sort((a, b) => b.score - a.score)
    .slice(0, topK)
    .map((r) => ({ file: r.chunk.file, startLine: r.chunk.startLine, endLine: r.chunk.endLine, preview: r.chunk.preview, score: Math.round(r.score * 100) / 100 }));
}
