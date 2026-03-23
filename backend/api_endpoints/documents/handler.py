from datetime import datetime
from flask import jsonify
from database.db import (
    add_document,
    change_chat_mode,
    delete_doc,
    reset_chat,
    reset_uploaded_docs,
    retrieve_docs,
)


def IngestDocumentsHandler(request, user_email, parser_module, chunk_document_fn):
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


def RetrieveCurrentDocsHandler(request, user_email):
    return jsonify(doc_info=retrieve_docs(request.json.get("chat_id"), user_email))


def DeleteDocHandler(request, user_email):
    delete_doc(request.json.get("doc_id"), user_email)
    return "success"


def ChangeChatModeHandler(request, user_email):
    chat_id = request.json.get("chat_id")
    chat_mode = request.json.get("model_type")
    try:
        reset_chat(chat_id, user_email)
        change_chat_mode(chat_mode, chat_id, user_email)
        return "Success"
    except Exception:
        return "Error"


def ResetChatHandler(request, user_email):
    chat_id = request.json.get("chat_id")
    if request.json.get("delete_docs"):
        reset_uploaded_docs(chat_id, user_email)
    reset_chat(chat_id, user_email)
    return jsonify({"Success": "Success"}), 200
