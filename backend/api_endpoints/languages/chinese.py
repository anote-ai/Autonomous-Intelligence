from flask import Blueprint, request, jsonify
from openai import OpenAI
import os
from werkzeug.utils import secure_filename
import PyPDF2
import pandas as pd
from docx import Document
import json


client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

chinese_blueprint = Blueprint('chinese', __name__)

MODEL_NAME = "ft:gpt-4.1-mini-2025-04-14:personal::BskbGPbc"

def extract_text_from_file(file_storage):
    filename = secure_filename(file_storage.filename)
    ext = os.path.splitext(filename)[1].lower()

    if ext == ".txt":
        file_storage.seek(0)
        return file_storage.read().decode("utf-8")

    elif ext == ".pdf":
        file_storage.seek(0)
        reader = PyPDF2.PdfReader(file_storage)
        text = ""
        for page in reader.pages:
            text += page.extract_text() or ""
        return text

    elif ext == ".docx":
        file_storage.seek(0)
        doc = Document(file_storage)
        return "\n".join([para.text for para in doc.paragraphs])

    elif ext == ".csv":
        file_storage.seek(0)
        df = pd.read_csv(file_storage)
        return df.to_string(index=False)

    else:
        raise ValueError("Unsupported file type.")

@chinese_blueprint.route("/api/chat/chinese", methods=["POST"])
def chat_chinese():
    try:
        file = request.files.get("file")
        messages_json = request.form.get("messages")

        messages = []
        prompt = ""

        if messages_json:
            try:
                messages = json.loads(messages_json)
                if messages and isinstance(messages, list):
                    prompt = messages[-1]["content"]
            except Exception as e:
                print("❌ Failed to parse messages:", e)

            print("🟡 Prompt:", prompt)
            print("🟡 File:", file)

        if not messages and not file:
            return jsonify({"error": "Missing messages or file"}), 400
        
        file_content = ""
        if file:
            try:
                file_content = extract_text_from_file(file)
            except Exception as e:
                return jsonify({"error": f"Failed to parse file: {str(e)}"}), 400

        if file_content:
            messages[-1]["content"] = f"""{messages[-1]["content"]}

Uploaded document:
\"\"\"
{file_content.strip()}
\"\"\""""
        
        full_messages = [
            {
                "role": "system",
                "content": "You are a chatbot assistant meant to speak to the user in chinese. You should help to user to answer on any questions in chinese. Respond in chinese no matter the language of the user. Be helpful and do not make up or hallucinate, if you do not know an answer, say you do not know."
            }
        ] + messages

        completion = client.chat.completions.create(
            model=MODEL_NAME,
            messages=full_messages
        )
        print("🧾 Sending messages to OpenAI:\n", json.dumps(messages, indent=2))

        reply = completion.choices[0].message.content
        return jsonify({"response": reply})

    except Exception as e:
        import logging
        logging.error(f"[ERROR] {str(e)}", exc_info=True)
        return jsonify({"error": "An internal error has occurred"}), 500