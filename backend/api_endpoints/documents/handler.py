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
        result = parser_module.from_buffer(file)
        text = result["content"].strip()
        filename = file.filename
        doc_id, does_exist = add_document(text, filename, chat_id=chat_id)
        if not does_exist:
            chunk_document_fn.remote(text, max_chunk_size, doc_id)

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
