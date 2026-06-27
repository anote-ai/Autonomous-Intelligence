import { describe, it, expect, beforeEach, afterEach } from "vitest";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { loadConfig } from "../config.js";

describe("loadConfig()", () => {
  let tmpDir: string;

  beforeEach(() => {
    tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), "anote-config-test-"));
  });

  afterEach(() => {
    fs.rmSync(tmpDir, { recursive: true, force: true });
  });

  it("returns empty object when no config file found", () => {
    const config = loadConfig(tmpDir);
    expect(config).toEqual({});
  });

  it("merges .anote.json values correctly", () => {
    const configData = { model: "claude-opus-4-5", maxTurns: 10 };
    fs.writeFileSync(
      path.join(tmpDir, ".anote.json"),
      JSON.stringify(configData),
      "utf8"
    );
    const config = loadConfig(tmpDir);
    expect(config.model).toBe("claude-opus-4-5");
    expect(config.maxTurns).toBe(10);
  });

  it("ignores invalid JSON gracefully", () => {
    fs.writeFileSync(
      path.join(tmpDir, ".anote.json"),
      "{ this is not valid json !!!",
      "utf8"
    );
    const config = loadConfig(tmpDir);
    expect(config).toEqual({});
  });

  it("loads MCP server config (stdio + http)", () => {
    const configData = {
      mcpServers: {
        github: { command: "npx", args: ["-y", "@modelcontextprotocol/server-github"] },
        docs: { type: "http", url: "https://example.com/mcp" },
      },
    };
    fs.writeFileSync(
      path.join(tmpDir, ".anote.json"),
      JSON.stringify(configData),
      "utf8"
    );
    const config = loadConfig(tmpDir);
    expect(config.mcpServers?.github).toEqual({
      command: "npx",
      args: ["-y", "@modelcontextprotocol/server-github"],
    });
    expect(config.mcpServers?.docs).toEqual({
      type: "http",
      url: "https://example.com/mcp",
    });
  });
});
