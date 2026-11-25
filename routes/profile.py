"""
User Profile & Account Settings Blueprint for Interview AI.
"""

import os
import re
import uuid

import bcrypt
from flask import Blueprint, current_app, jsonify, render_template, request, session
from routes.auth import EMAIL_REGEX, get_current_user, login_required, serialize_user
from services.question_bank import ROLE_OPTIONS

profile_bp = Blueprint("profile", __name__)


def _allowed_file(filename: str) -> bool:
    if "." not in filename:
        return False
    ext = filename.rsplit(".", 1)[1].lower()
    return ext in current_app.config["ALLOWED_EXTENSIONS"]


# ---------------------------------------------------------------------------
# Page Route
# ---------------------------------------------------------------------------
@profile_bp.route("/profile", methods=["GET"])
@login_required
def profile_page():
    return render_template(
        "profile.html",
        active_page="profile",
        page_title="My Profile Settings",
        roles=ROLE_OPTIONS,
    )


# ---------------------------------------------------------------------------
# JSON API Routes
# ---------------------------------------------------------------------------
@profile_bp.route("/api/profile", methods=["GET"])
@login_required
def api_get_profile():
    user = get_current_user()
    return jsonify({"user": serialize_user(user)}), 200


@profile_bp.route("/api/profile", methods=["PUT"])
@login_required
def api_update_profile():
    user = get_current_user()
    users = current_app.db.users

    if request.content_type and "multipart/form-data" in request.content_type:
        name = (request.form.get("name") or "").strip()
        email = (request.form.get("email") or "").strip().lower()
        phone = (request.form.get("phone") or "").strip()
        college = (request.form.get("college") or "").strip()
        target_role = (request.form.get("target_role") or "").strip()
        photo_file = request.files.get("photo")
    else:
        data = request.get_json(silent=True) or {}
        name = (data.get("name") or "").strip()
        email = (data.get("email") or "").strip().lower()
        phone = (data.get("phone") or "").strip()
        college = (data.get("college") or "").strip()
        target_role = (data.get("target_role") or "").strip()
        photo_file = None

    if len(name) < 2:
        return jsonify({"error": "Name must be at least 2 characters."}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Please enter a valid email address."}), 400
    if phone and not re.match(r"^[0-9+\-\s()]{7,20}$", phone):
        return jsonify({"error": "Please enter a valid phone number."}), 400

    # Ensure email uniqueness if changed
    if email != user.get("email"):
        existing = users.find_one({"email": email, "_id": {"$ne": user["_id"]}})
        if existing:
            return jsonify({"error": "That email is already associated with another account."}), 409

    updates = {
        "name": name,
        "email": email,
        "phone": phone,
        "college": college,
        "target_role": target_role or "Software Developer",
    }

    if photo_file and photo_file.filename:
        if not _allowed_file(photo_file.filename):
            return jsonify({"error": "Allowed photo formats: png, jpg, jpeg, gif, webp."}), 400

        ext = photo_file.filename.rsplit(".", 1)[1].lower()
        filename = f"{user['_id']}_{uuid.uuid4().hex[:8]}.{ext}"
        upload_dir = current_app.config["UPLOAD_FOLDER"]
        os.makedirs(upload_dir, exist_ok=True)
        save_path = os.path.join(upload_dir, filename)
        photo_file.save(save_path)
        updates["photo"] = f"/static/uploads/{filename}"

    users.update_one({"_id": user["_id"]}, {"$set": updates})
    updated_user = users.find_one({"_id": user["_id"]})

    return jsonify({
        "message": "Profile updated successfully.",
        "user": serialize_user(updated_user),
    }), 200


@profile_bp.route("/api/profile/password", methods=["PUT"])
@login_required
def api_update_password():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    old_password = data.get("old_password") or ""
    new_password = data.get("new_password") or ""
    confirm_password = data.get("confirm_password") or ""

    if not old_password or not new_password or not confirm_password:
        return jsonify({"error": "All password fields are required."}), 400

    stored_hash = user.get("password_hash", "")
    if isinstance(stored_hash, str):
        stored_hash = stored_hash.encode("utf-8")

    if not bcrypt.checkpw(old_password.encode("utf-8"), stored_hash):
        return jsonify({"error": "Current password is incorrect."}), 400

    if len(new_password) < 6:
        return jsonify({"error": "New password must be at least 6 characters."}), 400
    if new_password != confirm_password:
        return jsonify({"error": "New passwords do not match."}), 400
    if old_password == new_password:
        return jsonify({"error": "New password must be different from your current password."}), 400

    new_hash = bcrypt.hashpw(new_password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
    current_app.db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"password_hash": new_hash}},
    )

    return jsonify({"message": "Password changed successfully."}), 200


@profile_bp.route("/api/profile", methods=["DELETE"])
@login_required
def api_delete_account():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    password = data.get("password") or ""

    # Verify password if provided (required from UI modal for safety)
    if password:
        stored_hash = user.get("password_hash", "")
        if isinstance(stored_hash, str):
            stored_hash = stored_hash.encode("utf-8")
        if not bcrypt.checkpw(password.encode("utf-8"), stored_hash):
            return jsonify({"error": "Password verification failed."}), 400

    uid = user["_id"]
    current_app.db.interviews.delete_many({"user_id": uid})
    current_app.db.support_messages.delete_many({"user_id": uid})
    current_app.db.users.delete_one({"_id": uid})
    session.clear()

    return jsonify({"message": "Your account and all associated data have been permanently deleted."}), 200
