import type { Chunk } from "./types.js";

const CHUNK_BOUNDARY = /^(?:export\s+(?:default\s+)?(?:async\s+)?(?:function|class|const|let|var|interface|type|enum|abstract)|(?:async\s+)?function\s+\w|class\s+\w|def\s+\w|pub(?:\s+(?:async\s+)?fn|(?:\s+struct|\s+impl|\s+enum|\s+trait))\s+\w|func\s+\w|\w+\s*:=\s*func)/;

const CHUNK_SIZE = 60;
const MIN_CHUNK  = 5;
const OVERLAP    = 8;

export function chunkFile(relPath: string, content: string): Chunk[] {
  const lines = content.split("\n");
  const chunks: Chunk[] = [];
  const ext = relPath.split(".").pop()?.toLowerCase() ?? "";

  if (lines.length <= CHUNK_SIZE) {
    if (lines.length >= MIN_CHUNK) chunks.push(makeChunk(relPath, lines, 1, lines.length));
    return chunks;
  }

  if (["json", "yaml", "yml", "toml", "lock", "sum", "mod"].includes(ext)) {
    if (lines.length <= CHUNK_SIZE * 3) chunks.push(makeChunk(relPath, lines, 1, Math.min(lines.length, CHUNK_SIZE * 3)));
    return chunks;
  }

  const boundaries: number[] = [0];
  for (let i = 0; i < lines.length; i++) {
    const trimmed = lines[i].trimStart();
    if (CHUNK_BOUNDARY.test(trimmed)) {
      if (i - (boundaries[boundaries.length - 1] ?? 0) >= MIN_CHUNK) boundaries.push(i);
    }
  }
  boundaries.push(lines.length);

  const merged: number[] = [boundaries[0]];
  for (let i = 1; i < boundaries.length; i++) {
    const start = merged[merged.length - 1];
    const end = boundaries[i];
    if (end - start >= MIN_CHUNK) merged.push(end);
  }
  if (merged[merged.length - 1] !== lines.length) merged.push(lines.length);

  for (let i = 0; i < merged.length - 1; i++) {
    const windowStart = merged[i];
    const windowEnd = merged[i + 1];
    const windowSize = windowEnd - windowStart;

    if (windowSize <= CHUNK_SIZE) {
      chunks.push(makeChunk(relPath, lines, windowStart + 1, windowEnd));
    } else {
      for (let s = windowStart; s < windowEnd; s += CHUNK_SIZE - OVERLAP) {
        const e = Math.min(s + CHUNK_SIZE, windowEnd);
        if (e - s >= MIN_CHUNK) chunks.push(makeChunk(relPath, lines, s + 1, e));
        if (e === windowEnd) break;
      }
    }
  }

  return chunks;
}

function makeChunk(file: string, lines: string[], startLine: number, endLine: number): Chunk {
  const text = lines.slice(startLine - 1, endLine).join("\n");
  const preview = text.trimStart().slice(0, 120).replace(/\n/g, " ↵ ");
  return { id: `${file}:${startLine}`, file, startLine, endLine, preview, text };
}
