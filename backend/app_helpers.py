from __future__ import annotations

import csv
import io
import json
import os
import re
import shutil
from collections.abc import Iterable
from datetime import datetime, timezone
from typing import Any

from flask import Response

# Export formats supported by export_chat_history (issue #134 — File Export).
SUPPORTED_EXPORT_FORMATS = ("csv", "markdown", "json", "text")


def build_oauth_state(redirect_uri: str, product_hash: str | None, free_trial_code: str | None) -> dict[str, str]:
    state = {"redirect_uri": redirect_uri}
    if product_hash:
        state["product_hash"] = product_hash
    if free_trial_code:
        state["free_trial_code"] = free_trial_code
    return state


def build_callback_redirect_url(
    default_referrer: str,
    access_token: str,
    refresh_token: str,
    product_hash: str | None,
    free_trial_code: str | None,
) -> str:
    redirect_url = f"{default_referrer}?accessToken={access_token}&refreshToken={refresh_token}"
    if product_hash is not None:
        redirect_url += f"&product_hash={product_hash}"
    if free_trial_code is not None:
        redirect_url += f"&free_trial_code={free_trial_code}"
    return redirect_url


def pair_chat_messages(messages: list[dict[str, Any]] | None) -> list[tuple[str, str, str | None, str | None]]:
    if messages is None:
        raise TypeError("messages must not be None")

    regex = re.compile(r"Document:\s*[^:]+:\s*(.*?)(?=Document:|$)", re.DOTALL)
    paired_messages: list[tuple[str, str, str | None, str | None]] = []

    for index in range(len(messages) - 1):
        current_message = messages[index]
        next_message = messages[index + 1]
        if current_message["sent_from_user"] != 1 or next_message["sent_from_user"] != 0:
            continue

        relevant_chunks = next_message["relevant_chunks"]
        if relevant_chunks:
            found = re.findall(regex, relevant_chunks)
            paragraphs = [paragraph.strip() for paragraph in found]
            if len(paragraphs) > 1:
                paired_messages.append(
                    (
                        current_message["message_text"],
                        next_message["message_text"],
                        paragraphs[0],
                        paragraphs[1],
                    )
                )
            elif len(paragraphs) == 1:
                paired_messages.append(
                    (
                        current_message["message_text"],
                        next_message["message_text"],
                        paragraphs[0],
                        None,
                    )
                )
        else:
            paired_messages.append(
                (current_message["message_text"], next_message["message_text"], None, None)
            )

    return paired_messages


def chat_history_csv_response(
    paired_messages: Iterable[tuple[str, str, str | None, str | None]]
) -> Response:
    csv_output = io.StringIO()
    writer = csv.writer(csv_output)
    writer.writerow(["query", "response", "chunk1", "chunk2"])
    writer.writerows(paired_messages)
    csv_output.seek(0)
    return Response(
        csv_output.getvalue(),
        mimetype="text/csv",
        headers={"Content-disposition": "attachment; filename=chat_history.csv"},
    )


class UnsupportedExportFormatError(ValueError):
    """Raised when a caller requests an export format we don't support."""


def chat_history_markdown_response(
    paired_messages: Iterable[tuple[str, str, str | None, str | None]],
    *,
    title: str = "Chat History",
) -> Response:
    """Render paired Q&A turns (with evidence chunks, if any) as Markdown.

    Preserves the retrieved source chunks alongside each answer so the
    exported file remains useful/auditable outside the app (provenance).
    """
    lines = [f"# {title}", "", f"_Exported: {datetime.now(timezone.utc).isoformat()}_", ""]
    for query, response, chunk1, chunk2 in paired_messages:
        lines.append(f"## Q: {query}")
        lines.append("")
        lines.append(response)
        lines.append("")
        chunks = [chunk for chunk in (chunk1, chunk2) if chunk]
        if chunks:
            lines.append("**Sources:**")
            for chunk in chunks:
                lines.append(f"> {chunk}")
            lines.append("")
    body = "\n".join(lines).rstrip() + "\n"
    return Response(
        body,
        mimetype="text/markdown",
        headers={"Content-disposition": "attachment; filename=chat_history.md"},
    )


def chat_history_json_response(
    paired_messages: Iterable[tuple[str, str, str | None, str | None]],
) -> Response:
    """Render paired Q&A turns as a structured JSON document.

    Keeps source-chunk provenance per turn so downstream tools can trace
    answers back to the evidence used to generate them.
    """
    records = [
        {
            "query": query,
            "response": response,
            "sources": [chunk for chunk in (chunk1, chunk2) if chunk],
        }
        for query, response, chunk1, chunk2 in paired_messages
    ]
    payload = {
        "exportedAt": datetime.now(timezone.utc).isoformat(),
        "messages": records,
    }
    body = json.dumps(payload, indent=2, default=str)
    return Response(
        body,
        mimetype="application/json",
        headers={"Content-disposition": "attachment; filename=chat_history.json"},
    )


def chat_history_text_response(
    paired_messages: Iterable[tuple[str, str, str | None, str | None]],
) -> Response:
    """Render paired Q&A turns as plain text."""
    lines: list[str] = []
    for query, response, chunk1, chunk2 in paired_messages:
        lines.append(f"Q: {query}")
        lines.append(f"A: {response}")
        for chunk in (chunk1, chunk2):
            if chunk:
                lines.append(f"Source: {chunk}")
        lines.append("")
    body = "\n".join(lines).rstrip() + "\n"
    return Response(
        body,
        mimetype="text/plain",
        headers={"Content-disposition": "attachment; filename=chat_history.txt"},
    )


def chat_history_export_response(
    paired_messages: Iterable[tuple[str, str, str | None, str | None]],
    export_format: str,
) -> Response:
    """Dispatch to the correct chat-history export renderer by format name.

    Supported formats: csv, markdown, json, text (see SUPPORTED_EXPORT_FORMATS).
    Raises UnsupportedExportFormatError for anything else so callers can map
    it to a 400 response.
    """
    fmt = (export_format or "csv").strip().lower()
    if fmt not in SUPPORTED_EXPORT_FORMATS:
        raise UnsupportedExportFormatError(
            f"Unsupported export format '{export_format}'. "
            f"Supported formats: {', '.join(SUPPORTED_EXPORT_FORMATS)}"
        )

    # paired_messages may be a one-shot generator/iterator in some call sites;
    # materialize once so every branch below can safely consume it.
    paired_messages = list(paired_messages)

    if fmt == "csv":
        return chat_history_csv_response(paired_messages)
    if fmt == "markdown":
        return chat_history_markdown_response(paired_messages)
    if fmt == "json":
        return chat_history_json_response(paired_messages)
    return chat_history_text_response(paired_messages)


def reset_local_chat_artifacts(source_documents_path: str, output_document_path: str) -> str:
    if os.path.exists(source_documents_path):
        shutil.rmtree(source_documents_path)
    if os.path.exists(output_document_path):
        shutil.rmtree(output_document_path)
        os.makedirs(output_document_path)

    chat_history_file_path = os.path.join(output_document_path, "chat_history.csv")
    with open(chat_history_file_path, "w", newline="", encoding="utf-8") as csvfile:
        writer = csv.writer(csvfile)
        writer.writerow(["query", "response"])

    return "Reset was successful!"
