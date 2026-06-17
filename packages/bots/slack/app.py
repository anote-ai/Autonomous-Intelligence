"""
Anote Slack Bot
===============
Listens for @anote mentions in Slack channels and replies with AI responses
from the Anote backend.

Usage:
    pip install -r requirements.txt
    cp .env.example .env   # fill in your credentials
    python app.py
"""

import logging
import os
import re
import threading
from typing import Optional

from anthropic import Anthropic
from dotenv import load_dotenv
from flask import Flask, request
from slack_bolt import App
from slack_bolt.adapter.flask import SlackRequestHandler

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("anote.slack")

SLACK_BOT_TOKEN = os.environ["SLACK_BOT_TOKEN"]
SLACK_SIGNING_SECRET = os.environ["SLACK_SIGNING_SECRET"]
ANTHROPIC_API_KEY = os.environ["ANTHROPIC_API_KEY"]
SLACK_APP_TOKEN = os.environ.get("SLACK_APP_TOKEN", "")
MODEL = os.environ.get("ANOTE_MODEL", "claude-sonnet-4-6")
MAX_TOKENS = int(os.environ.get("ANOTE_MAX_TOKENS", "4096"))
PORT = int(os.environ.get("PORT", "3000"))
SLACK_MAX_CHARS = 2900

ANOTE_SYSTEM_PROMPT = """\
You are Anote, an expert AI coding assistant built by Anote AI.
You help developers write better code, fix bugs, explain concepts, review code,
generate tests, and refactor. You are responding via Slack — keep replies clear
and concise. Use Slack mrkdwn formatting (backticks for inline code, triple
backticks for code blocks). Avoid excessive markdown headers.
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


def trim_response(text: str, max_chars: int = SLACK_MAX_CHARS) -> str:
    if len(text) <= max_chars:
        return text
    cutoff = max_chars - 100
    return text[:cutoff] + "\n\n_(Response truncated — ask me to continue.)_"


def extract_query(text: str) -> Optional[str]:
    cleaned = re.sub(r"<@[A-Z0-9]+>", "", text, flags=re.IGNORECASE).strip()
    return cleaned if cleaned else None


slack_app = App(
    token=SLACK_BOT_TOKEN,
    signing_secret=SLACK_SIGNING_SECRET,
)


def build_blocks(text: str) -> list:
    return [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": trim_response(text),
            },
        }
    ]


@slack_app.event("app_mention")
def handle_mention(event, say, client, logger):
    text: str = event.get("text", "")
    channel: str = event["channel"]
    thread_ts: str = event.get("thread_ts", event["ts"])
    event_ts: str = event["ts"]

    logger.info(
        "app_mention — user=%s channel=%s text=%r",
        event.get("user"),
        channel,
        text[:80],
    )

    query = extract_query(text)
    if not query:
        say(
            text="Hi! Mention me with a question or command, e.g. `@anote explain src/index.ts`",
            thread_ts=thread_ts,
        )
        return

    thinking_ts: Optional[str] = None
    try:
        result = say(text="_Anote is thinking…_", thread_ts=event_ts)
        thinking_ts = result.get("ts") if result else None
    except Exception as exc:
        logger.warning("Could not post thinking message: %s", exc)

    def _run():
        try:
            answer = call_anote_backend(query)
        except Exception as exc:
            answer = f":warning: Anote encountered an error:\n```\n{exc}\n```"

        blocks = build_blocks(answer)

        try:
            if thinking_ts:
                client.chat_update(
                    channel=channel,
                    ts=thinking_ts,
                    text=answer,
                    blocks=blocks,
                )
            else:
                say(text=answer, blocks=blocks, thread_ts=event_ts)
        except Exception as exc:
            logger.error("Failed to post Slack reply: %s", exc, exc_info=True)

    threading.Thread(target=_run, daemon=True).start()


@slack_app.event("message")
def handle_message_events(event, logger):
    subtype = event.get("subtype", "")
    if subtype in ("bot_message", "message_changed", "message_deleted"):
        return
    logger.debug("Unhandled message event subtype=%r", subtype)


flask_app = Flask(__name__)
handler = SlackRequestHandler(slack_app)


@flask_app.route("/slack/events", methods=["POST"])
def slack_events():
    return handler.handle(request)


@flask_app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "anote-slack-bot"}


if __name__ == "__main__":
    if SLACK_APP_TOKEN:
        from slack_bolt.adapter.socket_mode import SocketModeHandler
        logger.info("Starting Slack bot in Socket Mode…")
        socket_handler = SocketModeHandler(slack_app, SLACK_APP_TOKEN)
        socket_handler.start()
    else:
        logger.info("Starting Slack bot in HTTP mode on port %d…", PORT)
        flask_app.run(host="0.0.0.0", port=PORT)
