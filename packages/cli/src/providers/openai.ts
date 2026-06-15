// OpenAIAdapter — covers OpenAI GPT, Ollama, and any OpenAI-compatible endpoint.
// Runs a full agentic tool loop: call API → execute tools → loop until stop.

import OpenAI from "openai";
import type { ProviderAdapter, Message, StreamOptions, StreamEvent } from "./types.js";
import { TOOL_DEFINITIONS, executeTool } from "./tools.js";

function buildClient(model: string): OpenAI {
  if (model.startsWith("ollama/")) {
    return new OpenAI({
      apiKey: "ollama",
      baseURL: process.env["OLLAMA_BASE_URL"] ?? "http://localhost:11434/v1",
    });
  }
  if (model.startsWith("local/")) {
    return new OpenAI({
      apiKey: process.env["OPENAI_API_KEY"] ?? "local",
      baseURL: process.env["OPENAI_BASE_URL"] ?? "http://localhost:8080/v1",
    });
  }
  return new OpenAI({ apiKey: process.env["OPENAI_API_KEY"] });
}

function normaliseModel(model: string): string {
  if (model.startsWith("ollama/")) return model.slice("ollama/".length);
  if (model.startsWith("local/")) return model.slice("local/".length);
  return model;
}

export class OpenAIAdapter implements ProviderAdapter {
  async *stream(messages: Message[], options: StreamOptions): AsyncIterable<StreamEvent> {
    const { cwd, allowedTools, systemPrompt, maxTurns, model } = options;

    const client = buildClient(model);
    const apiModel = normaliseModel(model);

    const apiMessages: OpenAI.Chat.ChatCompletionMessageParam[] = [
      { role: "system", content: systemPrompt },
      ...messages.map((m) => ({ role: m.role as "user" | "assistant", content: m.content })),
    ];

    const tools = TOOL_DEFINITIONS.filter((t) => allowedTools.includes(t.function.name));

    let fullAssistantText = "";
    let turn = 0;

    while (turn < maxTurns) {
      turn++;

      const stream = await client.chat.completions.create({
        model: apiModel,
        messages: apiMessages,
        tools: tools.length ? tools : undefined,
        tool_choice: tools.length ? "auto" : undefined,
        stream: true,
      });

      let currentText = "";
      const pendingToolCalls: Record<number, { id: string; name: string; argsJson: string }> = {};

      for await (const chunk of stream) {
        const delta = chunk.choices[0]?.delta;
        if (!delta) continue;

        if (delta.content) {
          currentText += delta.content;
          yield { type: "text", text: delta.content };
        }

        if (delta.tool_calls) {
          for (const tc of delta.tool_calls) {
            const idx = tc.index;
            if (!pendingToolCalls[idx]) {
              pendingToolCalls[idx] = { id: tc.id ?? "", name: tc.function?.name ?? "", argsJson: "" };
            }
            if (tc.id) pendingToolCalls[idx]!.id = tc.id;
            if (tc.function?.name) pendingToolCalls[idx]!.name = tc.function.name;
            if (tc.function?.arguments) pendingToolCalls[idx]!.argsJson += tc.function.arguments;
          }
        }
      }

      const toolCalls = Object.values(pendingToolCalls);
      if (currentText) fullAssistantText = currentText;

      if (!toolCalls.length) {
        yield { type: "done", result: fullAssistantText, stop_reason: "end_turn" };
        return;
      }

      apiMessages.push({
        role: "assistant",
        content: currentText || null,
        tool_calls: toolCalls.map((tc) => ({
          id: tc.id,
          type: "function" as const,
          function: { name: tc.name, arguments: tc.argsJson },
        })),
      });

      for (const tc of toolCalls) {
        let args: Record<string, unknown> = {};
        try { args = JSON.parse(tc.argsJson) as Record<string, unknown>; } catch { /* invalid json */ }

        yield { type: "tool", tool: tc.name, input: args };

        const result = await executeTool(tc.name, args, cwd, allowedTools);
        yield { type: "tool_result", content: result.content };

        apiMessages.push({
          role: "tool",
          tool_call_id: tc.id,
          content: result.content,
        });
      }
    }

    yield { type: "done", result: fullAssistantText, stop_reason: "max_turns" };
  }
}
