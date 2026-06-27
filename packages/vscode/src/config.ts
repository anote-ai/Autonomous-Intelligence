import * as vscode from "vscode";

export type AnoteProvider =
  | "anthropic"
  | "openai"
  | "gemini"
  | "llama"
  | "xai"
  | "custom";

export const DEFAULT_PROVIDER: AnoteProvider = "anthropic";
export const DEFAULT_MODEL = "claude-sonnet-4-6";

/** MCP server config, mirroring `@anthropic-ai/claude-agent-sdk`'s mcpServers shape. */
export type McpServerConfig =
  | { type?: "stdio"; command: string; args?: string[]; env?: Record<string, string> }
  | { type: "sse"; url: string; headers?: Record<string, string> }
  | { type: "http"; url: string; headers?: Record<string, string> };

/** MCP servers from the `anote.mcpServers` setting (Anthropic runtime only). */
export function getMcpServers(): Record<string, McpServerConfig> | undefined {
  const servers = vscode.workspace
    .getConfiguration("anote")
    .get<Record<string, McpServerConfig>>("mcpServers");
  return servers && Object.keys(servers).length ? servers : undefined;
}

export function getProvider(): AnoteProvider {
  return (
    vscode.workspace.getConfiguration("anote").get<AnoteProvider>("provider") ??
    DEFAULT_PROVIDER
  );
}

export function getModel(): string {
  return (
    vscode.workspace.getConfiguration("anote").get<string>("model") ??
    DEFAULT_MODEL
  );
}

export function getServerUrl(): string {
  return (
    vscode.workspace.getConfiguration("anote").get<string>("serverUrl") ?? ""
  ).trim();
}

export function getConfiguredApiKey(): string {
  const config = vscode.workspace.getConfiguration("anote");
  return (
    config.get<string>("apiKey") ||
    resolveProviderEnv(getProvider()) ||
    process.env.ANOTE_API_KEY ||
    ""
  );
}

export function providerDisplayName(provider: AnoteProvider): string {
  switch (provider) {
    case "anthropic":
      return "Anthropic";
    case "openai":
      return "OpenAI";
    case "gemini":
      return "Gemini";
    case "llama":
      return "Llama";
    case "xai":
      return "xAI";
    case "custom":
      return "Custom";
  }
}

export function providerSamples(provider: AnoteProvider): string[] {
  switch (provider) {
    case "openai":
      return ["gpt-4.1", "gpt-4o", "o4-mini"];
    case "gemini":
      return ["gemini-2.5-pro", "gemini-2.5-flash"];
    case "llama":
      return ["llama-3.3-70b-instruct", "qwen2.5-coder-32b-instruct"];
    case "xai":
      return ["grok-3", "grok-3-mini"];
    case "custom":
      return ["your-model-name"];
    case "anthropic":
    default:
      return ["claude-sonnet-4-6", "claude-opus-4-6", "claude-haiku-4-5"];
  }
}

export function directRuntimeSupportMessage(provider: AnoteProvider): string | undefined {
  if (provider === "anthropic") {
    return undefined;
  }

  return `${providerDisplayName(provider)} direct mode is not wired into the built-in VS Code runtime yet. Configure an Anote server in anote.serverUrl or switch anote.provider to anthropic.`;
}

function resolveProviderEnv(provider: AnoteProvider): string {
  switch (provider) {
    case "anthropic":
      return process.env.ANTHROPIC_API_KEY ?? "";
    case "openai":
      return process.env.OPENAI_API_KEY ?? "";
    case "gemini":
      return process.env.GEMINI_API_KEY ?? process.env.GOOGLE_API_KEY ?? "";
    case "llama":
      return process.env.LLAMA_API_KEY ?? process.env.OPENAI_API_KEY ?? "";
    case "xai":
      return process.env.XAI_API_KEY ?? "";
    case "custom":
      return process.env.ANOTE_API_KEY ?? process.env.OPENAI_API_KEY ?? "";
  }
}
