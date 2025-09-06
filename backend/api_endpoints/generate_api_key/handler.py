
from flask import jsonify
from database.db import generate_api_key

def GenerateAPIKeyHandler(request, user_email):
    print(f"GenerateAPIKeyHandler called with user_email: {user_email}")
    data = request.get_json() if request.is_json else {}
    key_name = data.get('name', 'Untitled Key')
    print(f"Key name: {key_name}")
    try:
        result = generate_api_key(user_email, key_name)
        print(f"Generated API key result: {result}")
        return jsonify(result)
    except Exception as e:
        print(f"Error generating API key: {e}")
        return jsonify({"error": str(e)}), 500