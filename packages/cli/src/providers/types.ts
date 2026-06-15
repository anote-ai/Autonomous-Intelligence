export interface Message {
  role: "user" | "assistant";
  content: string;
}

export interface StreamOptions {
  cwd: string;
  allowedTools: string[];
  systemPrompt: string;
  maxTurns: number;
  model: string;
}

export type StreamEvent =
  | { type: "text"; text: string }
  | { type: "tool"; tool: string; input: unknown }
  | { type: "tool_result"; content: unknown }
  | { type: "done"; result: string; stop_reason: string }
  | { type: "error"; message: string };

export interface ProviderAdapter {
  stream(messages: Message[], options: StreamOptions): AsyncIterable<StreamEvent>;
}

export type Provider = "anthropic" | "openai" | "gemini";

export function resolveProvider(model: string): Provider {
  if (model.startsWith("gpt-") || model.startsWith("o1") || model.startsWith("o3") || model.startsWith("o4") || model.startsWith("ollama/") || model.startsWith("local/")) return "openai";
  if (model.startsWith("gemini")) return "gemini";
  return "anthropic";
}
