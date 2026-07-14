from fastapi import APIRouter, Depends, HTTPException

from models.schemas import QuizGenerateRequest, QuizSubmitRequest
from services.auth_service import get_current_user
from services.quiz_service import generate_quiz, grade_quiz

router = APIRouter(prefix="/quiz", tags=["quiz"])


@router.post("/generate")
def create_quiz(request: QuizGenerateRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        return generate_quiz(user["id"], request.milestone, request.week_number, request.group_id)
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Quiz generation failed: {e}")


@router.post("/submit")
def submit_quiz(request: QuizSubmitRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        return grade_quiz(user["id"], request.quiz_id, [a.model_dump() for a in request.answers])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=f"Quiz grading failed: {e}")
