
from flask import jsonify
from database.db import generate_api_key
from database.db_auth import user_has_credits

def GenerateAPIKeyHandler(request, user_email):
    print(f"GenerateAPIKeyHandler called with user_email: {user_email}")
    
    # Check if user has credits before generating API key
    if not user_has_credits(user_email, min_credits=1):
        print(f"User {user_email} has insufficient credits to generate API key")
        return jsonify({"error": "Insufficient credits. You need at least 1 credit to generate an API key."}), 403
    
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