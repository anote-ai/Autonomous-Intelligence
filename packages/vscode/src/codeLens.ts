import * as vscode from "vscode";

export type CodeLensAction = "explain" | "fix" | "generateTests" | "refactor";

interface FunctionMatch {
  line: number;
  name: string;
  endLine: number;
}

// Language-specific patterns for function/class/method declarations
const PATTERNS: Record<string, RegExp[]> = {
  typescript:  [/^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)/, /^\s*(?:public|private|protected|static|async|\s)*(?:async\s+)?(\w+)\s*\(/],
  typescriptreact: [/^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)/, /^\s*(?:public|private|protected|static|async|\s)*(?:async\s+)?(\w+)\s*\(/],
  javascript: [/^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)/, /^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(/],
  javascriptreact: [/^\s*(?:export\s+)?(?:async\s+)?function\s+(\w+)/, /^\s*(?:export\s+)?const\s+(\w+)\s*=\s*(?:async\s+)?\(/],
  python: [/^\s*(?:async\s+)?def\s+(\w+)\s*\(/, /^\s*class\s+(\w+)\s*[:(]/],
  rust: [/^\s*(?:pub\s+)?(?:async\s+)?fn\s+(\w+)/, /^\s*(?:pub\s+)?struct\s+(\w+)/, /^\s*(?:pub\s+)?impl\s+/],
  go:   [/^\s*func\s+(?:\(\w+\s+\*?\w+\)\s+)?(\w+)\s*\(/],
  java: [/^\s*(?:public|private|protected|static|final|abstract|\s)*\s+\w+\s+(\w+)\s*\(/],
  c:    [/^\s*\w[\w\s\*]+\s+(\w+)\s*\(/],
  cpp:  [/^\s*\w[\w\s\*:~]+\s+(\w+)\s*\(/],
  csharp: [/^\s*(?:public|private|protected|internal|static|virtual|override|async|\s)*\s+\w+\s+(\w+)\s*\(/],
  ruby: [/^\s*def\s+(\w+)/, /^\s*class\s+(\w+)/],
  php:  [/^\s*(?:public|private|protected|static|\s)*function\s+(\w+)\s*\(/],
};

function findFunctions(document: vscode.TextDocument): FunctionMatch[] {
  const langId = document.languageId;
  const patterns = PATTERNS[langId];
  if (!patterns) return [];

  const matches: FunctionMatch[] = [];
  const lineCount = document.lineCount;

  for (let i = 0; i < lineCount; i++) {
    const lineText = document.lineAt(i).text;

    for (const pattern of patterns) {
      const m = pattern.exec(lineText);
      if (m) {
        const name = m[1] ?? "(anonymous)";
        // Find end of block: look for closing brace / dedent at same indent level
        const endLine = findBlockEnd(document, i, langId);
        matches.push({ line: i, name, endLine });
        break; // one match per line is enough
      }
    }
  }
  return matches;
}

function findBlockEnd(doc: vscode.TextDocument, startLine: number, langId: string): number {
  const isPython = langId === "python" || langId === "ruby";
  const startIndent = doc.lineAt(startLine).firstNonWhitespaceCharacterIndex;
  const lineCount = doc.lineCount;

  if (isPython) {
    for (let i = startLine + 1; i < lineCount; i++) {
      const line = doc.lineAt(i);
      if (!line.isEmptyOrWhitespace && line.firstNonWhitespaceCharacterIndex <= startIndent) {
        return Math.max(startLine, i - 1);
      }
    }
    return lineCount - 1;
  }

  // Brace-based languages
  let depth = 0;
  for (let i = startLine; i < Math.min(lineCount, startLine + 200); i++) {
    const text = doc.lineAt(i).text;
    for (const ch of text) {
      if (ch === "{") depth++;
      else if (ch === "}") {
        depth--;
        if (depth === 0) return i;
      }
    }
  }
  return Math.min(startLine + 30, lineCount - 1);
}

export class AnoteCodeLensProvider implements vscode.CodeLensProvider {
  private _onDidChangeCodeLenses = new vscode.EventEmitter<void>();
  readonly onDidChangeCodeLenses = this._onDidChangeCodeLenses.event;

  refresh() {
    this._onDidChangeCodeLenses.fire();
  }

  provideCodeLenses(document: vscode.TextDocument): vscode.CodeLens[] {
    const config = vscode.workspace.getConfiguration("anote");
    if (!config.get<boolean>("enableCodeLens", true)) return [];

    const functions = findFunctions(document);
    const lenses: vscode.CodeLens[] = [];

    for (const fn of functions) {
      const range = new vscode.Range(fn.line, 0, fn.endLine, 0);

      const actions: { title: string; action: CodeLensAction }[] = [
        { title: "Anote: Explain", action: "explain" },
        { title: "Fix", action: "fix" },
        { title: "Tests", action: "generateTests" },
        { title: "Refactor", action: "refactor" },
      ];

      for (const { title, action } of actions) {
        lenses.push(
          new vscode.CodeLens(new vscode.Range(fn.line, 0, fn.line, 0), {
            title,
            command: "anote.codeLensAction",
            arguments: [document.uri, range, action],
            tooltip: `Anote: ${action} — ${fn.name}`,
          })
        );
      }
    }

    return lenses;
  }
}
