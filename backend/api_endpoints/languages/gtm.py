from .language_chat import client, extract_text_from_file, make_language_blueprint
from flask import Blueprint, request, jsonify
import json
import logging

gpt4_blueprint = Blueprint('gpt4', __name__)


@gpt4_blueprint.route("/gtm/respond", methods=["POST"])
def generate_response_openai():
    MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BvmGNtx5"
    try:
        file = request.files.get("file")
        messages_json = request.form.get("messages")

        messages = []
        if messages_json:
            try:
                messages = json.loads(messages_json)
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

        if file_content:
            messages[-1]["content"] = (
                f'{messages[-1]["content"]}\n\nUploaded document:\n"""\n{file_content.strip()}\n"""'
            )

        system_content = "You are a chatbot assistant for the company Anote. You should help the user to answer their question."
        if file:
            system_content += " You may also use the uploaded document if available."

        full_messages = [{"role": "system", "content": system_content}] + messages

        completion = client.chat.completions.create(model=MODEL_NAME, messages=full_messages)
        return jsonify({"response": completion.choices[0].message.content})

    except Exception:
        logging.exception("Unhandled error in GTM endpoint")
        return jsonify({"error": "An internal error has occurred"}), 500


handler = gpt4_blueprint
