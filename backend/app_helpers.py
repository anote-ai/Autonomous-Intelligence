from __future__ import annotations

import csv
import io
import os
import re
import shutil
from collections.abc import Iterable
from typing import Any

from flask import Response


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
