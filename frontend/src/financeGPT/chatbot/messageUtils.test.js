import { describe, it, expect } from "vitest";
import {
  normalizeSources,
  parseRelevantChunks,
  formatChatMessages,
} from "./messageUtils";

// ---------------------------------------------------------------------------
// normalizeSources
// ---------------------------------------------------------------------------

describe("normalizeSources", () => {
  it("returns empty array for null", () => {
    expect(normalizeSources(null)).toEqual([]);
  });

  it("returns empty array for undefined", () => {
    expect(normalizeSources(undefined)).toEqual([]);
  });

  it("returns empty array for empty array", () => {
    expect(normalizeSources([])).toEqual([]);
  });

  it("normalizes an object source", () => {
    const result = normalizeSources([
      { chunk_text: "Hello world", document_name: "doc.pdf", page_number: 3 },
    ]);
    expect(result).toHaveLength(1);
    expect(result[0].chunk_text).toBe("Hello world");
    expect(result[0].document_name).toBe("doc.pdf");
    expect(result[0].page_number).toBe(3);
    expect(result[0].source_type).toBe("document_chunk");
  });

  it("normalizes an array-format source", () => {
    const result = normalizeSources([["chunk text", "my_doc.pdf", 5, 0, 100]]);
    expect(result).toHaveLength(1);
    expect(result[0].chunk_text).toBe("chunk text");
    expect(result[0].document_name).toBe("my_doc.pdf");
    expect(result[0].page_number).toBe(5);
    expect(result[0].start_index).toBe(0);
    expect(result[0].end_index).toBe(100);
  });

  it("filters out null sources", () => {
    const result = normalizeSources([null, undefined, { chunk_text: "ok", document_name: "d.pdf" }]);
    expect(result).toHaveLength(1);
  });

  it("handles camelCase aliases", () => {
    const result = normalizeSources([
      { chunkText: "text", documentName: "doc", pageNumber: 2 },
    ]);
    expect(result[0].chunk_text).toBe("text");
    expect(result[0].document_name).toBe("doc");
    expect(result[0].page_number).toBe(2);
  });

  it("defaults document_name when missing", () => {
    const result = normalizeSources([{ chunk_text: "text" }]);
    expect(result[0].document_name).toBe("Unknown document");
  });

  it("assigns sequential ids to array sources", () => {
    const result = normalizeSources([
      ["a", "doc1.pdf"],
      ["b", "doc2.pdf"],
    ]);
    expect(result[0].id).toBe("source-0");
    expect(result[1].id).toBe("source-1");
  });
});

// ---------------------------------------------------------------------------
// parseRelevantChunks
// ---------------------------------------------------------------------------

describe("parseRelevantChunks", () => {
  it("returns empty array for null", () => {
    expect(parseRelevantChunks(null)).toEqual([]);
  });

  it("returns empty array for non-string", () => {
    expect(parseRelevantChunks(42)).toEqual([]);
  });

  it("returns empty array for empty string", () => {
    expect(parseRelevantChunks("")).toEqual([]);
  });

  it("parses a valid chunk string", () => {
    const input = "Document: report.pdf: This is the relevant text.";
    const result = parseRelevantChunks(input);
    expect(result).toHaveLength(1);
    expect(result[0].document_name).toBe("report.pdf");
    expect(result[0].chunk_text).toBe("This is the relevant text.");
    expect(result[0].source_type).toBe("stored_relevant_chunk");
  });

  it("parses multiple chunks separated by double newline", () => {
    const input = [
      "Document: doc1.pdf: First chunk.",
      "Document: doc2.pdf: Second chunk.",
    ].join("\n\n");
    const result = parseRelevantChunks(input);
    expect(result).toHaveLength(2);
    expect(result[0].document_name).toBe("doc1.pdf");
    expect(result[1].document_name).toBe("doc2.pdf");
  });

  it("ignores entries not starting with 'Document: '", () => {
    const input = "Some random text\n\nDocument: real.pdf: actual content";
    const result = parseRelevantChunks(input);
    expect(result).toHaveLength(1);
    expect(result[0].document_name).toBe("real.pdf");
  });

  it("sets page_number to null", () => {
    const result = parseRelevantChunks("Document: f.pdf: text");
    expect(result[0].page_number).toBeNull();
  });
});

// ---------------------------------------------------------------------------
// formatChatMessages
// ---------------------------------------------------------------------------

describe("formatChatMessages", () => {
  const rawMessages = [
    {
      id: 1,
      message_text: "Hello",
      sent_from_user: 1,
      relevant_chunks: null,
      sources: null,
      reasoning: null,
      charts: null,
      created: "2024-01-01T10:00:00Z",
    },
    {
      id: 2,
      message_text: "Hi there!",
      sent_from_user: 0,
      relevant_chunks: null,
      sources: [{ chunk_text: "ctx", document_name: "d.pdf" }],
      reasoning: [{ step: "think" }],
      charts: [{ title: "chart1" }],
      created: "2024-01-01T10:00:01Z",
    },
  ];

  it("maps user messages to role=user", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(result[0].role).toBe("user");
  });

  it("maps bot messages to role=assistant", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(result[1].role).toBe("assistant");
  });

  it("copies message_text to content", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(result[0].content).toBe("Hello");
    expect(result[1].content).toBe("Hi there!");
  });

  it("includes chat_id on each message", () => {
    const result = formatChatMessages(rawMessages, 42);
    result.forEach((msg) => expect(msg.chat_id).toBe(42));
  });

  it("includes sources from normalized sources when present", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(result[1].sources).toHaveLength(1);
    expect(result[1].sources[0].chunk_text).toBe("ctx");
  });

  it("defaults reasoning to empty array", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(result[0].reasoning).toEqual([]);
  });

  it("includes charts", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(result[1].charts).toHaveLength(1);
  });

  it("converts created to timestamp", () => {
    const result = formatChatMessages(rawMessages, 42);
    expect(typeof result[0].timestamp).toBe("number");
    expect(result[0].timestamp).toBeGreaterThan(0);
  });
});
