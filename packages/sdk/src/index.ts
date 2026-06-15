/**
 * @anote-ai/sdk — TypeScript SDK for the Anote REST API v1.
 *
 * @example
 * ```ts
 * import { AnoteClient } from "@anote-ai/sdk";
 *
 * const client = new AnoteClient({ apiKey: "ant-..." });
 *
 * const { result } = await client.chat("Explain this codebase");
 * console.log(result);
 *
 * const usage = await client.getUsage();
 * console.log(`Used ${usage.current.requestCount} requests this month`);
 * ```
 */

// ── Types ─────────────────────────────────────────────────────────────────────

export interface AnoteClientOptions {
  /** API key starting with `ant-`. Generate one at your Anote instance → Settings → API Keys. */
  apiKey: string;
  /** Base URL of your Anote server. Defaults to `https://api.anote.ai`. */
  baseUrl?: string;
}

export interface ChatOptions {
  /** Working directory for file operations on the server. */
  cwd?: string;
  /** Claude model to use. */
  model?: "claude-opus-4-6" | "claude-sonnet-4-6" | "claude-haiku-4-5";
  /** Tools the AI may use. Default: read-only tools. */
  tools?: ("Read" | "Write" | "Edit" | "Bash" | "Glob" | "Grep")[];
}

export interface ChatResult {
  result: string;
  usage: { inputTokens: number; outputTokens: number };
}

export interface SessionSummary {
  sessionId: string;
  cwd: string;
  messageCount: number;
  inputTokens: number;
  outputTokens: number;
  model: string;
  createdAt: number;
  updatedAt: number;
}

export interface Message {
  role: "user" | "assistant";
  content: string;
  ts: number;
}

export interface SearchResult {
  sessionId: string;
  role: string;
  snippet: string;
  ts: number;
}

export interface MonthlyUsage {
  month: string;
  requestCount: number;
  inputTokens: number;
  outputTokens: number;
  updatedAt: number;
}

export interface UsageQuota {
  plan: "free" | "pro";
  maxRequests: number;
  maxInputTokens: number;
  maxOutputTokens: number;
}

export interface UsageSummary {
  current: MonthlyUsage;
  quota: UsageQuota;
  remaining: {
    requests: number | "unlimited";
    inputTokens: number | "unlimited";
    outputTokens: number | "unlimited";
  };
  history: MonthlyUsage[];
}

export interface ShareResult {
  token: string;
  shareUrl: string;
}

// ── Error class ─────────────────────────────────────────────────────────────────────

export class AnoteError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly body: unknown,
  ) {
    super(message);
    this.name = "AnoteError";
  }
}

// ── Client ────────────────────────────────────────────────────────────────────────────

export class AnoteClient {
  private readonly apiKey: string;
  private readonly baseUrl: string;

  constructor(options: AnoteClientOptions) {
    if (!options.apiKey) throw new Error("apiKey is required");
    this.apiKey = options.apiKey;
    this.baseUrl = (options.baseUrl ?? "https://api.anote.ai").replace(/\/$/, "") + "/api/v1";
  }

  // ── Core HTTP ───────────────────────────────────────────────────────────────────

  private async request<T>(
    method: string,
    path: string,
    body?: unknown,
    params?: Record<string, string | number>,
  ): Promise<T> {
    let url = `${this.baseUrl}${path}`;
    if (params) {
      const qs = new URLSearchParams(
        Object.entries(params)
          .filter(([, v]) => v !== undefined)
          .map(([k, v]) => [k, String(v)]),
      );
      if (qs.toString()) url += `?${qs}`;
    }

    const res = await fetch(url, {
      method,
      headers: {
        "Authorization": `Bearer ${this.apiKey}`,
        "Content-Type": "application/json",
        "User-Agent": "@anote-ai/sdk/1.0.0",
      },
      body: body !== undefined ? JSON.stringify(body) : undefined,
    });

    const data = await res.json().catch(() => ({}));

    if (!res.ok) {
      const msg = (data as { error?: string }).error ?? `HTTP ${res.status}`;
      throw new AnoteError(msg, res.status, data);
    }

    return data as T;
  }

  // ── Chat ────────────────────────────────────────────────────────────────────────

  /**
   * Send a message to the AI and receive a complete response.
   * Uses the non-streaming endpoint — best for scripting and automation.
   */
  async chat(message: string, options: ChatOptions = {}): Promise<ChatResult> {
    return this.request<ChatResult>("POST", "/chat", {
      message,
      cwd:   options.cwd,
      model: options.model,
      tools: options.tools,
    });
  }

  // ── Sessions ─────────────────────────────────────────────────────────────────────────

  /** List all chat sessions on the server. */
  async listSessions(): Promise<SessionSummary[]> {
    return this.request<SessionSummary[]>("GET", "/sessions");
  }

  /** Get the full message history of a session. */
  async getSessionMessages(sessionId: string): Promise<{ sessionId: string; history: Message[] }> {
    return this.request("GET", `/sessions/${encodeURIComponent(sessionId)}/messages`);
  }

  /** Delete a session. */
  async deleteSession(sessionId: string): Promise<{ ok: boolean }> {
    return this.request("DELETE", `/sessions/${encodeURIComponent(sessionId)}`);
  }

  /** Mint a shareable read-only link for a session. */
  async shareSession(sessionId: string): Promise<ShareResult> {
    return this.request("POST", `/sessions/${encodeURIComponent(sessionId)}/share`);
  }

  // ── Search ──────────────────────────────────────────────────────────────────────────

  /** Full-text search across all session histories. */
  async search(query: string, limit = 20): Promise<{ q: string; results: SearchResult[] }> {
    return this.request("GET", "/search", undefined, { q: query, limit });
  }

  // ── Usage & billing ──────────────────────────────────────────────────────────────────────

  /** Get current month usage and remaining quota. */
  async getUsage(): Promise<UsageSummary> {
    return this.request<UsageSummary>("GET", "/usage");
  }

  // ── Health ─────────────────────────────────────────────────────────────────────────────

  /** Check server liveness. Does not require authentication. */
  async health(): Promise<{ status: string; version: string }> {
    const res = await fetch(`${this.baseUrl}/health`, {
      headers: { "User-Agent": "@anote-ai/sdk/1.0.0" },
    });
    return res.json();
  }
}

// Default export for convenience
export default AnoteClient;
