import React, { useState, useEffect, useRef, useCallback } from "react";
import { useParams, useNavigate } from "react-router-dom";
import axios from "axios";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useAuth, useTheme } from "../App";
import RocketLogo from "../components/RocketLogo";

interface Message {
  id?: string;
  role: "user" | "assistant";
  content: string;
  createdAt?: string;
}

interface Session {
  id: string;
  title: string;
  createdAt: string;
}

interface UploadItem {
  id: string;
  name: string;
  step: "uploading" | "extracting" | "indexing" | "done" | "error";
  pct: number;
  error?: string;
}

const MODELS = [
  "claude-sonnet-4-6",
  "claude-haiku-4-5-20251001",
  "gpt-4o",
  "gpt-4o-mini",
];

const ACCEPTED_TYPES = [
  "application/pdf",
  "text/plain",
  "text/markdown",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ACCEPTED_LABEL = "PDF, DOCX, TXT, MD";
const ACCEPTED_EXT = ".pdf,.docx,.txt,.md";
const MAX_FILES = 10;
const MAX_SIZE_MB = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;

const STEP_LABELS: Record<UploadItem["step"], string> = {
  uploading: "Uploading...",
  extracting: "Extracting text...",
  indexing: "Indexing...",
  done: "Ready to chat",
  error: "Failed",
};

export default function ChatPage() {
  const { id: sessionId } = useParams<{ id: string }>();
  const nav = useNavigate();
  const { token, setToken } = useAuth();
  const { dark, toggle } = useTheme();

  const [sessions, setSessions] = useState<Session[]>([]);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [model, setModel] = useState(MODELS[0]);
  const [streaming, setStreaming] = useState(false);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dragging, setDragging] = useState(false);
  const [uploads, setUploads] = useState<UploadItem[]>([]);

  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const abortRef = useRef<AbortController | null>(null);
  const dragCounterRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const headers = { Authorization: `Bearer ${token}` };

  const loadSessions = useCallback(async () => {
    try {
      const res = await axios.get("/api/chat/sessions", { headers });
      setSessions(res.data.sessions || []);
    } catch {}
  }, [token]);

  const loadMessages = useCallback(async (id: string) => {
    try {
      const res = await axios.get(`/api/chat/sessions/${id}`, { headers });
      setMessages(res.data.messages || []);
    } catch {}
  }, [token]);

  useEffect(() => { loadSessions(); }, [loadSessions]);
  useEffect(() => {
    if (sessionId) loadMessages(sessionId);
    else setMessages([]);
  }, [sessionId, loadMessages]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const autoResize = () => {
    const ta = textareaRef.current;
    if (!ta) return;
    ta.style.height = "auto";
    ta.style.height = Math.min(ta.scrollHeight, 200) + "px";
  };

  const newChat = () => nav("/");
  const logout = () => { setToken(null); nav("/login"); };

  const uploadFile = async (file: File) => {
    const id = crypto.randomUUID();

    if (!ACCEPTED_TYPES.includes(file.type)) {
      setUploads((prev) => [...prev, {
        id, name: file.name, step: "error", pct: 0,
        error: `Unsupported type — use ${ACCEPTED_LABEL}`,
      }]);
      return;
    }

    if (file.size > MAX_SIZE_BYTES) {
      setUploads((prev) => [...prev, {
        id, name: file.name, step: "error", pct: 0,
        error: `File exceeds ${MAX_SIZE_MB}MB limit. Try splitting it into smaller sections.`,
      }]);
      return;
    }

    setUploads((prev) => [...prev, { id, name: file.name, step: "uploading", pct: 0 }]);

    const form = new FormData();
    form.append("file", file);

    let simulationInterval: ReturnType<typeof setInterval> | null = null;

    const startSimulation = () => {
      let pct = 34;
      simulationInterval = setInterval(() => {
        pct += 1;
        const step: UploadItem["step"] = pct < 67 ? "extracting" : "indexing";
        if (pct >= 99) { clearInterval(simulationInterval!); return; }
        setUploads((prev) => prev.map((u) => u.id === id ? { ...u, step, pct } : u));
      }, 200);
    };

    try {
      await axios.post("/api/documents/upload", form, {
        headers: { ...headers, "Content-Type": "multipart/form-data" },
        onUploadProgress: (e) => {
          const pct = e.total ? Math.round((e.loaded / e.total) * 33) : 0;
          setUploads((prev) => prev.map((u) => u.id === id ? { ...u, pct } : u));
          if (e.loaded === e.total) startSimulation();
        },
      });

      if (simulationInterval) clearInterval(simulationInterval);
      setUploads((prev) => prev.map((u) => u.id === id ? { ...u, step: "done", pct: 100 } : u));
      setTimeout(() => setUploads((prev) => prev.filter((u) => u.id !== id)), 3000);
    } catch (err: any) {
      if (simulationInterval) clearInterval(simulationInterval);
      const msg = err?.response?.data?.error === "Internal server error"
        ? "We had trouble reading this file. Try converting it to PDF first."
        : "Upload failed — please try again.";
      setUploads((prev) => prev.map((u) => u.id === id ? { ...u, step: "error", error: msg } : u));
    }
  };

  const handleFiles = (files: FileList | null) => {
    if (!files) return;
    Array.from(files).slice(0, MAX_FILES).forEach(uploadFile);
  };

  const onDragEnter = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current++;
    setDragging(true);
  };

  const onDragLeave = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) setDragging(false);
  };

  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); };

  const onDrop = (e: React.DragEvent) => {
    e.preventDefault();
    dragCounterRef.current = 0;
    setDragging(false);
    handleFiles(e.dataTransfer.files);
  };

  const sendMessage = async () => {
    if (!input.trim() || streaming) return;
    const userMsg: Message = { role: "user", content: input.trim() };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
    setStreaming(true);

    let assistantContent = "";
    setMessages((prev) => [...prev, { role: "assistant", content: "" }]);

    try {
      abortRef.current = new AbortController();
      const res = await fetch("/api/chat/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json", Authorization: `Bearer ${token}` },
        body: JSON.stringify({ message: userMsg.content, session_id: sessionId, model }),
        signal: abortRef.current.signal,
      });

      if (!res.ok) throw new Error("Stream failed");
      if (!res.body) throw new Error("No body");

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        for (const line of lines) {
          if (line.startsWith("data: ")) {
            const data = line.slice(6).trim();
            if (data === "[DONE]") break;
            try {
              const parsed = JSON.parse(data);
              if (parsed.type === "text" && parsed.text) {
                assistantContent += parsed.text;
                setMessages((prev) => {
                  const updated = [...prev];
                  updated[updated.length - 1] = { role: "assistant", content: assistantContent };
                  return updated;
                });
              }
              if (parsed.type === "session_id" && !sessionId) {
                nav(`/chat/${parsed.session_id}`, { replace: true });
                loadSessions();
              }
            } catch {}
          }
        }
      }
    } catch (err: any) {
      if (err.name !== "AbortError") {
        setMessages((prev) => {
          const updated = [...prev];
          updated[updated.length - 1] = { role: "assistant", content: "Sorry, something went wrong. Please try again." };
          return updated;
        });
      }
    } finally {
      setStreaming(false);
      abortRef.current = null;
      loadSessions();
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); sendMessage(); }
  };

  const deleteSession = async (id: string, e: React.MouseEvent) => {
    e.stopPropagation();
    e.preventDefault();
    try {
      await axios.delete(`/api/chat/sessions/${id}`, { headers });
      if (sessionId === id) nav("/");
      loadSessions();
    } catch {}
  };

  return (
    <div
      className="flex h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white relative"
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {/* Drag overlay */}
      {dragging && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-white/90 dark:bg-[#212121]/90 border-4 border-dashed border-gray-400 dark:border-gray-500 pointer-events-none">
          <svg className="w-16 h-16 text-gray-400 dark:text-gray-500 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-lg font-medium text-gray-600 dark:text-gray-300">Drop to upload</p>
          <p className="text-sm text-gray-400 dark:text-gray-500 mt-1">Supports {ACCEPTED_LABEL}</p>
        </div>
      )}

      {/* Sidebar */}
      <aside className={`${sidebarOpen ? "w-64" : "w-0"} transition-all duration-200 overflow-hidden flex-shrink-0 bg-[#F7F7F8] dark:bg-[#171717] flex flex-col`}>
        <div className="p-3 flex items-center gap-2">
          <RocketLogo className="w-7 h-7 flex-shrink-0" />
          <span className="font-semibold text-sm truncate">Anote AI</span>
        </div>
        <div className="px-2 pb-2 space-y-0.5">
          <button
            onClick={newChat}
            className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2"
          >
            <span className="text-lg">+</span> New chat
          </button>
          <button
            onClick={() => nav("/documents")}
            className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2"
          >
            <span>📁</span> Documents
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-2 space-y-0.5">
          {sessions.map((s) => (
            <div
              key={s.id}
              onClick={() => nav(`/chat/${s.id}`)}
              className={`group flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${
                s.id === sessionId ? "bg-gray-200 dark:bg-[#2F2F2F]" : "hover:bg-gray-200 dark:hover:bg-[#2F2F2F]"
              }`}
            >
              <span className="truncate">{s.title || "New chat"}</span>
              <button
                onClick={(e) => deleteSession(s.id, e)}
                className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-xs ml-1 flex-shrink-0"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
          <button
            onClick={logout}
            className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors"
          >
            Sign out
          </button>
        </div>
      </aside>

      {/* Main */}
      <div className="flex-1 flex flex-col min-w-0">
        {/* Header */}
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <button
            onClick={() => setSidebarOpen((o) => !o)}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400"
            aria-label="Toggle sidebar"
          >
            ☰
          </button>
          <select
            value={model}
            onChange={(e) => setModel(e.target.value)}
            className="text-sm bg-transparent border border-gray-300 dark:border-gray-600 rounded-lg px-3 py-1.5 text-gray-700 dark:text-gray-300 focus:outline-none"
          >
            {MODELS.map((m) => <option key={m} value={m}>{m}</option>)}
          </select>
          <button
            onClick={toggle}
            className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400"
            aria-label="Toggle dark mode"
          >
            {dark ? "☀️" : "🌙"}
          </button>
        </header>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto">
          {messages.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <RocketLogo className="w-16 h-16 opacity-30" />
              <p className="text-gray-400 dark:text-gray-500 text-lg">How can I help you today?</p>
              <p className="text-xs text-gray-400 dark:text-gray-500">Drop a file anywhere to upload — {ACCEPTED_LABEL}</p>
            </div>
          ) : (
            <div className="max-w-3xl mx-auto px-4 py-6 space-y-6">
              {messages.map((msg, i) => (
                <div key={i} className={`flex gap-4 ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.role === "assistant" && (
                    <div className="w-8 h-8 rounded-full bg-gray-100 dark:bg-[#2F2F2F] flex items-center justify-center flex-shrink-0 mt-0.5">
                      <RocketLogo className="w-5 h-5" />
                    </div>
                  )}
                  <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                    msg.role === "user"
                      ? "bg-gray-100 dark:bg-[#2F2F2F] text-gray-900 dark:text-white"
                      : "bg-transparent text-gray-900 dark:text-white"
                  }`}>
                    {msg.role === "assistant" ? (
                      <div className="prose prose-sm dark:prose-invert max-w-none">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {msg.content || (streaming && i === messages.length - 1 ? "▋" : "")}
                        </ReactMarkdown>
                      </div>
                    ) : (
                      <p className="whitespace-pre-wrap text-sm">{msg.content}</p>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </div>

        {/* Upload progress cards */}
        {uploads.length > 0 && (
          <div className="px-4 pt-3 max-w-3xl mx-auto w-full space-y-2">
            {uploads.map((u) => (
              <div key={u.id} className="bg-[#F7F7F8] dark:bg-[#2F2F2F] rounded-xl px-4 py-3 flex items-center gap-3">
                <span className="text-lg flex-shrink-0">
                  {u.step === "done" ? "✅" : u.step === "error" ? "❌" : "📄"}
                </span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium truncate text-gray-900 dark:text-white">{u.name}</span>
                    <span className={`text-xs ml-2 flex-shrink-0 ${
                      u.step === "done" ? "text-green-500"
                      : u.step === "error" ? "text-red-500"
                      : "text-gray-400 dark:text-gray-500"
                    }`}>
                      {u.step === "error" ? u.error : STEP_LABELS[u.step]}
                    </span>
                  </div>
                  {u.step !== "error" && (
                    <div className="h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-300 ${
                          u.step === "done" ? "bg-green-500" : "bg-gray-900 dark:bg-white"
                        }`}
                        style={{ width: `${u.pct}%` }}
                      />
                    </div>
                  )}
                  {u.step !== "error" && u.step !== "done" && (
                    <div className="flex gap-4 mt-1.5">
                      {(["uploading", "extracting", "indexing"] as const).map((s, i) => {
                        const steps = ["uploading", "extracting", "indexing"] as const;
                        const currentIdx = steps.indexOf(u.step as typeof steps[number]);
                        const done = i < currentIdx;
                        const active = i === currentIdx;
                        return (
                          <span key={s} className={`text-xs ${
                            done ? "text-gray-900 dark:text-white"
                            : active ? "text-gray-700 dark:text-gray-300"
                            : "text-gray-300 dark:text-gray-600"
                          }`}>
                            {done ? "✓ " : ""}{i + 1}. {s.charAt(0).toUpperCase() + s.slice(1)}
                          </span>
                        );
                      })}
                    </div>
                  )}
                </div>
                {(u.step === "done" || u.step === "error") && (
                  <button
                    onClick={() => setUploads((prev) => prev.filter((x) => x.id !== u.id))}
                    className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 text-xs flex-shrink-0"
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Input */}
        <div className="border-t border-gray-200 dark:border-gray-700 px-4 py-4 mt-2">
          <input
            ref={fileInputRef}
            type="file"
            accept={ACCEPTED_EXT}
            multiple
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
          <div className="max-w-3xl mx-auto">
            <div className="relative flex items-end bg-[#F7F7F8] dark:bg-[#2F2F2F] rounded-2xl border border-gray-300 dark:border-gray-600">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="ml-2 mb-2 p-2 rounded-lg text-gray-400 hover:text-gray-600 dark:hover:text-gray-300 hover:bg-gray-200 dark:hover:bg-[#3F3F3F] transition-colors flex-shrink-0"
                aria-label="Upload file"
                title={`Upload file — ${ACCEPTED_LABEL}`}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.172 7l-6.586 6.586a2 2 0 102.828 2.828l6.414-6.586a4 4 0 00-5.656-5.656l-6.415 6.585a6 6 0 108.486 8.486L20.5 13" />
                </svg>
              </button>
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => { setInput(e.target.value); autoResize(); }}
                onKeyDown={handleKeyDown}
                placeholder="Message Anote AI..."
                rows={1}
                className="flex-1 bg-transparent px-2 py-3.5 text-sm text-gray-900 dark:text-white placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none min-h-[52px]"
              />
              <button
                onClick={streaming ? () => abortRef.current?.abort() : sendMessage}
                disabled={!streaming && !input.trim()}
                className="m-2 p-2 rounded-lg bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 disabled:opacity-30 disabled:cursor-not-allowed transition-colors flex-shrink-0"
                aria-label={streaming ? "Stop" : "Send"}
              >
                {streaming ? (
                  <span className="w-4 h-4 flex items-center justify-center">■</span>
                ) : (
                  <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
                    <path d="M2 21l21-9L2 3v7l15 2-15 2v7z" />
                  </svg>
                )}
              </button>
            </div>
            <p className="text-xs text-center text-gray-400 dark:text-gray-500 mt-2">
              Anote AI can make mistakes. Verify important information.
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
