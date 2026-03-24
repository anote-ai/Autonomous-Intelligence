"""
Re-export facade for database and finance-service functions.

Agents, the MCP server, and the SDK import from this module so that
the internal database/service structure can change without touching callers.
"""

from database.db import (
    access_shareable_chat,
    add_chat,
    add_document,
    add_message,
    add_model_key,
    add_prompt,
    add_prompt_answer,
    add_sources_to_message as add_sources_to_db,
    add_sources_to_prompt as add_wf_sources_to_db,
    change_chat_mode,
    create_chat_shareable_url,
    delete_chat,
    delete_doc,
    ensure_demo_user_exists,
    ensure_sdk_user_exists,
    find_most_recent_chat,
    get_chat_info,
    get_document_content,
    get_message_info,
    reset_chat,
    reset_uploaded_docs,
    retrieve_chats,
    retrieve_docs,
    retrieve_messages,
    retrieve_messages_from_share_uuid,
)
from flask import jsonify
from services import finance_gpt as finance_gpt_service

# ── aliases expected by callers ────────────────────────────────────────────────
add_chat_to_db = add_chat
add_document_to_db = add_document
add_message_to_db = add_message
add_model_key_to_db = add_model_key
add_prompt_to_db = add_prompt
add_answer_to_db = add_prompt_answer
change_chat_mode_db = change_chat_mode
create_chat_shareable_url = create_chat_shareable_url  # noqa: F811 (re-export)
delete_chat_from_db = delete_chat
delete_doc_from_db = delete_doc
ensure_demo_user_exists = ensure_demo_user_exists  # noqa: F811
ensure_SDK_user_exists = ensure_sdk_user_exists
find_most_recent_chat_from_db = find_most_recent_chat
get_chat_info = get_chat_info  # noqa: F811
get_document_content_from_db = get_document_content
get_message_info = get_message_info  # noqa: F811
reset_chat_db = reset_chat
reset_uploaded_docs = reset_uploaded_docs  # noqa: F811
retrieve_chats_from_db = retrieve_chats
retrieve_docs_from_db = retrieve_docs
retrieve_message_from_db = retrieve_messages
retrieve_messages_from_share_uuid = retrieve_messages_from_share_uuid  # noqa: F811
update_chat_name_db = None  # imported below to avoid circular alias

from database.db import update_chat_name  # noqa: E402
update_chat_name_db = update_chat_name

# ── finance-service re-exports ─────────────────────────────────────────────────
chunk_document = finance_gpt_service.chunk_document
chunk_document_by_page = finance_gpt_service.chunk_document_by_page
chunk_document_by_page_optimized = finance_gpt_service.chunk_document_by_page_optimized
chunk_document_optimized = finance_gpt_service.chunk_document_optimized
fast_pdf_ingestion = finance_gpt_service.fast_pdf_ingestion
get_relevant_chunks = finance_gpt_service.get_relevant_chunks
get_text_from_single_file = finance_gpt_service.get_text_from_single_file
get_text_from_url = finance_gpt_service.get_text_from_url
get_text_pages_from_single_file = finance_gpt_service.get_text_pages_from_single_file
knn = finance_gpt_service.knn
preload_embedding_model = finance_gpt_service.preload_embedding_model
preload_models = finance_gpt_service.preload_models
preload_text_splitter = finance_gpt_service.preload_text_splitter
prepare_chunks_for_embedding = finance_gpt_service.prepare_chunks_for_embedding


def access_sharable_chat(share_uuid, user_id=1):
    new_chat_id = access_shareable_chat(share_uuid, user_id)
    if new_chat_id is None:
        return jsonify({"error": "Snapshot not found"}), 404
    return jsonify({"new_chat_id": new_chat_id})
