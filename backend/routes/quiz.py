from fastapi import APIRouter, Depends, HTTPException, Request

from models.schemas import QuizGenerateRequest, QuizSubmitRequest
from services.auth_service import get_current_user
from services.quiz_service import generate_quiz, grade_quiz
from services.rate_limit import AI_QUIZ_GEN_LIMIT, AI_QUIZ_SUBMIT_LIMIT, limiter, user_or_ip_key

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate")
@limiter.limit(AI_QUIZ_GEN_LIMIT, key_func=user_or_ip_key)
def create_quiz(request: Request, payload: QuizGenerateRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        return generate_quiz(user["id"], payload.milestone, payload.week_number, payload.group_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Quiz generation failed: {e}")


@router.post("/submit")
@limiter.limit(AI_QUIZ_SUBMIT_LIMIT, key_func=user_or_ip_key)
def submit_quiz(request: Request, payload: QuizSubmitRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        return grade_quiz(user["id"], payload.quiz_id, [a.model_dump() for a in payload.answers])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Quiz grading failed: {e}")
