
from flask import jsonify
from database.api_keys import create_api_key
from database.db_auth import user_has_credits

def generate_api_key(email, key_name=None, expires_at=None, rate_limit_per_minute=None):
    return create_api_key(
        email,
        name=key_name,
        expires_at=expires_at,
        rate_limit_per_minute=rate_limit_per_minute,
    )

def GenerateAPIKeyHandler(request, user_email):
    if not user_has_credits(user_email, min_credits=1):
        return jsonify({"error": "Insufficient credits. You need at least 1 credit to generate an API key."}), 402
    
    data = request.get_json() if request.is_json else {}
    key_name = data.get('name', 'Untitled Key')
    try:
        if data.get("expires_at") or data.get("rate_limit_per_minute"):
            result = generate_api_key(
                user_email,
                key_name,
                data.get("expires_at"),
                data.get("rate_limit_per_minute"),
            )
        else:
            result = generate_api_key(user_email, key_name)
        return jsonify(result)
    except Exception as e:
        print(f"Error generating API key: {e}")
        return jsonify({"error": "Internal server error"}), 500
