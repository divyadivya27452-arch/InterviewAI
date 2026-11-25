"""
Authentication Blueprint & Session/JWT Helpers for Interview AI.
"""

import re
from datetime import datetime, timedelta, timezone
from functools import wraps
from typing import Any, Dict, Optional

import bcrypt
import jwt
from bson import ObjectId
from flask import (
    Blueprint,
    current_app,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")


def serialize_user(user_doc: Dict[str, Any]) -> Dict[str, Any]:
    """Return a safe public representation of a user document."""
    created_at = user_doc.get("created_at")
    return {
        "id": str(user_doc["_id"]),
        "name": user_doc.get("name", ""),
        "email": user_doc.get("email", ""),
        "phone": user_doc.get("phone", ""),
        "college": user_doc.get("college", ""),
        "target_role": user_doc.get("target_role", "Software Developer"),
        "photo": user_doc.get("photo") or "/static/img/default-avatar.svg",
        "created_at": created_at.isoformat() if isinstance(created_at, datetime) else str(created_at or ""),
    }


def _create_jwt(user_id: str) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "iat": now,
        "exp": now + timedelta(hours=current_app.config["JWT_EXPIRY_HOURS"]),
    }
    return jwt.encode(
        payload,
        current_app.config["SECRET_KEY"],
        algorithm=current_app.config["JWT_ALGORITHM"],
    )


def get_current_user() -> Optional[Dict[str, Any]]:
    """
    Resolve the authenticated user from Flask session or Bearer JWT header.
    Caches result on flask.g for the duration of the request.
    """
    if hasattr(g, "_cached_user"):
        return g._cached_user

    user_id = session.get("user_id")

    if not user_id:
        auth_header = request.headers.get("Authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header.split(" ", 1)[1].strip()
            try:
                decoded = jwt.decode(
                    token,
                    current_app.config["SECRET_KEY"],
                    algorithms=[current_app.config["JWT_ALGORITHM"]],
                )
                user_id = decoded.get("sub")
            except jwt.PyJWTError:
                user_id = None

    user_doc = None
    if user_id and ObjectId.is_valid(user_id):
        user_doc = current_app.db.users.find_one({"_id": ObjectId(user_id)})

    g._cached_user = user_doc
    return user_doc


def login_required(view_func):
    """
    Protect both HTML page routes (redirect to /login) and /api/* routes (401 JSON).
    """

    @wraps(view_func)
    def wrapped(*args, **kwargs):
        user = get_current_user()
        if not user:
            if request.path.startswith("/api/"):
                return jsonify({"error": "Authentication required. Please log in."}), 401
            return redirect(url_for("auth.login_page"))
        return view_func(*args, **kwargs)

    return wrapped


# ---------------------------------------------------------------------------
# Page Routes
# ---------------------------------------------------------------------------
@auth_bp.route("/login", methods=["GET"])
def login_page():
    if get_current_user():
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("login.html")


@auth_bp.route("/register", methods=["GET"])
def register_page():
    if get_current_user():
        return redirect(url_for("dashboard.dashboard_page"))
    return render_template("register.html")


@auth_bp.route("/logout", methods=["GET"])
def logout():
    session.clear()
    return redirect(url_for("auth.login_page"))


# ---------------------------------------------------------------------------
# JSON API Routes
# ---------------------------------------------------------------------------
@auth_bp.route("/api/register", methods=["POST"])
def api_register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    confirm_password = data.get("confirm_password") or ""

    if len(name) < 2:
        return jsonify({"error": "Full name must be at least 2 characters."}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"error": "Password must be at least 6 characters long."}), 400
    if password != confirm_password:
        return jsonify({"error": "Passwords do not match."}), 400

    users = current_app.db.users
    if users.find_one({"email": email}):
        return jsonify({"error": "An account with this email already exists."}), 409

    password_hash = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    new_user = {
        "name": name,
        "email": email,
        "password_hash": password_hash,
        "phone": "",
        "college": "",
        "target_role": "Software Developer",
        "photo": "/static/img/default-avatar.svg",
        "created_at": datetime.now(timezone.utc),
    }

    result = users.insert_one(new_user)
    new_user["_id"] = result.inserted_id

    session.clear()
    session.permanent = True
    session["user_id"] = str(result.inserted_id)

    token = _create_jwt(str(result.inserted_id))
    return jsonify({
        "message": "Account created successfully.",
        "token": token,
        "user": serialize_user(new_user),
    }), 201


@auth_bp.route("/api/login", methods=["POST"])
def api_login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"error": "Email and password are required."}), 400

    user = current_app.db.users.find_one({"email": email})
    if not user:
        return jsonify({"error": "Invalid email or password."}), 401

    stored_hash = user.get("password_hash", "")
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
        return jsonify({"error": "Invalid email or password."}), 401

    session.clear()
    session.permanent = True
    session["user_id"] = str(user["_id"])

    token = _create_jwt(str(user["_id"]))
    return jsonify({
        "message": "Logged in successfully.",
        "token": token,
        "user": serialize_user(user),
    }), 200
