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
from services.vision_service import describe_image

# ---------------------------------------------------------------------------
# MIME-type helpers
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

# Extension → MIME fallback when the browser doesn't send a Content-Type
_EXT_TO_MIME: dict[str, str] = {
    "jpg": "image/jpeg", "jpeg": "image/jpeg", "png": "image/png",
    "gif": "image/gif", "webp": "image/webp", "bmp": "image/bmp",
    "tiff": "image/tiff", "tif": "image/tiff",
    "mp4": "video/mp4", "mov": "video/quicktime", "avi": "video/x-msvideo",
    "mkv": "video/x-matroska", "webm": "video/webm",
    "mp3": "audio/mpeg", "m4a": "audio/x-m4a", "ogg": "audio/ogg",
    "wav": "audio/wav", "aac": "audio/aac", "flac": "audio/flac",
}


def _resolve_mime(file) -> str:
    """Return the best-guess MIME type for an uploaded FileStorage object."""
    mime = (file.content_type or "").split(";")[0].strip().lower()
    if mime and mime != "application/octet-stream":
        return mime
    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    return _EXT_TO_MIME.get(ext, "application/octet-stream")


def _media_category(mime: str) -> str:
    """Map a MIME type to one of: 'text', 'image', 'video', 'audio'."""
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
            # Existing text-extraction path via Apache Tika
            result = parser_module.from_buffer(file)
            text = (result.get("content") or "").strip()
            doc_id, does_exist = add_document(
                text, filename, chat_id=chat_id, media_type="text", mime_type=mime
            )
            if not does_exist:
                chunk_document_fn.remote(text, max_chunk_size, doc_id)

        elif category == "image":
            # Vision-LLM path: generate a rich text description and index it
            # so the image is fully searchable via RAG.
            image_bytes = file.read()
            print(f"Generating vision description for image: {filename} ({len(image_bytes)} bytes)")
            description = describe_image(image_bytes, mime_type=mime)
            print(f"Vision description ({len(description)} chars): {description[:120]}…")
            doc_id, does_exist = add_document(
                description, filename, chat_id=chat_id, media_type="image", mime_type=mime
            )
            if not does_exist and description:
                chunk_document_fn.remote(description, max_chunk_size, doc_id)

        else:
            # video / audio — store the record without text for now.
            # Dedicated transcription pipelines (PRs 3 & 4) will fill these in.
            doc_id, does_exist = add_document(
                None, filename, chat_id=chat_id, media_type=category, mime_type=mime
            )

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
