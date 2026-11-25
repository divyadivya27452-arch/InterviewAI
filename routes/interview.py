"""
Interview Session, Evaluation, Feedback & History Blueprint for Interview AI.
"""

import math
import re
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List

from bson import ObjectId
from flask import Blueprint, current_app, jsonify, render_template, request
from routes.auth import get_current_user, login_required
from services.evaluator import SKILL_KEYS, evaluate_interview
from services.question_bank import (
    LEVEL_OPTIONS,
    QUESTION_COUNT_OPTIONS,
    ROLE_OPTIONS,
    TYPE_OPTIONS,
    get_questions,
)

interview_bp = Blueprint("interview", __name__)


def _iso(dt: Any) -> str:
    if isinstance(dt, datetime):
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.isoformat()
    return str(dt or "")


def _serialize_interview_full(doc: Dict[str, Any], previous_skills: Dict[str, float] = None) -> Dict[str, Any]:
    return {
        "id": str(doc["_id"]),
        "role": doc.get("role", ""),
        "level": doc.get("level", ""),
        "type": doc.get("type", ""),
        "total_questions": doc.get("total_questions", 0),
        "questions": doc.get("questions", []),
        "overall_score": round(float(doc.get("overall_score", 0)), 1),
        "skill_scores": doc.get("skill_scores", {}),
        "skills_improved": doc.get("skills_improved", []),
        "previous_skill_scores": previous_skills or {},
        "evaluation_mode": doc.get("evaluation_mode", "rule-based"),
        "duration_seconds": int(doc.get("duration_seconds", 0) or 0),
        "status": doc.get("status", "In Progress"),
        "created_at": _iso(doc.get("created_at")),
        "completed_at": _iso(doc.get("completed_at")),
    }


def _strip_question_secrets(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return questions to the client during an active interview without ideal answers."""
    return [
        {
            "index": q.get("index", i),
            "question": q.get("question", ""),
            "category": q.get("category", "Technical"),
            "answer": q.get("answer", ""),
            "skipped": bool(q.get("skipped", False)),
            "time_spent_seconds": int(q.get("time_spent_seconds", 0) or 0),
        }
        for i, q in enumerate(questions)
    ]


# ---------------------------------------------------------------------------
# Page Routes
# ---------------------------------------------------------------------------
@interview_bp.route("/interview", methods=["GET"])
@login_required
def interview_page():
    return render_template(
        "interview.html",
        active_page="interview",
        page_title="AI Interview",
        roles=ROLE_OPTIONS,
        levels=LEVEL_OPTIONS,
        types=TYPE_OPTIONS,
        counts=QUESTION_COUNT_OPTIONS,
    )


@interview_bp.route("/history", methods=["GET"])
@login_required
def history_page():
    return render_template(
        "history.html",
        active_page="history",
        page_title="Interview History",
        roles=ROLE_OPTIONS,
        levels=LEVEL_OPTIONS,
        types=TYPE_OPTIONS,
    )


@interview_bp.route("/feedback", methods=["GET"])
@interview_bp.route("/feedback/<interview_id>", methods=["GET"])
@login_required
def feedback_page(interview_id: str = ""):
    if not interview_id:
        interview_id = request.args.get("id", "")
    return render_template(
        "feedback.html",
        active_page="feedback",
        page_title="AI Feedback",
        interview_id=interview_id,
    )


# ---------------------------------------------------------------------------
# JSON API Routes
# ---------------------------------------------------------------------------
@interview_bp.route("/api/interview/start", methods=["POST"])
@login_required
def api_interview_start():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    role = (data.get("role") or "").strip()
    level = (data.get("level") or "").strip()
    q_type = (data.get("type") or "").strip()
    try:
        total_questions = int(data.get("total_questions", 5))
    except (TypeError, ValueError):
        total_questions = 0

    if role not in ROLE_OPTIONS:
        return jsonify({"error": "Invalid job role selected."}), 400
    if level not in LEVEL_OPTIONS:
        return jsonify({"error": "Invalid difficulty level selected."}), 400
    if q_type not in TYPE_OPTIONS:
        return jsonify({"error": "Invalid question type selected."}), 400
    if total_questions not in QUESTION_COUNT_OPTIONS:
        return jsonify({"error": "Number of questions must be 5, 10, or 20."}), 400

    questions = get_questions(role=role, q_type=q_type, level=level, count=total_questions)
    now = datetime.now(timezone.utc)

    interview_doc = {
        "user_id": user["_id"],
        "role": role,
        "level": level,
        "type": q_type,
        "total_questions": len(questions),
        "questions": questions,
        "overall_score": 0.0,
        "skill_scores": {},
        "skills_improved": [],
        "duration_seconds": 0,
        "status": "In Progress",
        "created_at": now,
        "completed_at": None,
    }

    result = current_app.db.interviews.insert_one(interview_doc)

    return jsonify({
        "interview_id": str(result.inserted_id),
        "role": role,
        "level": level,
        "type": q_type,
        "total_questions": len(questions),
        "questions": _strip_question_secrets(questions),
    }), 201


@interview_bp.route("/api/interview/answer", methods=["POST"])
@login_required
def api_interview_answer():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    interview_id = (data.get("interview_id") or "").strip()
    if not ObjectId.is_valid(interview_id):
        return jsonify({"error": "Invalid interview ID."}), 400

    try:
        question_index = int(data.get("question_index"))
    except (TypeError, ValueError):
        return jsonify({"error": "Invalid question index."}), 400

    answer = (data.get("answer") or "").strip()
    skipped = bool(data.get("skipped", False))
    try:
        time_spent = max(0, int(data.get("time_spent_seconds", 0) or 0))
    except (TypeError, ValueError):
        time_spent = 0
    try:
        total_duration = max(0, int(data.get("duration_seconds", 0) or 0))
    except (TypeError, ValueError):
        total_duration = 0

    interview = current_app.db.interviews.find_one({
        "_id": ObjectId(interview_id),
        "user_id": user["_id"],
    })
    if not interview:
        return jsonify({"error": "Interview not found."}), 404
    if interview.get("status") == "Completed":
        return jsonify({"error": "This interview is already completed."}), 400

    questions = interview.get("questions", [])
    if question_index < 0 or question_index >= len(questions):
        return jsonify({"error": "Question index out of range."}), 400

    update_fields = {
        f"questions.{question_index}.answer": "" if skipped else answer,
        f"questions.{question_index}.skipped": skipped,
        f"questions.{question_index}.time_spent_seconds": time_spent,
    }
    if total_duration > 0:
        update_fields["duration_seconds"] = total_duration

    current_app.db.interviews.update_one(
        {"_id": interview["_id"]},
        {"$set": update_fields},
    )

    return jsonify({"message": "Answer saved.", "question_index": question_index}), 200


@interview_bp.route("/api/interview/finish", methods=["POST"])
@login_required
def api_interview_finish():
    user = get_current_user()
    data = request.get_json(silent=True) or {}

    interview_id = (data.get("interview_id") or "").strip()
    if not ObjectId.is_valid(interview_id):
        return jsonify({"error": "Invalid interview ID."}), 400

    interview = current_app.db.interviews.find_one({
        "_id": ObjectId(interview_id),
        "user_id": user["_id"],
    })
    if not interview:
        return jsonify({"error": "Interview not found."}), 404

    if interview.get("status") == "Completed":
        return jsonify(_serialize_interview_full(interview)), 200

    # Merge any final answers included in the finish payload
    final_answers = data.get("answers")
    questions = interview.get("questions", [])
    if isinstance(final_answers, list):
        for item in final_answers:
            if not isinstance(item, dict):
                continue
            idx = item.get("question_index")
            if isinstance(idx, int) and 0 <= idx < len(questions):
                skipped = bool(item.get("skipped", False))
                ans_text = "" if skipped else (item.get("answer") or "").strip()
                questions[idx]["answer"] = ans_text
                questions[idx]["skipped"] = skipped
                if "time_spent_seconds" in item:
                    questions[idx]["time_spent_seconds"] = max(0, int(item.get("time_spent_seconds") or 0))
        interview["questions"] = questions

    try:
        duration_seconds = max(0, int(data.get("duration_seconds", interview.get("duration_seconds", 0)) or 0))
    except (TypeError, ValueError):
        duration_seconds = int(interview.get("duration_seconds", 0) or 0)

    # Evaluate answers (Gemini if configured, otherwise rule-based)
    evaluation = evaluate_interview(interview)
    new_skills = evaluation["skill_scores"]

    # Compare with previous completed interviews to mark skills improved
    prior_completed = list(
        current_app.db.interviews.find({
            "user_id": user["_id"],
            "status": "Completed",
            "_id": {"$ne": interview["_id"]},
        }).sort("created_at", -1)
    )

    previous_skills: Dict[str, float] = {}
    skills_improved: List[str] = []
    if prior_completed:
        # Compare against the user's most recent previous completed interview
        prev_doc = prior_completed[0]
        previous_skills = prev_doc.get("skill_scores") or {}
        for skill in SKILL_KEYS:
            if float(new_skills.get(skill, 0)) > float(previous_skills.get(skill, 0)):
                skills_improved.append(skill)

    completed_at = datetime.now(timezone.utc)
    update_doc = {
        "questions": evaluation["questions"],
        "overall_score": evaluation["overall_score"],
        "skill_scores": new_skills,
        "skills_improved": skills_improved,
        "evaluation_mode": evaluation["evaluation_mode"],
        "duration_seconds": duration_seconds,
        "status": "Completed",
        "completed_at": completed_at,
    }

    current_app.db.interviews.update_one(
        {"_id": interview["_id"]},
        {"$set": update_doc},
    )

    interview.update(update_doc)
    return jsonify(_serialize_interview_full(interview, previous_skills=previous_skills)), 200


@interview_bp.route("/api/interviews", methods=["GET"])
@login_required
def api_list_interviews():
    user = get_current_user()
    query: Dict[str, Any] = {"user_id": user["_id"]}

    search = (request.args.get("search") or "").strip()
    role = (request.args.get("role") or "").strip()
    q_type = (request.args.get("type") or "").strip()
    level = (request.args.get("level") or "").strip()
    status = (request.args.get("status") or "").strip()
    date_from = (request.args.get("date_from") or "").strip()
    date_to = (request.args.get("date_to") or "").strip()

    if role:
        query["role"] = role
    if q_type:
        query["type"] = q_type
    if level:
        query["level"] = level
    if status:
        query["status"] = status

    if search:
        safe_pattern = re.escape(search)
        query["$or"] = [
            {"role": {"$regex": safe_pattern, "$options": "i"}},
            {"type": {"$regex": safe_pattern, "$options": "i"}},
            {"level": {"$regex": safe_pattern, "$options": "i"}},
            {"status": {"$regex": safe_pattern, "$options": "i"}},
        ]

    date_filter: Dict[str, datetime] = {}
    if date_from:
        try:
            dt_from = datetime.strptime(date_from, "%Y-%m-%d").replace(tzinfo=timezone.utc)
            date_filter["$gte"] = dt_from
        except ValueError:
            pass
    if date_to:
        try:
            dt_to = datetime.strptime(date_to, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
            date_filter["$lt"] = dt_to
        except ValueError:
            pass
    if date_filter:
        query["created_at"] = date_filter

    try:
        page = max(1, int(request.args.get("page", 1)))
    except ValueError:
        page = 1
    try:
        limit = min(50, max(1, int(request.args.get("limit", 10))))
    except ValueError:
        limit = 10

    col = current_app.db.interviews
    total = col.count_documents(query)
    total_pages = max(1, math.ceil(total / limit))
    if page > total_pages:
        page = total_pages

    skip = (page - 1) * limit
    docs = list(col.find(query).sort("created_at", -1).skip(skip).limit(limit))

    items = [
        {
            "id": str(doc["_id"]),
            "date": _iso(doc.get("created_at")),
            "role": doc.get("role", ""),
            "type": doc.get("type", ""),
            "level": doc.get("level", ""),
            "total_questions": doc.get("total_questions", 0),
            "score": round(float(doc.get("overall_score", 0)), 1) if doc.get("status") == "Completed" else None,
            "status": doc.get("status", "In Progress"),
            "duration_seconds": int(doc.get("duration_seconds", 0) or 0),
        }
        for doc in docs
    ]

    return jsonify({
        "interviews": items,
        "total": total,
        "page": page,
        "limit": limit,
        "total_pages": total_pages,
    }), 200


@interview_bp.route("/api/interviews/<interview_id>", methods=["GET"])
@login_required
def api_get_interview(interview_id: str):
    user = get_current_user()
    col = current_app.db.interviews

    if interview_id == "latest":
        doc = col.find_one(
            {"user_id": user["_id"], "status": "Completed"},
            sort=[("created_at", -1)],
        )
        if not doc:
            return jsonify({"error": "No completed interviews found yet."}), 404
    else:
        if not ObjectId.is_valid(interview_id):
            return jsonify({"error": "Invalid interview ID."}), 400
        doc = col.find_one({"_id": ObjectId(interview_id), "user_id": user["_id"]})
        if not doc:
            return jsonify({"error": "Interview not found."}), 404

    # If client requests resume view for In Progress interview, strip secrets
    if doc.get("status") != "Completed" and request.args.get("mode") == "resume":
        return jsonify({
            "id": str(doc["_id"]),
            "role": doc.get("role", ""),
            "level": doc.get("level", ""),
            "type": doc.get("type", ""),
            "total_questions": doc.get("total_questions", 0),
            "duration_seconds": int(doc.get("duration_seconds", 0) or 0),
            "status": doc.get("status", "In Progress"),
            "questions": _strip_question_secrets(doc.get("questions", [])),
        }), 200

    # Find immediate prior completed interview for skill comparison
    prior_doc = col.find_one(
        {
            "user_id": user["_id"],
            "status": "Completed",
            "_id": {"$ne": doc["_id"]},
            "created_at": {"$lt": doc.get("created_at")},
        },
        sort=[("created_at", -1)],
    )
    previous_skills = (prior_doc.get("skill_scores") or {}) if prior_doc else {}

    return jsonify(_serialize_interview_full(doc, previous_skills=previous_skills)), 200


@interview_bp.route("/api/interviews/<interview_id>", methods=["DELETE"])
@login_required
def api_delete_interview(interview_id: str):
    user = get_current_user()
    if not ObjectId.is_valid(interview_id):
        return jsonify({"error": "Invalid interview ID."}), 400

    result = current_app.db.interviews.delete_one({
        "_id": ObjectId(interview_id),
        "user_id": user["_id"],
    })
    if result.deleted_count == 0:
        return jsonify({"error": "Interview record not found."}), 404

    return jsonify({"message": "Interview record deleted."}), 200
