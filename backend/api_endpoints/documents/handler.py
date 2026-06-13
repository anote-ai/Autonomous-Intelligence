import logging
from datetime import datetime
from typing import Any, cast

from agents.config import AgentConfig
from database.db import (
    add_document,
    change_chat_mode,
    delete_doc,
    reset_chat,
    reset_uploaded_docs,
    retrieve_docs,
)
from flask import Request, jsonify
from flask.typing import ResponseReturnValue
from services.audio_service import transcribe_audio
from services.tabular_service import ingest_plaintext, ingest_tabular
from services.video_service import describe_video
from services.vision_service import describe_image

logger = logging.getLogger(__name__)

# Hard upper bound on files per upload batch. Prevents a single request from
# consuming arbitrary handler time / memory. Tune via env var if needed.
MAX_FILES_PER_BATCH = 50

# Per-category byte limits — used by handler to reject oversized files BEFORE
# loading them into memory. These mirror the limits already enforced by the
# downstream services so users get an early, clear rejection.
#
# Read via getattr so the handler stays importable when AgentConfig is stubbed
# (e.g. in test suites) without these attributes.
_CATEGORY_BYTE_LIMITS: dict[str, int] = {
    "image": getattr(AgentConfig, "MAX_IMAGE_BYTES", 20 * 1024 * 1024),
    "audio": getattr(AgentConfig, "MAX_AUDIO_BYTES", 25 * 1024 * 1024),
    "video": getattr(AgentConfig, "MAX_VIDEO_BYTES", 500 * 1024 * 1024),
    # Text covers PDF/DOCX/CSV/etc. — there is no service-level cap today, so
    # we apply a generous default (20 MB) to keep parser latency reasonable.
    "text": 20 * 1024 * 1024,
}

# ---------------------------------------------------------------------------
# MIME-type classification
# ---------------------------------------------------------------------------

_IMAGE_MIMES = {
    "image/jpeg", "image/png", "image/gif", "image/webp",
    "image/bmp", "image/tiff", "image/svg+xml",
}
_VIDEO_MIMES = {
    "video/mp4", "video/quicktime", "video/x-msvideo", "video/x-matroska",
    "video/webm", "video/mpeg", "video/ogg",
}
_AUDIO_MIMES = {
    "audio/mpeg", "audio/mp4", "audio/ogg", "audio/wav", "audio/webm",
    "audio/x-m4a", "audio/aac", "audio/flac",
}
# Spreadsheet formats that lose structure when run through Tika
_TABULAR_MIMES = {
    "text/csv",
    "text/tab-separated-values",
    "application/vnd.ms-excel",                                          # .xls
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", # .xlsx
    "application/vnd.oasis.opendocument.spreadsheet",                    # .ods
}
# Plain-text formats — read directly, no Tika overhead
_PLAINTEXT_MIMES = {
    "text/plain",
    "text/markdown",
    "text/x-markdown",
    "text/x-rst",
    "text/x-python",
    "text/javascript",
    "text/html",
    "text/xml",
    "application/json",
    "application/xml",
}

# Extension → MIME fallback when the browser omits or sends octet-stream
_EXT_TO_MIME: dict[str, str] = {
    # images
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
    "tiff": "image/tiff", "tif": "image/tiff",
    # video
    "mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo",
    "mkv": "video/x-matroska", "webm": "video/webm",
    # audio
    "mp3": "audio/mpeg", "m4a": "audio/x-m4a", "ogg": "audio/ogg",
    "wav": "audio/wav", "aac": "audio/aac", "flac": "audio/flac",
    # tabular
    "csv": "text/csv", "tsv": "text/tab-separated-values",
    "xls": "application/vnd.ms-excel",
    "xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "ods": "application/vnd.oasis.opendocument.spreadsheet",
    # plaintext
    "txt": "text/plain", "md": "text/markdown", "markdown": "text/markdown",
    "rst": "text/x-rst", "py": "text/x-python", "js": "text/javascript",
    "json": "application/json", "xml": "application/xml",
    "html": "text/html", "htm": "text/html",
}


def _resolve_mime(file: Any) -> str:
    """Return the best-guess MIME type for an uploaded FileStorage object."""
    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime and mime != "application/octet-stream":
        return mime
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    return _EXT_TO_MIME.get(ext, "application/octet-stream")


def _text_subcategory(mime: str, filename: str) -> str:
    """Within the broad 'text' category return a finer subcategory."""
    if mime in _TABULAR_MIMES:
        return "tabular"
    if mime in _PLAINTEXT_MIMES:
        return "plaintext"
    # Extension-based fallback (MIME might be generic text/plain for .csv)
    ext = (filename or "").rsplit(".", 1)[-1].lower()
    if ext in ("csv", "tsv", "xls", "xlsx", "ods"):
        return "tabular"
    if ext in ("txt", "md", "markdown", "rst", "py", "js", "json", "xml", "html", "htm"):
        return "plaintext"
    return "document"  # PDF, DOCX, DOC, RTF → Tika


def _media_category(mime: str) -> str:
    """Map a MIME type to a top-level category."""
    if mime in _IMAGE_MIMES:
        return "image"
    if mime in _VIDEO_MIMES:
        return "video"
    if mime in _AUDIO_MIMES:
        return "audio"
    return "text"


def _mask_email(email: str) -> str:
    """Mask the local part of an email for safe logging.

    `alice@example.com` → `a***@example.com`. Keeps the domain visible so
    operators can still group log lines by tenant / org while avoiding direct
    PII exposure in log aggregators (GDPR / CCPA hygiene).
    """
    if not email or "@" not in email:
        return "***"
    local, _, domain = email.partition("@")
    if not local:
        return "***@" + domain
    return local[0] + "***@" + domain


def _file_size_bytes(file: Any) -> int:
    """Return the upload size in bytes without reading the body into memory.

    Tries `content_length` first (HTTP header, populated by Flask/Werkzeug for
    most uploads). Falls back to a non-destructive stream seek/tell — by this
    point Werkzeug has already buffered the upload (in memory or a temp file)
    so seek/tell does NOT trigger an additional allocation.

    Returns 0 if the size cannot be determined.
    """
    cl = getattr(file, "content_length", 0) or 0
    if cl > 0:
        return int(cl)

    stream = getattr(file, "stream", None)
    if stream is None or not hasattr(stream, "seek") or not hasattr(stream, "tell"):
        return 0

    try:
        cur = stream.tell()
        stream.seek(0, 2)  # SEEK_END
        size = stream.tell()
        stream.seek(cur)
        return int(size)
    except (OSError, ValueError):
        return 0


def _too_large(file: Any, category: str) -> tuple[bool, int, int]:
    """Check if *file* exceeds the limit for *category*.

    Returns (is_too_large, actual_bytes, limit_bytes). When the size cannot be
    determined we allow the upload (returns False) — the downstream service
    layer enforces its own cap as a backstop.
    """
    limit = _CATEGORY_BYTE_LIMITS.get(category, 0)
    actual = _file_size_bytes(file)
    if limit <= 0 or actual <= 0:
        return False, actual, limit
    return actual > limit, actual, limit


# ---------------------------------------------------------------------------
# Handlers
# ---------------------------------------------------------------------------

def IngestDocumentsHandler(
    request: Request,
    user_email: str,
    parser_module: Any,
    chunk_document_fn: Any,
) -> ResponseReturnValue:
    start_time = datetime.now()
    logger.info("ingest_documents start")

    # --- chat_id: safe extraction with 400 on missing -------------------------
    chat_ids = request.form.getlist("chat_id")
    if not chat_ids or not chat_ids[0]:
        return jsonify({
            "error": "missing_chat_id",
            "message": "'chat_id' form field is required.",
        }), 400
    chat_id = chat_ids[0]

    # --- files: validate batch shape ------------------------------------------
    files = request.files.getlist("files[]")
    if not files:
        return jsonify({
            "error": "no_files",
            "message": "No files provided under 'files[]'.",
        }), 400

    if len(files) > MAX_FILES_PER_BATCH:
        return jsonify({
            "error": "too_many_files",
            "message": (
                f"Upload batch contains {len(files)} files; "
                f"limit is {MAX_FILES_PER_BATCH} per request."
            ),
            "limit": MAX_FILES_PER_BATCH,
            "received": len(files),
        }), 413  # Payload Too Large

    max_chunk_size = 1000
    uploaded: list[dict[str, Any]] = []
    failed: list[dict[str, Any]] = []
    skipped: list[dict[str, Any]] = []

    for file in files:
        filename = file.filename or "<unnamed>"
        mime = _resolve_mime(file)
        category = _media_category(mime)

        # --- size pre-check (defense in depth) --------------------------------
        is_big, actual, limit = _too_large(file, category)
        if is_big:
            logger.warning(
                "rejecting oversized %s '%s': %d bytes > %d limit",
                category, filename, actual, limit,
            )
            skipped.append({
                "filename": filename,
                "reason": "file_too_large",
                "size_bytes": actual,
                "limit_bytes": limit,
                "category": category,
            })
            continue

        # --- per-file try/except: one failure does not poison the batch ------
        try:
            doc_id = _ingest_single_file(
                file=file,
                filename=filename,
                mime=mime,
                category=category,
                chat_id=chat_id,
                max_chunk_size=max_chunk_size,
                parser_module=parser_module,
                chunk_document_fn=chunk_document_fn,
            )
            uploaded.append({
                "filename": filename,
                "category": category,
                "doc_id": doc_id,
            })
        except Exception as exc:  # noqa: BLE001 — surface any failure to the user
            # Full stack trace + exception message goes to server logs only.
            # The HTTP response carries the exception class name (a stable,
            # non-sensitive identifier) so clients can branch on failure type
            # without internal paths / SQL / secrets leaking out.
            logger.exception("ingest failed for '%s'", filename)
            failed.append({
                "filename": filename,
                "category": category,
                "error": exc.__class__.__name__,
            })

    elapsed = (datetime.now() - start_time).total_seconds()
    logger.info(
        "ingest_documents done elapsed=%.2fs uploaded=%d failed=%d skipped=%d",
        elapsed, len(uploaded), len(failed), len(skipped),
    )

    # Backward-compatible Success key kept for existing frontend code; new
    # callers should read uploaded/failed/skipped for per-file outcomes.
    return jsonify({
        "Success": "Document Uploaded" if not failed and not skipped else "Partial success",
        "uploaded": uploaded,
        "failed": failed,
        "skipped": skipped,
        "elapsed_seconds": round(elapsed, 3),
    }), 200


def _ingest_single_file(
    *,
    file: Any,
    filename: str,
    mime: str,
    category: str,
    chat_id: str,
    max_chunk_size: int,
    parser_module: Any,
    chunk_document_fn: Any,
) -> int:
    """Ingest one file. Returns the new doc_id. Raises on any failure."""
    if category == "text":
        subcategory = _text_subcategory(mime, filename)

        if subcategory == "tabular":
            raw = file.read()
            text = ingest_tabular(raw, filename=filename, mime_type=mime)
        elif subcategory == "plaintext":
            raw = file.read()
            text = ingest_plaintext(raw, filename=filename)
        else:
            # PDF, DOCX, DOC, RTF, PPT … → Apache Tika
            result = parser_module.from_buffer(file)
            text = (result.get("content") or "").strip()

        doc_id, does_exist = add_document(
            text, filename, chat_id=chat_id, media_type="text", mime_type=mime
        )
        if not does_exist:
            chunk_document_fn.remote(text, max_chunk_size, doc_id)
        return cast(int, doc_id)

    if category == "image":
        image_bytes = file.read()
        description = describe_image(image_bytes, mime_type=mime)
        doc_id, does_exist = add_document(
            description, filename, chat_id=chat_id, media_type="image", mime_type=mime
        )
        if not does_exist and description:
            chunk_document_fn.remote(description, max_chunk_size, doc_id)
        return cast(int, doc_id)

    if category == "audio":
        audio_bytes = file.read()
        transcript = transcribe_audio(audio_bytes, filename=filename)
        doc_id, does_exist = add_document(
            transcript, filename, chat_id=chat_id, media_type="audio", mime_type=mime
        )
        if not does_exist and transcript:
            chunk_document_fn.remote(transcript, max_chunk_size, doc_id)
        return cast(int, doc_id)

    # video
    video_bytes = file.read()
    analysis = describe_video(video_bytes, filename=filename, mime_type=mime)
    doc_id, does_exist = add_document(
        analysis, filename, chat_id=chat_id, media_type="video", mime_type=mime
    )
    if not does_exist and analysis:
        chunk_document_fn.remote(analysis, max_chunk_size, doc_id)
    return cast(int, doc_id)


def RetrieveCurrentDocsHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    return jsonify(doc_info=retrieve_docs(payload.get("chat_id"), user_email))


def DeleteDocHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    delete_doc(payload.get("doc_id"), user_email)
    return "success"


def ChangeChatModeHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    chat_id = payload.get("chat_id")
    chat_mode = payload.get("model_type")
    try:
        reset_chat(chat_id, user_email)
        change_chat_mode(chat_mode, chat_id, user_email)
        return "Success"
    except Exception:
        return "Error"


def ResetChatHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    chat_id = payload.get("chat_id")
    if payload.get("delete_docs"):
        reset_uploaded_docs(chat_id, user_email)
    reset_chat(chat_id, user_email)
    return jsonify({"Success": "Success"}), 200
