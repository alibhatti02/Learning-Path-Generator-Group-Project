from fastapi import APIRouter, Depends, HTTPException, Request

from models.schemas import (
    GroupCreateRequest,
    GroupJoinRequest,
    SetHoursRequest,
    WeekCompleteRequest,
)
from services.auth_service import get_current_user
from services.rate_limit import AI_ROADMAP_LIMIT, limiter, user_or_ip_key
from services.group_service import (
    complete_week,
    create_group,
    delete_group,
    get_leaderboard,
    get_my_membership,
    join_group,
    leave_group,
    list_my_groups,
    set_hours,
)

router = APIRouter(prefix="/groups", tags=["groups"])


@router.post("", status_code=201)
def create(request: GroupCreateRequest, user: dict = Depends(get_current_user)) -> dict:
    return create_group(user["id"], request.name, request.skill_topic, request.experience_level)


@router.get("")
def list_mine(user: dict = Depends(get_current_user)) -> list[dict]:
    return list_my_groups(user["id"])


@router.post("/join")
def join(request: GroupJoinRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        return join_group(user["id"], request.invite_code)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{group_id}/hours")
@limiter.limit(AI_ROADMAP_LIMIT, key_func=user_or_ip_key)
def set_my_hours(group_id: int, request: Request, payload: SetHoursRequest, user: dict = Depends(get_current_user)) -> dict:
    """Private endpoint — sets MY hours and generates MY roadmap. No other member ever sees this call happen."""
    try:
        return set_hours(user["id"], group_id, payload.hourly_commitment)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{group_id}/me")
def my_membership(group_id: int, user: dict = Depends(get_current_user)) -> dict:
    """Private view of MY own pace/hours/roadmap. Never call this to build another member's view."""
    try:
        return get_my_membership(user["id"], group_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{group_id}/complete-week")
def complete(group_id: int, request: WeekCompleteRequest, user: dict = Depends(get_current_user)) -> dict:
    try:
        return complete_week(
            user["id"], group_id, request.quiz_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{group_id}/leaderboard")
def leaderboard(group_id: int, user: dict = Depends(get_current_user)) -> dict:
    """Public leaderboard — ranks and points only. Hours are never included in this response."""
    try:
        return get_leaderboard(user["id"], group_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))


@router.post("/{group_id}/leave", status_code=204)
def leave(group_id: int, user: dict = Depends(get_current_user)) -> None:
    """Removes the caller from the group. The creator can't leave — see delete instead."""
    try:
        leave_group(user["id"], group_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{group_id}", status_code=204)
def delete(group_id: int, user: dict = Depends(get_current_user)) -> None:
    """Deletes the group entirely. Creator-only."""
    try:
        delete_group(user["id"], group_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))