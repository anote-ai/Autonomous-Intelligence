from datetime import datetime
from typing import Any, cast

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
    print("start time is", start_time)

    chat_id = request.form.getlist("chat_id")[0]
    files = request.files.getlist("files[]")
    max_chunk_size = 1000

    print("before files loop time is", datetime.now() - start_time)
    for file in files:
        filename = file.filename
        mime = _resolve_mime(file)
        category = _media_category(mime)

        if category == "text":
            subcategory = _text_subcategory(mime, filename or "")

            if subcategory == "tabular":
                # Native CSV / Excel parsing — preserves column structure
                raw = file.read()
                print(f"Ingesting tabular file: {filename} ({len(raw)} bytes)")
                text = ingest_tabular(raw, filename=filename, mime_type=mime)
                print(f"Tabular text ({len(text)} chars): {text[:120]}…")
                doc_id, does_exist = add_document(
                    text, filename, chat_id=chat_id, media_type="text", mime_type=mime
                )
                if not does_exist:
                    chunk_document_fn.remote(text, max_chunk_size, doc_id)

            elif subcategory == "plaintext":
                # Direct UTF-8 decode — faster and cleaner than Tika for raw text
                raw = file.read()
                print(f"Ingesting plain-text file: {filename} ({len(raw)} bytes)")
                text = ingest_plaintext(raw, filename=filename)
                doc_id, does_exist = add_document(
                    text, filename, chat_id=chat_id, media_type="text", mime_type=mime
                )
                if not does_exist:
                    chunk_document_fn.remote(text, max_chunk_size, doc_id)

            else:
                # PDF, DOCX, DOC, RTF, PPT … → Apache Tika (original path)
                result = parser_module.from_buffer(file)
                text = (result.get("content") or "").strip()
                doc_id, does_exist = add_document(
                    text, filename, chat_id=chat_id, media_type="text", mime_type=mime
                )
                if not does_exist:
                    chunk_document_fn.remote(text, max_chunk_size, doc_id)

        elif category == "image":
            image_bytes = file.read()
            print(f"Generating vision description for image: {filename} ({len(image_bytes)} bytes)")
            description = describe_image(image_bytes, mime_type=mime)
            print(f"Vision description ({len(description)} chars): {description[:120]}…")
            doc_id, does_exist = add_document(
                description, filename, chat_id=chat_id, media_type="image", mime_type=mime
            )
            if not does_exist and description:
                chunk_document_fn.remote(description, max_chunk_size, doc_id)

        elif category == "audio":
            audio_bytes = file.read()
            print(f"Transcribing audio: {filename} ({len(audio_bytes)} bytes)")
            transcript = transcribe_audio(audio_bytes, filename=filename)
            print(f"Transcript ({len(transcript)} chars): {transcript[:120]}…")
            doc_id, does_exist = add_document(
                transcript, filename, chat_id=chat_id, media_type="audio", mime_type=mime
            )
            if not does_exist and transcript:
                chunk_document_fn.remote(transcript, max_chunk_size, doc_id)

        else:  # video
            video_bytes = file.read()
            print(f"Analysing video: {filename} ({len(video_bytes)} bytes)")
            analysis = describe_video(video_bytes, filename=filename, mime_type=mime)
            print(f"Video analysis ({len(analysis)} chars): {analysis[:120]}…")
            doc_id, does_exist = add_document(
                analysis, filename, chat_id=chat_id, media_type="video", mime_type=mime
            )
            if not does_exist and analysis:
                chunk_document_fn.remote(analysis, max_chunk_size, doc_id)

    return jsonify({"Success": "Document Uploaded"}), 200


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
