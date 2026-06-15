import { describe, it, expect } from "vitest";
import { AnoteClient } from "./index.js";

describe("AnoteClient", () => {
  it("constructs with a base URL", () => {
    const client = new AnoteClient({ baseUrl: "http://localhost:5000" });
    expect(client).toBeDefined();
  });

  it("constructs with default base URL", () => {
    const client = new AnoteClient({});
    expect(client).toBeDefined();
  });
});
