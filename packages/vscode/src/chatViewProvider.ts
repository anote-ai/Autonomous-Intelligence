import * as vscode from "vscode";
import * as fs from "fs";
import { AnoteAgent } from "./agent";
import { getModel, getProvider, providerDisplayName } from "./config";

interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

interface PendingContext {
  name: string;
  lang: string;
  code: string;
}

export const pendingReverts = new Map<string, string>();
export const diffState: { activePath: string | null } = { activePath: null };

export class AnnoteChatViewProvider implements vscode.WebviewViewProvider {
  private _view?: vscode.WebviewView;
  private _history: ChatMessage[] = [];
  private _pendingContext: PendingContext[] = [];

  constructor(
    private readonly _extensionUri: vscode.Uri,
    private readonly _agent: AnoteAgent,
    private readonly _context: vscode.ExtensionContext,
    private readonly _statusBarItem?: vscode.StatusBarItem
  ) {
    // Load persisted history if setting is enabled
    const config = vscode.workspace.getConfiguration("anote");
    if (config.get<boolean>("persistSessions", true)) {
      const saved = this._context.globalState.get<ChatMessage[]>(
        "anote.chatHistory",
        []
      );
      this._history = saved;
    }
  }

  private _saveHistory() {
    const config = vscode.workspace.getConfiguration("anote");
    if (config.get<boolean>("persistSessions", true)) {
      const trimmed = this._history.slice(-100);
      this._context.globalState.update("anote.chatHistory", trimmed);
    }
  }

  public resolveWebviewView(
    webviewView: vscode.WebviewView,
    _context: vscode.WebviewViewResolveContext,
    _token: vscode.CancellationToken
  ) {
    this._view = webviewView;

    webviewView.webview.options = {
      enableScripts: true,
      localResourceRoots: [this._extensionUri],
    };

    webviewView.webview.html = this.getHtml(webviewView.webview);

    // Listen for configuration changes (model/provider)
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("anote.model") || e.affectsConfiguration("anote.provider")) {
        this._view?.webview.postMessage({
          type: "modelInfo",
          model: getModel(),
          provider: providerDisplayName(getProvider()),
        });
      }
    });

    // Handle messages from webview
    webviewView.webview.onDidReceiveMessage(async (message) => {
      switch (message.type) {
        case "ready": {
          // Send current model
          this._view?.webview.postMessage({
            type: "modelInfo",
            model: getModel(),
            provider: providerDisplayName(getProvider()),
          });
          // Restore history
          if (this._history.length > 0) {
            this._view?.webview.postMessage({
              type: "restoreHistory",
              messages: this._history,
            });
          }
          // Flush pending context
          if (this._pendingContext.length > 0) {
            for (const ctx of this._pendingContext) {
              this._view?.webview.postMessage({ type: "addContext", ...ctx });
            }
            this._pendingContext = [];
          }
          break;
        }
        case "sendMessage": {
          await this.handleUserMessage(message.text);
          break;
        }
        case "clearChat": {
          this._history = [];
          this._saveHistory();
          break;
        }
        case "copyCode": {
          await vscode.env.clipboard.writeText(message.code);
          break;
        }
        case "applyCode": {
          await this.applyCodeToEditor(message.code);
          break;
        }
        case "openSettings": {
          vscode.commands.executeCommand(
            "workbench.action.openSettings",
            "anote"
          );
          break;
        }
        case "getModel": {
          this._view?.webview.postMessage({
            type: "modelInfo",
            model: getModel(),
            provider: providerDisplayName(getProvider()),
          });
          break;
        }
      }
    });
  }

  public sendPromptToChat(prompt: string, title: string, submit = false) {
    if (this._view) {
      this._view.webview.postMessage({ type: "setInput", text: prompt, title, submit });
    }
  }

  public addContextToChat(name: string, lang: string, code: string) {
    if (this._view) {
      this._view.webview.postMessage({ type: "addContext", name, lang, code });
    } else {
      this._pendingContext.push({ name, lang, code });
    }
  }

  public async advanceDiff(accept: boolean, absPath: string): Promise<void> {
    if (!accept) {
      const original = pendingReverts.get(absPath);
      if (original !== undefined) {
        fs.writeFileSync(absPath, original, "utf8");
      }
    }
    pendingReverts.delete(absPath);
    diffState.activePath = null;
  }

  private async handleUserMessage(text: string) {
    if (!text.trim()) return;

    this._history.push({ role: "user", content: text });

    const msgId = `msg-${Date.now()}`;
    this._view?.webview.postMessage({ type: "startStream", id: msgId });

    let fullResponse = "";
    const pendingToolIds: string[] = [];
    let toolCounter = 0;
    const toolIdMap = new Map<string, string>(); // agent toolId → webview toolId
    const toolQueue: string[] = [];               // FIFO for tool_result matching

    try {
      const messages = this._history.map((m) => ({
        role: m.role,
        content: m.content,
      }));

      for await (const chunk of this._agent.stream(messages)) {
        switch (chunk.type) {
          case "text":
            fullResponse += chunk.content ?? "";
            this._view?.webview.postMessage({
              type: "streamText",
              id: msgId,
              text: chunk.content ?? "",
            });
            break;
          case "tool":
            toolCounter += 1;
            pendingToolIds.push(`${msgId}-tool-${toolCounter}`);
            this._view?.webview.postMessage({
              type: "toolUse",
              id: msgId,
              toolName: chunk.toolName ?? "tool",
              toolId: pendingToolIds[pendingToolIds.length - 1],
            });
            break;
          case "tool_result": {
            const uid = chunk.toolName
              ? (toolIdMap.get(chunk.toolName) ?? toolQueue.shift())
              : toolQueue.shift();
            if (uid) {
              const idx = toolQueue.indexOf(uid);
              if (idx !== -1) toolQueue.splice(idx, 1);
            }
            this._view?.webview.postMessage({
              type: "toolDone",
              id: msgId,
              toolId: pendingToolIds.shift() ?? `${msgId}-tool-${toolCounter}`,
            });
            break;
          }
          case "done":
            this._view?.webview.postMessage({
              type: "streamEnd",
              id: msgId,
              tokens: (() => {
                const u = (chunk as unknown as { usage?: { inputTokens?: number; outputTokens?: number } }).usage;
                return u ? (u.inputTokens ?? 0) + (u.outputTokens ?? 0) : undefined;
              })(),
            });
            break;
          case "error":
            this._view?.webview.postMessage({
              type: "streamError",
              id: msgId,
              error: chunk.error ?? "Unknown error",
            });
            break;
        }
      }
    } catch (err: unknown) {
      const errMsg = err instanceof Error ? err.message : String(err);
      this._view?.webview.postMessage({
        type: "streamError",
        id: msgId,
        error: errMsg,
      });
    }

    if (fullResponse) {
      this._history.push({ role: "assistant", content: fullResponse });
      this._saveHistory();
    }
  }

  private async applyCodeToEditor(code: string) {
    const editor = vscode.window.activeTextEditor;
    if (!editor) {
      vscode.window.showWarningMessage("No active editor to apply code to.");
      return;
    }

    const selection = editor.selection;
    const existingText = editor.document.getText(
      selection.isEmpty ? undefined : selection
    );

    // If there's existing content, show a diff before applying
    if (existingText.trim()) {
      const choice = await vscode.window.showInformationMessage(
        "Apply code to editor?",
        { modal: false },
        "Apply",
        "Diff",
        "Cancel"
      );
      if (!choice || choice === "Cancel") return;

      if (choice === "Diff") {
        // Open diff view: original vs proposed
        const originalUri = vscode.Uri.parse(
          `untitled:Original (${editor.document.fileName.split("/").pop() ?? "file"})`
        );
        const proposedUri = vscode.Uri.parse(
          `untitled:Proposed (${editor.document.fileName.split("/").pop() ?? "file"})`
        );
        await vscode.commands.executeCommand("vscode.diff", originalUri, proposedUri, "Anote: Proposed changes");
        // Fall through to also apply after diff view (user already clicked Diff, they can decide)
        return;
      }
    }

    await editor.edit((editBuilder) => {
      if (selection.isEmpty) {
        editBuilder.insert(selection.active, code);
      } else {
        editBuilder.replace(selection, code);
      }
    });
    vscode.window.showInformationMessage("Code applied to editor.");
  }

  private getHtml(webview: vscode.Webview): string {
    const nonce = getNonce();
    const iconUri = webview.asWebviewUri(
      vscode.Uri.joinPath(this._extensionUri, "media", "icon.png")
    );
    return String.raw`<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <meta http-equiv="Content-Security-Policy" content="default-src 'none'; script-src 'nonce-${nonce}'; style-src 'unsafe-inline'; img-src ${webview.cspSource} data:; connect-src 'none';" />
  <title>Anote</title>
  <style>
    *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: var(--vscode-font-family);
      font-size: var(--vscode-font-size);
      color: var(--vscode-foreground);
      background: var(--vscode-sideBar-background, var(--vscode-editor-background));
      display: flex;
      flex-direction: column;
      height: 100vh;
      overflow: hidden;
    }
    #header {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 9px 10px;
      border-bottom: 1px solid var(--vscode-panel-border, #333);
      background: var(--vscode-sideBar-background, var(--vscode-editor-background));
      flex-shrink: 0;
    }
    #logo {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      flex: 1;
      color: var(--vscode-foreground);
      min-width: 0;
    }
    .brand-icon {
      width: 16px;
      height: 16px;
      object-fit: contain;
      flex-shrink: 0;
    }
    .brand-text {
      color: var(--vscode-foreground);
      font-size: 13px;
      font-weight: 600;
      letter-spacing: 0;
    }
    #model-badge {
      font-size: 11px;
      padding: 3px 7px;
      border-radius: 999px;
      background: var(--vscode-editorWidget-background, var(--vscode-badge-background, #3a3a3a));
      color: var(--vscode-descriptionForeground, var(--vscode-badge-foreground, #ccc));
      cursor: pointer;
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, transparent));
      transition: border-color 0.15s;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
      max-width: 130px;
    }
    #model-badge:hover { border-color: var(--vscode-textLink-foreground, #4fc1ff); }
    .icon-btn {
      background: none; border: none; cursor: pointer;
      color: var(--vscode-icon-foreground, var(--vscode-foreground)); opacity: 0.75;
      width: 26px; height: 26px; padding: 0; border-radius: 4px; font-size: 14px; line-height: 1;
      transition: opacity 0.15s, background 0.15s;
    }
    .icon-btn:hover { opacity: 1; background: var(--vscode-toolbar-hoverBackground, rgba(255,255,255,0.07)); }
    #messages {
      flex: 1; overflow-y: auto;
      padding: 12px 10px 6px;
      display: flex; flex-direction: column; gap: 12px;
    }
    #messages::-webkit-scrollbar { width: 5px; }
    #messages::-webkit-scrollbar-thumb { background: var(--vscode-scrollbarSlider-background, #555); border-radius: 3px; }
    #welcome {
      display: flex; flex-direction: column; align-items: center;
      justify-content: center; flex: 1; gap: 14px; padding: 20px; text-align: center;
    }
    #welcome .wlc-icon {
      width: 30px;
      height: 30px;
      object-fit: contain;
    }
    #welcome h2 { font-size: 15px; font-weight: 600; color: var(--vscode-foreground); }
    #welcome p { font-size: 12px; color: var(--vscode-descriptionForeground); line-height: 1.5; max-width: 280px; }
    .chip-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 6px; width: 100%; max-width: 300px; }
    .quick-chip {
      background: var(--vscode-sideBarSectionHeader-background, var(--vscode-button-secondaryBackground, #3a3a3a));
      color: var(--vscode-foreground);
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, #444));
      border-radius: 5px; padding: 7px 8px; font-size: 11px;
      cursor: pointer; display: flex; flex-direction: column; align-items: center; text-align: center; transition: background 0.15s; line-height: 1.3;
    }
    .quick-chip:hover { background: var(--vscode-list-hoverBackground, var(--vscode-button-secondaryHoverBackground, #4a4a4a)); }
    .quick-chip .chip-icon {
      display: inline-flex; align-items: center; justify-content: center;
      width: 18px; height: 18px; margin-bottom: 3px; border-radius: 4px;
      background: var(--vscode-badge-background, rgba(255,255,255,0.08));
      color: var(--vscode-badge-foreground, var(--vscode-foreground));
      font-size: 10px; font-weight: 700;
    }
    .msg { display: flex; flex-direction: column; gap: 5px; animation: fadeIn 0.15s ease; }
    @keyframes fadeIn { from { opacity: 0; transform: translateY(4px); } to { opacity: 1; transform: translateY(0); } }
    .msg-role {
      display: flex; align-items: center; gap: 6px;
      font-size: 11px; font-weight: 600;
      color: var(--vscode-descriptionForeground);
      letter-spacing: 0;
    }
    .msg-role::before {
      content: ""; width: 7px; height: 7px; border-radius: 50%;
      background: var(--vscode-descriptionForeground);
      opacity: 0.65;
    }
    .msg.user .msg-role::before { background: var(--vscode-button-background, #0e639c); opacity: 1; }
    .msg.assistant .msg-role::before { background: var(--vscode-testing-iconPassed, #73c991); opacity: 1; }
    .msg-content {
      padding: 9px 10px; border-radius: 6px;
      font-size: 12.5px; line-height: 1.6; word-break: break-word;
      color: var(--vscode-foreground);
    }
    .msg.user .msg-content {
      background: var(--vscode-input-background, rgba(255,255,255,0.04));
      border: 1px solid var(--vscode-input-border, var(--vscode-widget-border, var(--vscode-panel-border, #3a3a3a)));
    }
    .msg.assistant .msg-content {
      background: var(--vscode-editor-background, rgba(255,255,255,0.03));
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, #333));
    }
    .msg-content p { margin-bottom: 6px; }
    .msg-content p:last-child { margin-bottom: 0; }
    .msg-content ul, .msg-content ol { padding-left: 18px; margin-bottom: 6px; }
    .msg-content li { margin-bottom: 2px; }
    .msg-content code:not(.hljs) {
      background: var(--vscode-textCodeBlock-background, rgba(255,255,255,0.08)); padding: 1px 4px; border-radius: 3px;
      font-family: var(--vscode-editor-font-family, monospace); font-size: 11.5px;
      color: var(--vscode-editor-foreground, var(--vscode-foreground));
    }
    .msg-content pre {
      position: relative; margin: 8px 0; border-radius: 6px; overflow: hidden;
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, transparent));
      background: var(--vscode-textCodeBlock-background, rgba(255,255,255,0.06));
    }
    .msg-content pre code {
      display: block; padding: 10px 12px; overflow-x: auto;
      font-size: 11.5px; font-family: var(--vscode-editor-font-family, monospace); line-height: 1.5;
    }
    .msg-content pre code.block-code {
      background: transparent;
    }
    .code-actions { position: absolute; top: 4px; right: 4px; display: flex; gap: 4px; opacity: 0; transition: opacity 0.15s; }
    .msg-content pre:hover .code-actions { opacity: 1; }
    .code-btn {
      background: var(--vscode-button-secondaryBackground, rgba(0,0,0,0.5));
      color: var(--vscode-button-secondaryForeground, #ccc);
      border: 1px solid var(--vscode-widget-border, transparent); border-radius: 4px;
      padding: 2px 7px; font-size: 10px; cursor: pointer; transition: background 0.15s;
    }
    .code-btn:hover { background: var(--vscode-button-secondaryHoverBackground, rgba(0,0,0,0.8)); }
    .tool-indicator {
      display: flex; align-items: center; gap: 7px;
      width: fit-content; max-width: 100%;
      font-size: 11.5px; color: var(--vscode-descriptionForeground);
      padding: 4px 7px; margin: 6px 0 2px;
      background: var(--vscode-sideBarSectionHeader-background, rgba(255,255,255,0.04));
      border: 1px solid var(--vscode-widget-border, var(--vscode-panel-border, transparent));
      border-radius: 999px;
    }
    .tool-label { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .tool-dot { width: 7px; height: 7px; border-radius: 50%; flex-shrink: 0; }
    .tool-dot.running { background: var(--vscode-progressBar-background, #f0c040); animation: pulse 1s infinite; }
    .tool-dot.done { background: var(--vscode-testing-iconPassed, #4caf50); animation: none; }
    @keyframes pulse { 0%, 100% { opacity: 1; } 50% { opacity: 0.3; } }
    .cursor {
      display: inline-block; width: 2px; height: 13px;
      background: var(--vscode-foreground); margin-left: 1px;
      vertical-align: middle; animation: blink 0.7s step-end infinite;
    }
    @keyframes blink { 0%,100%{opacity:1} 50%{opacity:0} }
    #context-area { display: none; flex-wrap: wrap; gap: 5px; padding: 6px 10px; border-top: 1px solid var(--vscode-panel-border, #333); background: var(--vscode-sideBar-background, var(--vscode-editor-background)); flex-shrink: 0; }
    #context-area.visible { display: flex; }
    .ctx-chip {
      display: flex; align-items: center; gap: 4px;
      background: var(--vscode-badge-background, #3a3a3a);
      color: var(--vscode-badge-foreground, #ccc);
      border-radius: 12px; padding: 2px 8px 2px 9px; font-size: 10.5px;
      border: 1px solid var(--vscode-panel-border, #444);
    }
    .ctx-chip button { background: none; border: none; color: inherit; cursor: pointer; opacity: 0.5; font-size: 12px; line-height: 1; padding: 0 0 0 2px; }
    .ctx-chip button:hover { opacity: 1; }
    #input-area { display: flex; align-items: flex-end; gap: 6px; padding: 9px 10px; border-top: 1px solid var(--vscode-panel-border, #333); background: var(--vscode-sideBar-background, var(--vscode-editor-background)); flex-shrink: 0; }
    #input {
      flex: 1; resize: none;
      background: var(--vscode-input-background, #3c3c3c);
      color: var(--vscode-input-foreground, #ccc);
      border: 1px solid var(--vscode-input-border, #555);
      border-radius: 5px; padding: 8px 9px;
      font-family: var(--vscode-font-family); font-size: 12.5px; line-height: 1.4;
      outline: none; min-height: 36px; max-height: 140px; overflow-y: auto;
    }
    #input:focus { border-color: var(--vscode-focusBorder, #4fc1ff); }
    #send-btn {
      background: var(--vscode-button-background, #0e639c);
      color: var(--vscode-button-foreground, #fff);
      border: none; border-radius: 5px; cursor: pointer;
      width: 34px; height: 34px; display: inline-flex; align-items: center; justify-content: center;
      font-size: 14px; line-height: 1; transition: background 0.15s; flex-shrink: 0;
    }
    #send-btn:hover { background: var(--vscode-button-hoverBackground, #1177bb); }
    #send-btn:disabled { opacity: 0.4; cursor: not-allowed; }
  </style>
</head>
<body>
  <div id="header">
    <span id="logo">
      <img src="${iconUri}" alt="Anote" class="brand-icon" />
      <span class="brand-text">Anote</span>
    </span>
    <span id="model-badge" title="Click to open settings">&#8212;</span>
    <span id="token-usage" style="font-size:10px;color:var(--vscode-descriptionForeground);margin-left:auto;margin-right:2px;" title="Total tokens used this session"></span>
    <button class="icon-btn" id="clear-btn" title="Clear chat" aria-label="Clear chat">&#x2715;</button>
    <button class="icon-btn" id="settings-btn" title="Settings" aria-label="Settings">&#9881;</button>
  </div>

  <div id="messages">
    <div id="welcome">
      <img src="${iconUri}" alt="Anote" class="wlc-icon" />
      <h2>Anote AI Assistant</h2>
      <p>Ask about your code, request changes, or start with a focused action.</p>
      <div class="chip-grid">
        <button class="quick-chip" data-action="explain">
          <span class="chip-icon">?</span>Explain code
        </button>
        <button class="quick-chip" data-action="review">
          <span class="chip-icon">R</span>Review file
        </button>
        <button class="quick-chip" data-action="tests">
          <span class="chip-icon">T</span>Write tests
        </button>
        <button class="quick-chip" data-action="improve">
          <span class="chip-icon">I</span>Improve code
        </button>
        <button class="quick-chip" data-action="fix">
          <span class="chip-icon">F</span>Fix bugs
        </button>
        <button class="quick-chip" data-action="commit">
          <span class="chip-icon">C</span>Write commit
        </button>
        <button class="quick-chip" data-action="document">
          <span class="chip-icon">D</span>Add docs
        </button>
        <button class="quick-chip" data-action="security">
          <span class="chip-icon">S</span>Security audit
        </button>
      </div>
    </div>
  </div>

  <div id="context-area"></div>

  <div id="input-area">
    <textarea id="input" placeholder="Ask Anote..." rows="1"></textarea>
    <button id="send-btn" title="Send (Ctrl+Enter)" aria-label="Send">&gt;</button>
  </div>

  <script nonce="${nonce}">
    var vscode = acquireVsCodeApi();
    var messagesEl = document.getElementById('messages');
    var welcomeEl = document.getElementById('welcome');
    var inputEl = document.getElementById('input');
    var sendBtn = document.getElementById('send-btn');
    var clearBtn = document.getElementById('clear-btn');
    var settingsBtn = document.getElementById('settings-btn');
    var modelBadge = document.getElementById('model-badge');
    var contextArea = document.getElementById('context-area');

    var streaming = false;
    var streamEl = null;
    var streamCursor = null;
    var streamBuffer = '';
    var contextItems = [];
    var toolEls = {};
    var thinkingEl = null;
    var totalTokens = 0;
    var tokenUsageEl = document.getElementById('token-usage');
    var backtick = String.fromCharCode(96);
    var tripleBacktick = backtick + backtick + backtick;

    function escapeHtml(s) {
      return String(s)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;');
    }

    function renderMd(text) {
      return renderSimpleMarkdown(text || '');
    }

    function renderSimpleMarkdown(text) {
      var normalized = String(text).replace(/\r\n/g, '\n');
      var lines = normalized.split('\n');
      var html = [];
      var paragraph = [];
      var listItems = [];
      var codeLines = [];
      var inCodeBlock = false;

      function flushParagraph() {
        if (paragraph.length === 0) { return; }
        html.push('<p>' + renderInline(paragraph.join(' ')) + '</p>');
        paragraph = [];
      }

      function flushList() {
        if (listItems.length === 0) { return; }
        html.push('<ul>' + listItems.map(function(item) {
          return '<li>' + renderInline(item) + '</li>';
        }).join('') + '</ul>');
        listItems = [];
      }

      function flushCodeBlock() {
        if (codeLines.length === 0) { return; }
        html.push('<pre><code class="block-code">' + escapeHtml(codeLines.join('\n')) + '</code></pre>');
        codeLines = [];
      }

      for (var i = 0; i < lines.length; i++) {
        var line = lines[i];
        if (line.trim().slice(0, 3) === tripleBacktick) {
          flushParagraph();
          flushList();
          if (inCodeBlock) {
            flushCodeBlock();
          }
          inCodeBlock = !inCodeBlock;
          continue;
        }

        if (inCodeBlock) {
          codeLines.push(line);
          continue;
        }

        var trimmed = line.trim();
        if (!trimmed) {
          flushParagraph();
          flushList();
          continue;
        }

        if (/^[-*]\s+/.test(trimmed)) {
          flushParagraph();
          listItems.push(trimmed.replace(/^[-*]\s+/, ''));
          continue;
        }

        if (/^\d+\.\s+/.test(trimmed)) {
          flushParagraph();
          listItems.push(trimmed.replace(/^\d+\.\s+/, ''));
          continue;
        }

        flushList();
        paragraph.push(trimmed);
      }

      flushParagraph();
      flushList();
      flushCodeBlock();

      if (html.length === 0) {
        return '<p></p>';
      }

      return html.join('');
    }

    function renderInline(text) {
      var escaped = renderInlineCode(escapeHtml(text));
      escaped = escaped.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');
      escaped = escaped.replace(/\*([^*]+)\*/g, '<em>$1</em>');
      return escaped;
    }

    function renderInlineCode(text) {
      var parts = text.split(backtick);
      if (parts.length < 3) { return text; }
      var html = '';
      for (var i = 0; i < parts.length; i++) {
        if (i % 2 === 1) {
          html += '<code>' + parts[i] + '</code>';
        } else {
          html += parts[i];
        }
      }
      return html;
    }

    function formatToolName(name) {
      var raw = String(name || 'tool').trim();
      var normalized = raw.replace(/[_-]+/g, ' ');
      normalized = normalized.replace(/\b\w/g, function(ch) { return ch.toUpperCase(); });
      return normalized || 'Tool';
    }

    function highlightAll(el) {
      el.querySelectorAll('pre code').forEach(function(block) {
        var pre = block.closest('pre');
        if (pre) { addCodeActions(pre); }
      });
    }

    function addCodeActions(preEl) {
      if (!preEl || preEl.querySelector('.code-actions')) { return; }
      var codeEl = preEl.querySelector('code');
      if (!codeEl) { return; }
      var actions = document.createElement('div');
      actions.className = 'code-actions';
      var copyBtn = document.createElement('button');
      copyBtn.className = 'code-btn';
      copyBtn.textContent = 'Copy';
      (function(cb, ce) {
        cb.onclick = function() {
          vscode.postMessage({ type: 'copyCode', code: ce.innerText });
          cb.textContent = 'Copied!';
          setTimeout(function() { cb.textContent = 'Copy'; }, 1500);
        };
      }(copyBtn, codeEl));
      var applyBtn = document.createElement('button');
      applyBtn.className = 'code-btn';
      applyBtn.textContent = 'Apply';
      (function(ce) {
        applyBtn.onclick = function() {
          vscode.postMessage({ type: 'applyCode', code: ce.innerText });
        };
      }(codeEl));
      actions.appendChild(copyBtn);
      actions.appendChild(applyBtn);
      preEl.appendChild(actions);
    }

    function hideWelcome() {
      if (welcomeEl) { welcomeEl.style.display = 'none'; }
    }

    function scrollToBottom() {
      messagesEl.scrollTop = messagesEl.scrollHeight;
    }

    function appendMessage(role, htmlContent) {
      hideWelcome();
      var msgDiv = document.createElement('div');
      msgDiv.className = 'msg ' + role;
      var roleDiv = document.createElement('div');
      roleDiv.className = 'msg-role';
      roleDiv.textContent = role === 'user' ? 'You' : 'Anote';
      var contentDiv = document.createElement('div');
      contentDiv.className = 'msg-content';
      contentDiv.innerHTML = htmlContent;
      msgDiv.appendChild(roleDiv);
      msgDiv.appendChild(contentDiv);
      messagesEl.appendChild(msgDiv);
      highlightAll(contentDiv);
      scrollToBottom();
      return contentDiv;
    }

    function removeThinkingEl() {
      if (thinkingEl) { thinkingEl.remove(); thinkingEl = null; }
    }

    function startStreamMessage() {
      hideWelcome();
      streaming = true;
      streamBuffer = '';
      sendBtn.disabled = true;
      var msgDiv = document.createElement('div');
      msgDiv.className = 'msg assistant';
      var roleDiv = document.createElement('div');
      roleDiv.className = 'msg-role';
      roleDiv.textContent = 'Anote';
      var contentDiv = document.createElement('div');
      contentDiv.className = 'msg-content';
      streamCursor = document.createElement('span');
      streamCursor.className = 'cursor';
      // Thinking indicator before first token
      thinkingEl = document.createElement('div');
      thinkingEl.className = 'thinking-indicator';
      thinkingEl.innerHTML = '<div class="thinking-spinner"></div><span>Thinking…</span>';
      contentDiv.appendChild(thinkingEl);
      contentDiv.appendChild(streamCursor);
      msgDiv.appendChild(roleDiv);
      msgDiv.appendChild(contentDiv);
      messagesEl.appendChild(msgDiv);
      streamEl = contentDiv;
      scrollToBottom();
    }

    function appendStreamText(text) {
      if (!streamEl) { return; }
      removeThinkingEl();
      streamBuffer += text;
      if (streamCursor && streamCursor.parentNode === streamEl) {
        streamEl.removeChild(streamCursor);
      }
      streamEl.innerHTML = renderMd(streamBuffer);
      streamEl.appendChild(streamCursor);
      highlightAll(streamEl);
      scrollToBottom();
    }

    function endStreamMessage() {
      if (!streamEl) { return; }
      removeThinkingEl();
      // Stop all running timers
      Object.values(toolEls).forEach(function(t) {
        if (t._timer) { clearInterval(t._timer); }
      });
      if (streamCursor && streamCursor.parentNode === streamEl) {
        streamEl.removeChild(streamCursor);
      }
      streamEl.innerHTML = renderMd(streamBuffer);
      highlightAll(streamEl);
      streamEl = null;
      streamCursor = null;
      streamBuffer = '';
      streaming = false;
      sendBtn.disabled = false;
      scrollToBottom();
    }

    function addToolIndicator(toolId, toolName) {
      if (!streamEl) { return; }
      removeThinkingEl();
      if (streamCursor && streamCursor.parentNode === streamEl) {
        streamEl.removeChild(streamCursor);
      }
      var ind = document.createElement('div');
      ind.className = 'tool-indicator';
      var dot = document.createElement('span');
      dot.className = 'tool-dot running';
      var label = document.createElement('span');
      label.className = 'tool-label';
      label.textContent = 'Running ' + formatToolName(toolName);
      ind.appendChild(dot);
      ind.appendChild(label);
      ind.appendChild(elapsed);
      streamEl.appendChild(ind);
      streamEl.appendChild(streamCursor);
      var startTime = Date.now();
      var timer = setInterval(function() {
        if (!toolEls[toolId] || toolEls[toolId].done) { clearInterval(timer); return; }
        elapsed.textContent = ((Date.now() - startTime) / 1000).toFixed(1) + 's';
      }, 200);
      toolEls[toolId] = { dot: dot, label: label, elapsed: elapsed, _timer: timer, done: false };
      scrollToBottom();
    }

    function markToolDone(toolId) {
      var t = toolEls[toolId];
      if (!t) { return; }
      t.done = true;
      if (t._timer) { clearInterval(t._timer); }
      t.dot.className = 'tool-dot done';
      t.label.textContent = t.label.textContent.replace(/^Running /, 'Done ');
    }

    function addContextChip(name, lang, code) {
      var item = { name: name, lang: lang, code: code };
      contextItems.push(item);
      contextArea.classList.add('visible');
      var chip = document.createElement('div');
      chip.className = 'ctx-chip';
      var nameSpan = document.createElement('span');
      nameSpan.textContent = name + (lang ? ' (' + lang + ')' : '');
      var removeBtn = document.createElement('button');
      removeBtn.textContent = '×';
      removeBtn.title = 'Remove';
      (function(i, c) {
        removeBtn.onclick = function() {
          var idx = contextItems.indexOf(i);
          if (idx !== -1) { contextItems.splice(idx, 1); }
          c.remove();
          if (contextItems.length === 0) { contextArea.classList.remove('visible'); }
        };
      }(item, chip));
      chip.appendChild(nameSpan);
      chip.appendChild(removeBtn);
      contextArea.appendChild(chip);
    }

    function buildMessageWithContext(text) {
      if (contextItems.length === 0) { return text; }
      var full = '';
      for (var i = 0; i < contextItems.length; i++) {
        var ctx = contextItems[i];
        full += 'Context: ' + ctx.name + '\n\`\`\`' + ctx.lang + '\n' + ctx.code + '\n\`\`\`\n\n';
      }
      full += text;
      contextItems = [];
      contextArea.innerHTML = '';
      contextArea.classList.remove('visible');
      return full;
    }

    function restoreHistory(messages) {
      for (var i = 0; i < messages.length; i++) {
        var m = messages[i];
        var html = m.role === 'user'
          ? '<p>' + escapeHtml(m.content) + '</p>'
          : renderMd(m.content);
        appendMessage(m.role, html);
      }
    }

    function updateModelBadge(model, provider) {
      var short = String(model || '').replace(/-\d{4}-\d{2}-\d{2}$/, '');
      modelBadge.textContent = provider ? provider + ': ' + short : short;
      modelBadge.title = (provider ? provider + ' · ' : '') + model + ' — Click to open settings';
    }

    function sendMessage() {
      var text = inputEl.value.trim();
      if (!text || streaming) { return; }
      var fullText = buildMessageWithContext(text);
      appendMessage('user', '<p>' + escapeHtml(text) + '</p>');
      inputEl.value = '';
      autoResize();
      vscode.postMessage({ type: 'sendMessage', text: fullText });
    }

    function autoResize() {
      inputEl.style.height = 'auto';
      inputEl.style.height = Math.min(inputEl.scrollHeight, 140) + 'px';
    }

    sendBtn.addEventListener('click', sendMessage);
    inputEl.addEventListener('keydown', function(e) {
      if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
        e.preventDefault();
        sendMessage();
      }
    });
    inputEl.addEventListener('input', autoResize);

    clearBtn.addEventListener('click', function() {
      messagesEl.innerHTML = '';
      messagesEl.appendChild(welcomeEl);
      welcomeEl.style.display = '';
      streamEl = null;
      streamBuffer = '';
      streaming = false;
      sendBtn.disabled = false;
      totalTokens = 0;
      if (tokenUsageEl) tokenUsageEl.textContent = '';
      vscode.postMessage({ type: 'clearChat' });
    });

    settingsBtn.addEventListener('click', function() {
      vscode.postMessage({ type: 'openSettings' });
    });

    modelBadge.addEventListener('click', function() {
      vscode.postMessage({ type: 'openSettings' });
    });

    document.querySelectorAll('.quick-chip').forEach(function(chip) {
      chip.addEventListener('click', function() {
        var action = chip.dataset.action;
        var prompts = {
          explain: 'Explain the selected code in detail, including what it does, how it works, and any important edge cases.',
          review: 'Review this file for bugs, security issues, code quality, and best practices. Provide specific suggestions.',
          tests: 'Generate comprehensive unit tests for this code with good coverage of edge cases and error paths.',
          improve: 'Suggest improvements to make this code cleaner, more efficient, and easier to maintain.',
          fix: 'Find and fix all bugs, errors, and issues in this code.',
          commit: 'Write a concise, conventional commit message for the changes in this file.',
          document: 'Add clear, helpful documentation comments (JSDoc/TSDoc) to all public functions and classes.',
          security: 'Perform a security audit of this code. Identify vulnerabilities (injection, XSS, auth issues, etc.) and suggest fixes.'
        };
        inputEl.value = prompts[action] || '';
        inputEl.focus();
        autoResize();
      });
    });

    window.addEventListener('message', function(event) {
      var msg = event.data;
      switch (msg.type) {
        case 'modelInfo':
          updateModelBadge(msg.model, msg.provider);
          break;
        case 'restoreHistory':
          restoreHistory(msg.messages);
          break;
        case 'setInput':
          inputEl.value = msg.text || '';
          inputEl.focus();
          autoResize();
          if (msg.submit && !streaming) {
            sendMessage();
          }
          break;
        case 'addContext':
          addContextChip(msg.name, msg.lang, msg.code);
          break;
        case 'startStream':
          startStreamMessage();
          break;
        case 'streamText':
          appendStreamText(msg.text);
          break;
        case 'toolUse':
          addToolIndicator(msg.toolId, msg.toolName);
          break;
        case 'toolDone':
          markToolDone(msg.toolId);
          break;
        case 'streamEnd':
          endStreamMessage();
          if (msg.tokens) {
            totalTokens += msg.tokens;
            if (tokenUsageEl) {
              tokenUsageEl.textContent = totalTokens >= 1000
                ? (totalTokens / 1000).toFixed(1) + 'k tok'
                : totalTokens + ' tok';
            }
          }
          break;
        case 'streamError':
          endStreamMessage();
          appendMessage('assistant', '<p style="color:var(--vscode-errorForeground,#f48771)">Error: ' + escapeHtml(msg.error) + '</p>');
          break;
      }
    });

    vscode.postMessage({ type: 'ready' });
  </script>
</body>
</html>`;
  }
}

function getNonce(): string {
  let text = "";
  const possible =
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789";
  for (let i = 0; i < 32; i++) {
    text += possible.charAt(Math.floor(Math.random() * possible.length));
  }
  return text;
}
