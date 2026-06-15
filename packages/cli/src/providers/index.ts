import { resolveProvider } from "./types.js";
import { OpenAIAdapter } from "./openai.js";
import { GeminiAdapter } from "./gemini.js";
import type { ProviderAdapter } from "./types.js";

export { resolveProvider } from "./types.js";
export type { ProviderAdapter, StreamEvent, StreamOptions, Message } from "./types.js";

export interface ResolveResult {
  adapter: ProviderAdapter;
  error?: string;
}

export function getAdapter(model: string): ResolveResult {
  const provider = resolveProvider(model);

  switch (provider) {
    case "anthropic":
      return {
        adapter: { stream: async function* () { yield { type: "error" as const, message: "Use claude-agent-sdk for Anthropic models." }; } },
        error: "Use claude-agent-sdk for Anthropic models.",
      };

    case "openai": {
      const needsKey = !model.startsWith("ollama/") && !model.startsWith("local/");
      if (needsKey && !process.env["OPENAI_API_KEY"]) return { adapter: new OpenAIAdapter(), error: "OPENAI_API_KEY is not set" };
      return { adapter: new OpenAIAdapter() };
    }

    case "gemini":
      if (!process.env["GEMINI_API_KEY"]) return { adapter: new GeminiAdapter(), error: "GEMINI_API_KEY is not set" };
      return { adapter: new GeminiAdapter() };
  }
}

export function configuredProviders(): Record<string, boolean> {
  return { anthropic: !!process.env["ANTHROPIC_API_KEY"], openai: !!process.env["OPENAI_API_KEY"], gemini: !!process.env["GEMINI_API_KEY"], ollama: true };
}
