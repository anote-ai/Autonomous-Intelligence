import os
import sqlite3
import ollama
import json
import requests

from tika import parser as p

from handlers.private_db import *
from handlers.public_handlers import is_file_or_isHtml

USER_SDK_EMAIL = "api@example.com"

def upload_private(task_type, model_type, ticker, file_paths):
    user_id = create_db_file()

    conn, cursor = get_db_connection()


    task_type_mapping = {"documents": 0, "edgar": 1}
    task_type_number = task_type_mapping.get(task_type, task_type)

    model_type_mapping = {"llama": 0, "mistral": 1}
    model_type_number = model_type_mapping.get(model_type, model_type)

    cursor.execute('INSERT INTO chats (user_id, model_type, associated_task) VALUES (?, ?, ?)', (user_id, model_type_number, task_type_number))
    chat_id = cursor.lastrowid

    conn.commit()
    conn.close()

    files = []
    paths = []

    if task_type == "documents":
        if file_paths is None:
            return {"error": "No files uploaded. Please upload at least one file."}
        for path in file_paths:
            if is_file_or_isHtml(path) == "file":
                files.append(path)
            elif is_file_or_isHtml(path) == "html":
                #text = get_text_from_url(path) #from chatbot_endpoints
                paths.append(path)
            else:
                return {"error": f"Invalid file path or URL: {path}"}
        process_files(task_type, files, paths, USER_SDK_EMAIL, model_type, chat_id)
    return {'id': chat_id}

def chat_private(chat_id, message, finetuned_model_key=None):

    conn, cursor = get_db_connection()

    model_type, task_type = get_chat_info(chat_id)

    add_message_to_db(message, chat_id, 1)

    #Get most relevant section from the document
    sources = get_relevant_chunks(2, message, chat_id)
    sources_str = " ".join([", ".join(str(elem) for elem in source) for source in sources])
    sources_swapped = [[str(elem) for elem in source[::-1]] for source in sources]


    if (model_type == 0):
        response = ollama.chat(model='llama2', messages=[
            {
            'role': 'user',
            'content': f'You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{message}.',

            },
        ])
        answer = response['message']['content']
    else:
        response = ollama.chat(model='mistral', messages=[
            {
            'role': 'user',
            'content': f'You are a factual chatbot that answers questions about uploaded documents. You only answer with answers you find in the text, no outside information. These are the sources from the text:{sources_str} And this is the question:{message}.',

            },
        ])
        answer = response['message']['content']

    #This adds bot message
    message_id = add_message_to_db(answer, chat_id, 0)

    try:
        add_sources_to_db(message_id, sources)
    except:
        print("error adding sources to db or no sources")

    response_dict = {
        "message_id": message_id,
        "answer": answer,
        "sources": sources_swapped
    }

    return response_dict


def evaluate_private(message_id):
    question_json, answer_json = get_message_info(message_id)

    question = question_json['message_text']
    answer = answer_json['message_text']
    context = answer_json['relevant_chunks']

    #get it in the corret data format to put in ragas
    if not isinstance(context, list):
        context = [context]

    contexts = [context]

    data = {
        "question": [question],
        "answer": [answer],
        "contexts": contexts
    }

    result = data

    return result


def process_files(chat_type, files, paths, user_email, model_type, chat_id):
    import ray
    ray.init(ignore_reinit_error=True)
    if chat_type == "documents": #question-answering
        #Ingest pdf
        MAX_CHUNK_SIZE = 1000

        for file in files:

            result = p.from_file(file)
            text = result["content"].strip()

            filename = file

            doc_id, doesExist = add_document_to_db(text, filename, chat_id=chat_id)

            if not doesExist:
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                result = ray.get(result_id)
        for path in paths:
            text = get_text_from_url(path)

            doc_id, doesExist = add_document_to_db(text, path, chat_id=chat_id)

            if not doesExist:
                result_id = chunk_document.remote(text, MAX_CHUNK_SIZE, doc_id)
                result = ray.get(result_id)
    else:
        return {"id": "Please enter a valid task type"}

    return {"id": chat_id}

def get_text_from_url(web_url):
    response = requests.get(web_url)
    result = p.from_buffer(response.content)
    text = result["content"].strip()
    text = text.replace("\n", "").replace("\t", "")
    return text

