"""
Dashboard, Performance Analytics, and Support Blueprint for Interview AI.
"""

from collections import Counter, defaultdict
from datetime import datetime, timezone
from typing import Any, Dict, List

from flask import Blueprint, current_app, jsonify, redirect, render_template, request, url_for
from routes.auth import get_current_user, login_required
from services.evaluator import SKILL_KEYS

dashboard_bp = Blueprint("dashboard", __name__)


def _format_duration(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds or 0))
    hours = total_seconds // 3600
    minutes = (total_seconds % 3600) // 60
    if hours > 0:
        return f"{hours}h {minutes}m"
    if minutes > 0:
        return f"{minutes}m"
    return f"{total_seconds}s" if total_seconds > 0 else "0m"


def _iso_date(dt: Any) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt or "")


def _short_date_label(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.strftime("%b %d")
    return ""


def _compute_improved_skills(completed_docs: List[Dict[str, Any]]) -> List[str]:
    """
    Compare the user's latest completed interview skill scores against their
    earliest completed interview (baseline) to identify improved skills.
    """
    if len(completed_docs) < 2:
        return []

    # completed_docs sorted oldest -> newest
    baseline = completed_docs[0].get("skill_scores") or {}
    latest = completed_docs[-1].get("skill_scores") or {}
    improved = [
        skill for skill in SKILL_KEYS
        if float(latest.get(skill, 0)) > float(baseline.get(skill, 0))
    ]
    return improved


# ---------------------------------------------------------------------------
# Page Routes
# ---------------------------------------------------------------------------
@dashboard_bp.route("/", methods=["GET"])
@login_required
def index():
    return redirect(url_for("dashboard.dashboard_page"))


@dashboard_bp.route("/dashboard", methods=["GET"])
@login_required
def dashboard_page():
    return render_template("dashboard.html", active_page="dashboard", page_title="Dashboard")


@dashboard_bp.route("/performance", methods=["GET"])
@login_required
def performance_page():
    return render_template("performance.html", active_page="performance", page_title="Performance Analytics")


@dashboard_bp.route("/help", methods=["GET"])
@login_required
def help_page():
    return render_template("help.html", active_page="help", page_title="Help & Support")


# ---------------------------------------------------------------------------
# JSON API Routes
# ---------------------------------------------------------------------------
@dashboard_bp.route("/api/dashboard/stats", methods=["GET"])
@login_required
def api_dashboard_stats():
    user = get_current_user()
    interviews = list(
        current_app.db.interviews.find({"user_id": user["_id"]}).sort("created_at", 1)
    )

    total_interviews = len(interviews)
    completed = [doc for doc in interviews if doc.get("status") == "Completed"]
    completed_count = len(completed)

    if completed_count > 0:
        avg_score = round(sum(float(doc.get("overall_score", 0)) for doc in completed) / completed_count, 1)
    else:
        avg_score = 0.0

    improved_skills = _compute_improved_skills(completed)
    total_seconds = sum(int(doc.get("duration_seconds", 0) or 0) for doc in interviews)

    return jsonify({
        "total_interviews": total_interviews,
        "completed_interviews": completed_count,
        "average_score": avg_score,
        "skills_improved": len(improved_skills),
        "improved_skill_names": improved_skills,
        "practice_time_seconds": total_seconds,
        "practice_time_formatted": _format_duration(total_seconds),
    }), 200


@dashboard_bp.route("/api/dashboard/performance", methods=["GET"])
@login_required
def api_dashboard_performance():
    user = get_current_user()
    docs = list(
        current_app.db.interviews.find(
            {"user_id": user["_id"], "status": "Completed"}
        )
        .sort("created_at", -1)
        .limit(10)
    )
    docs.reverse()  # Chronological order (oldest -> newest of the last 10)

    items = [
        {
            "id": str(doc["_id"]),
            "date": _iso_date(doc.get("created_at")),
            "label": _short_date_label(doc.get("created_at")),
            "score": round(float(doc.get("overall_score", 0)), 1),
            "role": doc.get("role", ""),
            "type": doc.get("type", ""),
            "level": doc.get("level", ""),
        }
        for doc in docs
    ]
    return jsonify({"items": items}), 200


@dashboard_bp.route("/api/dashboard/recent", methods=["GET"])
@login_required
def api_dashboard_recent():
    user = get_current_user()
    docs = list(
        current_app.db.interviews.find({"user_id": user["_id"]})
        .sort("created_at", -1)
        .limit(8)
    )

    recent = [
        {
            "id": str(doc["_id"]),
            "date": _iso_date(doc.get("created_at")),
            "role": doc.get("role", ""),
            "type": doc.get("type", ""),
            "level": doc.get("level", ""),
            "total_questions": doc.get("total_questions", 0),
            "score": round(float(doc.get("overall_score", 0)), 1) if doc.get("status") == "Completed" else None,
            "status": doc.get("status", "In Progress"),
        }
        for doc in docs
    ]
    return jsonify({"interviews": recent}), 200


@dashboard_bp.route("/api/performance", methods=["GET"])
@login_required
def api_performance():
    user = get_current_user()
    completed = list(
        current_app.db.interviews.find(
            {"user_id": user["_id"], "status": "Completed"}
        ).sort("created_at", 1)
    )

    if not completed:
        return jsonify({
            "summary": {
                "best_score": None,
                "lowest_score": None,
                "average_score": 0,
                "most_practiced_role": None,
                "total_completed": 0,
            },
            "score_trend": [],
            "skill_averages": {k: 0 for k in SKILL_KEYS},
            "by_role": [],
            "by_type": [],
            "by_level": [],
        }), 200

    scores = [float(doc.get("overall_score", 0)) for doc in completed]
    roles_counter = Counter(doc.get("role", "Other") for doc in completed)
    most_practiced_role = roles_counter.most_common(1)[0][0]

    skill_sums = defaultdict(float)
    skill_counts = defaultdict(int)
    role_scores = defaultdict(list)
    type_scores = defaultdict(list)
    level_scores = defaultdict(list)

    score_trend = []
    for doc in completed:
        s = round(float(doc.get("overall_score", 0)), 1)
        score_trend.append({
            "id": str(doc["_id"]),
            "date": _iso_date(doc.get("created_at")),
            "label": _short_date_label(doc.get("created_at")),
            "score": s,
            "role": doc.get("role", ""),
            "type": doc.get("type", ""),
            "level": doc.get("level", ""),
        })
        role_scores[doc.get("role", "Other")].append(s)
        type_scores[doc.get("type", "Mixed")].append(s)
        level_scores[doc.get("level", "Intermediate")].append(s)

        ss = doc.get("skill_scores") or {}
        for k in SKILL_KEYS:
            if k in ss:
                skill_sums[k] += float(ss[k])
                skill_counts[k] += 1

    skill_averages = {
        k: round(skill_sums[k] / skill_counts[k], 1) if skill_counts[k] else 0.0
        for k in SKILL_KEYS
    }

    by_role = [
        {"role": k, "average_score": round(sum(v) / len(v), 1), "count": len(v)}
        for k, v in role_scores.items()
    ]
    by_type = [
        {"type": k, "average_score": round(sum(v) / len(v), 1), "count": len(v)}
        for k, v in type_scores.items()
    ]
    level_order = ["Beginner", "Intermediate", "Advanced"]
    by_level = [
        {
            "level": lvl,
            "average_score": round(sum(level_scores[lvl]) / len(level_scores[lvl]), 1) if level_scores[lvl] else 0,
            "count": len(level_scores[lvl]),
        }
        for lvl in level_order
        if level_scores[lvl]
    ]

    return jsonify({
        "summary": {
            "best_score": round(max(scores), 1),
            "lowest_score": round(min(scores), 1),
            "average_score": round(sum(scores) / len(scores), 1),
            "most_practiced_role": most_practiced_role,
            "total_completed": len(completed),
        },
        "score_trend": score_trend,
        "skill_averages": skill_averages,
        "by_role": by_role,
        "by_type": by_type,
        "by_level": by_level,
    }), 200


@dashboard_bp.route("/api/support", methods=["POST"])
@login_required
def api_support():
    user = get_current_user()
    data = request.get_json(silent=True) or {}
    subject = (data.get("subject") or "").strip()
    message = (data.get("message") or "").strip()

    if len(subject) < 3:
        return jsonify({"error": "Subject must be at least 3 characters."}), 400
    if len(message) < 10:
        return jsonify({"error": "Please provide a detailed message (at least 10 characters)."}), 400

    doc = {
        "user_id": user["_id"],
        "subject": subject,
        "message": message,
        "created_at": datetime.now(timezone.utc),
    }
    result = current_app.db.support_messages.insert_one(doc)
    return jsonify({
        "message": "Your support message has been sent. We'll respond shortly.",
        "id": str(result.inserted_id),
    }), 201
