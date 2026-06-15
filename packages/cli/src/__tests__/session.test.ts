import { describe, it, expect } from "vitest";
import { compactMessages } from "../session.js";
import type { StoredMessage } from "../session.js";

function makeMessages(count: number): StoredMessage[] {
  return Array.from({ length: count }, (_, i) => ({
    role: i % 2 === 0 ? "user" : "assistant",
    content: `Message ${i}`,
    ts: Date.now() + i,
  }));
}

describe("compactMessages()", () => {
  it("returns all messages when under limit", () => {
    const messages = makeMessages(5);
    const result = compactMessages(messages, 20);
    expect(result).toHaveLength(5);
    expect(result).toEqual(messages);
  });

  it("truncates to keepLast messages when over limit", () => {
    const messages = makeMessages(30);
    const result = compactMessages(messages, 10);
    expect(result).toHaveLength(10);
  });

  it("preserves message order after truncation", () => {
    const messages = makeMessages(25);
    const result = compactMessages(messages, 5);
    expect(result).toHaveLength(5);
    const expected = messages.slice(20);
    expect(result).toEqual(expected);
    expect(result[0].content).toBe("Message 20");
    expect(result[4].content).toBe("Message 24");
  });
});
