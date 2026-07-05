from fastapi import APIRouter, Depends, HTTPException

from services.auth_service import get_current_user
from services.path_service import delete_path, get_path, list_paths

router = APIRouter(prefix="/paths", tags=["paths"])


@router.get("")
def get_sessions(user: dict = Depends(get_current_user)) -> list[dict]:
    return list_paths(user["id"])


@router.get("/{path_id}")
def get_session(path_id: int, user: dict = Depends(get_current_user)) -> dict:
    record = get_path(user["id"], path_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Learning path not found.")
    return record


@router.delete("/{path_id}")
def delete_session(path_id: int, user: dict = Depends(get_current_user)) -> dict:
    if not delete_path(user["id"], path_id):
        raise HTTPException(status_code=404, detail="Learning path not found.")
    return {"deleted": path_id}
