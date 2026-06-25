import React, { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "react-router-dom";
import axios from "axios";
import { useAuth, useTheme } from "../App";
import RocketLogo from "../components/RocketLogo";

interface Folder { id: number; name: string; }
interface Document { id: string; filename: string; chunks: number; folder_id: number | null; }
interface UploadItem { id: string; name: string; step: "uploading" | "extracting" | "indexing" | "done" | "error"; pct: number; error?: string; }
interface RubberBand { startX: number; startY: number; curX: number; curY: number; }

const ACCEPTED_TYPES = [
  "application/pdf", "text/plain", "text/markdown",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
];
const ACCEPTED_LABEL = "PDF, DOCX, TXT, MD";
const ACCEPTED_EXT = ".pdf,.docx,.txt,.md";
const MAX_FILES = 10;
const MAX_SIZE_MB = 50;
const MAX_SIZE_BYTES = MAX_SIZE_MB * 1024 * 1024;
const STEP_LABELS: Record<UploadItem["step"], string> = {
  uploading: "Uploading...", extracting: "Extracting text...", indexing: "Indexing...", done: "Ready", error: "Failed",
};

export default function DocumentsPage() {
  const { token, setToken } = useAuth();
  const { dark, toggle } = useTheme();
  const nav = useNavigate();

  const [folders, setFolders] = useState<Folder[]>([]);
  const [documents, setDocuments] = useState<Document[]>([]);
  const [selectedFolder, setSelectedFolder] = useState<Folder | null>(null);
  const [uploads, setUploads] = useState<UploadItem[]>([]);
  const [draggingDoc, setDraggingDoc] = useState<string | null>(null);
  const [draggingOver, setDraggingOver] = useState<number | "root" | null>(null);
  const [newFolderName, setNewFolderName] = useState("");
  const [creatingFolder, setCreatingFolder] = useState(false);
  const [renamingId, setRenamingId] = useState<number | null>(null);
  const [renameValue, setRenameValue] = useState("");
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const [dragOver, setDragOver] = useState(false);

  // Multi-select state
  const [selectedDocs, setSelectedDocs] = useState<Set<string>>(new Set());
  const [rubberBand, setRubberBand] = useState<RubberBand | null>(null);
  const [lastClickedId, setLastClickedId] = useState<string | null>(null);
  const [bulkMoveFolder, setBulkMoveFolder] = useState<string>("");

  const dragCounterRef = useRef(0);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);
  const docItemRefs = useRef<Map<string, HTMLDivElement>>(new Map());
  const isRubberBanding = useRef(false);

  const headers = { Authorization: `Bearer ${token}` };

  const loadFolders = useCallback(async () => {
    try {
      const res = await axios.get("/api/folders", { headers });
      setFolders(res.data.folders || []);
    } catch {}
  }, [token]);

  const loadDocuments = useCallback(async () => {
    try {
      const params = selectedFolder ? { folder_id: selectedFolder.id } : {};
      const res = await axios.get("/api/documents", { headers, params });
      setDocuments(res.data.documents || []);
    } catch {}
  }, [token, selectedFolder]);

  useEffect(() => { loadFolders(); }, [loadFolders]);
  useEffect(() => { loadDocuments(); }, [loadDocuments]);
  useEffect(() => { setSelectedDocs(new Set()); }, [selectedFolder]);

  // Rubber-band mouse events on window
  useEffect(() => {
    const onMouseMove = (e: MouseEvent) => {
      if (!isRubberBanding.current || !rubberBand || !listRef.current) return;
      const rect = listRef.current.getBoundingClientRect();
      const curX = e.clientX - rect.left;
      const curY = e.clientY - rect.top + listRef.current.scrollTop;
      setRubberBand((rb) => rb ? { ...rb, curX, curY } : null);

      // Determine which docs intersect the rubber band
      const minX = Math.min(rubberBand.startX, curX);
      const maxX = Math.max(rubberBand.startX, curX);
      const minY = Math.min(rubberBand.startY, curY);
      const maxY = Math.max(rubberBand.startY, curY);

      const hit = new Set<string>();
      docItemRefs.current.forEach((el, id) => {
        const r = el.getBoundingClientRect();
        const elTop = r.top - rect.top + listRef.current!.scrollTop;
        const elBottom = elTop + r.height;
        const elLeft = r.left - rect.left;
        const elRight = elLeft + r.width;
        if (elLeft < maxX && elRight > minX && elTop < maxY && elBottom > minY) {
          hit.add(id);
        }
      });
      setSelectedDocs(hit);
    };

    const onMouseUp = () => {
      if (isRubberBanding.current) {
        isRubberBanding.current = false;
        setRubberBand(null);
      }
    };

    window.addEventListener("mousemove", onMouseMove);
    window.addEventListener("mouseup", onMouseUp);
    return () => {
      window.removeEventListener("mousemove", onMouseMove);
      window.removeEventListener("mouseup", onMouseUp);
    };
  }, [rubberBand]);

  const onListMouseDown = (e: React.MouseEvent<HTMLDivElement>) => {
    if (draggingDoc) return;
    // Only start rubber band when clicking directly on the list background
    const target = e.target as HTMLElement;
    if (target.closest("[data-doc-item]")) return;
    if (!listRef.current) return;
    const rect = listRef.current.getBoundingClientRect();
    const startX = e.clientX - rect.left;
    const startY = e.clientY - rect.top + listRef.current.scrollTop;
    isRubberBanding.current = true;
    setRubberBand({ startX, startY, curX: startX, curY: startY });
    if (!e.shiftKey && !e.ctrlKey && !e.metaKey) setSelectedDocs(new Set());
  };

  const onDocClick = (e: React.MouseEvent, docId: string, displayDocs: Document[]) => {
    e.stopPropagation();
    if (e.shiftKey && lastClickedId) {
      // Range select
      const ids = displayDocs.map((d) => d.id);
      const a = ids.indexOf(lastClickedId);
      const b = ids.indexOf(docId);
      const range = ids.slice(Math.min(a, b), Math.max(a, b) + 1);
      setSelectedDocs((prev) => new Set([...prev, ...range]));
    } else if (e.ctrlKey || e.metaKey) {
      // Toggle
      setSelectedDocs((prev) => {
        const next = new Set(prev);
        next.has(docId) ? next.delete(docId) : next.add(docId);
        return next;
      });
    } else {
      // Single select (or deselect if already only this one)
      setSelectedDocs((prev) =>
        prev.size === 1 && prev.has(docId) ? new Set() : new Set([docId])
      );
    }
    setLastClickedId(docId);
  };

  const createFolder = async () => {
    const name = newFolderName.trim();
    if (!name) return;
    try {
      const res = await axios.post("/api/folders", { name }, { headers });
      setFolders((prev) => [...prev, res.data]);
      setNewFolderName("");
      setCreatingFolder(false);
    } catch {}
  };

  const renameFolder = async (id: number) => {
    const name = renameValue.trim();
    if (!name) { setRenamingId(null); return; }
    try {
      await axios.patch(`/api/folders/${id}`, { name }, { headers });
      setFolders((prev) => prev.map((f) => f.id === id ? { ...f, name } : f));
      if (selectedFolder?.id === id) setSelectedFolder((f) => f ? { ...f, name } : f);
    } catch {}
    setRenamingId(null);
  };

  const deleteFolder = async (id: number) => {
    if (!confirm("Delete this folder? Documents inside will become unfiled.")) return;
    try {
      await axios.delete(`/api/folders/${id}`, { headers });
      setFolders((prev) => prev.filter((f) => f.id !== id));
      if (selectedFolder?.id === id) setSelectedFolder(null);
      loadDocuments();
    } catch {}
  };

  const deleteDocument = async (docId: string) => {
    try {
      await axios.delete(`/api/documents/${docId}`, { headers });
      setDocuments((prev) => prev.filter((d) => d.id !== docId));
      setSelectedDocs((prev) => { const n = new Set(prev); n.delete(docId); return n; });
    } catch {}
  };

  const deleteSelected = async () => {
    if (!confirm(`Delete ${selectedDocs.size} document${selectedDocs.size > 1 ? "s" : ""}?`)) return;
    await Promise.all(Array.from(selectedDocs).map(deleteDocument));
    setSelectedDocs(new Set());
  };

  const moveDocument = async (docId: string, folderId: number | null) => {
    try {
      await axios.patch(`/api/documents/${docId}/move`, { folder_id: folderId }, { headers });
      setDocuments((prev) => prev.map((d) => d.id === docId ? { ...d, folder_id: folderId } : d));
      loadDocuments();
    } catch {}
  };

  const moveSelected = async (folderId: number | null) => {
    await Promise.all(Array.from(selectedDocs).map((id) => moveDocument(id, folderId)));
    setSelectedDocs(new Set());
    setBulkMoveFolder("");
  };

  const uploadFile = async (file: File) => {
    const id = crypto.randomUUID();
    if (!ACCEPTED_TYPES.includes(file.type)) {
      setUploads((prev) => [...prev, { id, name: file.name, step: "error", pct: 0, error: `Unsupported type — use ${ACCEPTED_LABEL}` }]);
      return;
    }
    if (file.size > MAX_SIZE_BYTES) {
      setUploads((prev) => [...prev, { id, name: file.name, step: "error", pct: 0, error: `Exceeds ${MAX_SIZE_MB}MB limit` }]);
      return;
    }
    setUploads((prev) => [...prev, { id, name: file.name, step: "uploading", pct: 0 }]);
    const form = new FormData();
    form.append("file", file);
    if (selectedFolder) form.append("folder_id", String(selectedFolder.id));

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
      loadDocuments();
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

  const onDragEnter = (e: React.DragEvent) => { e.preventDefault(); dragCounterRef.current++; setDragOver(true); };
  const onDragLeave = (e: React.DragEvent) => { e.preventDefault(); dragCounterRef.current--; if (dragCounterRef.current === 0) setDragOver(false); };
  const onDragOver = (e: React.DragEvent) => { e.preventDefault(); };
  const onDrop = (e: React.DragEvent) => {
    e.preventDefault(); dragCounterRef.current = 0; setDragOver(false);
    if (e.dataTransfer.files.length > 0) handleFiles(e.dataTransfer.files);
  };

  const onDocDragStart = (docId: string) => { setDraggingDoc(docId); isRubberBanding.current = false; setRubberBand(null); };
  const onDocDragEnd = () => { setDraggingDoc(null); setDraggingOver(null); };
  const onFolderDragOver = (e: React.DragEvent, target: number | "root") => { e.preventDefault(); if (draggingDoc) setDraggingOver(target); };
  const onFolderDrop = (e: React.DragEvent, target: number | "root") => {
    e.preventDefault();
    if (draggingDoc) moveDocument(draggingDoc, target === "root" ? null : target);
    setDraggingDoc(null); setDraggingOver(null);
  };

  const logout = () => { setToken(null); nav("/login"); };

  const displayDocs = selectedFolder
    ? documents.filter((d) => d.folder_id === selectedFolder.id)
    : documents;

  // Rubber band rect in screen coords for rendering
  const getRubberBandStyle = () => {
    if (!rubberBand || !listRef.current) return {};
    const rect = listRef.current.getBoundingClientRect();
    const scroll = listRef.current.scrollTop;
    const x1 = Math.min(rubberBand.startX, rubberBand.curX);
    const y1 = Math.min(rubberBand.startY, rubberBand.curY) - scroll;
    const w = Math.abs(rubberBand.curX - rubberBand.startX);
    const h = Math.abs(rubberBand.curY - rubberBand.startY);
    return { left: rect.left + x1, top: rect.top + y1, width: w, height: h };
  };

  return (
    <div
      className="flex h-screen bg-white dark:bg-[#212121] text-gray-900 dark:text-white relative"
      onDragEnter={onDragEnter}
      onDragLeave={onDragLeave}
      onDragOver={onDragOver}
      onDrop={onDrop}
    >
      {/* Rubber band selection rectangle */}
      {rubberBand && (
        <div
          className="fixed z-40 border border-blue-400 bg-blue-400/10 pointer-events-none"
          style={getRubberBandStyle()}
        />
      )}

      {/* File drag overlay */}
      {dragOver && !draggingDoc && (
        <div className="absolute inset-0 z-50 flex flex-col items-center justify-center bg-white/90 dark:bg-[#212121]/90 border-4 border-dashed border-gray-400 dark:border-gray-500 pointer-events-none">
          <svg className="w-16 h-16 text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
          </svg>
          <p className="text-lg font-medium text-gray-600 dark:text-gray-300">Drop to upload</p>
          <p className="text-sm text-gray-400 mt-1">Supports {ACCEPTED_LABEL}</p>
        </div>
      )}

      {/* Left sidebar */}
      <aside className={`${sidebarOpen ? "w-64" : "w-0"} transition-all duration-200 overflow-hidden flex-shrink-0 bg-[#F7F7F8] dark:bg-[#171717] flex flex-col border-r border-gray-200 dark:border-gray-700`}>
        <div className="p-3 flex items-center gap-2">
          <RocketLogo className="w-7 h-7 flex-shrink-0" />
          <span className="font-semibold text-sm truncate">Anote AI</span>
        </div>
        <div className="px-2 pb-1 space-y-0.5">
          <button onClick={() => nav("/")} className="w-full text-left px-3 py-2 rounded-lg text-sm hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2">
            <span>💬</span> Chat
          </button>
          <button onClick={() => nav("/documents")} className="w-full text-left px-3 py-2 rounded-lg text-sm bg-gray-200 dark:bg-[#2F2F2F] flex items-center gap-2">
            <span>📁</span> Documents
          </button>
        </div>
        <div className="px-3 pt-3 pb-1">
          <p className="text-xs font-semibold text-gray-400 dark:text-gray-500 uppercase tracking-wider">My Documents</p>
        </div>
        <div className="px-2">
          <div
            onClick={() => setSelectedFolder(null)}
            onDragOver={(e) => onFolderDragOver(e, "root")}
            onDrop={(e) => onFolderDrop(e, "root")}
            className={`flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${selectedFolder === null ? "bg-gray-200 dark:bg-[#2F2F2F]" : "hover:bg-gray-200 dark:hover:bg-[#2F2F2F]"} ${draggingOver === "root" ? "ring-2 ring-gray-400" : ""}`}
          >
            <span className="flex items-center gap-2"><span>📄</span><span>All documents</span></span>
            <span className="text-xs text-gray-400">{documents.length}</span>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto px-2 pt-1 space-y-0.5">
          {folders.map((folder) => (
            <div
              key={folder.id}
              onDragOver={(e) => onFolderDragOver(e, folder.id)}
              onDrop={(e) => onFolderDrop(e, folder.id)}
              className={`group flex items-center justify-between px-3 py-2 rounded-lg text-sm cursor-pointer transition-colors ${selectedFolder?.id === folder.id ? "bg-gray-200 dark:bg-[#2F2F2F]" : "hover:bg-gray-200 dark:hover:bg-[#2F2F2F]"} ${draggingOver === folder.id ? "ring-2 ring-gray-400" : ""}`}
              onClick={() => setSelectedFolder(folder)}
            >
              {renamingId === folder.id ? (
                <input autoFocus value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={() => renameFolder(folder.id)}
                  onKeyDown={(e) => { if (e.key === "Enter") renameFolder(folder.id); if (e.key === "Escape") setRenamingId(null); }}
                  onClick={(e) => e.stopPropagation()}
                  className="flex-1 bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-gray-600 rounded px-1 text-sm focus:outline-none"
                />
              ) : (
                <span className="flex items-center gap-2 truncate"><span>📁</span><span className="truncate">{folder.name}</span></span>
              )}
              <div className="opacity-0 group-hover:opacity-100 flex gap-1 flex-shrink-0 ml-1">
                <button onClick={(e) => { e.stopPropagation(); setRenamingId(folder.id); setRenameValue(folder.name); }} className="text-gray-400 hover:text-gray-700 dark:hover:text-gray-200 text-xs p-0.5" title="Rename">✏️</button>
                <button onClick={(e) => { e.stopPropagation(); deleteFolder(folder.id); }} className="text-gray-400 hover:text-red-500 text-xs p-0.5" title="Delete">✕</button>
              </div>
            </div>
          ))}
          {creatingFolder ? (
            <div className="px-3 py-1">
              <input autoFocus value={newFolderName}
                onChange={(e) => setNewFolderName(e.target.value)}
                onBlur={() => { if (!newFolderName.trim()) setCreatingFolder(false); else createFolder(); }}
                onKeyDown={(e) => { if (e.key === "Enter") createFolder(); if (e.key === "Escape") setCreatingFolder(false); }}
                placeholder="Folder name..."
                className="w-full bg-white dark:bg-[#1a1a1a] border border-gray-300 dark:border-gray-600 rounded px-2 py-1 text-sm focus:outline-none"
              />
            </div>
          ) : (
            <button onClick={() => setCreatingFolder(true)} className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-400 dark:text-gray-500 hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors flex items-center gap-2">
              <span>+</span> New folder
            </button>
          )}
        </div>
        <div className="p-3 border-t border-gray-200 dark:border-gray-700">
          <button onClick={logout} className="w-full text-left px-3 py-2 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-200 dark:hover:bg-[#2F2F2F] transition-colors">Sign out</button>
        </div>
      </aside>

      {/* Main panel */}
      <div className="flex-1 flex flex-col min-w-0">
        <header className="flex items-center justify-between px-4 py-3 border-b border-gray-200 dark:border-gray-700">
          <div className="flex items-center gap-3">
            <button onClick={() => setSidebarOpen((o) => !o)} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400">☰</button>
            <nav className="flex items-center gap-1 text-sm text-gray-500 dark:text-gray-400">
              <button onClick={() => setSelectedFolder(null)} className="hover:text-gray-900 dark:hover:text-white transition-colors">My Documents</button>
              {selectedFolder && (<><span>/</span><span className="text-gray-900 dark:text-white font-medium">{selectedFolder.name}</span></>)}
            </nav>
          </div>
          <div className="flex items-center gap-2">
            <input ref={fileInputRef} type="file" accept={ACCEPTED_EXT} multiple className="hidden" onChange={(e) => handleFiles(e.target.files)} />
            <button onClick={() => fileInputRef.current?.click()} className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm bg-gray-900 dark:bg-white text-white dark:text-gray-900 hover:bg-gray-800 dark:hover:bg-gray-100 transition-colors">
              <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12" /></svg>
              Upload
            </button>
            <button onClick={toggle} className="p-2 rounded-lg hover:bg-gray-100 dark:hover:bg-[#2F2F2F] text-gray-500 dark:text-gray-400">{dark ? "☀️" : "🌙"}</button>
          </div>
        </header>

        {/* Bulk action toolbar */}
        {selectedDocs.size > 0 && (
          <div className="flex items-center gap-3 px-6 py-2 bg-blue-50 dark:bg-blue-950/30 border-b border-blue-200 dark:border-blue-800">
            <span className="text-sm font-medium text-blue-700 dark:text-blue-300">{selectedDocs.size} selected</span>
            <div className="flex items-center gap-1">
              <select
                value={bulkMoveFolder}
                onChange={(e) => setBulkMoveFolder(e.target.value)}
                className="text-xs bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-600 rounded px-2 py-1 focus:outline-none"
              >
                <option value="">Move to...</option>
                <option value="root">Unfiled</option>
                {folders.map((f) => <option key={f.id} value={String(f.id)}>{f.name}</option>)}
              </select>
              {bulkMoveFolder && (
                <button
                  onClick={() => moveSelected(bulkMoveFolder === "root" ? null : parseInt(bulkMoveFolder))}
                  className="text-xs px-2 py-1 rounded bg-blue-600 text-white hover:bg-blue-700 transition-colors"
                >Move</button>
              )}
            </div>
            <button onClick={deleteSelected} className="text-xs px-2 py-1 rounded text-red-600 hover:bg-red-50 dark:hover:bg-red-950/30 transition-colors">
              Delete selected
            </button>
            <button onClick={() => setSelectedDocs(new Set())} className="ml-auto text-xs text-gray-400 hover:text-gray-600 dark:hover:text-gray-300">
              Clear selection
            </button>
          </div>
        )}

        {/* Upload progress */}
        {uploads.length > 0 && (
          <div className="px-6 pt-4 space-y-2">
            {uploads.map((u) => (
              <div key={u.id} className="bg-[#F7F7F8] dark:bg-[#2F2F2F] rounded-xl px-4 py-3 flex items-center gap-3">
                <span className="text-lg flex-shrink-0">{u.step === "done" ? "✅" : u.step === "error" ? "❌" : "📄"}</span>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center justify-between mb-1">
                    <span className="text-sm font-medium truncate">{u.name}</span>
                    <span className={`text-xs ml-2 flex-shrink-0 ${u.step === "done" ? "text-green-500" : u.step === "error" ? "text-red-500" : "text-gray-400"}`}>
                      {u.step === "error" ? u.error : STEP_LABELS[u.step]}
                    </span>
                  </div>
                  {u.step !== "error" && (
                    <div className="h-1.5 bg-gray-200 dark:bg-gray-600 rounded-full overflow-hidden">
                      <div className={`h-full rounded-full transition-all duration-300 ${u.step === "done" ? "bg-green-500" : "bg-gray-900 dark:bg-white"}`} style={{ width: `${u.pct}%` }} />
                    </div>
                  )}
                </div>
                {(u.step === "done" || u.step === "error") && (
                  <button onClick={() => setUploads((prev) => prev.filter((x) => x.id !== u.id))} className="text-gray-400 hover:text-gray-600 text-xs flex-shrink-0">✕</button>
                )}
              </div>
            ))}
          </div>
        )}

        {/* Document list */}
        <div
          ref={listRef}
          className="flex-1 overflow-y-auto px-6 py-4 select-none"
          onMouseDown={onListMouseDown}
        >
          {displayDocs.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-full gap-4 text-center">
              <svg className="w-16 h-16 text-gray-200 dark:text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1} d="M9 13h6m-3-3v6m5 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
              </svg>
              <p className="text-gray-400 dark:text-gray-500">No documents yet — drag files here or click Upload</p>
              <p className="text-xs text-gray-300 dark:text-gray-600">Supports {ACCEPTED_LABEL}</p>
            </div>
          ) : (
            <div className="space-y-2">
              {displayDocs.map((doc) => {
                const isSelected = selectedDocs.has(doc.id);
                return (
                  <div
                    key={doc.id}
                    data-doc-item="true"
                    ref={(el) => { if (el) docItemRefs.current.set(doc.id, el); else docItemRefs.current.delete(doc.id); }}
                    draggable
                    onDragStart={() => onDocDragStart(doc.id)}
                    onDragEnd={onDocDragEnd}
                    onClick={(e) => onDocClick(e, doc.id, displayDocs)}
                    onMouseDown={(e) => e.stopPropagation()}
                    className={`group flex items-center gap-3 px-4 py-3 rounded-xl transition-colors cursor-pointer ${
                      isSelected
                        ? "bg-blue-100 dark:bg-blue-900/40 ring-2 ring-blue-400 dark:ring-blue-500"
                        : "bg-[#F7F7F8] dark:bg-[#2F2F2F] hover:bg-gray-100 dark:hover:bg-[#3a3a3a]"
                    }`}
                  >
                    <div className={`w-5 h-5 rounded border flex items-center justify-center flex-shrink-0 ${isSelected ? "bg-blue-500 border-blue-500" : "border-gray-300 dark:border-gray-600"}`}>
                      {isSelected && <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" /></svg>}
                    </div>
                    <span className="text-xl flex-shrink-0">📄</span>
                    <div className="flex-1 min-w-0">
                      <p className="text-sm font-medium truncate">{doc.filename}</p>
                      <p className="text-xs text-gray-400 dark:text-gray-500">{doc.chunks} chunks</p>
                    </div>
                    <select
                      value={doc.folder_id ?? ""}
                      onChange={(e) => { e.stopPropagation(); moveDocument(doc.id, e.target.value ? parseInt(e.target.value) : null); }}
                      onClick={(e) => e.stopPropagation()}
                      className="opacity-0 group-hover:opacity-100 text-xs bg-white dark:bg-[#1a1a1a] border border-gray-200 dark:border-gray-600 rounded px-1 py-0.5 focus:outline-none text-gray-600 dark:text-gray-300"
                      title="Move to folder"
                    >
                      <option value="">Unfiled</option>
                      {folders.map((f) => <option key={f.id} value={f.id}>{f.name}</option>)}
                    </select>
                    <button
                      onClick={(e) => { e.stopPropagation(); deleteDocument(doc.id); }}
                      className="opacity-0 group-hover:opacity-100 text-gray-400 hover:text-red-500 text-xs flex-shrink-0"
                      title="Delete"
                    >✕</button>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
