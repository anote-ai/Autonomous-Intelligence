import { describe, it, expect } from "vitest";
import { HookRunner } from "../hooks.js";

describe("HookRunner", () => {
  it("returns allowed when no hooks configured", () => {
    const runner = new HookRunner({});
    const result = runner.runPreToolUse("Read", JSON.stringify({ path: "/tmp/test" }));
    expect(result.denied).toBe(false);
    expect(result.messages).toEqual([]);
  });

  it("preToolUse hook exit 0 = allow", () => {
    const runner = new HookRunner({ preToolUse: ["exit 0"] });
    const result = runner.runPreToolUse("Read", JSON.stringify({ path: "/tmp/test" }));
    expect(result.denied).toBe(false);
  });

  it("preToolUse hook exit 2 = deny with message", () => {
    const runner = new HookRunner({ preToolUse: ["echo 'tool denied by policy' && exit 2"] });
    const result = runner.runPreToolUse("Bash", JSON.stringify({ command: "rm -rf /" }));
    expect(result.denied).toBe(true);
    expect(result.messages.length).toBeGreaterThan(0);
    expect(result.messages[0]).toContain("tool denied by policy");
  });
});
