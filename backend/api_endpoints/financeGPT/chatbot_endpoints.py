from flask import jsonify

from database.db import (
    add_chat,
    add_document,
    add_message,
    add_model_key,
    add_prompt,
    add_prompt_answer,
    add_sources_to_message,
    add_sources_to_prompt,
    access_shareable_chat,
    change_chat_mode,
    create_chat_shareable_url as create_shareable_url,
    delete_chat,
    delete_doc,
    ensure_demo_user_exists as ensure_demo_user,
    ensure_sdk_user_exists as ensure_sdk_user,
    find_most_recent_chat,
    get_chat_info as fetch_chat_info,
    get_document_content,
    get_message_info as fetch_message_info,
    reset_chat,
    reset_uploaded_docs as clear_uploaded_docs,
    retrieve_messages_from_share_uuid as fetch_messages_from_share_uuid,
    retrieve_chats,
    retrieve_docs,
    retrieve_messages,
    update_chat_name,
)
from services import finance_gpt as finance_gpt_service

_get_model = finance_gpt_service._get_model
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


def add_chat_to_db(user_email, chat_type, model_type):
    return add_chat(user_email, chat_type, model_type)


def create_chat_shareable_url(chat_id):
    return create_shareable_url(chat_id)


def access_sharable_chat(share_uuid, user_id=1):
    new_chat_id = access_shareable_chat(share_uuid, user_id)
    if new_chat_id is None:
        return jsonify({"error": "Snapshot not found"}), 404
    return jsonify({"new_chat_id": new_chat_id})


def update_chat_name_db(user_email, chat_id, new_name):
    return update_chat_name(user_email, chat_id, new_name)


def retrieve_chats_from_db(user_email):
    return retrieve_chats(user_email)


def find_most_recent_chat_from_db(user_email):
    return find_most_recent_chat(user_email)


def retrieve_message_from_db(user_email, chat_id, chat_type):
    return retrieve_messages(user_email, chat_id, chat_type)


def delete_chat_from_db(chat_id, user_email):
    return delete_chat(chat_id, user_email)


def retrieve_messages_from_share_uuid(share_uuid):
    return fetch_messages_from_share_uuid(share_uuid)


def get_document_content_from_db(document_id, email):
    return get_document_content(document_id, email)


def reset_chat_db(chat_id, user_email):
    return reset_chat(chat_id, user_email)


def reset_uploaded_docs(chat_id, user_email):
    return clear_uploaded_docs(chat_id, user_email)


def change_chat_mode_db(chat_mode_to_change_to, chat_id, user_email):
    return change_chat_mode(chat_mode_to_change_to, chat_id, user_email)


def add_document_to_db(text, document_name, chat_id=None):
    return add_document(text, document_name, chat_id)


def add_sources_to_db(message_id, sources):
    return add_sources_to_message(message_id, sources)


def add_wf_sources_to_db(prompt_id, sources):
    return add_sources_to_prompt(prompt_id, sources)


def add_message_to_db(text, chat_id, is_user, reasoning=None):
    return add_message(text, chat_id, is_user, reasoning)


def add_prompt_to_db(prompt_text):
    return add_prompt(prompt_text)


def add_answer_to_db(answer, citation_id):
    return add_prompt_answer(answer, citation_id)


def retrieve_docs_from_db(chat_id, user_email):
    return retrieve_docs(chat_id, user_email)


def delete_doc_from_db(doc_id, user_email):
    return delete_doc(doc_id, user_email)


def add_model_key_to_db(model_key, chat_id, user_email):
    return add_model_key(model_key, chat_id, user_email)


def ensure_demo_user_exists(user_email):
    return ensure_demo_user(user_email)


def ensure_SDK_user_exists(user_email):
    return ensure_sdk_user(user_email)


def get_chat_info(chat_id):
    return fetch_chat_info(chat_id)


def get_message_info(answer_id, user_email):
    return fetch_message_info(answer_id, user_email)
