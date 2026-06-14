/**
 * Session persistence — saves/loads conversation history to ~/.anote/sessions/.
 * Mirrors the Python port's session_store.py and Rust runtime/session.rs.
 */

import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export interface StoredMessage {
  role: "user" | "assistant";
  content: string;
  ts: number;
}

export interface StoredSession {
  sessionId: string;
  cwd: string;
  messages: StoredMessage[];
  inputTokens: number;
  outputTokens: number;
  createdAt: number;
  updatedAt: number;
}

function sessionsDir(): string {
  const dir = path.join(os.homedir(), ".anote", "sessions");
  fs.mkdirSync(dir, { recursive: true });
  return dir;
}

export function saveSession(session: StoredSession): string {
  const dir = sessionsDir();
  const file = path.join(dir, `${session.sessionId}.json`);
  fs.writeFileSync(file, JSON.stringify(session, null, 2), "utf8");
  return file;
}

export function loadSession(sessionId: string): StoredSession | null {
  const file = path.join(sessionsDir(), `${sessionId}.json`);
  if (!fs.existsSync(file)) return null;
  try {
    return JSON.parse(fs.readFileSync(file, "utf8")) as StoredSession;
  } catch {
    return null;
  }
}

export function listSessions(limit = 20): StoredSession[] {
  const dir = sessionsDir();
  const files = fs
    .readdirSync(dir)
    .filter((f) => f.endsWith(".json"))
    .map((f) => {
      const p = path.join(dir, f);
      return { file: p, mtime: fs.statSync(p).mtimeMs };
    })
    .sort((a, b) => b.mtime - a.mtime)
    .slice(0, limit);

  const sessions: StoredSession[] = [];
  for (const { file } of files) {
    try {
      sessions.push(JSON.parse(fs.readFileSync(file, "utf8")) as StoredSession);
    } catch {
      // skip corrupt files
    }
  }
  return sessions;
}

export function deleteSession(sessionId: string): boolean {
  const file = path.join(sessionsDir(), `${sessionId}.json`);
  if (fs.existsSync(file)) {
    fs.unlinkSync(file);
    return true;
  }
  return false;
}

/** Auto-compact: keep only the last N messages in a session's history */
export function compactMessages(
  messages: StoredMessage[],
  keepLast = 20
): StoredMessage[] {
  if (messages.length <= keepLast) return messages;
  return messages.slice(messages.length - keepLast);
}
