"""Shared logic for all language-specific chat endpoints."""
import json
import logging
import os

import pandas as pd
import PyPDF2
from docx import Document
from flask import Blueprint, jsonify, request
from openai import OpenAI
from werkzeug.utils import secure_filename

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))


def extract_text_from_file(file_storage):
    filename = secure_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        file_storage.seek(0)
        return file_storage.read().decode("utf-8")
    elif ext == ".pdf":
        file_storage.seek(0)
        reader = PyPDF2.PdfReader(file_storage)
        return "".join(page.extract_text() or "" for page in reader.pages)
    elif ext == ".docx":
        file_storage.seek(0)
        doc = Document(file_storage)
        return "\n".join(para.text for para in doc.paragraphs)
    elif ext == ".csv":
        file_storage.seek(0)
        return pd.read_csv(file_storage).to_string(index=False)
    else:
        raise ValueError("Unsupported file type.")


def make_language_blueprint(
    name: str,
    route: str,
    model_name: str,
    system_prompt: str,
    language_suffix: str,
    empty_doc_response: str,
) -> Blueprint:
    """
    Factory that creates a Flask Blueprint for a language-specific chat endpoint.

    Args:
        name: Blueprint name (e.g. "arabic")
        route: URL route (e.g. "/api/chat/arabic")
        model_name: Fine-tuned model ID
        system_prompt: System message instructing the model to respond in the target language
        language_suffix: Text appended to the last user message to reinforce language choice
        empty_doc_response: Response text when the uploaded document contains no readable text
    """
    bp = Blueprint(name, __name__)

    @bp.route(route, methods=["POST"])
    def chat_handler():
        try:
            file = request.files.get("file")
            messages_json = request.form.get("messages")

            messages = []
            if messages_json:
                try:
                    messages = json.loads(messages_json)
                    if messages and isinstance(messages, list):
                        messages[-1]["content"] += f" {language_suffix}"
                except Exception:
                    logging.exception("Failed to parse messages JSON")

            if not messages and not file:
                return jsonify({"error": "Missing messages or file"}), 400

            file_content = ""
            if file:
                try:
                    file_content = extract_text_from_file(file)
                except Exception:
                    logging.exception("Failed to parse uploaded file")
                    return jsonify({"error": "Failed to parse file."}), 400

                if not file_content.strip():
                    return jsonify({"response": empty_doc_response})

            if file_content:
                messages[-1]["content"] = (
                    f'{messages[-1]["content"]}\n\nUploaded document:\n"""\n{file_content.strip()}\n"""'
                )

            full_messages = [{"role": "system", "content": system_prompt}] + messages

            completion = client.chat.completions.create(
                model=model_name,
                messages=full_messages,
            )
            return jsonify({"response": completion.choices[0].message.content})

        except Exception:
            logging.exception("Unhandled error in language chat endpoint")
            return jsonify({"error": "An internal error has occurred"}), 500

    # Give the view function a unique name so Flask doesn't complain about collisions
    chat_handler.__name__ = f"chat_{name}"
    return bp
