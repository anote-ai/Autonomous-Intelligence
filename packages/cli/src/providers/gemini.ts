import { GoogleGenerativeAI, SchemaType, type Content, type FunctionCall, type Tool } from "@google/generative-ai";
import type { ProviderAdapter, Message, StreamOptions, StreamEvent } from "./types.js";
import { executeTool } from "./tools.js";

const GEMINI_TOOLS: Tool[] = [{
  functionDeclarations: [
    { name: "Read", description: "Read a file from the filesystem.", parameters: { type: SchemaType.OBJECT, properties: { file_path: { type: SchemaType.STRING, description: "File path to read" }, offset: { type: SchemaType.NUMBER }, limit: { type: SchemaType.NUMBER } }, required: ["file_path"] } },
    { name: "Write", description: "Write content to a file.", parameters: { type: SchemaType.OBJECT, properties: { file_path: { type: SchemaType.STRING }, content: { type: SchemaType.STRING } }, required: ["file_path", "content"] } },
    { name: "Edit", description: "Replace an exact string in a file.", parameters: { type: SchemaType.OBJECT, properties: { file_path: { type: SchemaType.STRING }, old_string: { type: SchemaType.STRING }, new_string: { type: SchemaType.STRING } }, required: ["file_path", "old_string", "new_string"] } },
    { name: "Bash", description: "Run a shell command.", parameters: { type: SchemaType.OBJECT, properties: { command: { type: SchemaType.STRING }, timeout: { type: SchemaType.NUMBER } }, required: ["command"] } },
    { name: "Glob", description: "Find files matching a glob pattern.", parameters: { type: SchemaType.OBJECT, properties: { pattern: { type: SchemaType.STRING }, cwd: { type: SchemaType.STRING } }, required: ["pattern"] } },
    { name: "Grep", description: "Search for a regex pattern in files.", parameters: { type: SchemaType.OBJECT, properties: { pattern: { type: SchemaType.STRING }, path: { type: SchemaType.STRING }, include: { type: SchemaType.STRING } }, required: ["pattern"] } },
  ],
}];

export class GeminiAdapter implements ProviderAdapter {
  async *stream(messages: Message[], options: StreamOptions): AsyncIterable<StreamEvent> {
    const { cwd, allowedTools, systemPrompt, maxTurns, model } = options;
    const apiKey = process.env["GEMINI_API_KEY"];
    if (!apiKey) { yield { type: "error", message: "GEMINI_API_KEY is not set" }; return; }

    const allowedGeminiTools: Tool[] = GEMINI_TOOLS.map((t) => {
      const base = t as { functionDeclarations?: Array<{ name: string }> };
      return { ...t, functionDeclarations: base.functionDeclarations?.filter((fd) => allowedTools.includes(fd.name)) } as Tool;
    });

    const genAI = new GoogleGenerativeAI(apiKey);
    const genModel = genAI.getGenerativeModel({ model, systemInstruction: systemPrompt, tools: allowedGeminiTools });
    const history: Content[] = messages.slice(0, -1).map((m) => ({ role: m.role === "user" ? "user" : "model", parts: [{ text: m.content }] }));
    const chat = genModel.startChat({ history });

    let fullAssistantText = "";
    let turn = 0;
    let latestMessage = messages[messages.length - 1]!.content;

    while (turn < maxTurns) {
      turn++;
      const streamResult = await chat.sendMessageStream(latestMessage);
      let currentText = "";
      const toolCalls: FunctionCall[] = [];

      for await (const chunk of streamResult.stream) {
        const candidate = chunk.candidates?.[0];
        if (!candidate) continue;
        for (const part of candidate.content?.parts ?? []) {
          if (part.text) { currentText += part.text; yield { type: "text", text: part.text }; }
          if (part.functionCall) toolCalls.push(part.functionCall);
        }
      }

      if (currentText) fullAssistantText = currentText;
      if (!toolCalls.length) { yield { type: "done", result: fullAssistantText, stop_reason: "end_turn" }; return; }

      const toolResultParts: Array<{ functionResponse: { name: string; response: { content: string } } }> = [];
      for (const tc of toolCalls) {
        const args = (tc.args ?? {}) as Record<string, unknown>;
        yield { type: "tool", tool: tc.name, input: args };
        const result = await executeTool(tc.name, args, cwd, allowedTools);
        yield { type: "tool_result", content: result.content };
        toolResultParts.push({ functionResponse: { name: tc.name, response: { content: result.content } } });
      }

      latestMessage = toolResultParts.map((p) => `Tool result for ${p.functionResponse.name}:\n${p.functionResponse.response.content}`).join("\n\n");
    }

    yield { type: "done", result: fullAssistantText, stop_reason: "max_turns" };
  }
}
