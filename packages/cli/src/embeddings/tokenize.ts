const STOP_WORDS = new Set([
  "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
  "have", "has", "had", "do", "does", "did", "will", "would", "could",
  "should", "may", "might", "must", "can", "to", "of", "in", "on", "at",
  "for", "by", "with", "as", "or", "and", "but", "if", "not", "this",
  "that", "it", "its", "from", "into", "than", "then", "so", "no", "yes",
  "true", "false", "null", "undefined", "void", "new", "return", "import",
  "export", "const", "let", "var", "function", "class", "interface", "type",
  "enum", "extends", "implements", "public", "private", "protected", "static",
  "async", "await", "try", "catch", "throw", "finally", "case", "break",
  "continue", "default", "switch", "while", "for", "of", "in", "else",
]);

function splitCamel(s: string): string[] {
  return s
    .replace(/([a-z])([A-Z])/g, "$1 $2")
    .replace(/([A-Z]+)([A-Z][a-z])/g, "$1 $2")
    .split(" ")
    .map((w) => w.toLowerCase())
    .filter((w) => w.length >= 2);
}

export function tokenize(text: string): string[] {
  const tokens: string[] = [];
  const raw = text.split(/[\s\n\r\t,;:.()\ \[\]{}<>'"=|&^%@!?/\\+\-*~`]+/);
  for (const chunk of raw) {
    if (!chunk || chunk.length < 2 || chunk.length > 60) continue;
    if (/^\d+$/.test(chunk)) continue;
    if (/[A-Z]/.test(chunk)) {
      const parts = splitCamel(chunk);
      for (const p of parts) { if (p.length >= 2 && !STOP_WORDS.has(p)) tokens.push(p); }
      const lower = chunk.toLowerCase();
      if (!STOP_WORDS.has(lower) && lower.length >= 2) tokens.push(lower);
    } else {
      const parts = chunk.toLowerCase().split("_").filter((p) => p.length >= 2);
      for (const p of parts) { if (!STOP_WORDS.has(p)) tokens.push(p); }
    }
  }
  return tokens;
}

export function termFrequency(text: string): Map<string, number> {
  const counts = new Map<string, number>();
  for (const t of tokenize(text)) counts.set(t, (counts.get(t) ?? 0) + 1);
  return counts;
}
