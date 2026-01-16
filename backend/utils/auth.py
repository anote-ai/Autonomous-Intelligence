import redis
from flask import session, g, jsonify
from functools import wraps
import os
import ssl

# Configure Redis connection with optional password authentication and optional TLS
use_ssl = os.getenv("REDIS_USE_SSL", "false").lower() == "true"

if use_ssl:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", os.getenv("REDIS_IP", "redis")),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD", None),
        db=0,
        decode_responses=True,
    ssl_cert_reqs=ssl.CERT_REQUIRED if use_ssl else ssl.CERT_NONE,
        ssl_ca_certs=os.getenv("REDIS_SSL_CA_CERTS", None),
    )
else:
    redis_client = redis.Redis(
        host=os.getenv("REDIS_HOST", os.getenv("REDIS_IP", "redis")),
        port=int(os.getenv("REDIS_PORT", 6379)),
        password=os.getenv("REDIS_PASSWORD", None),
        db=0,
        decode_responses=True,
        ssl=False,
    )

def auth_required(f):
    """
    Decorator to protect routes that require authentication.
    Checks if user_id exists in session.
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        user_id = session.get('user_id')
        if not user_id:
            return jsonify({'error': 'Authentication required'}), 401
        
        # Store user_id in g for use within the request
        g.user_id = user_id
        return f(*args, **kwargs)
    return decorated_function
