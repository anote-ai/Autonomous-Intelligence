import * as vscode from "vscode";
import * as fs from "fs";
import * as path from "path";
import { AnnoteChatViewProvider, pendingReverts, diffState } from "./chatViewProvider";
import { AnoteAgent } from "./agent";
import {
  type AnoteProvider,
  getModel,
  getServerUrl,
  providerSamples,
} from "./config";
import { AnoteCodeLensProvider, type CodeLensAction } from "./codeLens";

let chatProvider: AnnoteChatViewProvider | undefined;

export function activate(context: vscode.ExtensionContext) {
  const agent = new AnoteAgent(context);

  // Status bar item — shows active tool during long agentic tasks
  const statusBarItem = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Left, 10);
  statusBarItem.name = "Anote";
  context.subscriptions.push(statusBarItem);

  // Register the chat webview provider (sidebar panel)
  chatProvider = new AnnoteChatViewProvider(context.extensionUri, agent, context, statusBarItem);
  context.subscriptions.push(
    vscode.window.registerWebviewViewProvider(
      "anote.chatView",
      chatProvider,
      { webviewOptions: { retainContextWhenHidden: true } }
    )
  );

  // ── CodeLens ─────────────────────────────
  const codeLensProvider = new AnoteCodeLensProvider();
  const codeLensLanguages = [
    "typescript", "typescriptreact", "javascript", "javascriptreact",
    "python", "rust", "go", "java", "c", "cpp", "csharp", "ruby", "php",
  ];
  context.subscriptions.push(
    vscode.languages.registerCodeLensProvider(
      codeLensLanguages.map((language) => ({ language })),
      codeLensProvider
    )
  );

  // Refresh CodeLens when the setting changes
  context.subscriptions.push(
    vscode.workspace.onDidChangeConfiguration((e) => {
      if (e.affectsConfiguration("anote.enableCodeLens")) codeLensProvider.refresh();
    })
  );

  // Single command handler for all CodeLens actions
  context.subscriptions.push(
    vscode.commands.registerCommand(
      "anote.codeLensAction",
      async (uri: vscode.Uri, range: vscode.Range, action: CodeLensAction) => {
        const editor = await vscode.window.showTextDocument(uri);
        editor.selection = new vscode.Selection(range.start, range.end);
        const commandMap: Record<CodeLensAction, string> = {
          explain: "anote.explainSelection",
          fix: "anote.fixSelection",
          generateTests: "anote.generateTests",
          refactor: "anote.refactorSelection",
        };
        vscode.commands.executeCommand(commandMap[action]);
      }
    )
  );

  // ── Commands ─────────────────────────────

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.openChat", () => {
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.setup", async () => {
      const providerPick = await vscode.window.showQuickPick(
        [
          { label: "Anthropic", value: "anthropic" as AnoteProvider },
          { label: "OpenAI via Anote server", value: "openai" as AnoteProvider },
          { label: "Gemini via Anote server", value: "gemini" as AnoteProvider },
          { label: "Llama via Anote server", value: "llama" as AnoteProvider },
          { label: "xAI via Anote server", value: "xai" as AnoteProvider },
          { label: "Custom provider via Anote server", value: "custom" as AnoteProvider },
        ],
        {
          title: "Choose an Anote provider",
          placeHolder: "Direct VS Code runtime currently supports Anthropic; other providers use an Anote server.",
        }
      );
      if (!providerPick) return;

      const config = vscode.workspace.getConfiguration("anote");
      await config.update("provider", providerPick.value, vscode.ConfigurationTarget.Global);

      const isAnthropicDirect = providerPick.value === "anthropic";
      if (isAnthropicDirect) {
        const apiKey = await vscode.window.showInputBox({
          title: "Set your Anthropic API key",
          prompt: "Stored in VS Code settings for Anote.",
          ignoreFocusOut: true,
          password: true,
        });
        if (apiKey !== undefined) {
          await config.update("apiKey", apiKey, vscode.ConfigurationTarget.Global);
        }
      } else {
        const serverUrl = await vscode.window.showInputBox({
          title: "Set your Anote server URL",
          prompt: "Example: https://anote.yourcompany.com or http://localhost:3000",
          value: getServerUrl(),
          ignoreFocusOut: true,
        });
        if (serverUrl !== undefined) {
          await config.update("serverUrl", serverUrl.trim(), vscode.ConfigurationTarget.Global);
        }
      }

      const model = await vscode.window.showInputBox({
        title: "Choose a default model",
        prompt: `Examples: ${providerSamples(providerPick.value).join(", ")}`,
        value: getModel(),
        ignoreFocusOut: true,
      });
      if (model !== undefined && model.trim()) {
        await config.update("model", model.trim(), vscode.ConfigurationTarget.Global);
      }

      vscode.commands.executeCommand("anote.chatView.focus");
      vscode.window.showInformationMessage("Anote is ready.");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.explainSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.selection;
      const text = editor.document.getText(selection.isEmpty ? undefined : selection);
      const lang = editor.document.languageId;
      const fileName = editor.document.fileName.split("/").pop() ?? "file";
      chatProvider?.sendPromptToChat(`Explain the following ${lang} code from ${fileName}:\n\`\`\`${lang}\n${text}\n\`\`\``, `Explain code in ${fileName}`, true);
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.fixSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.selection;
      const text = editor.document.getText(selection.isEmpty ? undefined : selection);
      const lang = editor.document.languageId;
      const fileName = editor.document.fileName.split("/").pop() ?? "file";
      chatProvider?.sendPromptToChat(`Fix any bugs or issues in this ${lang} code from ${fileName}:\n\`\`\`${lang}\n${text}\n\`\`\`\n\nProvide the corrected code with explanation of what was wrong.`, `Fix code in ${fileName}`, true);
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.reviewFile", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const filePath = editor.document.fileName;
      const fileName = filePath.split("/").pop() ?? "file";
      const content = editor.document.getText();
      const lang = editor.document.languageId;
      chatProvider?.sendPromptToChat(`Review this ${lang} file (${fileName}) for bugs, security issues, performance problems, and code quality:\n\`\`\`${lang}\n${content}\n\`\`\`\n\nProvide specific, actionable feedback organized by severity.`, `Review ${fileName}`, true);
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.generateTests", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const filePath = editor.document.fileName;
      const fileName = filePath.split("/").pop() ?? "file";
      const content = editor.document.getText();
      const lang = editor.document.languageId;
      chatProvider?.sendPromptToChat(`Generate comprehensive unit tests for this ${lang} file (${fileName}):\n\`\`\`${lang}\n${content}\n\`\`\`\n\nInclude tests for: happy paths, edge cases, error handling, and boundary conditions.`, `Generate tests for ${fileName}`, true);
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.refactorSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.selection;
      const text = editor.document.getText(selection.isEmpty ? undefined : selection);
      const lang = editor.document.languageId;
      const fileName = editor.document.fileName.split("/").pop() ?? "file";
      chatProvider?.sendPromptToChat(`Refactor this ${lang} code from ${fileName} to improve readability, maintainability, and performance:\n\`\`\`${lang}\n${text}\n\`\`\`\n\nExplain each significant change.`, `Refactor code in ${fileName}`, true);
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.askAboutSelection", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.selection;
      const text = editor.document.getText(selection.isEmpty ? undefined : selection);
      const lang = editor.document.languageId;
      const fileName = editor.document.fileName.split("/").pop() ?? "file";
      const question = await vscode.window.showInputBox({
        prompt: "What would you like to know about the selected code?",
        placeHolder: "e.g., How does this work? What does this function do?",
      });
      if (!question) return;
      chatProvider?.sendPromptToChat(`Regarding this ${lang} code from ${fileName}:\n\`\`\`${lang}\n${text}\n\`\`\`\n\n${question}`, question, true);
      vscode.commands.executeCommand("anote.chatView.focus");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.addToChat", async () => {
      const editor = vscode.window.activeTextEditor;
      if (!editor) return;
      const selection = editor.selection;
      const text = editor.document.getText(selection.isEmpty ? undefined : selection);
      const lang = editor.document.languageId;
      const fileName = editor.document.fileName.split("/").pop() ?? "file";
      chatProvider?.addContextToChat(fileName, lang, text);
      vscode.commands.executeCommand("anote.chatView.focus");
      vscode.window.showInformationMessage(`Added ${fileName} to Anote chat context`);
    })
  );

  // Attach File — file picker → extract content → inject into chat
  context.subscriptions.push(
    vscode.commands.registerCommand("anote.attachFile", async () => {
      const uris = await vscode.window.showOpenDialog({
        title: "Attach File to Anote Chat",
        canSelectMany: true,
        filters: {
          "Supported files": [
            "pdf", "docx",
            "png", "jpg", "jpeg", "webp", "gif",
            "ts", "tsx", "js", "jsx", "py", "go", "rs", "java",
            "cpp", "c", "h", "cs", "rb", "php", "md", "txt",
            "json", "yaml", "yml", "toml", "sh",
          ],
          "All files": ["*"],
        },
      });
      if (!uris || uris.length === 0) return;

      const IMAGE_EXTS = new Set([".png", ".jpg", ".jpeg", ".webp", ".gif"]);
      const BINARY_EXTS = new Set([".pdf", ".docx"]);

      for (const uri of uris) {
        const filePath = uri.fsPath;
        const ext = path.extname(filePath).toLowerCase();
        const name = path.basename(filePath);

        try {
          if (IMAGE_EXTS.has(ext)) {
            const buf = fs.readFileSync(filePath);
            const data = buf.toString("base64");
            const mimeMap: Record<string, string> = {
              ".png": "image/png", ".jpg": "image/jpeg", ".jpeg": "image/jpeg",
              ".webp": "image/webp", ".gif": "image/gif",
            };
            const mime = mimeMap[ext] ?? "image/png";
            chatProvider?.addContextToChat(name, "image", `[Image: data:${mime};base64,${data}]`);
          } else if (BINARY_EXTS.has(ext)) {
            vscode.window.showWarningMessage(
              `${ext.slice(1).toUpperCase()} extraction requires the Anote server. ` +
              `Configure it via "Anote: Set Up", then try again.`
            );
            continue;
          } else {
            const MAX_BYTES = 150_000;
            let content = fs.readFileSync(filePath, "utf-8");
            if (content.length > MAX_BYTES) {
              content = content.slice(0, MAX_BYTES) + "\n\n[... file truncated ...]";
            }
            chatProvider?.addContextToChat(name, ext.slice(1) || "text", content);
          }

          vscode.commands.executeCommand("anote.chatView.focus");
          vscode.window.showInformationMessage(`Attached ${name} to Anote chat`);
        } catch (err) {
          vscode.window.showErrorMessage(`Could not attach ${name}: ${String(err)}`);
        }
      }
    })
  );

  // Semantic search — query the local TF-IDF index via the Anote server
  context.subscriptions.push(
    vscode.commands.registerCommand("anote.semanticSearch", async () => {
      const serverUrl = getServerUrl();

      if (!serverUrl) {
        vscode.window.showWarningMessage(
          "Semantic search requires an Anote server. Configure one via Anote: Set Up, " +
          "or run: anote index && anote search \"your query\" in the terminal."
        );
        return;
      }

      const query = await vscode.window.showInputBox({
        title: "Anote Semantic Search",
        prompt: 'Search the codebase semantically — e.g. "JWT token validation"',
        placeHolder: "What are you looking for?",
      });
      if (!query?.trim()) return;

      const cwd = vscode.workspace.workspaceFolders?.[0]?.uri.fsPath ?? process.cwd();

      try {
        const url = `${serverUrl}/api/search?${new URLSearchParams({ q: query, cwd, top: "10" })}`;
        const resp = await fetch(url);

        if (resp.status === 404) {
          const choice = await vscode.window.showWarningMessage(
            "No search index found. Run `anote index` in your project to enable semantic search.",
            "Open Terminal"
          );
          if (choice === "Open Terminal") {
            vscode.commands.executeCommand("workbench.action.terminal.new");
          }
          return;
        }

        if (!resp.ok) {
          vscode.window.showErrorMessage(`Search failed: ${resp.statusText}`);
          return;
        }

        const data = await resp.json() as {
          results: { file: string; startLine: number; endLine: number; preview: string; score: number }[];
        };

        if (!data.results.length) {
          vscode.window.showInformationMessage(`No results found for "${query}"`);
          return;
        }

        const items = data.results.map((r) => ({
          label: `$(file-code) ${r.file}:${r.startLine}`,
          description: `score ${r.score.toFixed(2)}`,
          detail: r.preview.slice(0, 120),
          result: r,
        }));

        const pick = await vscode.window.showQuickPick(items, {
          title: `Anote Semantic Search — "${query}"`,
          placeHolder: `${data.results.length} result${data.results.length !== 1 ? "s" : ""} — select to open`,
          matchOnDetail: true,
          matchOnDescription: true,
        });

        if (!pick) return;

        const absPath = path.join(cwd, pick.result.file);
        const uri = vscode.Uri.file(absPath);
        const doc = await vscode.workspace.openTextDocument(uri);
        const line = Math.max(0, pick.result.startLine - 1);
        await vscode.window.showTextDocument(doc, {
          selection: new vscode.Range(line, 0, line, 0),
        });
      } catch (err) {
        vscode.window.showErrorMessage(`Semantic search error: ${String(err)}`);
      }
    })
  );

  // Show welcome message on first activation
  const hasShownWelcome = context.globalState.get("anote.hasShownWelcome");
  if (!hasShownWelcome) {
    vscode.window
      .showInformationMessage(
        "Anote is installed. Run a quick setup or open chat now.",
        "Set Up Anote",
        "Open Chat",
        "Open Settings"
      )
      .then((choice) => {
        if (choice === "Set Up Anote") {
          vscode.commands.executeCommand("anote.setup");
        } else if (choice === "Open Chat") {
          vscode.commands.executeCommand("anote.chatView.focus");
        } else if (choice === "Open Settings") {
          vscode.commands.executeCommand("workbench.action.openSettings", "anote");
        }
      });
    context.globalState.update("anote.hasShownWelcome", true);
  }

  // ── Diff-review commands ─────────────────────────────────────

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.acceptEdit", async () => {
      const absPath = diffState.activePath;
      if (!absPath) {
        vscode.window.showInformationMessage("No Anote diff currently open.");
        return;
      }
      await chatProvider?.advanceDiff(true, absPath);
      await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.rejectEdit", async () => {
      const absPath = diffState.activePath;
      if (!absPath) {
        vscode.window.showInformationMessage("No Anote diff currently open.");
        return;
      }
      await chatProvider?.advanceDiff(false, absPath);
      await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.acceptAllEdits", async () => {
      if (pendingReverts.size === 0 && !diffState.activePath) {
        vscode.window.showInformationMessage("No Anote edits pending review.");
        return;
      }
      let accepted = 0;
      while (diffState.activePath) {
        const p = diffState.activePath;
        await chatProvider?.advanceDiff(true, p);
        await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
        accepted++;
      }
      if (accepted > 0) vscode.window.showInformationMessage(`Accepted ${accepted} Anote edit${accepted > 1 ? "s" : ""}.`);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.rejectAllEdits", async () => {
      if (pendingReverts.size === 0 && !diffState.activePath) {
        vscode.window.showInformationMessage("No Anote edits pending review.");
        return;
      }
      let rejected = 0;
      while (diffState.activePath) {
        const p = diffState.activePath;
        await chatProvider?.advanceDiff(false, p);
        await vscode.commands.executeCommand("workbench.action.closeActiveEditor");
        rejected++;
      }
      if (rejected > 0) vscode.window.showInformationMessage(`Rejected ${rejected} Anote edit${rejected > 1 ? "s" : ""}.`);
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.revertEdit", async () => {
      if (pendingReverts.size === 0) {
        vscode.window.showInformationMessage("No Anote edits available to revert.");
        return;
      }

      let absPath: string;
      if (pendingReverts.size === 1) {
        absPath = pendingReverts.keys().next().value as string;
      } else {
        const items = Array.from(pendingReverts.keys()).map((p) => ({
          label: path.basename(p),
          description: p,
          absPath: p,
        }));
        const pick = await vscode.window.showQuickPick(items, {
          title: "Revert Anote Edit",
          placeHolder: "Select a file to revert",
        });
        if (!pick) return;
        absPath = pick.absPath;
      }

      const original = pendingReverts.get(absPath);
      if (original === undefined) return;
      try {
        fs.writeFileSync(absPath, original, "utf8");
        pendingReverts.delete(absPath);
        vscode.window.showInformationMessage(`Reverted ${path.basename(absPath)}`);
      } catch (err) {
        vscode.window.showErrorMessage(`Could not revert: ${String(err)}`);
      }
    })
  );

  context.subscriptions.push(
    vscode.commands.registerCommand("anote.showPendingDiffs", async () => {
      if (pendingReverts.size === 0) {
        vscode.window.showInformationMessage("No Anote edits to review.");
        return;
      }
      const items = Array.from(pendingReverts.keys()).map((p) => ({
        label: path.basename(p),
        description: p,
        absPath: p,
      }));
      const pick = await vscode.window.showQuickPick(items, {
        title: "Anote-Modified Files",
        placeHolder: "Select a file to open its diff",
      });
      if (!pick) return;

      const original = pendingReverts.get(pick.absPath);
      if (original === undefined) return;
      const fileName = path.basename(pick.absPath);
      const os = await import("os");
      const tmpPath = path.join(os.tmpdir(), `anote-orig-${Date.now()}-${fileName}`);
      fs.writeFileSync(tmpPath, original, "utf8");
      await vscode.commands.executeCommand(
        "vscode.diff",
        vscode.Uri.file(tmpPath),
        vscode.Uri.file(pick.absPath),
        `Anote: Review ${fileName}  (Accept ✓ or Reject ✗ in toolbar)`
      );
    })
  );
}

export function deactivate() {
  chatProvider = undefined;
}
