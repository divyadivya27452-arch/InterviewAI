"""
Interview AI — Flask Application Entry Point.
"""

import logging
import os

from config import Config
from flask import Flask, jsonify, redirect, request, url_for
from flask_cors import CORS
from pymongo import ASCENDING, DESCENDING, MongoClient
from routes.auth import auth_bp, get_current_user, serialize_user
from routes.dashboard import dashboard_bp
from routes.interview import interview_bp
from routes.profile import profile_bp

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)


def create_app(config_class=Config) -> Flask:
    """Application factory creating and configuring the Flask app."""
    app = Flask(__name__)
    app.config.from_object(config_class)

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    CORS(app, supports_credentials=True)

    # Connect to MongoDB
    client = MongoClient(app.config["MONGO_URI"], serverSelectionTimeoutMS=5000)
    db_name = None
    try:
        default_db = client.get_default_database()
        db_name = default_db.name
    except Exception:
        db_name = "interview_ai"

    app.mongo_client = client
    app.db = client[db_name or "interview_ai"]

    # Ensure helpful indexes (non-blocking if MongoDB is temporarily offline at import)
    try:
        app.db.users.create_index([("email", ASCENDING)], unique=True)
        app.db.interviews.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
        app.db.support_messages.create_index([("user_id", ASCENDING), ("created_at", DESCENDING)])
    except Exception as exc:
        logging.getLogger(__name__).warning("Could not ensure MongoDB indexes on startup: %s", exc)

    # Register Blueprints
    app.register_blueprint(auth_bp)
    app.register_blueprint(dashboard_bp)
    app.register_blueprint(interview_bp)
    app.register_blueprint(profile_bp)

    @app.context_processor
    def inject_current_user():
        user = get_current_user()
        return {"current_user": serialize_user(user) if user else None}

    @app.errorhandler(413)
    def file_too_large(_err):
        return jsonify({"error": "Uploaded file is too large (max 5 MB)."}), 413

    @app.errorhandler(404)
    def not_found(_err):
        if request.path.startswith("/api/"):
            return jsonify({"error": "Endpoint not found."}), 404
        return redirect(url_for("dashboard.dashboard_page"))

    return app


app = create_app()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=app.config["PORT"], debug=app.config["DEBUG"])
