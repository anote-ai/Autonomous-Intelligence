"""RAG pipeline — document ingestion and retrieval."""
from __future__ import annotations

import os
from pathlib import Path

_UPLOAD_DIR: Path = Path(os.environ.get("UPLOAD_FOLDER", "/tmp/anote_uploads")).resolve()
_UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# Public alias used by other modules
UPLOAD_FOLDER = _UPLOAD_DIR


def ingest_document(doc_id: str, file_path: Path) -> int:
    """Ingest a document into the vector store. Returns chunk count."""
    # Prevent path traversal: file_path must be within the upload directory
    resolved = file_path.resolve()
    if not str(resolved).startswith(str(_UPLOAD_DIR) + os.sep):
        raise ValueError("Access to file outside upload folder is not allowed")
    text = _extract_text(resolved)
    chunks = _chunk_text(text)
    if not chunks:
        return 0
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db"))
        ef = embedding_functions.DefaultEmbeddingFunction()
        collection = client.get_or_create_collection(
            "documents", embedding_function=ef  # type: ignore[arg-type]
        )
        ids = [f"{doc_id}-{i}" for i in range(len(chunks))]
        collection.add(documents=chunks, ids=ids, metadatas=[{"doc_id": doc_id}] * len(chunks))
    except Exception:
        pass
    return len(chunks)


def query_documents(
    question: str,
    doc_ids: list[str] | None = None,
    model: str = "claude-sonnet-4-6",
    top_k: int = 5,
) -> str:
    """Answer a question using RAG."""
    import os
    context = ""
    try:
        import chromadb
        from chromadb.utils import embedding_functions
        client = chromadb.PersistentClient(path=os.environ.get("CHROMA_PERSIST_DIR", "./chroma_db"))
        ef = embedding_functions.DefaultEmbeddingFunction()
        collection = client.get_or_create_collection(
            "documents", embedding_function=ef  # type: ignore[arg-type]
        )
        where: dict | None = {"doc_id": {"$in": doc_ids}} if doc_ids else None  # type: ignore[type-arg]
        results = collection.query(query_texts=[question], n_results=top_k, where=where)
        raw_docs = results.get("documents")
        docs: list[str] = raw_docs[0] if raw_docs else []  # type: ignore[index]
        context = "\n\n".join(docs)
    except Exception:
        pass

    if not context:
        return "I could not find relevant information in the documents."

    api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    if not api_key:
        return f"Context found: {context[:500]}"

    import anthropic
    client_llm = anthropic.Anthropic(api_key=api_key)
    prompt = f"Context:\n{context}\n\nQuestion: {question}\n\nAnswer:"
    response = client_llm.messages.create(
        model=model,
        max_tokens=2048,
        messages=[{"role": "user", "content": prompt}],  # type: ignore[list-item]
    )
    block = response.content[0] if response.content else None
    return block.text if block and hasattr(block, "text") else ""  # type: ignore[union-attr]


def _extract_text(file_path: Path) -> str:
    # Validate again at extraction time — defensive in-depth
    if not str(file_path.resolve()).startswith(str(_UPLOAD_DIR) + os.sep):
        return ""
    ext = file_path.suffix.lower()
    if ext in (".txt", ".md", ".csv"):
        return file_path.read_text(encoding="utf-8", errors="ignore")
    if ext == ".pdf":
        try:
            import PyPDF2
            with open(file_path, "rb") as f:
                reader = PyPDF2.PdfReader(f)
                return "\n".join(page.extract_text() or "" for page in reader.pages)
        except Exception:
            return ""
    return ""


def _chunk_text(text: str, chunk_size: int = 1000, overlap: int = 100) -> list[str]:
    if not text.strip():
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = start + chunk_size
        chunks.append(text[start:end])
        start = end - overlap
    return chunks
