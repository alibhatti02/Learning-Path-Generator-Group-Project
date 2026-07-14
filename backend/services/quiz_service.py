import json
import os
import requests
from services.ai_service import azure_chat_json
from services.database import get_db

# Local Ollama handles quizzes by default (free, low latency); Azure OpenAI is the
# automatic fallback when Ollama is unreachable — e.g. on an Azure deployment with no local model.
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
QUIZ_MODEL = os.getenv("QUIZ_MODEL", "qwen3.5:9b")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "120"))

PASS_THRESHOLD = 0.6  # fraction of total points needed to pass


def _call_ollama(system_prompt: str, user_prompt: str) -> dict:
    response = requests.post(
        f"{OLLAMA_HOST}/api/chat",
        json={
            "model": QUIZ_MODEL,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "format": "json",
            "stream": False,
        },
        timeout=OLLAMA_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return json.loads(response.json()["message"]["content"])


def _call_azure(system_prompt: str, user_prompt: str) -> dict:
    return azure_chat_json([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])


def _call_llm(system_prompt: str, user_prompt: str) -> dict:
    """Routes to Ollama first, falls back to Azure OpenAI. Raises RuntimeError if both fail."""
    try:
        return _call_ollama(system_prompt, user_prompt)
    except Exception as ollama_err:
        print(f"⚠️ Ollama ({QUIZ_MODEL}) unavailable, falling back to Azure OpenAI: {ollama_err}")
        try:
            return _call_azure(system_prompt, user_prompt)
        except Exception as azure_err:
            raise RuntimeError(
                f"Both quiz models failed. Ollama: {ollama_err} | Azure: {azure_err}"
            )


def generate_quiz(user_id: int, milestone: str, week_number: int, group_id: int | None = None) -> dict:
    """
    Generates 3 multiple-choice + 2 open-ended questions for a weekly milestone,
    persists them (answers included) as a quiz_attempts row, and returns the
    questions with correct answers stripped out so they never reach the client.
    """
    system_prompt = (
        "You are a quiz author for a technical learning platform. "
        "Respond ONLY with a valid JSON object, no markdown fences, matching exactly:\n"
        "{\n"
        '  "questions": [\n'
        '    {"question_number": 1, "type": "multiple_choice", "question": "...", '
        '"options": ["...", "...", "...", "..."], "correct_answer": "..."},\n'
        '    {"question_number": 4, "type": "open_ended", "question": "..."}\n'
        "  ]\n"
        "}\n"
        "Rules: exactly 5 questions — questions 1-3 are type multiple_choice with exactly 4 options "
        "each and a correct_answer that is copied verbatim from the options; questions 4-5 are type "
        "open_ended with no options field. Questions must test practical understanding, not trivia."
    )
    user_prompt = (
        f"Write a quiz for week {week_number} of a learning path. "
        f"The milestone being tested is: '{milestone}'."
    )

    data = _call_llm(system_prompt, user_prompt)
    questions = data.get("questions", [])
    if len(questions) != 5:
        raise RuntimeError(f"Model returned {len(questions)} questions instead of 5.")

    # Normalize numbering so the frontend's answer map lines up regardless of model quirks
    for i, q in enumerate(questions, start=1):
        q["question_number"] = i

    # Stripping and persist
    quiz_id = create_attempt(user_id, milestone, week_number, group_id, questions)
    public = [{k: v for k, v in q.items() if k != "correct_answer"} for q in questions]
    return {"quiz_id": quiz_id, "week_number": week_number, "milestone": milestone, "questions": public}


def grade_quiz(user_id: int, quiz_id: int, answers: list[dict]) -> dict:
    """
    Grades a stored quiz attempt. Loads the questions (with answers) the server
    saved at generation time — the client never supplies them — then grades MCQs
    deterministically and open-ended answers via the LLM. Locks the attempt after
    the first successful grade so scores can't be re-fished.
    """
    attempt = get_attempt(user_id, quiz_id)
    if attempt is None:
        raise ValueError("Quiz not found.")
    if attempt["status"] == "graded":
        raise ValueError("This quiz has already been submitted.")

    milestone = attempt["milestone"]
    week_number = attempt["week_number"]
    questions = json.loads(attempt["questions_json"])

    answer_map = {a["question_number"]: a.get("answer", "") for a in answers}
    feedback: list[dict] = []
    open_ended: list[dict] = []
    score = 0

    for q in questions:
        num = q.get("question_number")
        given = str(answer_map.get(num, "")).strip()

        if q.get("type") == "multiple_choice":
            correct_answer = str(q.get("correct_answer", "")).strip()
            is_correct = given.lower() == correct_answer.lower()
            score += 1 if is_correct else 0
            feedback.append({
                "question_number": num,
                "correct": is_correct,
                "explanation": (
                    f"Correct — '{correct_answer}' is the right answer."
                    if is_correct
                    else f"Not quite. The correct answer is '{correct_answer}'."
                ),
            })
        else:
            open_ended.append({"question_number": num, "question": q.get("question", ""), "answer": given})

    graded_open = _grade_open_ended(milestone, open_ended) if open_ended else []
    for item in graded_open:
        score += 1 if item.get("correct") else 0
        feedback.append(item)

    feedback.sort(key=lambda f: f["question_number"])
    total = len(questions)
    passed = total > 0 and (score / total) >= PASS_THRESHOLD

    # Persist the score and lock the attempt only after grading fully succeeds —
    # if the open-ended LLM call raised above, the attempt stays 'pending' and retryable.
    _mark_graded(quiz_id, score, total)

    return {
        "quiz_id": quiz_id,
        "week_number": week_number,
        "score": score,
        "total": total,
        "passed": passed,
        "feedback": feedback,
        "overall_feedback": _overall_feedback(score, total, passed),
    }


def _grade_open_ended(milestone: str, submissions: list[dict]) -> list[dict]:
    system_prompt = (
        "You are a fair, encouraging grader for a technical learning platform. "
        "Respond ONLY with a valid JSON object, no markdown fences, matching exactly:\n"
        '{"feedback": [{"question_number": 4, "correct": true, "explanation": "..."}]}\n'
        "Rules: mark an answer correct if it demonstrates genuine understanding of the concept, even "
        "if imperfectly worded. Mark it incorrect if it is blank, off-topic, or fundamentally wrong. "
        "Each explanation is 1-3 sentences telling the learner what was right or what to review."
    )
    user_prompt = (
        f"The milestone being tested is: '{milestone}'. Grade these open-ended answers:\n"
        f"{json.dumps(submissions, indent=2)}"
    )

    data = _call_llm(system_prompt, user_prompt)
    graded = data.get("feedback", [])

    # If the model dropped a question, count it as ungraded-but-wrong rather than crashing
    graded_nums = {g.get("question_number") for g in graded}
    for sub in submissions:
        if sub["question_number"] not in graded_nums:
            graded.append({
                "question_number": sub["question_number"],
                "correct": False,
                "explanation": "This answer could not be graded automatically — review the topic and retry.",
            })
    return graded


def _overall_feedback(score: int, total: int, passed: bool) -> str:
    if total == 0:
        return "No questions were submitted for grading."
    ratio = score / total
    if ratio == 1:
        return "Perfect score — you've clearly mastered this milestone. On to the next week!"
    if passed:
        return "Solid work — you passed this milestone. Review the missed questions before moving on."
    return "You haven't quite got this milestone yet. Revisit this week's resources and try again."


def create_attempt(user_id, milestone, week_number, group_id, questions) -> int:
    """Stores a freshly generated quiz (answers included) and returns its id."""
    with get_db() as conn:
        cur = conn.execute(
            """
            INSERT INTO quiz_attempts (user_id, group_id, milestone, week_number, questions_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (user_id, group_id, milestone, week_number, json.dumps(questions)),
        )
        return cur.lastrowid


def get_attempt(user_id, quiz_id) -> dict | None:
    """Loads an attempt scoped to its owner — user_id in the WHERE clause blocks
    reading anyone else's quiz. Returns None if it doesn't exist or isn't theirs."""
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM quiz_attempts WHERE id = ? AND user_id = ?", (quiz_id, user_id)
        ).fetchone()
    return dict(row) if row else None


def _mark_graded(quiz_id, score, total) -> None:
    with get_db() as conn:
        conn.execute(
            "UPDATE quiz_attempts SET score = ?, total = ?, status = 'graded' WHERE id = ?",
            (score, total, quiz_id),
        )