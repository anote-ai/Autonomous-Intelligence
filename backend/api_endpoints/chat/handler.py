from typing import Any, cast

from database.db import (
    add_chat,
    delete_chat,
    find_most_recent_chat,
    get_chat_info,
    retrieve_chats,
    retrieve_messages,
    update_chat_name,
)
from flask import Request, jsonify
from flask.typing import ResponseReturnValue


def CreateNewChatHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    chat_type = payload.get("chat_type")
    model_type = payload.get("model_type")
    chat_id = add_chat(user_email, chat_type, model_type)
    return jsonify(chat_id=chat_id)


def RetrieveChatsHandler(user_email: str) -> ResponseReturnValue:
    return jsonify(chat_info=retrieve_chats(user_email))


def RetrieveMessagesHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    chat_type = payload.get("chat_type")
    chat_id = payload.get("chat_id")
    messages = retrieve_messages(user_email, chat_id, chat_type)
    _, _, chat_name = get_chat_info(chat_id)
    return jsonify({"messages": messages, "chat_name": chat_name})


def UpdateChatNameHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    update_chat_name(user_email, payload.get("chat_id"), payload.get("chat_name"))
    return jsonify({"Success": "Chat name updated"}), 200


def DeleteChatHandler(request: Request, user_email: str) -> ResponseReturnValue:
    payload = cast(dict[str, Any], request.get_json(force=True))
    return jsonify({"message": delete_chat(payload.get("chat_id"), user_email)})


def FindMostRecentChatHandler(user_email: str) -> ResponseReturnValue:
    return jsonify(chat_info=find_most_recent_chat(user_email))
