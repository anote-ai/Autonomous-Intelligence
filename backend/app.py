from flask import Flask
from flask_cors import CORS
from routes.file_routes import file_bp
from routes.health_routes import health_bp
from routes.auth_routes import auth_bp
from routes.chat_routes import chat_bp
from database.db import Database
import os
from flask_session import Session
import redis


app = Flask(__name__)

# Session configuration (must be set before Session initialization)
SECRET_KEY = os.getenv('SECRET_KEY')
if not SECRET_KEY:
    if os.getenv('FLASK_ENV') == 'development':
        # Insecure fallback for development only
        SECRET_KEY = 'dev-secret-key-change-in-production'
        print("WARNING: Using insecure development SECRET_KEY. Set SECRET_KEY environment variable in production!")
    else:
        raise RuntimeError("SECRET_KEY environment variable must be set in production")

app.config['SECRET_KEY'] = SECRET_KEY
app.config["SESSION_PERMANENT"] = False     # Sessions expire when browser closes
app.config["SESSION_TYPE"] = "redis"         # Use Redis for session storage (scalable)
app.config["SESSION_REDIS"] = redis.Redis(
    host=os.getenv("REDIS_HOST", "redis"),
    port=6379,
    db=1,  # Use db=1 for sessions (db=0 is used for caching)
    decode_responses=False  # Flask-Session expects bytes
)
# Require HTTPS cookies in production, allow HTTP in development
app.config["SESSION_COOKIE_SECURE"] = os.getenv('FLASK_ENV') != 'development'
app.config["SESSION_COOKIE_HTTPONLY"] = True  # Prevent JavaScript access
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"  # CSRF protection
app.config["SESSION_COOKIE_DOMAIN"] = None    # Allow localhost and 127.0.0.1

# Initialize Flask-Session
Session(app)

# Enable CORS with credentials support - include both localhost and 127.0.0.1
CORS(app, 
     origins=["http://localhost:5173", "http://127.0.0.1:5173"], 
     supports_credentials=True,
     allow_headers=["Content-Type", "Authorization"],
     methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
     expose_headers=["Set-Cookie"],
     max_age=3600)

Database.init_pool()

# Configuration
MAX_FILE_SIZE = 16 * 1024 * 1024  # 16MB

app.config['MAX_CONTENT_LENGTH'] = MAX_FILE_SIZE

# Register blueprints
app.register_blueprint(file_bp, url_prefix='/api')
app.register_blueprint(health_bp, url_prefix='/api')
app.register_blueprint(auth_bp, url_prefix='/api/auth')
app.register_blueprint(chat_bp, url_prefix='/api')


@app.errorhandler(413)
def request_entity_too_large(error):
    """Handle file too large error"""
    from flask import jsonify
    return jsonify({'error': 'File too large. Maximum size is 16MB'}), 413


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)