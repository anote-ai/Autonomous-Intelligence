
from flask import jsonify
from database.db import delete_api_key

def DeleteAPIKeyHandler(request, api_key_id=None):
    if api_key_id is None:
        api_key_id = request.json["api_key_id"]
    delete_api_key(api_key_id)
    return jsonify({"status": "OK"})
