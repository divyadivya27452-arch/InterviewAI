"""
Answer Evaluation Service for Interview AI.

Provides:
1. A comprehensive rule-based evaluator (keyword match, answer length/depth,
   structure/clarity, reasoning/STAR signals, and confidence).
2. Optional Google Gemini REST API evaluation when GEMINI_API_KEY is configured,
   with automatic fallback to the rule-based evaluator on error or missing key.
"""

import json
import logging
import re
from typing import Any, Dict, List, Tuple

import requests
from config import Config

logger = logging.getLogger(__name__)

SKILL_KEYS = [
    "Communication",
    "Technical Knowledge",
    "Confidence",
    "Problem Solving",
]

REASONING_MARKERS = {
    "because", "therefore", "since", "however", "whereas", "although",
    "for example", "for instance", "such as", "specifically", "trade-off",
    "tradeoff", "advantage", "disadvantage", "complexity", "latency",
    "scalability", "situation", "task", "action", "result", "outcome",
    "first", "second", "finally", "alternatively", "in contrast", "prevents",
    "ensures", "allows", "reduces", "improves",
}

HEDGING_PHRASES = {
    "i guess", "not sure", "don't know", "dont know", "idk", "maybe",
    "probably wrong", "no idea", "skip", "pass", "forgot",
}


def _tokenize(text: str) -> List[str]:
    return re.findall(r"[a-z0-9_+#.-]+", text.lower())


def _level_target_words(level: str) -> int:
    if level == "Beginner":
        return 35
    if level == "Advanced":
        return 65
    return 50


def _evaluate_single_rule_based(q_item: Dict[str, Any], level: str) -> Tuple[int, Dict[str, Any], Dict[str, float]]:
    """
    Evaluate one question-answer pair with deterministic rule-based heuristics.
    Returns (question_score, feedback_dict, component_skills_dict).
    """
    question_text = q_item.get("question", "")
    answer = (q_item.get("answer") or "").strip()
    keywords = q_item.get("keywords") or []
    ideal_answer = q_item.get("ideal_answer", "")
    category = q_item.get("category", "Technical")
    skipped = bool(q_item.get("skipped", False))

    lower_ans = answer.lower()
    words = _tokenize(answer)
    word_count = len(words)
    sentences = [s.strip() for s in re.split(r"[.!?]+", answer) if s.strip()]

    # Handle skipped or essentially empty answers
    if skipped or word_count < 3 or lower_ans in {"na", "n/a", "none", "idk", "skip", "-"}:
        feedback = {
            "strengths": ["Kept interview momentum moving forward."],
            "weaknesses": ["Question was skipped or answered with too little detail to evaluate."],
            "improvements": [
                f"Review core concepts around {', '.join(keywords[:3]) or 'this topic'} and structure a 3–5 sentence response."
            ],
            "ideal_answer": ideal_answer,
        }
        skills = {
            "Communication": 15.0,
            "Technical Knowledge": 10.0,
            "Confidence": 10.0,
            "Problem Solving": 12.0,
        }
        return 0, feedback, skills

    # 1. Keyword Coverage (0 - 40 pts)
    matched_kw = []
    missing_kw = []
    for kw in keywords:
        kw_lower = kw.lower()
        # Match phrase or primary stem (first 5 chars for longer words)
        if kw_lower in lower_ans or (len(kw_lower) >= 6 and kw_lower[:5] in lower_ans):
            matched_kw.append(kw)
        else:
            missing_kw.append(kw)

    kw_ratio = (len(matched_kw) / len(keywords)) if keywords else 0.5
    # Saturate nicely: hitting >= 65% of expected keywords yields near full keyword credit
    kw_score = min(1.0, kw_ratio / 0.65) * 40.0

    # 2. Length & Depth (0 - 25 pts)
    target_words = _level_target_words(level)
    length_ratio = min(1.0, word_count / target_words)
    length_score = length_ratio * 25.0

    # 3. Structure & Clarity (0 - 20 pts)
    structure_pts = 0.0
    if len(sentences) >= 2:
        structure_pts += 8.0
    elif word_count >= 18:
        structure_pts += 4.0

    if len(sentences) >= 3:
        structure_pts += 4.0

    avg_words_per_sentence = word_count / max(1, len(sentences))
    if 8 <= avg_words_per_sentence <= 32:
        structure_pts += 4.0
    else:
        structure_pts += 2.0

    # Check punctuation / capitalization polish
    if any(ch in answer for ch in (".", ",", ";", ":")):
        structure_pts += 4.0
    structure_score = min(20.0, structure_pts)

    # 4. Reasoning, Examples & Confidence (0 - 15 pts)
    reasoning_hits = sum(1 for m in REASONING_MARKERS if m in lower_ans)
    hedge_hits = sum(1 for h in HEDGING_PHRASES if h in lower_ans)
    reasoning_score = min(15.0, reasoning_hits * 4.5 + 3.0)
    confidence_penalty = min(12.0, hedge_hits * 6.0)

    raw_score = kw_score + length_score + structure_score + reasoning_score - confidence_penalty
    # Floor non-trivial honest attempts at 22, cap at 98 for rule-based realism
    q_score = int(round(max(18.0, min(98.0, raw_score))))

    # Derive per-question skill signals
    comm_score = max(25.0, min(98.0, (length_score / 25.0) * 45.0 + (structure_score / 20.0) * 45.0 + 10.0))
    tech_score = max(18.0, min(98.0, (kw_score / 40.0) * 75.0 + (length_score / 25.0) * 20.0 + 5.0))
    conf_score = max(20.0, min(98.0, 55.0 + (length_ratio * 35.0) - (hedge_hits * 15.0) + (5.0 if matched_kw else 0.0)))
    prob_score = max(20.0, min(98.0, (reasoning_score / 15.0) * 55.0 + (kw_score / 40.0) * 35.0 + 10.0))

    if category == "HR":
        # For HR questions, Technical Knowledge reflects domain/process awareness blended with communication
        tech_score = round(0.6 * tech_score + 0.4 * comm_score, 1)

    # Build thoughtful strengths / weaknesses / improvements
    strengths: List[str] = []
    weaknesses: List[str] = []
    improvements: List[str] = []

    if matched_kw:
        strengths.append(f"Addressed key concepts including {', '.join(matched_kw[:3])}.")
    if word_count >= target_words * 0.85:
        strengths.append("Provided thorough detail and well-developed explanation.")
    if reasoning_hits >= 2:
        strengths.append("Included strong reasoning, examples, or cause-and-effect framing.")
    if len(sentences) >= 3 and not strengths:
        strengths.append("Structured the response across clear sentences.")
    if not strengths:
        strengths.append("Attempted the question directly and stayed on topic.")

    if word_count < target_words * 0.55:
        weaknesses.append(f"Response is brief ({word_count} words); {level}-level interviews benefit from deeper elaboration.")
    if len(missing_kw) > len(matched_kw) and missing_kw:
        weaknesses.append(f"Missed important terms/aspects such as {', '.join(missing_kw[:3])}.")
    if reasoning_hits == 0:
        weaknesses.append("Lacked a concrete example, trade-off, or 'why' explanation.")
    if hedge_hits > 0:
        weaknesses.append("Phrasing sounded uncertain; avoid hedging phrases when stating what you know.")
    if not weaknesses:
        weaknesses.append("Could further sharpen precision by quantifying impact or edge cases.")

    if missing_kw:
        improvements.append(f"Explicitly weave in concepts like {', '.join(missing_kw[:3])} to strengthen completeness.")
    if category == "HR":
        improvements.append("Use the STAR framework (Situation, Task, Action, Result) with a measurable outcome.")
    else:
        improvements.append("Include a brief real-world example or trade-off to demonstrate applied understanding.")
    if len(sentences) < 2:
        improvements.append("Break your explanation into 3–4 clear sentences: definition, how it works, and when to use it.")

    feedback = {
        "strengths": strengths[:3],
        "weaknesses": weaknesses[:3],
        "improvements": improvements[:3],
        "ideal_answer": ideal_answer,
    }

    skills = {
        "Communication": round(comm_score, 1),
        "Technical Knowledge": round(tech_score, 1),
        "Confidence": round(conf_score, 1),
        "Problem Solving": round(prob_score, 1),
    }

    return q_score, feedback, skills


def evaluate_rule_based(interview: Dict[str, Any]) -> Dict[str, Any]:
    """Evaluate an entire interview using deterministic rule-based scoring."""
    questions = interview.get("questions", [])
    level = interview.get("level", "Intermediate")

    evaluated_questions: List[Dict[str, Any]] = []
    skill_totals = {k: 0.0 for k in SKILL_KEYS}
    score_sum = 0

    for q_item in questions:
        q_score, feedback, q_skills = _evaluate_single_rule_based(q_item, level)
        updated_q = dict(q_item)
        updated_q["score"] = q_score
        updated_q["feedback"] = feedback
        evaluated_questions.append(updated_q)
        score_sum += q_score
        for k in SKILL_KEYS:
            skill_totals[k] += q_skills[k]

    n = max(1, len(evaluated_questions))
    overall_score = round(score_sum / n, 1)
    skill_scores = {k: round(skill_totals[k] / n, 1) for k in SKILL_KEYS}

    return {
        "overall_score": overall_score,
        "skill_scores": skill_scores,
        "questions": evaluated_questions,
        "evaluation_mode": "rule-based",
    }


def _evaluate_with_gemini(interview: Dict[str, Any], api_key: str) -> Dict[str, Any]:
    """
    Evaluate all answers in a single Gemini API call returning structured JSON.
    Raises an exception on HTTP/parsing errors so caller falls back cleanly.
    """
    questions = interview.get("questions", [])
    role = interview.get("role", "Software Developer")
    level = interview.get("level", "Intermediate")
    q_type = interview.get("type", "Mixed")

    qa_payload = [
        {
            "index": q.get("index", i),
            "category": q.get("category", "Technical"),
            "question": q.get("question", ""),
            "expected_keywords": q.get("keywords", []),
            "reference_hint": q.get("ideal_answer", ""),
            "candidate_answer": "" if q.get("skipped") else (q.get("answer") or ""),
            "skipped": bool(q.get("skipped", False)),
        }
        for i, q in enumerate(questions)
    ]

    prompt = (
        f"You are an expert technical & HR interviewer evaluating a {level} {role} "
        f"({q_type}) mock interview.\n"
        "Evaluate EVERY item in the JSON array below strictly and constructively. "
        "If candidate_answer is empty or skipped is true, assign score 0.\n\n"
        "Return ONLY valid JSON matching this exact schema (no markdown fences):\n"
        "{\n"
        '  "overall_score": <number 0-100>,\n'
        '  "skill_scores": {\n'
        '    "Communication": <number 0-100>,\n'
        '    "Technical Knowledge": <number 0-100>,\n'
        '    "Confidence": <number 0-100>,\n'
        '    "Problem Solving": <number 0-100>\n'
        "  },\n"
        '  "evaluations": [\n'
        "    {\n"
        '      "index": <int>,\n'
        '      "score": <int 0-100>,\n'
        '      "strengths": [<1-3 short strings>],\n'
        '      "weaknesses": [<1-3 short strings>],\n'
        '      "improvements": [<1-3 short strings>],\n'
        '      "ideal_answer": "<concise 2-3 sentence model answer>"\n'
        "    }\n"
        "  ]\n"
        "}\n\n"
        f"Interview Q&A:\n{json.dumps(qa_payload, ensure_ascii=False)}"
    )

    model = Config.GEMINI_MODEL or "gemini-2.0-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "temperature": 0.3,
            "responseMimeType": "application/json",
        },
    }

    resp = requests.post(url, json=payload, timeout=25)
    resp.raise_for_status()
    data = resp.json()

    raw_text = data["candidates"][0]["content"]["parts"][0]["text"].strip()
    # Strip markdown code fences if present
    raw_text = re.sub(r"^```(?:json)?\s*|\s*```$", "", raw_text, flags=re.MULTILINE).strip()
    parsed = json.loads(raw_text)

    eval_map = {item["index"]: item for item in parsed.get("evaluations", []) if "index" in item}
    if len(eval_map) != len(questions):
        raise ValueError("Gemini evaluation count mismatch")

    evaluated_questions = []
    for i, q_item in enumerate(questions):
        idx = q_item.get("index", i)
        ev = eval_map[idx]
        updated_q = dict(q_item)
        score = int(round(max(0, min(100, float(ev.get("score", 0))))))
        if updated_q.get("skipped") or not (updated_q.get("answer") or "").strip():
            score = 0
        updated_q["score"] = score
        updated_q["feedback"] = {
            "strengths": ev.get("strengths") or ["Attempted the question."],
            "weaknesses": ev.get("weaknesses") or ["Could expand further."],
            "improvements": ev.get("improvements") or ["Include concrete examples."],
            "ideal_answer": ev.get("ideal_answer") or q_item.get("ideal_answer", ""),
        }
        evaluated_questions.append(updated_q)

    raw_skills = parsed.get("skill_scores", {})
    skill_scores = {
        k: round(max(0.0, min(100.0, float(raw_skills.get(k, 50.0)))), 1)
        for k in SKILL_KEYS
    }
    overall_score = round(
        sum(q["score"] for q in evaluated_questions) / max(1, len(evaluated_questions)),
        1,
    )

    return {
        "overall_score": overall_score,
        "skill_scores": skill_scores,
        "questions": evaluated_questions,
        "evaluation_mode": "gemini",
    }


def evaluate_interview(interview: Dict[str, Any]) -> Dict[str, Any]:
    """
    Evaluate an interview using Gemini API if GEMINI_API_KEY is configured,
    otherwise fall back seamlessly to the rule-based evaluator.
    """
    api_key = Config.GEMINI_API_KEY
    if api_key:
        try:
            return _evaluate_with_gemini(interview, api_key)
        except Exception as exc:
            logger.warning("Gemini evaluation failed, falling back to rule-based evaluator: %s", exc)

    return evaluate_rule_based(interview)
