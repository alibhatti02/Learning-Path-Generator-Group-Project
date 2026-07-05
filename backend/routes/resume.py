from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from services.auth_service import get_current_user
from services.resume_service import analyze_resume

router = APIRouter(prefix="/resume", tags=["resume"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # resumes have no business being bigger than 5MB


@router.post("/analyze")
async def analyze(file: UploadFile = File(...), user: dict = Depends(get_current_user)) -> dict:
    content = await file.read()

    if len(content) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="File too large — keep resumes under 5MB.")
    if not content:
        raise HTTPException(status_code=400, detail="The uploaded file is empty.")

    try:
        return analyze_resume(file.filename or "", content)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except RuntimeError as e:
        raise HTTPException(status_code=503, detail=str(e))
