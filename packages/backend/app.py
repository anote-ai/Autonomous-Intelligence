"""Anote AI unified backend — Flask application factory."""
from __future__ import annotations

import os

from flask import Flask, jsonify
from flask_cors import CORS
from flask_jwt_extended import JWTManager

from api_endpoints.auth.handler import auth_bp
from api_endpoints.chat.handler import chat_bp
from api_endpoints.documents.handler import documents_bp
from api_endpoints.payments.handler import payments_bp
from api_endpoints.search.handler import search_bp
from api_endpoints.user.handler import user_bp
from api_endpoints.workspaces.handler import workspaces_bp


def create_app(config: dict | None = None) -> Flask:
    """Create and configure the Flask application."""
    app = Flask(__name__)

    app.config.update(
        SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me"),
        JWT_SECRET_KEY=os.environ.get("JWT_SECRET_KEY", "dev-secret-change-me"),
        JWT_ACCESS_TOKEN_EXPIRES=False,
        TESTING=False,
        DB_HOST=os.environ.get("DB_HOST", "localhost"),
        DB_NAME=os.environ.get("DB_NAME", "anote"),
        DB_USER=os.environ.get("DB_USER", "root"),
        DB_PASSWORD=os.environ.get("DB_PASSWORD", ""),
        REDIS_URL=os.environ.get("REDIS_URL", "redis://localhost:6379"),
        ANTHROPIC_API_KEY=os.environ.get("ANTHROPIC_API_KEY", ""),
        OPENAI_API_KEY=os.environ.get("OPENAI_API_KEY", ""),
        GEMINI_API_KEY=os.environ.get("GEMINI_API_KEY", ""),
        STRIPE_SECRET_KEY=os.environ.get("STRIPE_SECRET_KEY", ""),
        UPLOAD_FOLDER=os.environ.get("UPLOAD_FOLDER", "/tmp/anote_uploads"),
    )
    if config:
        app.config.update(config)

    CORS(app, resources={r"/*": {"origins": "*"}})
    JWTManager(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(chat_bp)
    app.register_blueprint(documents_bp)
    app.register_blueprint(search_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(payments_bp)
    app.register_blueprint(workspaces_bp)

    @app.get("/health")
    def health() -> tuple:
        return jsonify({"status": "ok", "service": "anote-backend"}), 200

    @app.get("/")
    def root() -> tuple:
        return jsonify({"name": "Anote AI Backend", "version": "1.0.0"}), 200

    return app


if __name__ == "__main__":
    app = create_app()
    port = int(os.environ.get("PORT", 5000))
    debug = os.environ.get("APP_ENV", "local") == "local"
    app.run(host="0.0.0.0", port=port, debug=debug)
