/** A chunk of source code extracted from a file. */
export interface Chunk {
  id: string;
  file: string;
  startLine: number;
  endLine: number;
  preview: string;
  text: string;
}

/** A chunk with its sparse TF-IDF vector (normalized). */
export interface IndexedChunk {
  id: string;
  file: string;
  startLine: number;
  endLine: number;
  preview: string;
  vec: Record<string, number>;
  dense?: number[];
}

export interface FileMeta {
  hash: string;
  chunks: number;
  indexedAt: number;
}

export interface IndexMeta {
  version: number;
  indexedAt: number;
  provider: "tfidf" | "ollama" | "openai";
  numChunks: number;
  vocab: Record<string, number>;
  files: Record<string, FileMeta>;
}

export interface SearchResult {
  file: string;
  startLine: number;
  endLine: number;
  preview: string;
  score: number;
}
