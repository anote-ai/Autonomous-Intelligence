import type { Chunk, IndexedChunk } from "./types.js";
import { termFrequency } from "./tokenize.js";

const TOP_VOCAB_SIZE = 3000;

export function buildTfIdf(chunks: Chunk[]): {
  indexed: IndexedChunk[];
  vocab: Record<string, number>;
} {
  const N = chunks.length;
  if (N === 0) return { indexed: [], vocab: {} };

  const chunkTf = chunks.map((c) => termFrequency(c.text));

  const df = new Map<string, number>();
  for (const tf of chunkTf) {
    for (const term of tf.keys()) {
      df.set(term, (df.get(term) ?? 0) + 1);
    }
  }

  const sortedTerms = Array.from(df.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, TOP_VOCAB_SIZE)
    .map(([term]) => term);
  const vocabSet = new Set(sortedTerms);

  const vocab: Record<string, number> = {};
  for (const term of sortedTerms) {
    const d = df.get(term) ?? 1;
    vocab[term] = Math.log(1 + N / d);
  }

  const indexed: IndexedChunk[] = chunks.map((chunk, i) => {
    const tf = chunkTf[i];
    const totalTerms = chunk.text.split(/\s+/).length;
    const vec: Record<string, number> = {};
    let norm = 0;
    for (const [term, count] of tf.entries()) {
      if (!vocabSet.has(term)) continue;
      const tfWeight = count / Math.max(totalTerms, 1);
      const weight = tfWeight * (vocab[term] ?? 0);
      if (weight > 0) { vec[term] = weight; norm += weight * weight; }
    }
    norm = Math.sqrt(norm);
    if (norm > 0) for (const term in vec) vec[term] /= norm;
    return { id: chunk.id, file: chunk.file, startLine: chunk.startLine, endLine: chunk.endLine, preview: chunk.preview, vec };
  });

  return { indexed, vocab };
}

export function embedQuery(query: string, vocab: Record<string, number>): Record<string, number> {
  const tf = termFrequency(query);
  const totalTerms = query.split(/\s+/).length;
  const vec: Record<string, number> = {};
  let norm = 0;
  for (const [term, count] of tf.entries()) {
    const idf = vocab[term];
    if (idf === undefined) continue;
    const weight = (count / Math.max(totalTerms, 1)) * idf;
    if (weight > 0) { vec[term] = weight; norm += weight * weight; }
  }
  norm = Math.sqrt(norm);
  if (norm > 0) for (const term in vec) vec[term] /= norm;
  return vec;
}

export function cosineSimilarity(a: Record<string, number>, b: Record<string, number>): number {
  const [small, large] = Object.keys(a).length <= Object.keys(b).length ? [a, b] : [b, a];
  let dot = 0;
  for (const term in small) {
    const bVal = large[term];
    if (bVal !== undefined) dot += small[term] * bVal;
  }
  return dot;
}
