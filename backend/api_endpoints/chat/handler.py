from flask import jsonify
from database.db import (
    add_chat,
    delete_chat,
    find_most_recent_chat,
    get_chat_info,
    retrieve_chats,
    retrieve_messages,
    update_chat_name,
)


def CreateNewChatHandler(request, user_email):
    chat_type = request.json.get("chat_type")
    model_type = request.json.get("model_type")
    chat_id = add_chat(user_email, chat_type, model_type)
    return jsonify(chat_id=chat_id)


def RetrieveChatsHandler(user_email):
    return jsonify(chat_info=retrieve_chats(user_email))


def RetrieveMessagesHandler(request, user_email):
    chat_type = request.json.get("chat_type")
    chat_id = request.json.get("chat_id")
    messages = retrieve_messages(user_email, chat_id, chat_type)
    _, _, chat_name = get_chat_info(chat_id)
    return jsonify({"messages": messages, "chat_name": chat_name})


def UpdateChatNameHandler(request, user_email):
    update_chat_name(user_email, request.json.get("chat_id"), request.json.get("chat_name"))
    return jsonify({"Success": "Chat name updated"}), 200


def DeleteChatHandler(request, user_email):
    return delete_chat(request.json.get("chat_id"), user_email)


def FindMostRecentChatHandler(user_email):
    return jsonify(chat_info=find_most_recent_chat(user_email))
