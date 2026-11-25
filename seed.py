"""
Seed script for Interview AI.

Populates MongoDB with a demo user and realistic sample interviews across
multiple roles, difficulty levels, and question types so the Dashboard,
Performance Analytics, History, and Feedback views are immediately rich.

Usage:
    python seed.py          # Creates demo user & sample data if not already present
    python seed.py --reset  # Clears existing demo user's interviews and re-seeds
"""

import argparse
from datetime import datetime, timedelta, timezone

import bcrypt
from pymongo import MongoClient

from config import Config
from services.evaluator import SKILL_KEYS, evaluate_rule_based
from services.question_bank import get_questions

DEMO_EMAIL = "demo@interviewai.com"
DEMO_PASSWORD = "DemoUser123!"

SAMPLE_ANSWERS_HIGH = (
    "In practice, I approach this by breaking down the core requirements first and clarifying any constraints. "
    "For example, when handling scalability, latency, and maintainability trade-offs, I combine clean architecture "
    "with proper validation, automated testing, and monitoring. This ensures reliable performance and clear outcomes."
)

SAMPLE_ANSWERS_MEDIUM = (
    "I have used this concept in my recent projects because it improves structure and reliability. "
    "Specifically, I focus on writing modular code, handling edge cases, and verifying results with tests."
)

SAMPLE_ANSWERS_BASIC = (
    "I think this is mainly used to organize data and make applications work better, though I would review "
    "the exact implementation details and documentation for advanced edge cases."
)


def _craft_answer(keywords, quality: str) -> str:
    kw_phrase = ", ".join(keywords[:4]) if keywords else "core principles"
    if quality == "high":
        return (
            f"To address this effectively, it is important to understand {kw_phrase}. "
            f"{SAMPLE_ANSWERS_HIGH} Because of these trade-offs, applying {kw_phrase} systematically leads to measurable results."
        )
    if quality == "medium":
        return (
            f"This relies heavily on {kw_phrase}. {SAMPLE_ANSWERS_MEDIUM}"
        )
    return f"It involves {keywords[0] if keywords else 'this topic'}. {SAMPLE_ANSWERS_BASIC}"


def seed(reset: bool = False) -> None:
    client = MongoClient(Config.MONGO_URI, serverSelectionTimeoutMS=5000)
    try:
        db = client.get_default_database()
    except Exception:
        db = client["interview_ai"]

    users_col = db.users
    interviews_col = db.interviews

    existing_user = users_col.find_one({"email": DEMO_EMAIL})
    if existing_user and not reset:
        existing_count = interviews_col.count_documents({"user_id": existing_user["_id"]})
        if existing_count > 0:
            print(f"Demo user ({DEMO_EMAIL}) already exists with {existing_count} interviews. Use --reset to re-seed.")
            return

    if not existing_user:
        pw_hash = bcrypt.hashpw(DEMO_PASSWORD.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")
        user_doc = {
            "name": "Alex Morgan",
            "email": DEMO_EMAIL,
            "password_hash": pw_hash,
            "phone": "+1 555-019-2834",
            "college": "Pacific Institute of Technology",
            "target_role": "Full Stack Developer",
            "photo": "/static/img/default-avatar.svg",
            "created_at": datetime.now(timezone.utc) - timedelta(days=25),
        }
        res = users_col.insert_one(user_doc)
        user_id = res.inserted_id
        print(f"Created demo user: {DEMO_EMAIL} / {DEMO_PASSWORD}")
    else:
        user_id = existing_user["_id"]
        if reset:
            interviews_col.delete_many({"user_id": user_id})
            print(f"Cleared existing interviews for {DEMO_EMAIL}.")

    now = datetime.now(timezone.utc)

    # Chronological progression showing clear improvement across attempts
    specs = [
        {"days_ago": 20, "role": "Web Developer", "level": "Beginner", "type": "Technical", "count": 5, "quality": "basic", "duration": 420, "status": "Completed"},
        {"days_ago": 17, "role": "Python Developer", "level": "Beginner", "type": "HR", "count": 5, "quality": "medium", "duration": 390, "status": "Completed"},
        {"days_ago": 14, "role": "Data Analyst", "level": "Intermediate", "type": "Mixed", "count": 5, "quality": "medium", "duration": 540, "status": "Completed"},
        {"days_ago": 10, "role": "Full Stack Developer", "level": "Intermediate", "type": "Technical", "count": 5, "quality": "medium", "duration": 610, "status": "Completed"},
        {"days_ago": 7, "role": "Software Developer", "level": "Intermediate", "type": "Mixed", "count": 10, "quality": "high", "duration": 1080, "status": "Completed"},
        {"days_ago": 4, "role": "AI/ML Engineer", "level": "Advanced", "type": "Technical", "count": 5, "quality": "high", "duration": 720, "status": "Completed"},
        {"days_ago": 2, "role": "Full Stack Developer", "level": "Advanced", "type": "Mixed", "count": 5, "quality": "high", "duration": 690, "status": "Completed"},
        {"days_ago": 0, "role": "Python Developer", "level": "Intermediate", "type": "Mixed", "count": 5, "quality": "partial", "duration": 180, "status": "In Progress"},
    ]

    prev_skills = {}
    inserted = 0

    for spec in specs:
        created_at = now - timedelta(days=spec["days_ago"], hours=2)
        questions = get_questions(spec["role"], spec["type"], spec["level"], spec["count"])

        if spec["status"] == "In Progress":
            # Answer first 2 questions so user can resume seamlessly
            for idx in range(2):
                questions[idx]["answer"] = _craft_answer(questions[idx]["keywords"], "medium")
                questions[idx]["time_spent_seconds"] = 75
            doc = {
                "user_id": user_id,
                "role": spec["role"],
                "level": spec["level"],
                "type": spec["type"],
                "total_questions": spec["count"],
                "questions": questions,
                "overall_score": 0.0,
                "skill_scores": {},
                "skills_improved": [],
                "duration_seconds": spec["duration"],
                "status": "In Progress",
                "created_at": created_at,
                "completed_at": None,
            }
            interviews_col.insert_one(doc)
            inserted += 1
            continue

        for idx, q in enumerate(questions):
            # Vary quality slightly across questions for realistic score spreads
            q_quality = spec["quality"]
            if spec["quality"] == "medium" and idx == len(questions) - 1:
                q_quality = "high"
            q["answer"] = _craft_answer(q["keywords"], q_quality)
            q["time_spent_seconds"] = max(45, spec["duration"] // spec["count"])

        temp_interview = {
            "role": spec["role"],
            "level": spec["level"],
            "type": spec["type"],
            "questions": questions,
        }
        evaluated = evaluate_rule_based(temp_interview)
        new_skills = evaluated["skill_scores"]

        skills_improved = []
        if prev_skills:
            skills_improved = [
                s for s in SKILL_KEYS
                if float(new_skills.get(s, 0)) > float(prev_skills.get(s, 0))
            ]
        prev_skills = new_skills

        doc = {
            "user_id": user_id,
            "role": spec["role"],
            "level": spec["level"],
            "type": spec["type"],
            "total_questions": spec["count"],
            "questions": evaluated["questions"],
            "overall_score": evaluated["overall_score"],
            "skill_scores": new_skills,
            "skills_improved": skills_improved,
            "evaluation_mode": "rule-based",
            "duration_seconds": spec["duration"],
            "status": "Completed",
            "created_at": created_at,
            "completed_at": created_at + timedelta(seconds=spec["duration"]),
        }
        interviews_col.insert_one(doc)
        inserted += 1

    print(f"Seeded {inserted} sample interviews for {DEMO_EMAIL}.")
    print("Login credentials:")
    print(f"  Email:    {DEMO_EMAIL}")
    print(f"  Password: {DEMO_PASSWORD}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed demo user and sample interviews into MongoDB.")
    parser.add_argument("--reset", action="store_true", help="Clear existing demo user interviews before seeding.")
    args = parser.parse_args()
    seed(reset=args.reset)
