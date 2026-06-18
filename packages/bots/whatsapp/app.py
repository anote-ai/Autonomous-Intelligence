"""
Anote WhatsApp Bot
==================
Receives incoming WhatsApp messages via Twilio's WhatsApp sandbox and replies
with AI responses from the Anote backend (Anthropic Claude).

Usage:
    pip install -r requirements.txt
    cp .env.example .env   # fill in your credentials
    python app.py

Configure your Twilio WhatsApp sandbox webhook to:
    POST https://<your-host>/whatsapp
"""

import logging
import os

from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, request
from twilio.twiml.messaging_response import MessagingResponse

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("anote.whatsapp")

ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
MODEL = os.environ.get("ANOTE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.environ.get("ANOTE_MAX_TOKENS", "1600"))
PORT = int(os.environ.get("PORT", "3002"))
WHATSAPP_MAX_CHARS = 1600

ANOTE_SYSTEM_PROMPT = """\
You are Anote, an expert AI coding assistant built by Anote AI.
You help developers write better code, fix bugs, explain concepts, review code,
generate tests, and refactor. You are responding via WhatsApp — keep replies
clear and concise. Use plain text; avoid heavy markdown. Short code snippets
are fine using backticks.
"""

anthropic_client = Anthropic(api_key=ANTHROPIC_API_KEY)


def call_anote_backend(prompt: str) -> str:
    logger.info("Calling Anote backend with prompt: %r", prompt[:120])
    try:
        response = anthropic_client.messages.create(
            model=MODEL,
            max_tokens=MAX_TOKENS,
            system=ANOTE_SYSTEM_PROMPT,
            messages=[{"role": "user", "content": prompt}],
        )
        text = response.content[0].text if response.content else ""
        logger.info("Anote backend returned %d chars", len(text))
        return text
    except Exception as exc:
        logger.error("Anthropic API error: %s", exc, exc_info=True)
        raise


def trim_response(text: str, max_chars: int = WHATSAPP_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    cutoff = max_chars - 80
    return text[:cutoff] + "\n\n(Truncated — reply 'more' to continue.)"


app = Flask(__name__)


@app.route("/whatsapp", methods=["POST"])
def whatsapp_reply():
    body = request.form.get("Body", "").strip()
    sender = request.form.get("From", "unknown")

    logger.info("Incoming WhatsApp from=%s body=%r", sender, body[:80])

    twiml = MessagingResponse()

    if not body:
        twiml.message("Hi! Send me a coding question and I'll help you out.")
        return str(twiml), 200, {"Content-Type": "text/xml"}

    try:
        answer = call_anote_backend(body)
        reply = trim_response(answer)
    except Exception as exc:
        logger.error("Backend error: %s", exc, exc_info=True)
        reply = "Sorry, Anote encountered an error. Please try again shortly."

    twiml.message(reply)
    return str(twiml), 200, {"Content-Type": "text/xml"}


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "anote-whatsapp-bot"}


if __name__ == "__main__":
    logger.info("Starting Anote WhatsApp bot on port %d…", PORT)
    app.run(host="0.0.0.0", port=PORT)
