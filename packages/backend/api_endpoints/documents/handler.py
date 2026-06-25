"""Document endpoints — upload, list, delete, move, Q&A via RAG."""
from __future__ import annotations

import uuid
from pathlib import Path

from flask import Blueprint, jsonify, request
from flask_jwt_extended import get_jwt_identity

from database.db import (
    create_document,
    get_connection,
    get_document_by_uuid,
    get_documents,
    move_document,
)
from database.db import (
    delete_document as db_delete_document,
)
from middleware.auth import require_auth
from services.rag import UPLOAD_FOLDER, ingest_document, query_documents

documents_bp = Blueprint("documents", __name__, url_prefix="/api/documents")

_MIME_TO_EXT: dict[str, str] = {
    "application/pdf": ".pdf",
    "text/plain": ".txt",
    "text/markdown": ".md",
    "text/csv": ".csv",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
}


@documents_bp.post("/upload")
@require_auth
def upload() -> tuple:  # type: ignore[type-arg]
    if "file" not in request.files:
        return jsonify({"error": "No file provided"}), 400
    file = request.files["file"]

    content_type = (file.content_type or "").split(";")[0].strip().lower()
    ext = _MIME_TO_EXT.get(content_type)
    if not ext:
        return jsonify({"error": "Unsupported file type"}), 400

    folder_id_raw = request.form.get("folder_id")
    folder_id = int(folder_id_raw) if folder_id_raw and folder_id_raw.isdigit() else None

    doc_id = str(uuid.uuid4())
    save_path = UPLOAD_FOLDER / f"{doc_id}{ext}"

    try:
        file.save(save_path)
    except Exception as exc:
        print(f"Save failed: {exc}")
        return jsonify({"error": "Internal server error"}), 500

    try:
        chunk_count = ingest_document(doc_id=doc_id, file_path=save_path)
    except Exception as exc:
        save_path.unlink(missing_ok=True)
        print(f"Ingestion failed: {exc}")
        return jsonify({"error": "Internal server error"}), 500

    original_name = file.filename or f"upload{ext}"
    user_id = int(get_jwt_identity())

    try:
        cnx = get_connection()
        create_document(cnx, user_id, doc_id, original_name, chunk_count, folder_id)
        cnx.close()
    except Exception as exc:
        print(f"DB insert failed: {exc}")
        save_path.unlink(missing_ok=True)
        return jsonify({"error": "Internal server error"}), 500

    return jsonify({
        "id": doc_id,
        "filename": original_name,
        "chunks": chunk_count,
        "folder_id": folder_id,
    }), 201


@documents_bp.get("")
@require_auth
def list_documents() -> tuple:  # type: ignore[type-arg]
    folder_id_raw = request.args.get("folder_id")
    folder_id = int(folder_id_raw) if folder_id_raw and folder_id_raw.isdigit() else None
    try:
        cnx = get_connection()
        docs = get_documents(cnx, int(get_jwt_identity()), folder_id)
        cnx.close()
        return jsonify({"documents": docs}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@documents_bp.get("/<doc_id>")
@require_auth
def get_document(doc_id: str) -> tuple:  # type: ignore[type-arg]
    try:
        cnx = get_connection()
        doc = get_document_by_uuid(cnx, int(get_jwt_identity()), doc_id)
        cnx.close()
        if not doc:
            return jsonify({"error": "Document not found"}), 404
        return jsonify(doc), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@documents_bp.delete("/<doc_id>")
@require_auth
def remove_document(doc_id: str) -> tuple:  # type: ignore[type-arg]
    try:
        cnx = get_connection()
        doc = get_document_by_uuid(cnx, int(get_jwt_identity()), doc_id)
        if not doc:
            cnx.close()
            return jsonify({"error": "Document not found"}), 404
        db_delete_document(cnx, int(get_jwt_identity()), doc_id)
        cnx.close()
        for ext in (".pdf", ".txt", ".md", ".csv", ".docx"):
            Path(UPLOAD_FOLDER / f"{doc_id}{ext}").unlink(missing_ok=True)
        return jsonify({"deleted": True}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@documents_bp.patch("/<doc_id>/move")
@require_auth
def move(doc_id: str) -> tuple:  # type: ignore[type-arg]
    data = request.get_json(silent=True) or {}
    folder_id_raw = data.get("folder_id")
    folder_id = int(folder_id_raw) if folder_id_raw is not None and str(folder_id_raw).isdigit() else None
    try:
        cnx = get_connection()
        updated = move_document(cnx, int(get_jwt_identity()), doc_id, folder_id)
        cnx.close()
        if not updated:
            return jsonify({"error": "Document not found"}), 404
        return jsonify({"id": doc_id, "folder_id": folder_id}), 200
    except Exception:
        return jsonify({"error": "Internal server error"}), 500


@documents_bp.post("/<doc_id>/ask")
@require_auth
def ask_document(doc_id: str) -> tuple:  # type: ignore[type-arg]
    data = request.get_json(silent=True) or {}
    question = data.get("question", "").strip()
    if not question:
        return jsonify({"error": "question is required"}), 400
    model = data.get("model", "claude-sonnet-4-6")
    folder_id_raw = data.get("folder_id")
    folder_id = int(folder_id_raw) if folder_id_raw is not None and str(folder_id_raw).isdigit() else None

    try:
        if folder_id is not None:
            cnx = get_connection()
            docs = get_documents(cnx, int(get_jwt_identity()), folder_id)
            cnx.close()
            doc_ids = [d["id"] for d in docs]
        else:
            doc_ids = [doc_id]
        answer = query_documents(question=question, doc_ids=doc_ids, model=model)
        return jsonify({"answer": answer, "docId": doc_id}), 200
    except Exception as exc:
        print(f"Error answering document question: {exc}")
        return jsonify({"error": "Internal server error"}), 500
